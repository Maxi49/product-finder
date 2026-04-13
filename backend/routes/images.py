from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Annotated
from vision import process_images

router = APIRouter()


@router.post("/process-images")
async def process_images_endpoint(
    images: Annotated[list[UploadFile], File()]
):
    if len(images) > 3:
        raise HTTPException(status_code=422, detail="Maximum 3 images allowed")
    if len(images) == 0:
        raise HTTPException(status_code=422, detail="At least 1 image required")

    image_data = []
    for img in images:
        content = await img.read()
        media_type = img.content_type or "image/jpeg"
        image_data.append((content, media_type))

    products = await process_images(image_data)
    return {"products": [p.model_dump() for p in products]}
