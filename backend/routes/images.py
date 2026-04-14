import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Annotated
from vision import process_images, VisionTimeoutError, VisionAPIError, VisionParseError

logger = logging.getLogger(__name__)

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

    products, errors = await process_images(image_data)

    if errors and not products:
        first = errors[0]
        if isinstance(first, VisionTimeoutError):
            raise HTTPException(status_code=504, detail="Vision processing timed out. Try again with fewer or smaller images.")
        if isinstance(first, VisionAPIError):
            status = 503 if first.status_code is None else first.status_code
            raise HTTPException(status_code=status, detail=f"Vision API error: {first}")
        if isinstance(first, VisionParseError):
            logger.error("All images returned unparseable responses")
            raise HTTPException(status_code=502, detail="Vision service returned an unexpected response. Please try again.")
        raise HTTPException(status_code=500, detail="Vision processing failed for all images.")

    response: dict = {"products": [p.model_dump() for p in products]}

    if errors:
        response["warnings"] = [
            {"image_index": i, "error": type(e).__name__, "detail": str(e)}
            for i, e in enumerate(errors)
        ]

    return response
