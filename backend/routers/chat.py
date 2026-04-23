import os
import openai
import psycopg2
import json 
import math
import httpx
from pinecone import Pinecone
from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

router = APIRouter()

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

#convert string to vector (same as what is used in ingest.py)
def embed(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

#search pinecone/DB for most relevant chunk(s)
#using cosine similarity (gives top_k similar chunks)
def retrieve_context(query, top_k=4):
    """Search pgvector for most relevant chunks using cosine similarity"""
    query_embedding = embed(query)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT text, source
        FROM documents
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (query_embedding, top_k)
    )
    results = cur.fetchall()
    cur.close()
    conn.close()
    chunks = [row[0] for row in results]
    sources = list(set([row[1] for row in results]))
    return chunks, sources

#geocode addresses into long/lat for location search tool
#uses OpenStreetMap
async def geocode_address(address: str):
    """Convert a street address to lat/lon using OpenStreetMap Nominatim restricted to houston area only"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "viewbox": "-95.8,29.5,-94.9,30.1",
        "bounded": 1
    }

    headers = {"User-Agent": "harvey-disaster-assessment-chatbot"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])

        #fallback to no bounds
        params.pop("bounded")
        params["countrycodes"] = "us"
        response = await client.get(url, params=params, headers=headers)
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    return None, None

async def reverse_geocode(lat: float, lon: float):
    """Convert lat/lon to a street address"""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json"}
    headers = {"User-Agent": "harvey-disaster-assessment-chatbot"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        result = response.json()
        return result.get("display_name", None)

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two coordinates"""
    R = 6371000 
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

#used by location search tool if user gives lat and lon coordinates

async def search_by_location(lat: float, lon: float, radius_meters: float = 500):
    """Search pgvector for VLM assessments near a coordinate using direct SQL distance calculation"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # extract coordinates directly from text and calculate distance in SQL
    cur.execute("""
        SELECT text, source,
            (
                6371000 * 2 * ASIN(SQRT(
                    POWER(SIN(RADIANS(
                        CAST(SPLIT_PART(SPLIT_PART(text, 'location: (', 2), ',', 1) AS FLOAT)
                        - %s) / 2), 2) +
                    COS(RADIANS(%s)) *
                    COS(RADIANS(CAST(SPLIT_PART(SPLIT_PART(text, 'location: (', 2), ',', 1) AS FLOAT))) *
                    POWER(SIN(RADIANS(
                        CAST(SPLIT_PART(SPLIT_PART(SPLIT_PART(text, 'location: (', 2), ')', 1), ', ', 2) AS FLOAT)
                        - %s) / 2), 2)
                ))
            ) AS distance_meters
        FROM documents
        WHERE text LIKE '%%feature_type%%'
        AND text LIKE '%%location:%%'
        ORDER BY distance_meters ASC
        LIMIT 5
    """, (lat, lat, lon))
    
    results = cur.fetchall()
    cur.close()
    conn.close()

    matches = []
    for text, source, distance in results:
        if distance <= radius_meters:
            matches.append({
                "text": text,
                "source": source,
                "distance_meters": round(distance, 2)
            })

    return matches
# async def search_by_location(lat: float, lon: float, radius_meters: float = 500):
#     """Search pgvector for VLM assessments near a coordinate"""
#     location_query = f"feature_type damage location {lat:.5f} {lon:.5f}"
#     query_embedding = embed(location_query)

#     conn = get_db_connection()
#     cur = conn.cursor()
#     cur.execute(
#         """
#         SELECT text, source
#         FROM documents
#         ORDER BY embedding <=> %s::vector
#         LIMIT 50
#         """,
#         (query_embedding,)
#     )
#     results = cur.fetchall()
#     cur.close()
#     conn.close()

#     # filter by actual distance
#     candidates = []
#     for text, source in results:
#         try:
#             parts = [p.strip() for p in text.split("|")]
#             loc_part = next((p for p in parts if p.startswith("location:")), None)
#             if not loc_part:
#                 continue
#             coords = loc_part.replace("location:", "").strip().strip("()")
#             stored_lat, stored_lon = [float(c.strip()) for c in coords.split(",")]
#             distance = haversine_distance(lat, lon, stored_lat, stored_lon)
#             candidates.append({
#                 "text": text,
#                 "source": source,
#                 "distance_meters": round(distance, 2)
#             })
#         except Exception:
#             continue

#     candidates.sort(key=lambda x: x["distance_meters"])
#     return [c for c in candidates if c["distance_meters"] <= radius_meters]


