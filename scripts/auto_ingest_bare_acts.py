import asyncio
import os
import sys
import httpx
import fitz  # PyMuPDF
from datetime import date
from typing import List, Dict, Any

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.config import get_settings
from app.db.mongo import init_mongo, close_mongo
from app.services.legal_web_search import legal_web_search
from app.modules.rag.service import ingest_document, ensure_rag_indexes
from app.modules.rag.schemas import RagIngestRequest, RagLegalMetadata

# The "Big 50" + New Sanhitas
ACTS_TO_INGEST = [
    "Bharatiya Nyaya Sanhita 2023",
    "Bharatiya Nagarik Suraksha Sanhita 2023",
    "Bharatiya Sakshya Adhiniyam 2023",
]

async def download_pdf(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

async def ingest_act(act_name: str):
    print(f"\n--- Processing: {act_name} ---")
    
    # 1. Search for the official PDF or full text
    search_query = f"{act_name} official bare act full text pdf indiacode"
    print(f"Searching for: {search_query}")
    
    search_results = legal_web_search.search_legal_news(search_query, max_results=3)
    
    if not search_results["success"] or not search_results["results"]:
        print(f"Failed to find results for {act_name}")
        return

    # 2. Try to find a PDF link first
    best_result = None
    for res in search_results["results"]:
        if res["url"].endswith(".pdf") or "indiacode.nic.in" in res["url"]:
            best_result = res
            break
    
    if not best_result:
        best_result = search_results["results"][0]

    print(f"Found best source: {best_result['url']}")

    content = ""
    source_uri = best_result["url"]

    # 3. Handle PDF if found
    if source_uri.endswith(".pdf"):
        try:
            print("Downloading PDF...")
            pdf_bytes = await download_pdf(source_uri)
            content = extract_text_from_pdf_bytes(pdf_bytes)
            print(f"Extracted {len(content)} characters from PDF.")
        except Exception as e:
            print(f"PDF download/extraction failed: {e}")
            content = best_result.get("summary", "")
    else:
        # Fallback to Tavily's extracted content
        content = best_result.get("summary", "")
        print(f"Using web summary ({len(content)} characters).")

    if len(content) < 500:
        print(f"Warning: Content too short for {act_name}. Skipping.")
        return

    # 4. Ingest into RAG
    payload = RagIngestRequest(
        title=act_name,
        content=content,
        source_type="statute",
        source_uri=source_uri,
        language="en",
        tags=["bare-act", "official", "auto-synced", "statute"],
        legal_metadata=RagLegalMetadata(
            act_name=act_name,
            jurisdiction="India",
            doc_date=date.today() # Will update manually if needed
        ),
        external_id=f"auto-act-{act_name.lower().replace(' ', '-')}",
        chunk_size=1500,
        chunk_overlap=150
    )

    try:
        result = await ingest_document(
            tenant_id="seed-tenant-1",
            app_key="legalmitra",
            created_by="auto-sync-bot",
            payload=payload
        )
        print(f"Successfully ingested {act_name}! Document ID: {result['document_id']}")
    except Exception as e:
        if "already exists" in str(e):
            print(f"Act {act_name} already exists in knowledge base.")
        else:
            print(f"Ingestion failed for {act_name}: {e}")

async def main():
    await init_mongo()
    await ensure_rag_indexes()
    
    for idx, act in enumerate(ACTS_TO_INGEST):
        try:
            if idx > 0:
                print("Waiting 5 seconds for rate limit safety...")
                await asyncio.sleep(5)
            await ingest_act(act)
        except Exception as e:
            print(f"Critical error processing {act}: {e}")
    
    await close_mongo()

if __name__ == "__main__":
    asyncio.run(main())
