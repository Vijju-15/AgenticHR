"""Company management for multi-tenant support."""

from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
import json
from pathlib import Path
from loguru import logger


class Company(BaseModel):
    """Company model."""
    company_id: str
    company_name: str
    created_at: str
    collection_name: str
    metadata: Dict = {}
    

class CompanyManager:
    """Manages multiple companies and their knowledge bases."""
    
    def __init__(self):
        """Initialize company manager."""
        self.companies_file = Path("data/companies.json")
        self.companies_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing companies
        self.companies = self._load_companies()
    
    def _load_companies(self) -> Dict[str, Company]:
        """Load companies from file."""
        if self.companies_file.exists():
            with open(self.companies_file, 'r') as f:
                data = json.load(f)
                return {
                    cid: Company(**cdata) 
                    for cid, cdata in data.items()
                }
        return {}
    
    def _save_companies(self):
        """Save companies to file."""
        with open(self.companies_file, 'w') as f:
            data = {
                cid: company.model_dump() 
                for cid, company in self.companies.items()
            }
            json.dump(data, f, indent=2)
    
    def create_company(
        self, 
        company_name: str, 
        company_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Company:
        """
        Create a new company with isolated knowledge base.
        
        Args:
            company_name: Name of the company
            company_id: Optional custom company ID
            metadata: Optional metadata (industry, size, etc.)
            
        Returns:
            Company object
        """
        if company_id is None:
            # Generate ID from name
            company_id = company_name.lower().replace(" ", "_").replace("-", "_")
        
        # Check if already exists
        if company_id in self.companies:
            logger.warning(f"Company {company_id} already exists")
            return self.companies[company_id]
        
        # Create company
        company = Company(
            company_id=company_id,
            company_name=company_name,
            created_at=datetime.now().isoformat(),
            collection_name=f"hr_policies_{company_id}",
            metadata=metadata or {}
        )
        
        self.companies[company_id] = company
        self._save_companies()
        
        logger.info(f"Created company: {company_name} ({company_id})")
        return company
    
    def get_company(self, company_id: str) -> Optional[Company]:
        """Get company by ID."""
        return self.companies.get(company_id)
    
    def list_companies(self) -> List[Company]:
        """List all companies."""
        return list(self.companies.values())
    
    def delete_company(self, company_id: str) -> bool:
        """Delete a company."""
        if company_id in self.companies:
            del self.companies[company_id]
            self._save_companies()
            logger.info(f"Deleted company: {company_id}")
            return True
        return False
    
    def update_company_metadata(
        self, 
        company_id: str, 
        metadata: Dict
    ) -> Optional[Company]:
        """Update company metadata."""
        if company_id in self.companies:
            self.companies[company_id].metadata.update(metadata)
            self._save_companies()
            return self.companies[company_id]
        return None


# Global company manager instance
company_manager = CompanyManager()
