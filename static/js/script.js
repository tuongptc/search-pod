document.addEventListener('DOMContentLoaded', () => {
    const indexBtn = document.getElementById('index-btn');
    const selectImageBtn = document.getElementById('select-image-btn');
    const uploadImage = document.getElementById('upload-image');
    const pasteImageBtn = document.getElementById('paste-image-btn');
    const searchBtn = document.getElementById('search-btn');
    const clearImageBtn = document.getElementById('clear-image-btn');
    const sensitivity = document.getElementById('sensitivity');
    const sensitivityValue = document.getElementById('sensitivity-value');
    const statusText = document.getElementById('status-text');
    const progressBar = document.getElementById('progress-bar');
    const previewCanvas = document.getElementById('preview-canvas');
    const imageName = document.getElementById('image-name');
    const imageSize = document.getElementById('image-size');
    const imageFormat = document.getElementById('image-format');
    const results = document.getElementById('results');
    let currentImage = null;

    // Update sensitivity value display
    sensitivity.addEventListener('input', () => {
        sensitivityValue.textContent = sensitivity.value;
    });

    // Trigger file input click
    selectImageBtn.addEventListener('click', () => {
        uploadImage.click();
    });

    // Handle image upload
    async function handleImageUpload(file, sourceName = file.name) {
        const formData = new FormData();
        formData.append('image', file);
        try {
            const response = await fetch('/upload_image', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (data.error) {
                statusText.textContent = data.error;
                statusText.classList.add('error');
                return;
            }
            currentImage = data;
            imageName.textContent = sourceName;
            imageSize.textContent = `Size: ${data.size}`;
            imageFormat.textContent = `Format: ${data.format}`;
            searchBtn.disabled = false;
            clearImageBtn.disabled = false;
            statusText.textContent = `Image ${sourceName.includes('Clipboard') ? 'pasted' : 'selected'}`;
            statusText.classList.remove('error', 'success');
            // Draw image on canvas
            const ctx = previewCanvas.getContext('2d');
            const img = new Image();
            img.src = `/uploads/${data.filename}`;
            img.onload = () => {
                ctx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
                const maxSize = 200;
                const ratio = Math.min(maxSize / img.width, maxSize / img.height);
                const newWidth = img.width * ratio;
                const newHeight = img.height * ratio;
                const xOffset = (200 - newWidth) / 2;
                const yOffset = (200 - newHeight) / 2;
                ctx.drawImage(img, xOffset, yOffset, newWidth, newHeight);
                ctx.strokeStyle = '#BB86FC';
                ctx.lineWidth = 2;
                ctx.strokeRect(xOffset - 1, yOffset - 1, newWidth + 2, newHeight + 2);
            };
        } catch (error) {
            statusText.textContent = 'Error uploading image';
            statusText.classList.add('error');
        }
    }

    uploadImage.addEventListener('change', async () => {
        if (uploadImage.files.length === 0) return;
        await handleImageUpload(uploadImage.files[0]);
    });

    // Handle paste image
    async function handlePaste(event) {
        event.preventDefault();
        const items = (event.clipboardData || event.originalEvent.clipboardData).items;
        for (const item of items) {
            if (item.type.startsWith('image')) {
                const blob = item.getAsFile();
                const file = new File([blob], `Clipboard_${Date.now()}.png`, { type: blob.type });
                await handleImageUpload(file, 'Pasted from Clipboard');
                return;
            }
        }
        statusText.textContent = 'No image found in clipboard';
        statusText.classList.add('error');
    }

    pasteImageBtn.addEventListener('click', () => {
        navigator.clipboard.read().then(async (clipboardItems) => {
            for (const item of clipboardItems) {
                for (const type of item.types) {
                    if (type.startsWith('image')) {
                        const blob = await item.getType(type);
                        const file = new File([blob], `Clipboard_${Date.now()}.png`, { type: blob.type });
                        await handleImageUpload(file, 'Pasted from Clipboard');
                        return;
                    }
                }
            }
            statusText.textContent = 'No image found in clipboard';
            statusText.classList.add('error');
        }).catch((err) => {
            statusText.textContent = 'Failed to access clipboard. Try Ctrl+V or select an image.';
            statusText.classList.add('error');
        });
    });

    // Handle Ctrl+V paste anywhere on the page
    document.addEventListener('paste', handlePaste);

    // Clear image
    clearImageBtn.addEventListener('click', () => {
        currentImage = null;
        imageName.textContent = 'No image selected';
        imageSize.textContent = 'Size: -';
        imageFormat.textContent = 'Format: -';
        searchBtn.disabled = true;
        clearImageBtn.disabled = true;
        const ctx = previewCanvas.getContext('2d');
        ctx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
        statusText.textContent = 'Image cleared';
        statusText.classList.remove('error', 'success');
    });

    // Start indexing
    indexBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/index_drive', {
                method: 'POST'
            });
            const data = await response.json();
            if (data.error) {
                statusText.textContent = data.error;
                statusText.classList.add('error');
                return;
            }
            statusText.textContent = 'Indexing started...';
            statusText.classList.remove('error', 'success');
            progressBar.style.display = 'block';
            pollIndexStatus();
        } catch (error) {
            statusText.textContent = 'Error starting indexing';
            statusText.classList.add('error');
        }
    });

    // Poll indexing status
    function pollIndexStatus() {
        fetch('/index_status')
            .then(response => response.json())
            .then(data => {
                statusText.textContent = data.message;
                if (data.status === 'error') {
                    statusText.classList.add('error');
                    progressBar.style.display = 'none';
                } else if (data.status === 'complete') {
                    statusText.classList.add('success');
                    progressBar.style.display = 'none';
                } else {
                    statusText.classList.remove('error', 'success');
                    progressBar.value = data.total ? (data.progress / data.total) * 100 : 0;
                    progressBar.max = 100;
                    setTimeout(pollIndexStatus, 1000);
                }
            })
            .catch(() => {
                statusText.textContent = 'Error checking indexing status';
                statusText.classList.add('error');
                progressBar.style.display = 'none';
            });
    }

    // Start search
    searchBtn.addEventListener('click', async () => {
        if (!currentImage) return;
        const formData = new FormData();
        formData.append('filename', currentImage.filename);
        formData.append('sensitivity', sensitivity.value);
        try {
            statusText.textContent = 'Processing image...';
            statusText.classList.remove('error', 'success');
            progressBar.style.display = 'block';
            progressBar.value = 0;
            const response = await fetch('/search', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            progressBar.style.display = 'none';
            if (data.error) {
                statusText.textContent = data.error;
                statusText.classList.add('error');
                return;
            }
            statusText.textContent = data.message;
            statusText.classList.add('success');
            displayResults(data.matches);
        } catch (error) {
            statusText.textContent = 'Error during search';
            statusText.classList.add('error');
            progressBar.style.display = 'none';
        }
    });

    // Display search results
    function displayResults(matches) {
        results.innerHTML = '';
        if (!matches || matches.length === 0) {
            results.innerHTML = '<p>No matches found. Try adjusting the sensitivity<br>or use a different image.</p>';
            return;
        }
        matches.forEach(match => {
            const card = document.createElement('div');
            card.className = 'result-card';
            card.innerHTML = `
                <p>${match.name}</p>
                <div class="score-frame">
                    <span>Match Score:</span>
                    <div class="score-bar-bg">
                        <div class="score-bar-fill" style="width: ${match.score * 200}px;"></div>
                    </div>
                    <span>${Math.round(match.score * 100)}%</span>
                </div>
                <div class="actions">
                    <button onclick="window.open('${match.link}', '_blank')">View in Drive</button>
                    <button onclick="navigator.clipboard.writeText('${match.link}').then(() => alert('Link copied to clipboard'))">Copy Link</button>
                </div>
            `;
            results.appendChild(card);
        });
    }
});