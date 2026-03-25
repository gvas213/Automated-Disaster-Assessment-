import os
import openai
import json
from pinecone import Pinecone, ServerlessSpec
from pypdf import PdfReader
import tiktoken
from dotenv import load_dotenv

load_dotenv()

#temporarily using pinecone while testing will move to our DB when complete
openai.api_key = os.getenv("OPENAI_API_KEY")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = os.getenv("PINECONE_INDEX")

#check if the pinecone index exists
# if not create one
if INDEX_NAME not in [index.name for index in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=os.getenv("PINECONE_ENVIRONMENT"))
    )

index = pc.Index(INDEX_NAME)

#extract info from pdfs in /docs
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

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

def embed(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

#traverse /docs for pdfs -> read and chunk pdfs as found
# create vectors per chunk
def ingest_pdfs(pdf_folder):
    all_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf") or f.endswith(".json")  or f.endswith(".geojson")]
    print(f"{len(all_files)} files found...")

    for doc_id, filename in enumerate(all_files):
        path = os.path.join(pdf_folder, filename)
        print(f"processing: {filename}")

        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(path)
            chunks = chunk_text(text)
        elif filename.endswith(".json") or filename.endswith(".geojson"):
            chunks = extract_text_from_json(path)

        
        

        vectors = []
        for i, chunk in enumerate(chunks):
            embedding = embed(chunk)
            vectors.append({
                "id": f"doc{doc_id}_chunk{i}",
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "source": filename
                }
            })
        #add vectors to pinecone db (this will be changed slightly to align with backend)
        for j in range(0, len(vectors), 100):
            index.upsert(vectors=vectors[j:j+100])

        print(f"  → uploaded {len(vectors)} paragraphs from {filename}")

    print("complete")

if __name__ == "__main__":
    ingest_pdfs("./docs")