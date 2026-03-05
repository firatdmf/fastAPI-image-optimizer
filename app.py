from typing import List
from fastapi import FastAPI, UploadFile, File, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageOps
import io
import zipfile

# This import is necessary to register the AVIF plugin with Pillow
import pillow_avif

app = FastAPI()

# CORS middleware to allow requests from the Next.js frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def process_image_logic(pil_img: Image.Image, target_format: str, create_thumbnails: bool = True):
    """
    Processes a single image: resizes, compresses, and optionally creates a thumbnail.
    """
    # 1. Resize Logic: If the image is larger than 1500px on any side, resize it.
    dim_threshold = 1500
    width, height = pil_img.size
    if width > dim_threshold or height > dim_threshold:
        if width > height:
            new_width = dim_threshold
            new_height = int((dim_threshold / width) * height)
        else:
            new_height = dim_threshold
            new_width = int((dim_threshold / height) * width)
        pil_img = pil_img.resize((new_width, new_height), resample=Image.LANCZOS)

    # 2. Handle EXIF orientation data from cameras and convert to standard RGB.
    pil_img = ImageOps.exif_transpose(pil_img)
    if pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")

    # 3. Iterative Compression: Reduce quality until the image is under 200KB.
    quality = 100
    main_buffer = io.BytesIO()
    while quality > 40:
        main_buffer.seek(0)
        main_buffer.truncate(0)

        if target_format == 'avif':
            pil_img.save(
                main_buffer,
                format='AVIF',
                quality=quality,
                speed=6  # Speed is an AVIF-specific parameter (0=slowest, 10=fastest)
            )
        else:
            pil_img.save(
                main_buffer,
                format=target_format.upper(),
                quality=quality
            )

        # Stop if file size is under the target
        if main_buffer.tell() / 1024 <= 200:
            break
        quality -= 10
    
    main_data = main_buffer.getvalue()

    # 4. Thumbnail Generation (Conditional)
    thumb_data = None
    if create_thumbnails:
        thumb_img = pil_img.copy()
        thumb_img.thumbnail((800, 800), resample=Image.BICUBIC)
        thumb_buffer = io.BytesIO()
        thumb_img.save(thumb_buffer, format=target_format.upper(), quality=60)
        thumb_data = thumb_buffer.getvalue()

    return main_data, thumb_data


@app.post("/optimize")
async def optimize_api(
    files: List[UploadFile] = File(...),
    output_format: str = Form("avif"),
    create_thumbnails: bool = Form(True),
):
    """
    API endpoint to receive images and process them.
    - If one image is provided, it returns the optimized image file directly.
    - If multiple images are provided, it returns a zip file.
    """
    target_format = output_format.lower()
    if target_format not in ["webp", "avif"]:
        target_format = "avif"

    # If one file is uploaded, return a single file, not a zip.
    if len(files) == 1:
        file = files[0]
        if not file.content_type or not file.content_type.startswith("image/"):
            return Response(status_code=400, content="Invalid file type: Must be an image.")

        try:
            contents = await file.read()
            input_img = Image.open(io.BytesIO(contents))

            # The thumbnail is generated if requested, but only the main image is returned for single downloads.
            main_data, _ = process_image_logic(input_img, target_format, create_thumbnails)

            base_name = file.filename.rsplit(".", 1)[0] if file.filename else "image"
            
            return StreamingResponse(
                io.BytesIO(main_data),
                media_type=f"image/{target_format}",
                headers={
                    "Content-Disposition": f"attachment; filename=\"optimized_{base_name}.{target_format}\""
                },
            )
        except Exception as e:
            print(f"Error processing single file {file.filename}: {e}")
            return Response(status_code=500, content=f"Error processing file: {e}")

    # For multiple files, create and return a zip file.
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for file in files:
            if not file.content_type or not file.content_type.startswith("image/"):
                continue

            try:
                contents = await file.read()
                input_img = Image.open(io.BytesIO(contents))

                main_data, thumb_data = process_image_logic(input_img, target_format, create_thumbnails)

                base_name = file.filename.rsplit(".", 1)[0] if file.filename else "image"
                
                zip_file.writestr(f"optimized/{base_name}.{target_format}", main_data)
                
                if thumb_data:
                    zip_file.writestr(f"thumbnails/{base_name}_thumb.{target_format}", thumb_data)
            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")

    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"optimized_images_{target_format}.zip\""
        },
    )
