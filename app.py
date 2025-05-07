import os
import io
import numpy as np
from PIL import Image
import tempfile
import threading
import time
import pickle
from flask import Flask, request, render_template, jsonify, send_from_directory
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.models import Model
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
FOLDER_ID = '11kFOF8p4wGf7V0-rQvXUes_XfE5LtjCZ'  # Root folder ID

# Global variables
drive_service = None
vgg_model = None
vectors = []
file_ids = []
file_names = []
webViewLinks = []
indexing_status = {"status": "idle", "message": "", "progress": 0, "total": 0}
lock = threading.Lock()  # Thread lock for global variables

def setup_services():
    global drive_service
    try:
        credentials = service_account.Credentials.from_service_account_file(
            'service-account-key.json',
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        drive_service = build('drive', 'v3', credentials=credentials)
        logging.info("Google Drive API initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing Google Drive API: {e}")
        return str(e)

def load_vgg_model():
    global vgg_model
    try:
        vgg16_model = VGG16(weights="imagenet")
        vgg_model = Model(inputs=vgg16_model.inputs, outputs=vgg16_model.get_layer("fc1").output)
        logging.info("VGG16 model loaded successfully")
    except Exception as e:
        logging.error(f"Error loading VGG16 model: {e}")
        return str(e)

def image_preprocess(img):
    img = img.resize((224, 224))
    img = img.convert("RGB")
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    return x

def extract_vector(image_path):
    try:
        img = Image.open(image_path)
        img_tensor = image_preprocess(img)
        vector = vgg_model.predict(img_tensor, verbose=0)[0]
        vector = vector / np.linalg.norm(vector)
        return vector
    except Exception as e:
        logging.error(f"Error extracting vector: {e}")
        raise e

def list_all_png_files(folder_id, path_prefix=""):
    all_files = []
    query = f"'{folder_id}' in parents and (mimeType='application/vnd.google-apps.folder' or mimeType='image/png') and trashed=false"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name, mimeType, webViewLink)",
        pageSize=1000
    ).execute()
    items = results.get('files', [])
    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            subfolder_name = item['name']
            subfolder_path = f"{path_prefix}/{subfolder_name}" if path_prefix else subfolder_name
            logging.info(f"Processing subfolder: {subfolder_path}")
            subfolder_files = list_all_png_files(item['id'], subfolder_path)
            all_files.extend(subfolder_files)
        else:
            item_path = f"{path_prefix}/{item['name']}" if path_prefix else item['name']
            all_files.append({
                'id': item['id'],
                'name': item_path,
                'webViewLink': item.get('webViewLink', '')
            })
    return all_files

def index_google_drive_thread():
    global vectors, file_ids, file_names, webViewLinks, indexing_status
    start_time = time.time()
    try:
        if vgg_model is None:
            load_vgg_model()
        indexing_status["status"] = "running"
        indexing_status["message"] = "Fetching PNG files from Google Drive..."
        drive_files = list_all_png_files(FOLDER_ID)
        if not drive_files:
            indexing_status["status"] = "error"
            indexing_status["message"] = "No PNG files found in the specifiedfolder or its subfolders"
            return
        total_files = len(drive_files)
        indexing_status["total"] = total_files
        indexing_status["message"] = f"Indexing {total_files} PNG files..."
        vectors = []
        file_ids = []
        file_names = []
        webViewLinks = []
        for i, file in enumerate(drive_files):
            indexing_status["progress"] = i + 1
            update_interval = max(1, total_files // 20)
            if i % update_interval == 0 or i == total_files - 1:
                indexing_status["message"] = f"Processing file {i+1}/{total_files}: {file['name']}"
            try:
                file_id = file['id']
                file_name = file['name']
                webViewLink = file.get('webViewLink', '')
                request = drive_service.files().get_media(fileId=file_id)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                    fh = io.FileIO(tmp_file.name, 'wb')
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    fh.close()
                    try:
                        vector = extract_vector(tmp_file.name)
                        with lock:
                            vectors.append(vector)
                            file_ids.append(file_id)
                            file_names.append(file_name)
                            webViewLinks.append(webViewLink)
                    except Exception as e:
                        logging.error(f"Error extracting vector for {file_name}: {e}")
                    os.unlink(tmp_file.name)
            except Exception as e:
                logging.error(f"Error processing file {file.get('name')}: {e}")
                continue
        with lock:
            vectors = np.array(vectors)
        try:
            with open('vectors.pkl', 'wb') as f:
                pickle.dump(vectors, f)
            with open('file_ids.pkl', 'wb') as f:
                pickle.dump(file_ids, f)
            with open('file_names.pkl', 'wb') as f:
                pickle.dump(file_names, f)
            with open('webViewLinks.pkl', 'wb') as f:
                pickle.dump(webViewLinks, f)
            logging.info("Vectors and paths saved to disk")
        except Exception as e:
            logging.error(f"Error saving vectors and paths: {e}")
        elapsed_time = time.time() - start_time
        indexing_status["status"] = "complete"
        indexing_status["message"] = f"Indexing complete! {len(vectors)} files indexed in {elapsed_time:.2f} seconds"
    except Exception as e:
        logging.error(f"Error during indexing: {str(e)}")
        indexing_status["status"] = "error"
        indexing_status["message"] = f"Error during indexing: {str(e)}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/index_drive", methods=["POST"])
