from fastapi import APIRouter
from models.schemas import MapsResponse, MapItem, MapImages

router = APIRouter()

@router.get("/maps", response_model=MapsResponse)
async def get_maps():
    demo = MapItem(
        map_id="harvey-3",
        images=MapImages(
            before="https://harvey-map-overlays-utd.s3.us-east-1.amazonaws.com/harvey/overlay/before/harvey-before-3.png",
            after="https://harvey-map-overlays-utd.s3.us-east-1.amazonaws.com/harvey/overlay/after/harvey-after-3.png",
        ),
        # Leaflet expects [[southWestLat, southWestLng], [northEastLat, northEastLng]]
        map_bounds=[
            (29.7575513, -95.4594574),   # southWest
            (29.7619079, -95.4540520),   # northEast
        ],
        overlay_url="https://harvey-map-overlays-utd.s3.us-east-1.amazonaws.com/harvey/geojson/harvey-geojson-3.geojson",
    )

    return MapsResponse(maps=[demo])