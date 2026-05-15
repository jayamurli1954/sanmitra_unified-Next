import asyncio
import fitz  # PyMuPDF
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.db.mongo import init_mongo, close_mongo
from app.modules.rag.service import ingest_document, ensure_rag_indexes
from app.modules.rag.schemas import RagIngestRequest, RagLegalMetadata

PDF_PATH = "d:/Documents/DPDP_Act.pdf"
TENANT_ID = "seed-tenant-1"
APP_KEY = "legalmitra"

async def ingest_pdf():
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF file not found at {PDF_PATH}")
        return

    print(f"Reading PDF: {PDF_PATH}...")
    doc = fitz.open(PDF_PATH)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    if not full_text.strip():
        print("Error: No text extracted from PDF.")
        return

    print(f"Extracted {len(full_text)} characters. Initializing database...")
    await init_mongo()
    await ensure_rag_indexes()

    payload = RagIngestRequest(
        title="The Digital Personal Data Protection Act, 2023",
        content=full_text,
        source_type="statute",
        source_uri="file://" + PDF_PATH,
        language="en",
        tags=["DPDP Act", "Statute", "Official"],
        legal_metadata=RagLegalMetadata(
            act_name="The Digital Personal Data Protection Act, 2023",
            jurisdiction="India",
            doc_date="2023-08-11"
        ),
        external_id="dpdp-act-2023-official"
    )

    try:
        print("Ingesting into RAG knowledge base...")
        result = await ingest_document(
            tenant_id=TENANT_ID,
            app_key=APP_KEY,
            created_by="system",
            payload=payload
        )
        print(f"Successfully ingested! Document ID: {result['document_id']}")
        print(f"Chunks created: {result['chunk_count']}")
    except Exception as e:
        if "external_id already exists" in str(e):
            print("Note: Document already exists in the knowledge base.")
        else:
            print(f"Error during ingestion: {e}")

    await close_mongo()

if __name__ == "__main__":
    asyncio.run(ingest_pdf())
