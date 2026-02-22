from pydantic import BaseModel, Field
from typing import List, Optional, Tuple

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

# exactly two numbers per coordinate
LatLng = Tuple[float, float]

class MapImages(BaseModel):
    before: str
    after: str

class MapItem(BaseModel):
    map_id: str
    images: MapImages

    # Two bounds: [[top_left], [bottom_right]]
    map_bounds: List[LatLng] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Image bounds as [[top_left_lat, top_left_lng], [bottom_right_lat, bottom_right_lng]]"
    )

    overlay_url: Optional[str] = None

class MapsResponse(BaseModel):
    maps: List[MapItem]