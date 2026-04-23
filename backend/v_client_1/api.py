"""Sample FastAPI app for v_client_1 damage assessment.

Run with:
    uvicorn v_client_1.api:app --reload
"""

import os
import tempfile

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import json

from v_client_1.client import assess_user_images

app = FastAPI(title="Earthdial Damage Assessment API")


@app.post("/assess")
async def assess(
    before: UploadFile = File(..., description="Pre-disaster image"),
    after: UploadFile = File(..., description="Post-disaster image"),
    polygon_coords: str = Form(
        None,
        description='Optional JSON array of [x, y] pixel coords marking the building footprint. e.g. [[10,20],[100,20],[100,80],[10,80]]',
    ),
):
    """Assess hurricane damage from before/after satellite images.

    Returns a human-readable damage report with cost estimate.
    """
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


@app.get("/health")
def health():
    return {"status": "ok"}
