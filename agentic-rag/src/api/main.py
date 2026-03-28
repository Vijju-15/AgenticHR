"""FastAPI application for Multi-Tenant HR Assistant Agent."""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from loguru import logger
import uvicorn
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from src.config import settings
from src.config.company_manager import company_manager
from src.rag.multi_tenant_ingestion import multi_tenant_ingestion
from src.agents.multi_tenant_agentic_rag import multi_tenant_agent

app = FastAPI(
    title="Multi-Tenant HR Assistant Agent API",
    description="Dynamic HR Assistant supporting multiple companies",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.add(settings.log_file, rotation="500 MB", retention="10 days", level=settings.log_level)

class CompanyCreate(BaseModel):
    company_name: str = Field(..., description="Name of the company")
    company_id: Optional[str] = Field(None, description="Custom company ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CompanyResponse(BaseModel):
    company_id: str
    company_name: str
    created_at: str
    collection_name: str
    metadata: Dict[str, Any]

class QueryRequest(BaseModel):
    query: str = Field(..., description="User's question")
    company_id: str = Field(..., description="Company identifier")
    session_id: Optional[str] = Field(None)
    employee_id: Optional[str] = Field(None)

class QueryResponse(BaseModel):
    answer: str
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    tools_used: Optional[List[str]] = []
    session_id: Optional[str] = None
    confidence: Optional[float] = None
    status: str = "success"

class UploadResponse(BaseModel):
    status: str
    company_id: str
    filename: str
    chunks_stored: int
    message: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}

@app.post("/companies", response_model=CompanyResponse)
async def create_company(company: CompanyCreate):
    try:
        new_company = company_manager.create_company(
            company_name=company.company_name,
            company_id=company.company_id,
            metadata=company.metadata
        )
        return new_company
    except Exception as e:
        logger.error(f"Error creating company: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/companies", response_model=List[CompanyResponse])
async def list_companies():
    try:
        return company_manager.list_companies()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/companies/{company_id}")
async def get_company(company_id: str):
    """Get company details."""
    company = company_manager.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
    return company

@app.get("/companies/{company_id}/stats")
async def get_company_stats(company_id: str):
    """Get document statistics for a company."""
    try:
        company = company_manager.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
        
        stats = multi_tenant_ingestion.get_company_stats(company_id)
        return {
            "company_id": company_id,
            "company_name": company.company_name,
            **stats
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    company_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a company policy document."""
    try:
        # Verify company exists
        company = company_manager.get_company(company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {company_id} not found")
        
        # Save uploaded file temporarily
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            # Ingest document
            result = multi_tenant_ingestion.ingest_from_upload(
                company_id=company_id,
                file_path=Path(tmp_path),
                file_name=file.filename,
                doc_type=doc_type
            )
            
            return UploadResponse(
                status="success",
                company_id=company_id,
                filename=file.filename,
                chunks_stored=result["chunks_stored"],
                message=f"Document {file.filename} uploaded successfully for {company.company_name}"
            )
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    import asyncio
    from functools import partial
    try:
        context = {}
        if request.employee_id:
            context["employee_id"] = request.employee_id

        loop = asyncio.get_event_loop()
        fn = partial(
            multi_tenant_agent.query,
            query=request.query,
            company_id=request.company_id,
            session_id=request.session_id,
            context=context,
        )
        # Run the synchronous LLM call in a thread so it doesn't block the
        # event loop, and enforce a hard 80-second wall-clock timeout so a
        # hung Groq call never makes the server appear to hang indefinitely.
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(None, fn),
                timeout=80.0,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Query timed out for {request.company_id}: {request.query[:60]}")
            response = {
                "answer": "The request timed out while retrieving information. Please try again.",
                "company_id": request.company_id,
                "tools_used": [],
                "session_id": request.session_id or "default",
                "status": "timeout",
            }
        return response
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host=settings.api_host, port=settings.api_port, reload=True)
