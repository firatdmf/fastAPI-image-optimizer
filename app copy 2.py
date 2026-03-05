from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageOps
import io, zipfile, pillow_avif
from fastapi import Form

app = FastAPI()

# Add this block
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Allow your Next.js app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Link the 'static' and 'templates' folders
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def process_image_logic(pil_img, filename):
    # Resize Logic
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

    # Iterative Compression
    quality = 100
    main_buffer = io.BytesIO()
    while quality > 40:
        main_buffer.seek(0)
        main_buffer.truncate(0)
        pil_img.save(main_buffer, format="AVIF", quality=quality, speed=6)
        if main_buffer.tell() / 1024 <= 200:
            break
        quality -= 10

    # Thumbnail Logic
    thumb_img = pil_img.copy()
    thumb_img.thumbnail((800, 800), resample=Image.BICUBIC)
    thumb_buffer = io.BytesIO()
    thumb_img.save(thumb_buffer, format="AVIF", quality=60)

    return main_buffer.getvalue(), thumb_buffer.getvalue()


@app.post("/optimize")
async def optimize_api(
    files: List[UploadFile] = File(...),
    output_format: str = Form("avif"),  # Default to avif if not provided
):
    zip_buffer = io.BytesIO()

    # Standardize the format string
    target_format = output_format.lower()
    if target_format not in ["webp", "avif"]:
        target_format = "avif"

    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file in files:
            if not file.content_type.startswith("image/"):
                continue

            try:
                contents = await file.read()
                input_img = Image.open(io.BytesIO(contents))

                # --- Pass target_format into your logic ---
                main_data, thumb_data = process_image_logic(input_img, target_format)

                base_name = file.filename.rsplit(".", 1)[0]
                zip_file.writestr(f"optimized/{base_name}.{target_format}", main_data)
                zip_file.writestr(
                    f"thumbnails/{base_name}_thumb.{target_format}", thumb_data
                )
            except Exception as e:
                print(f"Error: {e}")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=optimized_{target_format}.zip"
        },
    )


# --- Update your processing function to use the format ---
def process_image_logic(pil_img, target_format):
    # ... (Keep your resizing logic here) ...

    # Iterative Compression
    quality = 100
    main_buffer = io.BytesIO()

    # WebP and AVIF both support the 'quality' parameter in Pillow
    while quality > 40:
        main_buffer.seek(0)
        main_buffer.truncate(0)
        # Use the dynamic format here
        pil_img.save(
            main_buffer,
            format=target_format.upper(),
            quality=quality,
            speed=6 if target_format == "avif" else None,
        )

        if main_buffer.tell() / 1024 <= 200:
            break
        quality -= 10

    # Thumbnail
    thumb_img = pil_img.copy()
    thumb_img.thumbnail((800, 800), resample=Image.BICUBIC)
    thumb_buffer = io.BytesIO()
    thumb_img.save(thumb_buffer, format=target_format.upper(), quality=60)

    return main_buffer.getvalue(), thumb_buffer.getvalue()


@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
