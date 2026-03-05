import io
import math
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image, ImageOps
import pillow_avif
import zipfile

app = FastAPI()

# --- REFACTORED LOGIC FROM YOUR SCRIPT ---

def process_image_logic(pil_img, filename):
    # 1. Resize (Operation 2 in your code)
    dim_threshold = 1500
    width, height = pil_img.size
    if width > dim_threshold or height > dim_threshold:
        if width > height:
            new_width, new_height = dim_threshold, int((dim_threshold / width) * height)
        else:
            new_height, new_width = dim_threshold, int((dim_threshold / height) * width)
        pil_img = pil_img.resize((new_width, new_height), resample=Image.LANCZOS)
    
    pil_img = ImageOps.exif_transpose(pil_img)
    if pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")

    # 2. Iterative Compression (Operation 4 in your code)
    # We use a buffer to check size without saving to disk
    quality = 100
    tmp_buffer = io.BytesIO()
    
    while quality > 40:
        tmp_buffer.seek(0)
        tmp_buffer.truncate(0)
        pil_img.save(tmp_buffer, format="AVIF", quality=quality, speed=6)
        file_size_kb = tmp_buffer.tell() / 1024
        if file_size_kb <= 200:
            break
        quality -= 10
    
    # 3. Create Thumbnail (Operation 6 in your code)
    thumb_img = pil_img.copy()
    thumb_img.thumbnail((800, 800), resample=Image.BICUBIC)
    thumb_buffer = io.BytesIO()
    thumb_img.save(thumb_buffer, format="AVIF", quality=60)
    
    return tmp_buffer.getvalue(), thumb_buffer.getvalue()

@app.post("/optimize")
async def optimize_api(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    # Read uploaded file
    contents = await file.read()
    input_img = Image.open(io.BytesIO(contents))
    
    # Process
    main_img_data, thumb_img_data = process_image_logic(input_img, file.filename)
    
    # Create a ZIP file in memory to return both images
    zip_buffer = io.BytesIO()
    base_name = file.filename.rsplit('.', 1)[0]
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr(f"{base_name}.avif", main_img_data)
        zip_file.writestr(f"{base_name}_thumb.avif", thumb_img_data)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename={base_name}_optimized.zip"}
    )

@app.get("/")
async def homepage():
    from fastapi.responses import HTMLResponse
    return HTMLResponse("""
        <h1>AVIF Optimizer</h1>
        <form action="/optimize" enctype="multipart/form-data" method="post">
            <input name="file" type="file">
            <button type="submit">Optimize & Download ZIP</button>
        </form>
    """)