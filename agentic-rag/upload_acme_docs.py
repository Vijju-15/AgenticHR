"""Upload documents to acme_corp company."""

import os
from pathlib import Path
from loguru import logger

if not os.getenv('GOOGLE_API_KEY'):
    raise RuntimeError('Set GOOGLE_API_KEY in your environment before running this script')

from src.rag.multi_tenant_ingestion import multi_tenant_ingestion

def upload_acme_documents():
    """Upload documents to acme_corp company."""
    
    company_id = "acme_corp"
    
    # Get the knowledge base directory
    kb_dir = Path("data/knowledge_base")
    
    if not kb_dir.exists():
        logger.error(f"Knowledge base directory not found: {kb_dir}")
        return
    
    # Get all markdown files
    files = list(kb_dir.glob("*.md"))
    
    if not files:
        logger.warning(f"No markdown files found in {kb_dir}")
        return
    
    logger.info(f"Found {len(files)} files to upload to {company_id}")
    for file in files:
        logger.info(f"  - {file.name}")
    
    # Prepare file tuples (file_path, file_name, doc_type)
    # file_path should be a Path object, not a string
    file_tuples = [
        (f, f.name, "policy")  # doc_type is 'policy' for all these files
        for f in files
    ]
    
    # Upload to acme_corp
    result = multi_tenant_ingestion.ingest_multiple_files(
        company_id=company_id,
        files=file_tuples
    )
    
    # Display results
    print("\n" + "="*60)
    print(f"Upload Results for {company_id}")
    print("="*60)
    print(f"Status: {result['status']}")
    print(f"Files Processed: {result['files_processed']}")
    print(f"Total Chunks: {result['total_chunks']}")
    print("\nDetails:")
    for file_result in result['results']:
        if file_result['status'] == 'success':
            print(f"  ✓ {file_result['filename']}: {file_result['chunks_created']} chunks")
        else:
            print(f"  ✗ Error: {file_result.get('message', 'Unknown error')}")
    
    # Get company stats
    stats = multi_tenant_ingestion.get_company_stats(company_id)
    print("\nCompany Knowledge Base Stats:")
    print(f"  Company: {stats['company_name']}")
    print(f"  Collection: {stats['collection_name']}")
    print(f"  Total Documents: {stats['total_vectors']}")
    print("="*60)

if __name__ == "__main__":
    upload_acme_documents()
