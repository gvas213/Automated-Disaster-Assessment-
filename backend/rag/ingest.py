import os
import json
import openai
import psycopg2
import tiktoken
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

#db connection
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def embed(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding
    
# --- PDF EXTRACTION ---
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

#adjusted to chunk by paragraph
#ignore headings/subheadings (no useful context)
def chunk_text(text, max_tokens=500):
    enc = tiktoken.get_encoding("cl100k_base")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()] #spliting on paragraph breaks
    paragraphs = [p for p in paragraphs if len(p.split()) > 20] #filter headers/sub-headings
    
    chunks = []
    for paragraph in paragraphs:
        tokens = enc.encode(paragraph)
        if len(tokens) <= max_tokens:
            chunks.append(paragraph)
        else:           #found some paragraphs are too long, default to chunk by tokens
            for i in range(0, len(tokens), max_tokens):
                chunk = enc.decode(tokens[i:i + max_tokens])
                chunks.append(chunk)
    return chunks

# --- GEOJSON EXTRACTION ---

#extract from json files
def extract_text_from_json(json_path):
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

        if data.get("type") == "FeatureCollection":
            chunks = []
            for feature in data["features"]:
                props = feature.get("properties", {})
                
                # skip entries with no useful damage info
                if not props.get("damage_type") and not props.get("feature_type"):
                    continue
                
                # pull coordinates to give location context
                coords = feature.get("geometry", {}).get("coordinates", [[[]]])[0][0]
                lat, lon = coords[1], coords[0]

                # build a readable string per feature
                chunk = (
                    f"feature_type: {props.get('feature_type', 'unknown')} | "
                    f"damage_type: {props.get('damage_type', 'unknown')} | "
                    f"cost_usd: {props.get('cost_usd', 'unknown')} | "
                    f"description: {props.get('description', 'none')} | "
                    f"uid: {props.get('uid', 'unknown')} | "
                    f"location: ({lat:.5f}, {lon:.5f})"
                )
                chunks.append(chunk)
            return chunks

        if isinstance(data, list):
            return [" | ".join(f"{k}: {v}" for k, v in item.items()) for item in data]
        
        #single object catch (not likely to happen based on VLM outputs)
        return [" | ".join(f"{k}: {v}" for k, v in data.items())]
    
# --- INSERT INTO PGVECTOR ---
def insert_chunks(chunks, source):
    conn = get_db_connection()
    cur = conn.cursor()
    for chunk in chunks:
        embedding = embed(chunk)
        cur.execute(
            "INSERT INTO documents (text, source, embedding) VALUES (%s, %s, %s)",
            (chunk, source, embedding)
        )
    conn.commit()
    cur.close()
    conn.close()

# --- INGESTION FUNCTIONS ---
# --- PDF INGESTION ---
# --- PDF INGESTION ---
# run this now against your /docs folder
def ingest_pdfs(pdf_folder="./docs"):
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
    print(f"{len(pdf_files)} PDFs found...")

    for filename in pdf_files:
        path = os.path.join(pdf_folder, filename)
        print(f"processing: {filename}")
        text = extract_text_from_pdf(path)
        chunks = chunk_text(text)
        insert_chunks(chunks, filename)
        print(f"  → inserted {len(chunks)} chunks from {filename}")

    print("PDF ingestion complete!")

# --- GEOJSON INGESTION ---
# run this separately once VLM outputs are finalized
def ingest_geojson(json_folder="./docs"):
    json_files = [f for f in os.listdir(json_folder) if f.endswith(".json") or f.endswith(".geojson")]
    print(f"{len(json_files)} GeoJSON files found...")

    for filename in json_files:
        path = os.path.join(json_folder, filename)
        print(f"processing: {filename}")
        chunks = extract_text_from_json(path)
        insert_chunks(chunks, filename)
        print(f"  → inserted {len(chunks)} chunks from {filename}")

    print("GeoJSON ingestion complete!")

# --- DELETE GEOJSON DATA ONLY ---
# run this to clear VLM data without touching PDF data
def clear_geojson_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM documents WHERE source LIKE '%.geojson' OR source LIKE '%.json'")
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"Deleted {deleted} GeoJSON vectors from documents table")

if __name__ == "__main__":
    # comment/uncomment whichever you need to run
    ingest_pdfs("./docs")
    # ingest_geojson("./docs")
    # clear_geojson_data()