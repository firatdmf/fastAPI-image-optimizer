let fileQueue = [];
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const previewContainer = document.getElementById('preview-container');
const previewGrid = document.getElementById('preview-grid');
const countLabel = document.getElementById('count');
const btnOptimize = document.getElementById('btn-optimize');
const status = document.getElementById('status');

dropZone.onclick = () => fileInput.click();
fileInput.onchange = (e) => handleFiles(e.target.files);

// --- Drag and Drop Event Handling ---

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// Add event listeners to the entire page to prevent the browser from opening the file
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    document.body.addEventListener(eventName, preventDefaults, false);
    dropZone.addEventListener(eventName, preventDefaults, false);
});

// Add visual feedback when dragging over the drop zone
['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('border-blue-500', 'bg-blue-50'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('border-blue-500', 'bg-blue-50'), false);
});

dropZone.addEventListener('drop', (e) => {
    // The 'drop' event's default is already prevented, now we just handle the files
    handleFiles(e.dataTransfer.files);
}, false);

function handleFiles(files) {
    const newFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
    
    newFiles.forEach(file => {
        fileQueue.push(file);
        
        // Create Preview Card
        const reader = new FileReader();
        reader.onload = (e) => {
            const card = document.createElement('div');
            card.className = "relative group bg-white border rounded p-1 shadow-sm";
            card.innerHTML = `
                <img src="${e.target.result}" class="h-24 w-full object-cover rounded">
                <button class="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity" onclick="removeFile('${file.name}')">×</button>
                <p class="text-[10px] truncate mt-1 text-gray-500">${file.name}</p>
            `;
            previewGrid.appendChild(card);
        };
        reader.readAsDataURL(file);
    });

    updateUI();
}

function removeFile(fileName) {
    fileQueue = fileQueue.filter(f => f.name !== fileName);
    renderPreviews(); // Redraw grid
    updateUI();
}

function updateUI() {
    countLabel.innerText = fileQueue.length;
    if (fileQueue.length > 0) {
        previewContainer.classList.remove('hidden');
    } else {
        previewContainer.classList.add('hidden');
    }
}

function renderPreviews() {
    previewGrid.innerHTML = '';
    // Re-rendering everything is simplest for small lists
    fileQueue.forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const card = document.createElement('div');
            card.className = "relative group bg-white border rounded p-1 shadow-sm";
            card.innerHTML = `
                <img src="${e.target.result}" class="h-24 w-full object-cover rounded">
                <button class="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity" onclick="removeFile('${file.name}')">×</button>
                <p class="text-[10px] truncate mt-1 text-gray-500">${file.name}</p>
            `;
            previewGrid.appendChild(card);
        };
        reader.readAsDataURL(file);
    });
}

// 3. THE OPTIMIZE ACTION
btnOptimize.onclick = async () => {
    if (fileQueue.length === 0) return;

    const selectedFormat = document.querySelector('input[name="format-choice"]:checked').value;
    status.classList.remove('hidden');
    btnOptimize.disabled = true;

    const formData = new FormData();
    formData.append('output_format', selectedFormat);
    fileQueue.forEach(file => formData.append('files', file));

    try {
        const response = await fetch('/optimize', { method: 'POST', body: formData });
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `optimized_batch_${selectedFormat}.zip`;
        a.click();
        
        // Clear queue after success
        fileQueue = [];
        previewGrid.innerHTML = '';
        updateUI();
    } catch (err) {
        alert("Optimization failed: " + err.message);
    } finally {
        status.classList.add('hidden');
        btnOptimize.disabled = false;
    }
};