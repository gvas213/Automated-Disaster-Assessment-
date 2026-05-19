# RAG Ingestion Script

This script processes and loads documents into the PostgreSQL vector database used by the project's chatbot. It supports two document types: **PDF files** (news articles, reports, reference documents) and **GeoJSON files** (VLM damage assessment outputs).

---

## Setup

Install dependencies:

```bash
pip install openai psycopg2-binary pypdf tiktoken python-dotenv
```

Create a `.env` file in the same directory as `ingest.py`:

```
OPENAI_API_KEY=your-openai-key
DATABASE_URL=your-database-url
```

---

## Adding New PDF Documents

1. Place your PDF files in the `./docs` folder
2. In `ingest.py`, make sure the `if __name__` block at the bottom is set to run `ingest_pdfs`:

```python
if __name__ == "__main__":
    ingest_pdfs("./docs")
    # ingest_geojson("./docs/geojson_output1")
    # clear_geojson_data()
```

3. Run the script:

```bash
python3 ingest.py
```

The script will automatically skip any PDFs that have already been ingested, so it's safe to run multiple times without creating duplicates.

---

## Adding New GeoJSON Files

GeoJSON files are kept separate from PDFs so that VLM outputs can be updated independently without affecting the PDF knowledge base.

1. Place your GeoJSON files in `./docs/geojson_output1` (or update the folder path in `ingest_geojson`)
2. In `ingest.py`, comment out `ingest_pdfs` and uncomment `ingest_geojson`:

```python
if __name__ == "__main__":
    # ingest_pdfs("./docs")
    ingest_geojson("./docs/geojson_output1")
    # clear_geojson_data()
```

3. Run the script:

```bash
python3 ingest.py
```

The script will skip files that have already been ingested, so it's safe to point it at a folder that contains previously processed files alongside new ones.

---

## Clearing GeoJSON Data

When VLM outputs are updated and need to be re-ingested, use the `clear_geojson_data` function to remove all GeoJSON vectors without touching PDF data:

```python
if __name__ == "__main__":
    # ingest_pdfs("./docs")
    # ingest_geojson("./docs/geojson_output1")
    clear_geojson_data()
```

After clearing, re-run with `ingest_geojson` to load the updated files.

---

## Running on the Server

To avoid ingestion stopping if your SSH connection drops, run the script in the background using `nohup`:

```bash
nohup python3 ingest.py > ingest.log 2>&1 &
```

To monitor progress:

```bash
tail -f ingest.log
```

To check how many files have been ingested:

```bash
psql $DATABASE_URL -c "SELECT COUNT(DISTINCT source) FROM documents WHERE text LIKE '%feature_type%';"
```
