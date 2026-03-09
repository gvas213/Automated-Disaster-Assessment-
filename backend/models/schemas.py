from pydantic import BaseModel, Field
from typing import List, Optional, Union, Tuple

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

LatLng = Union[Tuple[float, float], List]

class MapImages(BaseModel):
    before: str
    after: str

class MapItem(BaseModel):
    map_id: str
    images: MapImages

    map_bounds: Optional[List[LatLng]] = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="Image bounds as [[top_left_lat, top_left_lng], [bottom_right_lat, bottom_right_lng]]"
    )

    overlay_url: Optional[str] = None

class MapsResponse(BaseModel):
    maps: List[MapItem]