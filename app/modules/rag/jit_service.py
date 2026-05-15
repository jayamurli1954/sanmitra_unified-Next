import asyncio
import logging
import httpx
import fitz  # PyMuPDF
from datetime import date
from typing import Optional

from app.services.legal_web_search import legal_web_search
from app.modules.rag.schemas import RagIngestRequest, RagLegalMetadata
from app.modules.rag.service import ingest_document

logger = logging.getLogger(__name__)

async def trigger_jit_ingestion(query: str, tenant_id: str, app_key: str):
    """
    Background task to identify and ingest the relevant Bare Act based on a query.
    Checks if the act is already present in the local RAG database first.
    """
    try:
        # 0. Basic Act Detection Keywords
        act_keywords = [
            "BNS", "BNSS", "BSA", "IPC", "CPC", "CRPC", "Income Tax", "GST", 
            "Contract Act", "Evidence Act", "Negotiable Instruments", "NI Act",
            "Cheque Bounce", "PMLA", "NDPS", "UAPA"
        ]
        
        detected_act = None
        for kw in act_keywords:
            if kw.lower() in query.lower():
                detected_act = kw
                break
        
        if not detected_act:
            # If no clear keyword, use the whole query to search later
            detected_act = query

        # 1. Check if we already have this act indexed for this tenant/app
        from app.db.mongo import get_collection
        docs_col = get_collection("rag_documents")
        
        # Search by title or legal_act_name
        existing = await docs_col.find_one({
            "tenant_id": tenant_id,
            "app_key": app_key,
            "$or": [
                {"title": {"$regex": f".*{detected_act}.*", "$options": "i"}},
                {"legal_act_name": {"$regex": f".*{detected_act}.*", "$options": "i"}}
            ]
        })
        
        if existing:
            print(f"JIT: Act '{detected_act}' already exists in local DB. Skipping search.")
            return

        # 2. Ask AI or Search Tavily for the relevant Bare Act
        print(f"JIT: Act '{detected_act}' not found. Searching external sources...")
        search_query = f"official bare act PDF or text for {detected_act} India"
        search_results = legal_web_search.search_legal_news(search_query, max_results=3)
        
        if not search_results["success"] or not search_results["results"]:
            return

        # 3. Find the most authoritative result (IndiaCode, Govt portals or direct PDF)
        best_result = None
        for res in search_results["results"]:
            url = res["url"].lower()
            if any(domain in url for domain in ["indiacode.nic.in", "egazette.nic.in", "legislative.gov.in"]):
                best_result = res
                break
        
        if not best_result:
            # Fallback to any result with a PDF or a strong title match
            for res in search_results["results"]:
                if res["url"].endswith(".pdf") or detected_act.lower() in res["title"].lower():
                    best_result = res
                    break
        
        if not best_result:
            return

        act_name = best_result["title"]
        source_uri = best_result["url"]

        # 4. Extract and Ingest
        print(f"JIT Ingestion triggered for: {act_name}")
        
        content = ""
        if source_uri.endswith(".pdf"):
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(source_uri)
                if resp.status_code == 200:
                    doc = fitz.open(stream=resp.content, filetype="pdf")
                    content = "".join([page.get_text() for page in doc])
                    doc.close()
        
        if not content:
            # Use Tavily summary if extraction failed or was not a PDF
            content = best_result.get("content") or best_result.get("summary", "")

        if len(content) < 500:
            print(f"JIT: Content too short ({len(content)} chars). Aborting.")
            return

        payload = RagIngestRequest(
            title=act_name,
            content=content,
            source_type="statute",
            source_uri=source_uri,
            language="en",
            tags=["jit-ingested", "statute", detected_act.lower()],
            legal_metadata=RagLegalMetadata(
                act_name=act_name,
                jurisdiction="India",
                doc_date=date.today()
            ),
            external_id=f"jit-act-{uuid4()}" # Use UUID to avoid collisions
        )

        from app.modules.rag.service import ingest_document
        await ingest_document(
            tenant_id=tenant_id,
            app_key=app_key,
            created_by="jit-bot",
            payload=payload
        )
        print(f"JIT Ingestion complete: {act_name}")

    except Exception as e:
        logger.error(f"JIT Ingestion failed for query '{query}': {e}")