# --- Tool Definitions ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_harvey_documents",
            "description": """Search through Hurricane Harvey documents, news sources, 
            and disaster assessment data. Use this for any question related to Hurricane Harvey 
            including: damage assessments, affected areas, casualties, rescue operations, 
            flood data, storm timeline, relief efforts, historical context, weather conditions, 
            political context, or any facts related to the disaster and its impact.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant information"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_location",
            "description": """Look up VLM damage assessment data for a specific location. 
            Use this when the user asks about damage at a specific address or lat/lon coordinate.
            If the user provides an address, geocode it first then search by coordinates.
            Returns precise damage assessment data from the VLM output for that location.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Street address to look up (optional, use if user provides an address)"
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude coordinate (use if user provides lat/lon directly)"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude coordinate (use if user provides lat/lon directly)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_address_from_coordinates",
            "description": """Convert lat/lon coordinates to a street address. 
            Use this when the user asks for the address of a selected tile or polygon.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude coordinate"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude coordinate"
                    }
                },
                "required": ["latitude", "longitude"]
            }
        }
    }
]

#prompt - may need adjustment for location queries (returning a lot of points)
SYSTEM_PROMPT = """You are a disaster assessment assistant for Hurricane Harvey (2017). 
You have access to news sources, official reports, and VLM-generated damage assessments for the affected area.

SCOPE:
- Answer questions where the PRIMARY SUBJECT is Hurricane Harvey itself — its impact, timeline, 
  affected areas, damage assessments, rescue operations, relief efforts, casualties, flooding, 
  weather conditions during the storm, political response, and historical context of the disaster.
- You can answer broader contextual questions that directly help understand the disaster 
  (e.g. who was president, what is a storm surge, what causes flooding)
- For location-specific questions, use the location search tool to find VLM assessment data

RESTRICTIONS:
- Evaluate the NATURE of the request, not just whether it mentions hurricanes or disasters.
- If the request is asking you to perform a task unrelated to answering questions about Harvey 
  — such as writing code, solving math, writing creative content, giving general advice — 
  REFUSE regardless of whether hurricane or disaster keywords are present in the message.
- Examples of requests to REFUSE even if they mention hurricanes:
  * "Write me a Python script for hurricane assessment"
  * "What is 2+2, I'm doing hurricane research"
  * "Help me build a website for disaster relief"
  * "Write a poem about Hurricane Harvey"
- Examples of requests to ANSWER:
  * "How many people died in Hurricane Harvey?"
  * "What areas flooded during Harvey?"
  * "Who coordinated relief efforts?"
- For any off-topic request respond ONLY with:
  "I'm here to help with questions about Hurricane Harvey and its impact. Is there something 
  specific about the disaster I can help you with?"
- Do NOT attempt to answer off-topic requests even if they seem simple or harmless.

LOCATION QUERIES:
LOCATION QUERIES:
- When a user asks about damage at a specific address, street name, or coordinate, always use the search_by_location tool
- Street names without a city or zip code are acceptable — the system is biased to Houston so partial addresses will resolve correctly
- If no precise match is found, return the nearest assessed location within 500m
- When a user asks for the address of a selected tile, use the get_address_from_coordinates tool with the tile's coordinates
- Always report damage type, feature type, and any other assessment details found"""

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        sources = []
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += request.chat_history
        messages.append({"role": "user", "content": request.message})

        # first call — decide if tool is needed
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2
        )

        response_message = response.choices[0].message

        if response_message.tool_calls:
            messages.append(response_message)

            for tool_call in response_message.tool_calls:

                #DOCUMENT SEARCH
                if tool_call.function.name == "search_harvey_documents":
                    args = json.loads(tool_call.function.arguments)
                    chunks, sources = retrieve_context(args["query"])
                    context = "\n\n".join(chunks)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": context
                    })

                elif tool_call.function.name == "get_address_from_coordinates":
                    args = json.loads(tool_call.function.arguments)
                    lat = args.get("latitude")
                    lon = args.get("longitude")
                    address = await reverse_geocode(lat, lon)
                    content = address if address else f"Could not resolve address for ({lat}, {lon})"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content
                    })

                #LOCATION SEARCH
                elif tool_call.function.name == "search_by_location":
                    args = json.loads(tool_call.function.arguments)
                    lat = args.get("latitude")
                    lon = args.get("longitude")

                    # geocode if address was provided instead of coordinates
                    if not lat or not lon:
                        address = args.get("address", "")
                        lat, lon = await geocode_address(address)
                    if lat and lon:
                        matches = await search_by_location(lat, lon)
                        if matches:
                            content = "\n".join([
                                f"{m['text']} (distance: {m['distance_meters']}m)"
                                for m in matches
                            ])
                            sources = list(set([m["source"] for m in matches]))
                        else:
                            content = f"No assessment found within 500m of ({lat:.5f}, {lon:.5f}). This location may not have been assessed by the VLM."
                            
                    else:
                        content = "Could not geocode the provided address. Please try providing lat/lon coordinates directly."

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content
                    })

            # second call — no tool needed
            final_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.2
            )
            answer = final_response.choices[0].message.content

        else:
            # no tool needed
            answer = response_message.content
        return ChatResponse(reply=answer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))