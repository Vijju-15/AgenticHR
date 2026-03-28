"""
Copy documents to legacy collection for fair comparison
"""
from src.rag.ingestion import run_ingestion

if __name__ == "__main__":
    print(f"\n{'='*80}")
    print("SETTING UP LEGACY COLLECTION FOR FAIR COMPARISON")
    print(f"{'='*80}\n")
    
    print("Running ingestion for legacy hr_policies collection...")
    run_ingestion()
    
    print(f"\n{'='*80}")
    print("SETUP COMPLETE!")
    print("Legacy collection populated with documents")
    print(f"{'='*80}\n")
