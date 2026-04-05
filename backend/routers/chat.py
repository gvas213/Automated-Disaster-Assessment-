import os
import openai
import json 
import math
import httpx
from pinecone import Pinecone
from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))

router = APIRouter()

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
    query_embedding = embed(query)
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True   #used for text and source (for testing can be removed later)
    )
    chunks = [r["metadata"]["text"] for r in results["matches"]]    #extract text from chunk
    sources = list(set([r["metadata"]["source"] for r in results["matches"]]))  #extract source file
    return chunks, sources

#geocode addresses into long/lat for location search tool
#uses OpenStreetMap
async def geocode_address(address: str):
    """Convert a street address to lat/lon using OpenStreetMap Nominatim (free, no API key)"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }

    headers = {"User-Agent": "harvey-disaster-assessment-chatbot"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    return None, None

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
    """Search for VLM assessments near a coordinate by fetching nearby vectors and filtering by distance"""
    
    #feature-type = type of building
    #damage - none, minor, etc
    location_query = f"feature_type damage location {lat:.5f} {lon:.5f}"
    query_embedding = embed(location_query)
    
    results = index.query(
        vector=query_embedding,
        top_k=50, 
        include_metadata=True
    )

    #calculate actual distance for every result and sort by closest
    candidates = []
    for r in results["matches"]:
        text = r["metadata"]["text"]
        try:
            parts = [p.strip() for p in text.split("|")]
            loc_part = next((p for p in parts if p.startswith("location:")), None)
            if not loc_part:
                continue
            coords = loc_part.replace("location:", "").strip().strip("()")
            stored_lat, stored_lon = [float(c.strip()) for c in coords.split(",")]
            distance = haversine_distance(lat, lon, stored_lat, stored_lon)
            candidates.append({
                "text": text,
                "source": r["metadata"]["source"],
                "distance_meters": round(distance, 2)
            })
        except Exception:
            continue

    # sort by distance and return closest matches within radius
    candidates.sort(key=lambda x: x["distance_meters"])
    matches = [c for c in candidates if c["distance_meters"] <= radius_meters]

    return matches

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
- When a user asks about damage at a specific address or coordinate, always use the search_by_location tool
- If no precise match is found within the assessed area, let the user know that location may not have 
  been captured in the VLM assessment data and suggest they try nearby coordinates
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