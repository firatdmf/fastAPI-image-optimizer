const dropZone = document.getElementById('drop-zone')
const fileInput = document.getElementById('file-input')
const status = document.getElementById('status')

// 1. Click to open file dialog
dropZone.onclick = () => fileInput.click()
fileInput.onchange = (e) => handleUpload(e.target.files)

  // 2. Prevent default behaviors for Drag & Drop
  ;['dragenter', 'dragover', 'dragleave', 'drop'].forEach((eventName) => {
    dropZone.addEventListener(eventName, preventDefaults, false)
    document.body.addEventListener(eventName, preventDefaults, false)
  })

function preventDefaults(e) {
  e.preventDefault()
  e.stopPropagation()
}

// 3. Highlight drop zone when item is hovered over it
;['dragenter', 'dragover'].forEach((eventName) => {
  dropZone.addEventListener(
    eventName,
    () => {
      dropZone.classList.add('border-blue-500', 'bg-blue-50', 'scale-[1.02]')
    },
    false
  )
})

  ;['dragleave', 'drop'].forEach((eventName) => {
    dropZone.addEventListener(
      eventName,
      () => {
        dropZone.classList.remove('border-blue-500', 'bg-blue-50', 'scale-[1.02]')
      },
      false
    )
  })

// 4. Handle dropped files
dropZone.addEventListener(
  'drop',
  (e) => {
    const dt = e.dataTransfer
    const files = dt.files
    handleUpload(files)
  },
  false
)

// 5. The Upload Function
async function handleUpload(files) {
  if (files.length === 0) return

  // Get the selected format
  const selectedFormat = document.querySelector('input[name="format-choice"]:checked').value

  status.classList.remove('hidden')
  dropZone.classList.add('opacity-30', 'pointer-events-none')

  const formData = new FormData()
  formData.append('output_format', selectedFormat)

  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i])
  }

  try {
    const response = await fetch('/optimize', { method: 'POST', body: formData })
    if (!response.ok) throw new Error('Optimization failed')

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `optimized_${selectedFormat}.zip`
    document.body.appendChild(a)
    a.click()
    a.remove()
  } catch (err) {
    alert('Error: ' + err.message)
  } finally {
    status.classList.add('hidden')
    dropZone.classList.remove('opacity-30', 'pointer-events-none')
    fileInput.value = '' // Clear the input so you can upload the same file again
  }
}
