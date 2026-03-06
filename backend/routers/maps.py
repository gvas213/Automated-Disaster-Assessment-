from fastapi import APIRouter, HTTPException
import psycopg2
import os
from dotenv import load_dotenv

from models.schemas import MapsResponse, MapItem, MapImages

load_dotenv()
router = APIRouter()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

AWS_REGION = "us-east-2"

@router.get("/maps", response_model=MapsResponse)
async def get_maps():
    conn = None
    cur = None

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()

        cur.execute("""
            SELECT image_id, s3_bucket, img_name
            FROM images
            ORDER BY image_id ASC
            LIMIT 2;
        """)

        rows = cur.fetchall()

        if len(rows) < 2:
            raise HTTPException(status_code=404, detail="Not enough images found in database")

        first_image = rows[0]
        second_image = rows[1]

        after_url = f"https://{first_image[1]}.s3.{AWS_REGION}.amazonaws.com/{first_image[2]}"
        before_url = f"https://{second_image[1]}.s3.{AWS_REGION}.amazonaws.com/{second_image[2]}"

        demo = MapItem(
            map_id="harvey-3",
            images=MapImages(
                before=before_url,
                after=after_url,
            ),
            map_bounds=[
                (29.7575513, -95.4594574),
                (29.7619079, -95.4540520),
            ],
            overlay_url="https://harvey-map-overlays-utd.s3.us-east-1.amazonaws.com/harvey/geojson/harvey-geojson-3.geojson",
        )

        return MapsResponse(maps=[demo])

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()