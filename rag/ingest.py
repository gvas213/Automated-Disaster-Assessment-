import os
import openai
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
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
    print(f"{len(pdf_files)} PDFs...")

    for doc_id, filename in enumerate(pdf_files):
        path = os.path.join(pdf_folder, filename)
        print(f"processing: {filename}")

        text = extract_text_from_pdf(path)
        chunks = chunk_text(text)

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