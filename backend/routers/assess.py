import json
import os
import tempfile

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from v_client_1.client import assess_user_images

router = APIRouter()


@router.post("/assess")
async def assess(
    before: UploadFile = File(..., description="Pre-disaster image"),
    after: UploadFile = File(..., description="Post-disaster image"),
    polygon_coords: str = Form(
        None,
        description='Optional JSON array of [x, y] pixel coords marking the building footprint. e.g. [[10,20],[100,20],[100,80],[10,80]]',
    ),
):
    coords = None
    if polygon_coords:
        raw = json.loads(polygon_coords)
        coords = [tuple(pt) for pt in raw]

    with tempfile.TemporaryDirectory() as tmp:
        before_path = os.path.join(tmp, before.filename or "before.png")
        after_path = os.path.join(tmp, after.filename or "after.png")

        with open(before_path, "wb") as f:
            f.write(await before.read())
        with open(after_path, "wb") as f:
            f.write(await after.read())

        result = assess_user_images(before_path, after_path, polygon_coords=coords)

    return JSONResponse(content=result)
