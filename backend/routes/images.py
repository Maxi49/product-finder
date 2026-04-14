from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Annotated
from vision import process_images, VisionError

router = APIRouter()

SUPPORTED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


@router.post("/process-images")
async def process_images_endpoint(
    images: Annotated[list[UploadFile], File()]
):
    if len(images) == 0:
        raise HTTPException(status_code=422, detail="At least 1 image required")
    if len(images) > 3:
        raise HTTPException(status_code=422, detail="Maximum 3 images allowed")

    image_data = []
    for img in images:
        media_type = img.content_type or "image/jpeg"
        if media_type not in SUPPORTED_MEDIA_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported media type '{media_type}'. Allowed: {', '.join(sorted(SUPPORTED_MEDIA_TYPES))}",
            )
        content = await img.read()
        if len(content) == 0:
            raise HTTPException(status_code=422, detail=f"Image '{img.filename}' is empty")
        image_data.append((content, media_type))

    try:
        products, warnings = await process_images(image_data)
    except VisionError as e:
        status = 503 if e.retryable else 422
        raise HTTPException(status_code=status, detail=e.reason)

    response: dict = {"products": [p.model_dump() for p in products]}
    if warnings:
        response["warnings"] = warnings
    return response
