import os
import io
import numpy as np
from PIL import Image, ImageTk
import tempfile
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk
from tkinter.ttk import Progressbar, Style
import threading
import time
import pickle
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.models import Model
import webbrowser

class DeepVectorLogoFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Deep Vector Logo Finder")
        self.root.geometry("900x700")  # Slightly larger to accommodate the preview
        
        # Set dark theme
        self.dark_bg = "#212121"
        self.dark_secondary = "#303030"
        self.text_color = "#FFFFFF"
        self.accent_color = "#BB86FC"
        self.button_color = "#3700B3"
        self.card_bg = "#424242"
        
        self.root.configure(bg=self.dark_bg)
        
        # Configure style for dark theme
        self.configure_styles()
        
        # Initialize Google Drive API and VGG16 model
        self.drive_service = None
        self.vgg_model = None
        self.vectors = []
        self.file_ids = []
        self.file_names = []
        self.webViewLinks = []
        self.current_image = None
        self.current_image_tk = None  # For displaying in the preview panel
        
        # Setup services
        self.setup_services()
        
        # Create GUI elements
        self.create_widgets()
        
        # Bind paste event
        self.root.bind('<Control-v>', self.paste_image)
    
    def configure_styles(self):
        """Configure styles for dark theme"""
        style = ttk.Style()
        
        # Configure progress bar style
        style.configure("TProgressbar", 
                        thickness=10, 
                        troughcolor=self.dark_secondary,
                        background=self.accent_color)
        
        # Create new styles for widgets
        style.configure("Dark.TButton",
                       background=self.button_color,
                       foreground=self.text_color,
                       font=("Arial", 11, "bold"),
                       borderwidth=0,
                       focusthickness=3,
                       focuscolor=self.accent_color)
        
        style.map("Dark.TButton",
                 background=[('active', self.accent_color)],
                 foreground=[('active', self.text_color)])
    
    def setup_services(self):
        """Initialize Google Drive API and VGG16 model"""
        try:
            # Setup Google Drive API
            credentials = service_account.Credentials.from_service_account_file(
                'service-account-key.json', 
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            self.drive_service = build('drive', 'v3', credentials=credentials)
            print("Google Drive API initialized successfully")
        except Exception as e:
            print(f"Error initializing Google Drive API: {e}")
    
    def load_vgg_model(self):
        """Load VGG16 model for feature extraction"""
        try:
            # Load VGG16 model
            vgg16_model = VGG16(weights="imagenet")
            # Create model to extract features from fc1 layer (4096-dimensional vector)
            self.vgg_model = Model(inputs=vgg16_model.inputs, outputs=vgg16_model.get_layer("fc1").output)
            print("VGG16 model loaded successfully")
        except Exception as e:
            print(f"Error loading VGG16 model: {e}")
            self.root.after(0, lambda: self.status_label.config(
                text=f"Error loading VGG16 model: {e}",
                fg="red"
            ))
    
    def create_widgets(self):
        """Create GUI elements"""
        # Main container
        main_container = tk.Frame(self.root, bg=self.dark_bg)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title and header
        header_frame = tk.Frame(main_container, bg=self.dark_bg)
        header_frame.pack(fill=tk.X, pady=10)
        
        # Title label
        title_label = tk.Label(
            header_frame, 
            text="Deep Vector Logo Finder", 
            font=("Arial", 20, "bold"),
            bg=self.dark_bg,
            fg=self.accent_color
        )
        title_label.pack(pady=5)
        
        # Control panel frame
        control_panel = tk.Frame(main_container, bg=self.dark_bg)
        control_panel.pack(fill=tk.X, pady=10)
        
        # Buttons frame
        buttons_frame = tk.Frame(control_panel, bg=self.dark_bg)
        buttons_frame.pack(side=tk.LEFT, padx=10)
        
        # Index button - gray with black text
        self.index_btn = tk.Button(
            buttons_frame,
            text="Index Google Drive",
            command=self.index_google_drive,
            width=18,
            height=2,
            bg="#AAAAAA",  # Gray background
            fg="#000000",  # Black text
            font=("Arial", 11, "bold"),
            activebackground="#CCCCCC",
            activeforeground="#000000",
            bd=0,
            cursor="hand2"
        )
        self.index_btn.pack(side=tk.LEFT, padx=5)
        
        # Upload button - gray with black text
        self.upload_btn = tk.Button(
            buttons_frame,
            text="Select Image",
            command=self.upload_image,
            width=18,
            height=2,
            bg="#AAAAAA",  # Gray background
            fg="#000000",  # Black text
            font=("Arial", 11, "bold"),
            activebackground="#CCCCCC",
            activeforeground="#000000",
            bd=0,
            cursor="hand2"
        )
        self.upload_btn.pack(side=tk.LEFT, padx=5)
        
        # Paste button - gray with black text
        paste_button = tk.Button(
            buttons_frame,
            text="Paste Image (Ctrl+V)",
            command=lambda: self.paste_image(None),
            width=18,
            height=2,
            bg="#AAAAAA",  # Gray background
            fg="#000000",  # Black text
            font=("Arial", 11, "bold"),
            activebackground="#CCCCCC",
            activeforeground="#000000",
            bd=0,
            cursor="hand2"
        )
        paste_button.pack(side=tk.LEFT, padx=5)
        
        # Search button - gray with black text
        self.search_btn = tk.Button(
            buttons_frame,
            text="Search with Image",
            command=self.search_with_current_image,
            width=18,
            height=2,
            bg="#AAAAAA",  # Gray background
            fg="#000000",  # Black text
            font=("Arial", 11, "bold"),
            activebackground="#CCCCCC",
            activeforeground="#000000",
            bd=0,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        # Sensitivity slider frame
        sensitivity_frame = tk.Frame(control_panel, bg=self.dark_bg)
        sensitivity_frame.pack(side=tk.RIGHT, padx=10)
        
        sensitivity_label = tk.Label(
            sensitivity_frame,
            text="Matching Sensitivity:",
            font=("Arial", 11),
            bg=self.dark_bg,
            fg=self.text_color
        )
        sensitivity_label.pack(side=tk.LEFT, padx=5)
        
        self.sensitivity_var = tk.DoubleVar(value=0.4)
        sensitivity_slider = tk.Scale(
            sensitivity_frame,
            from_=0.1,
            to=0.9,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            length=150,
            variable=self.sensitivity_var,
            bg=self.dark_bg,
            fg=self.text_color,
            highlightthickness=0,
            troughcolor="#555555",
            activebackground="#888888",
            bd=0,
            sliderrelief=tk.FLAT
        )
        sensitivity_slider.pack(side=tk.LEFT, padx=5)
        
        # Status and progress frame
        status_frame = tk.Frame(main_container, bg=self.dark_bg)
        status_frame.pack(fill=tk.X, pady=5)
        
        # Status label
        self.status_label = tk.Label(
            status_frame,
            text="Please index Google Drive before searching",
            font=("Arial", 10),
            bg=self.dark_bg,
            fg=self.text_color
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Progress bar
        self.progress = Progressbar(
            status_frame,
            orient=tk.HORIZONTAL,
            length=300,
            mode='determinate',
            style="TProgressbar"
        )
        self.progress.pack(side=tk.RIGHT, padx=10)
        self.progress.pack_forget()  # Initially hidden
        
        # Add image preview frame (NEW)
        preview_frame = tk.Frame(main_container, bg=self.dark_secondary, bd=1, relief=tk.GROOVE)
        preview_frame.pack(fill=tk.X, pady=10)
        
        preview_label = tk.Label(
            preview_frame,
            text="Image Preview",
            font=("Arial", 14, "bold"),
            bg=self.dark_secondary,
            fg=self.text_color
        )
        preview_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Image preview canvas (NEW)
        self.preview_canvas = tk.Canvas(
            preview_frame,
            bg=self.dark_secondary,
            highlightthickness=0,
            width=200,
            height=200
        )
        self.preview_canvas.pack(side=tk.LEFT, padx=20, pady=10)
        
        # Image info frame (NEW)
        self.image_info_frame = tk.Frame(preview_frame, bg=self.dark_secondary)
        self.image_info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Image info labels (NEW)
        self.image_name_label = tk.Label(
            self.image_info_frame,
            text="No image selected",
            font=("Arial", 12, "bold"),
            bg=self.dark_secondary,
            fg=self.text_color,
            anchor=tk.W,
            justify=tk.LEFT
        )
        self.image_name_label.pack(anchor=tk.W, pady=5)
        
        self.image_size_label = tk.Label(
            self.image_info_frame,
            text="Size: -",
            font=("Arial", 11),
            bg=self.dark_secondary,
            fg=self.text_color,
            anchor=tk.W,
            justify=tk.LEFT
        )
        self.image_size_label.pack(anchor=tk.W, pady=2)
        
        self.image_format_label = tk.Label(
            self.image_info_frame,
            text="Format: -",
            font=("Arial", 11),
            bg=self.dark_secondary,
            fg=self.text_color,
            anchor=tk.W,
            justify=tk.LEFT
        )
        self.image_format_label.pack(anchor=tk.W, pady=2)
        
        # Clear image button (NEW)
        self.clear_image_btn = tk.Button(
            self.image_info_frame,
            text="Clear Image",
            command=self.clear_image,
            bg="#AAAAAA",
            fg="#000000",
            font=("Arial", 10),
            activebackground="#CCCCCC",
            activeforeground="#000000",
            bd=0,
            padx=15,
            pady=5,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.clear_image_btn.pack(anchor=tk.W, pady=10)
        
        # Results area
        results_frame = tk.Frame(main_container, bg=self.dark_bg, bd=1, relief=tk.GROOVE)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        results_label = tk.Label(
            results_frame,
            text="Search Results",
            font=("Arial", 14, "bold"),
            bg=self.dark_bg,
            fg=self.text_color
        )
        results_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # Create scrollable results area
        results_canvas = tk.Canvas(
            results_frame,
            bg=self.dark_bg,
            highlightthickness=0
        )
        
        scrollbar = tk.Scrollbar(
            results_frame,
            orient="vertical",
            command=results_canvas.yview
        )
        
        self.results_frame = tk.Frame(
            results_canvas,
            bg=self.dark_bg
        )
        
        self.results_frame.bind(
            "<Configure>",
            lambda e: results_canvas.configure(scrollregion=results_canvas.bbox("all"))
        )
        
        results_canvas.create_window((0, 0), window=self.results_frame, anchor="nw")
        results_canvas.configure(yscrollcommand=scrollbar.set)
        
        results_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Initial message in results area
        initial_message = tk.Label(
            self.results_frame,
            text="No search results yet.\nPlease select or paste an image and click search.",
            font=("Arial", 12),
            bg=self.dark_bg,
            fg=self.text_color,
            justify=tk.CENTER,
            pady=40
        )
        initial_message.pack()
    
    def clear_image(self):
        """Clear the current image and reset the preview"""
        self.current_image = None
        self.current_image_tk = None
        self.search_btn.config(state=tk.DISABLED)
        self.clear_image_btn.config(state=tk.DISABLED)
        
        # Clear preview
        self.preview_canvas.delete("all")
        self.image_name_label.config(text="No image selected")
        self.image_size_label.config(text="Size: -")
        self.image_format_label.config(text="Format: -")
        
        self.status_label.config(text="Image cleared")
    
    def update_preview(self, img=None, source_name=None):
        """Update image preview for pasted/uploaded images"""
        if img is None:
            # Reset current image
            self.clear_image()
            return
        
        try:
            # Store the image and enable search button
            self.current_image = img
            self.search_btn.config(state=tk.NORMAL)
            self.clear_image_btn.config(state=tk.NORMAL)
            
            # Get image info
            width, height = img.size
            format_name = img.format if img.format else "Unknown"
            
            # Set image information
            self.image_name_label.config(text=source_name if source_name else "Pasted/Selected Image")
            self.image_size_label.config(text=f"Size: {width}x{height} pixels")
            self.image_format_label.config(text=f"Format: {format_name}")
            
            # Resize for preview (maintain aspect ratio)
            max_size = 200
            ratio = min(max_size/width, max_size/height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # Create preview image
            preview_img = img.copy()
            preview_img = preview_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage for display
            self.current_image_tk = ImageTk.PhotoImage(preview_img)
            
            # Clear previous image
            self.preview_canvas.delete("all")
            
            # Calculate center position
            x_offset = (200 - new_width) // 2
            y_offset = (200 - new_height) // 2
            
            # Display image
            self.preview_canvas.create_image(
                x_offset, y_offset, 
                anchor=tk.NW, 
                image=self.current_image_tk
            )
            
            # Add a border around the image
            self.preview_canvas.create_rectangle(
                x_offset-1, y_offset-1, 
                x_offset+new_width+1, y_offset+new_height+1,
                outline=self.accent_color,
                width=2
            )
            
        except Exception as e:
            print(f"Error updating preview: {e}")
            self.status_label.config(
                text=f"Error updating preview: {e}",
                fg="red"
            )
    
    def paste_image(self, event=None):
        """Handle image paste from clipboard"""
        try:
            # Try using ImageGrab for Windows and macOS
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                self.update_preview(img, "Pasted from Clipboard")
                self.status_label.config(text="Image pasted from clipboard")
                return True
        except Exception as e:
            print(f"ImageGrab method failed: {e}")
            
        try:
            # Get image from clipboard as file path
            clipboard_img = self.root.clipboard_get()
            
            # If clipboard content is a file path
            if os.path.isfile(clipboard_img):
                try:
                    img = Image.open(clipboard_img)
                    self.update_preview(img, os.path.basename(clipboard_img))
                    self.status_label.config(text="Image pasted from clipboard")
                    return True
                except Exception as e:
                    print(f"Failed to open clipboard file: {e}")
        except tk.TclError as e:
            print(f"Clipboard get failed: {e}")
            
        # If all attempts failed
        self.status_label.config(
            text="Failed to paste image from clipboard",
            fg="red"
        )
        return False
    
    def search_with_current_image(self):
        """Search using the current pasted or uploaded image"""
        if self.current_image:
            # Save current image to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                self.current_image.save(tmp_file.name, format="PNG")
                tmp_path = tmp_file.name
            
            # Start search with this image
            self.start_search(tmp_path)
    
    def index_google_drive(self):
        """Index all PNG files in Google Drive and extract feature vectors"""
        self.status_label.config(text="Loading VGG16 model...")
        self.progress.pack(side=tk.RIGHT, padx=10)
        
        # Start indexing in a separate thread
        index_thread = threading.Thread(
            target=self._index_google_drive_thread
        )
        index_thread.daemon = True
        index_thread.start()
    def _index_google_drive_thread(self):
        """Thread for indexing Google Drive"""
        start_time = time.time()
        
        try:
            # Load VGG16 model
            if self.vgg_model is None:
                self.load_vgg_model()
            
            # Get all PNG files from specific folder in Google Drive (including subfolders)
            self.root.after(0, lambda: self.status_label.config(
                text="Fetching PNG files from Google Drive..."
            ))
            
            folder_id = '11kFOF8p4wGf7V0-rQvXUes_XfE5LtjCZ'  # Root folder ID
            
            # Function to recursively find all PNG files in a folder and its subfolders
            def list_all_png_files(folder_id, path_prefix=""):
                all_files = []
                
                # Get both subfolders and PNG files in current folder
                query = f"'{folder_id}' in parents and (mimeType='application/vnd.google-apps.folder' or mimeType='image/png') and trashed=false"
                results = self.drive_service.files().list(
                    q=query,
                    fields="files(id, name, mimeType, webViewLink)",
                    pageSize=1000
                ).execute()
                
                items = results.get('files', [])
                
                # Process each item
                for item in items:
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        # It's a folder, recursively process it
                        subfolder_name = item['name']
                        subfolder_path = f"{path_prefix}/{subfolder_name}" if path_prefix else subfolder_name
                        print(f"Processing subfolder: {subfolder_path}")
                        
                        # Recursively get files from subfolder
                        subfolder_files = list_all_png_files(item['id'], subfolder_path)
                        all_files.extend(subfolder_files)
                    else:
                        # It's a PNG file
                        item_path = f"{path_prefix}/{item['name']}" if path_prefix else item['name']
                        all_files.append({
                            'id': item['id'],
                            'name': item_path,  # Include full path for better identification
                            'webViewLink': item.get('webViewLink', '')
                        })
                
                return all_files
            
            # Get all PNG files from the main folder and its subfolders
            drive_files = list_all_png_files(folder_id)
            
            if not drive_files:
                self.root.after(0, lambda: self.status_label.config(
                    text="No PNG files found in the specified folder or its subfolders",
                    fg="red"
                ))
                self.root.after(0, lambda: self.progress.pack_forget())
                return
            
            total_files = len(drive_files)
            self.root.after(0, lambda: self.progress.config(maximum=total_files))
            self.root.after(0, lambda: self.status_label.config(
                text=f"Indexing {total_files} PNG files..."
            ))
            
            # Reset vectors and paths
            self.vectors = []
            self.file_ids = []
            self.file_names = []
            self.webViewLinks = []
            
            # Process each file
            for i, file in enumerate(drive_files):
                # Update progress
                self.root.after(0, lambda i=i: self.progress.config(value=i+1))
                
                update_interval = max(1, total_files // 20)
                if i % update_interval == 0 or i == total_files - 1:
                    self.root.after(0, lambda i=i, total=total_files, name=file['name']: 
                                self.status_label.config(
                                    text=f"Processing file {i+1}/{total}: {name}"
                                ))
                
                try:
                    file_id = file['id']
                    file_name = file['name']
                    webViewLink = file.get('webViewLink', '')
                    
                    # Download file to temporary location
                    request = self.drive_service.files().get_media(fileId=file_id)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                        fh = io.FileIO(tmp_file.name, 'wb')
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                        
                        # Close file before processing
                        fh.close()
                        
                        # Extract feature vector
                        try:
                            vector = self.extract_vector(tmp_file.name)
                            self.vectors.append(vector)
                            self.file_ids.append(file_id)
                            self.file_names.append(file_name)
                            self.webViewLinks.append(webViewLink)
                        except Exception as e:
                            print(f"Error extracting vector for {file_name}: {e}")
                        
                        # Clean up temp file
                        os.unlink(tmp_file.name)
                        
                except Exception as e:
                    print(f"Error processing file {file.get('name')}: {e}")
                    continue
            
            # Convert vectors to numpy array for faster processing
            self.vectors = np.array(self.vectors)
            
            # Save vectors and paths to disk
            try:
                print(f"Current working directory: {os.getcwd()}")
                with open('vectors.pkl', 'wb') as f:
                    pickle.dump(self.vectors, f)
                with open('file_ids.pkl', 'wb') as f:
                    pickle.dump(self.file_ids, f)
                with open('file_names.pkl', 'wb') as f:
                    pickle.dump(self.file_names, f)
                with open('webViewLinks.pkl', 'wb') as f:
                    pickle.dump(self.webViewLinks, f)
                print(f"Vectors saved to: {os.path.abspath('vectors.pkl')}")
                print(f"File IDs saved to: {os.path.abspath('file_ids.pkl')}")
                print(f"File names saved to: {os.path.abspath('file_names.pkl')}")
                print(f"Web view links saved to: {os.path.abspath('webViewLinks.pkl')}")
                print("Vectors and paths saved to disk")
            except Exception as e:
                print(f"Error saving vectors and paths: {e}")
            
            elapsed_time = time.time() - start_time
            self.root.after(0, lambda: self.status_label.config(
                text=f"Indexing complete! {len(self.vectors)} files indexed in {elapsed_time:.2f} seconds"
            ))
            self.root.after(0, lambda: self.progress.pack_forget())
            
        except Exception as e:
            print(f"Error during indexing: {str(e)}")
            self.root.after(0, lambda: self.status_label.config(
                text=f"Error during indexing: {str(e)}",
                fg="red"
            ))
            self.root.after(0, lambda: self.progress.pack_forget())    

    def image_preprocess(self, img):
        """Preprocess image for VGG16 model"""
        img = img.resize((224, 224))
        img = img.convert("RGB")
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        return x
    
    def extract_vector(self, image_path):
        """Extract feature vector from image using VGG16 model"""
        try:
            img = Image.open(image_path)
            img_tensor = self.image_preprocess(img)
            # Extract features
            vector = self.vgg_model.predict(img_tensor, verbose=0)[0]
            # Normalize vector
            vector = vector / np.linalg.norm(vector)
            return vector
        except Exception as e:
            print(f"Error extracting vector: {e}")
            raise e
    
    def upload_image(self):
        """Handle logo image upload and search"""
        # Open file dialog to select image
        file_path = filedialog.askopenfilename(
            title="Select Logo Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        
        if file_path:
            # Display preview of selected image
            try:
                img = Image.open(file_path)
                self.update_preview(img, os.path.basename(file_path))
                self.status_label.config(text="Image selected")
            except Exception as e:
                self.status_label.config(
                    text=f"Error opening image: {str(e)}",
                    fg="red"
                )
    
    def start_search(self, image_path):
        """Start the search process with the given image path"""
        # Check if vectors are loaded
        if len(self.vectors) == 0:
            try:
                # Try to load from disk
                with open('vectors.pkl', 'rb') as f:
                    self.vectors = pickle.load(f)
                with open('file_ids.pkl', 'rb') as f:
                    self.file_ids = pickle.load(f)
                with open('file_names.pkl', 'rb') as f:
                    self.file_names = pickle.load(f)
                with open('webViewLinks.pkl', 'rb') as f:
                    self.webViewLinks = pickle.load(f)
                print("Vectors and paths loaded from disk")
            except Exception as e:
                print(f"Error loading vectors and paths: {e}")
                self.status_label.config(
                    text="Please index Google Drive before searching",
                    fg="red"
                )
                return
        
        self.status_label.config(text=f"Processing image...")
        self.progress.pack(side=tk.RIGHT, padx=10)
        
        # Start search in a separate thread
        search_thread = threading.Thread(
            target=self.search_logos,
            args=(image_path,)
        )
        search_thread.daemon = True
        search_thread.start()
    
    def search_logos(self, query_image_path):
        """Search for similar logos based on feature vectors"""
        start_time = time.time()
        
        try:
            # Load VGG16 model if not loaded
            if self.vgg_model is None:
                self.load_vgg_model()
            
            # Extract feature vector from query image
            query_vector = self.extract_vector(query_image_path)
            
            # Calculate distance to all vectors
            distances = np.linalg.norm(self.vectors - query_vector, axis=1)
            
            # Get threshold from sensitivity slider
            threshold = self.sensitivity_var.get()
            
            # Sort distances and get indices of closest vectors
            # More sensitive (higher threshold) means we accept more distant matches
            max_distance = threshold  # Adjust this threshold as needed
            close_indices = np.where(distances < max_distance)[0]
            
            if len(close_indices) == 0:
                # If no matches found, just get the top 10 closest
                K = 10
                close_indices = np.argsort(distances)[:K]
            
            # Sort the close indices by distance
            close_indices = close_indices[np.argsort(distances[close_indices])]
            
            # Create matches list
            matches = []
            for idx in close_indices:
                matches.append({
                    'id': self.file_ids[idx],
                    'name': self.file_names[idx],
                    'link': self.webViewLinks[idx],
                    'score': 1.0 - distances[idx]  # Convert distance to similarity score
                })
            
            elapsed_time = time.time() - start_time
            self.root.after(0, lambda: self.display_results(matches, elapsed_time))
            
            # If the temporary file was created for search, clean it up
            if os.path.exists(query_image_path) and query_image_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(query_image_path)
                except:
                    pass
            
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(
                text=f"Error during search: {str(e)}",
                fg="red"
            ))
            self.root.after(0, lambda: self.progress.pack_forget())
            
            # If the temporary file was the issue
            if os.path.exists(query_image_path) and query_image_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(query_image_path)
                except:
                    pass
    
    def display_results(self, matches, elapsed_time=None):
        """Display matching results in the UI"""
        # Hide progress bar
        self.progress.pack_forget()
        
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        if not matches:
            time_info = f" in {elapsed_time:.2f} seconds" if elapsed_time else ""
            self.status_label.config(text=f"No matching logos found{time_info}")
            
            # Show no results message
            no_results = tk.Label(
                self.results_frame,
                text="No matches found. Try adjusting the sensitivity\nor use a different image.",
                font=("Arial", 12),
                bg=self.dark_bg,
                fg=self.text_color,
                justify=tk.CENTER,
                pady=40
            )
            no_results.pack(fill=tk.X)
            return
        
        time_info = f" in {elapsed_time:.2f} seconds" if elapsed_time else ""
        self.status_label.config(text=f"Found {len(matches)} possible matches{time_info}")
        
        # Display matches
        matches = matches[:10]  # Limit to top 10
        
        # Create result items
        for i, match in enumerate(matches):
            # Create result card with background
            result_card = tk.Frame(
                self.results_frame,
                bg=self.card_bg,
                padx=15,
                pady=10,
                relief=tk.RAISED,
                bd=1
            )
            result_card.pack(fill=tk.X, pady=8, padx=10)
            
            # File name label
            name_label = tk.Label(
                result_card,
                text=match['name'],
                font=("Arial", 12, "bold"),
                bg=self.card_bg,
                fg=self.text_color,
                anchor=tk.W,
                justify=tk.LEFT,
                padx=5
            )
            name_label.pack(anchor=tk.W, fill=tk.X, pady=(0, 5))
            
            # Score display 
            score_frame = tk.Frame(result_card, bg=self.card_bg)
            score_frame.pack(fill=tk.X, pady=5)
            
            score_label = tk.Label(
                score_frame,
                text=f"Match Score:",
                font=("Arial", 10),
                bg=self.card_bg,
                fg="#AAAAAA"
            )
            score_label.pack(side=tk.LEFT)
            
            # Score bar (visual indicator)
            score_value = match['score']
            score_bar_bg = tk.Frame(
                score_frame, 
                width=200, 
                height=12, 
                bg="#444444",
                bd=0
            )
            score_bar_bg.pack(side=tk.LEFT, padx=10)
            
            # Ensure score bar doesn't resize
            score_bar_bg.pack_propagate(False)
            
            # Score fill
            score_bar_fill = tk.Frame(
                score_bar_bg, 
                width=int(200 * score_value), 
                height=12, 
                bg=self.accent_color,
                bd=0
            )
            score_bar_fill.place(x=0, y=0)
            
            # Percentage display
            score_percent = tk.Label(
                score_frame,
                text=f"{int(score_value*100)}%",
                font=("Arial", 10, "bold"),
                bg=self.card_bg,
                fg=self.accent_color
            )
            score_percent.pack(side=tk.LEFT, padx=5)
            
            # Actions frame
            actions_frame = tk.Frame(result_card, bg=self.card_bg)
            actions_frame.pack(fill=tk.X, pady=10)
            
            # View button
            view_btn = tk.Button(
                actions_frame,
                text="View in Drive",
                command=lambda link=match['link']: self.open_link(link),
                bg="#AAAAAA",  # Gray background
                fg="#000000",  # Black text
                font=("Arial", 10, "bold"),
                activebackground="#CCCCCC",
                activeforeground="#000000",
                bd=0,
                padx=15,
                pady=5,
                cursor="hand2"
            )
            view_btn.pack(side=tk.RIGHT, padx=5)
            
            # Add right-click menu for copying link
            self.add_context_menu(view_btn, match['link'])
            
            # Add tooltip for the button
            self.create_tooltip(view_btn, "Right-click to copy link")
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 20
            
            # Create a toplevel window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(
                self.tooltip, 
                text=text, 
                justify=tk.LEFT,
                background="#424242", 
                foreground="#FFFFFF",
                relief=tk.SOLID, 
                borderwidth=1,
                font=("Arial", 10),
                padx=5,
                pady=2
            )
            label.pack(ipadx=1)
        
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)
    
    def add_context_menu(self, widget, link):
        """Add right-click context menu to widget"""
        menu = tk.Menu(widget, tearoff=0, bg=self.dark_secondary, fg=self.text_color, activebackground=self.accent_color)
        menu.add_command(label="Copy Link", command=lambda: self.copy_to_clipboard(link))
        menu.add_command(label="Open in Browser", command=lambda: self.open_link(link))
        
        def show_menu(event):
            menu.post(event.x_root, event.y_root)
            
        widget.bind('<Button-3>', show_menu)  # Right-click
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_label.config(
            text="Link copied to clipboard",
            fg="green"
        )
        # Reset status after 2 seconds
        self.root.after(2000, lambda: self.status_label.config(
            text="",
            fg=self.text_color
        ))
    
    def open_link(self, link):
        """Open Google Drive link in browser"""
        webbrowser.open(link)

def main():
    # Create and run the application
    root = tk.Tk()
    app = DeepVectorLogoFinderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