def index_drive():
    global indexing_status
    with lock:
        if indexing_status["status"] == "running":
            return jsonify({"error": "Indexing is already in progress"})
        indexing_status = {"status": "idle", "message": "Starting indexing...", "progress": 0, "total": 0}
    threading.Thread(target=index_google_drive_thread, daemon=True).start()
    return jsonify({"message": "Indexing started"})

@app.route("/index_status")
def index_status():
    with lock:
        return jsonify(indexing_status)

@app.route("/upload_image", methods=["POST"])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No image selected"}), 400
    try:
        img = Image.open(file)
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img.save(filepath, format="PNG")
        width, height = img.size
        return jsonify({
            "filename": filename,
            "name": file.filename,
            "size": f"{width}x{height} pixels",
            "format": img.format or "PNG"
        })
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        return jsonify({"error": f"Error processing image: {str(e)}"}), 500

@app.route("/search", methods=["POST"])
def search():
    if not os.path.exists('vectors.pkl'):
        logging.error("vectors.pkl not found")
        return jsonify({"error": "Please index Google Drive first"}), 400
    filename = request.form.get('filename')
    sensitivity = float(request.form.get('sensitivity', 0.4))
    if not filename:
        logging.error("No filename provided")
        return jsonify({"error": "No image provided"}), 400
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(image_path):
        logging.error(f"Image not found at {image_path}")
        return jsonify({"error": "Image not found"}), 400
    try:
        # Load vectors and related data safely
        with lock:
            local_vectors = []
            local_file_ids = []
            local_file_names = []
            local_webViewLinks = []
            try:
                with open('vectors.pkl', 'rb') as f:
                    local_vectors = pickle.load(f)
                with open('file_ids.pkl', 'rb') as f:
                    local_file_ids = pickle.load(f)
                with open('file_names.pkl', 'rb') as f:
                    local_file_names = pickle.load(f)
                with open('webViewLinks.pkl', 'rb') as f:
                    local_webViewLinks = pickle.load(f)
                logging.info("Vectors and paths loaded from disk")
            except Exception as e:
                logging.error(f"Error loading vectors and paths: {str(e)}")
                return jsonify({"error": "Failed to load indexed data. Please re-index Google Drive."}), 500

        # Check if vectors is valid
        if not isinstance(local_vectors, np.ndarray) or local_vectors.size == 0:
            logging.error("Invalid or empty vectors array")
            return jsonify({"error": "No indexed vectors available. Please index Google Drive."}), 400

        if vgg_model is None:
            load_vgg_model()

        start_time = time.time()
        query_vector = extract_vector(image_path)
        logging.info(f"Query vector shape: {query_vector.shape}, Vectors shape: {local_vectors.shape}")

        # Ensure shapes are compatible
        if query_vector.shape[0] != local_vectors.shape[1]:
            logging.error(f"Shape mismatch: query_vector {query_vector.shape}, vectors {local_vectors.shape}")
            return jsonify({"error": "Vector shape mismatch. Please re-index Google Drive."}), 500

        # Calculate distances
        distances = np.linalg.norm(local_vectors - query_vector, axis=1)
        logging.info(f"Distances shape: {distances.shape}, min: {distances.min()}, max: {distances.max()}")

        max_distance = sensitivity
        close_indices = np.where(distances < max_distance)[0]
        matches = []
        if close_indices.size > 0:
            # Sort indices by distance
            sorted_indices = close_indices[np.argsort(distances[close_indices])]
            matches = [{
                'id': local_file_ids[idx],
                'name': local_file_names[idx],
                'link': local_webViewLinks[idx],
                'score': float(1.0 - distances[idx])  # Convert to float for JSON serialization
            } for idx in sorted_indices[:10]]
            logging.info(f"Found {len(matches)} matches with sensitivity {max_distance}")
        else:
            # Fallback: get top 10 closest
            K = min(10, len(distances))
            sorted_indices = np.argsort(distances)[:K]
            matches = [{
                'id': local_file_ids[idx],
                'name': local_file_names[idx],
                'link': local_webViewLinks[idx],
                'score': float(1.0 - distances[idx])  # Convert to float for JSON serialization
            } for idx in sorted_indices]
            logging.info(f"No matches found with sensitivity {max_distance}, returning {len(matches)} closest")

        elapsed_time = time.time() - start_time
        try:
            os.unlink(image_path)  # Clean up temporary image
            logging.info(f"Cleaned up temporary image: {image_path}")
        except Exception as e:
            logging.warning(f"Failed to clean up temporary image {image_path}: {str(e)}")

        return jsonify({
            "matches": matches,
            "message": f"Found {len(matches)} possible matches in {elapsed_time:.2f} seconds"
        })
    except Exception as e:
        logging.error(f"Error during search: {str(e)}")
        return jsonify({"error": f"Error during search: {str(e)}"}), 500

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Initialize services on startup
setup_services()

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=3000)