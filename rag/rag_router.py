import os
import openai
import json 
import math
import httpx
from pinecone import Pinecone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))

router = APIRouter()

#models for request and response 
class ChatRequest(BaseModel):
    message: str    #user query
    chat_history: list[dict] = []   #prev msgs 

class ChatResponse(BaseModel):
    answer: str #llm response
    sources: list[str]  #pdfs used to answer

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
    R = 6371000  # earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

async def search_by_location(lat: float, lon: float, radius_meters: float = 20):
    """Search Pinecone vectors for a precise coordinate match within a tight radius"""
    # embed a location string to find matching vectors
    location_query = f"location: ({lat:.5f}, {lon:.5f})"
    query_embedding = embed(location_query)
    
    results = index.query(
        vector=query_embedding,
        top_k=10,  # cast wider net then filter by distance
        include_metadata=True
    )

    matches = []
    for r in results["matches"]:
        text = r["metadata"]["text"]
        # extract stored coordinates from metadata text
        try:
            loc_part = [p for p in text.split("|") if "location" in p][0]
            coords = loc_part.replace("location:", "").strip().strip("()")
            stored_lat, stored_lon = map(float, coords.split(","))
            distance = haversine_distance(lat, lon, stored_lat, stored_lon)
            if distance <= radius_meters:  # strict match within 20 meters
                matches.append({
                    "text": text,
                    "source": r["metadata"]["source"],
                    "distance_meters": round(distance, 2)
                })
        except Exception:
            continue

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

#prompt - needs adjustment to use RAG as tool
SYSTEM_PROMPT = """You are a disaster assessment assistant for Hurricane Harvey (2017). 
You have access to news sources, official reports, and VLM-generated damage assessments for the affected area.

SCOPE:
- Answer any question related to Hurricane Harvey, its impact, timeline, affected areas, damage assessments, 
  rescue operations, relief efforts, and surrounding context (weather, political climate, historical comparisons, etc.)
- You can answer broader contextual questions that help understand the disaster (e.g. who was president, 
  what was the regional weather like, what is a storm surge)
- For location-specific questions, use the location search tool to find VLM assessment data

RESTRICTIONS:
- If a question has absolutely no connection to Hurricane Harvey or its context, respond with:
  "I'm here to help with questions about Hurricane Harvey and its impact. Is there something specific 
  about the disaster I can help you with?"
- Never say you cannot answer something unless it is completely unrelated to the disaster
- Always search before saying you don't have information — the answer may be in the documents

LOCATION QUERIES:
- When a user asks about damage at a specific address or coordinate, always use the search_by_location tool
- If no precise match is found within the assessed area, let the user know that location may not have 
  been captured in the VLM assessment data and suggest they try nearby coordinates
- Always report damage type, feature type, and any other assessment details found"""

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        sources = []
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += request.chat_history
        messages.append({"role": "user", "content": request.message})

        # first call — let OpenAI decide which tool to use if any
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

                # --- RAG document search ---
                if tool_call.function.name == "search_harvey_documents":
                    args = json.loads(tool_call.function.arguments)
                    chunks, sources = retrieve_context(args["query"])
                    context = "\n\n".join(chunks)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": context
                    })

                # --- Location search ---
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
                            content = "\n".join([m["text"] for m in matches])
                            sources = list(set([m["source"] for m in matches]))
                        else:
                            content = f"No VLM assessment data found within 20 meters of ({lat:.5f}, {lon:.5f}). The location may not have been captured in the assessment."
                    else:
                        content = "Could not geocode the provided address. Please try providing lat/lon coordinates directly."

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content
                    })

            # second call — generate final answer with tool results
            final_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.2
            )
            answer = final_response.choices[0].message.content

        else:
            # no tool needed — answered directly
            answer = response_message.content

        return ChatResponse(answer=answer, sources=sources)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))