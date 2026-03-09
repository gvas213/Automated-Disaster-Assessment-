from pathlib import Path
import json

from fastapi import APIRouter
from models.schemas import MapsResponse

router = APIRouter()

MAPS_FILE = Path(__file__).resolve().parent.parent / "data" / "maps.json"

with open(MAPS_FILE, "r", encoding="utf-8") as f:
    MAPS_DATA = MapsResponse(**json.load(f))

@router.get("/maps", response_model=MapsResponse)
async def get_maps():
    return MAPS_DATA