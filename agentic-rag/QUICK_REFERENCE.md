# 🚀 Quick Reference Card

## Essential Commands

### Setup
```powershell
.\setup.ps1                          # Automated setup
```

### Start Qdrant
```powershell
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

### Start API
```powershell
python -m src.api.main              # Development mode
uvicorn src.api.main:app --reload  # With auto-reload
```

### Ingest Documents
```powershell
python -m src.rag.ingestion
```

### Run Tests
```powershell
pytest tests/ -v
```

### Docker
```powershell
cd docker
docker-compose up -d                # Start all services
docker-compose logs -f hr-agent     # View logs
docker-compose down                 # Stop services
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/query` | POST | Query agent |
| `/compare` | POST | Compare both agents |
| `/metrics` | GET | Get metrics |
| `/ingest` | POST | Re-ingest documents |
| `/docs` | GET | API documentation |

## Sample Requests

### Simple Query
```json
POST /query
{
  "query": "How many casual leaves do I get?",
  "agent_type": "conversational"
}
```

### Action Query
```json
POST /query
{
  "query": "Apply sick leave for 2024-12-01 to 2024-12-03",
  "employee_id": "EMP123",
  "agent_type": "agentic"
}
```

### Compare
```json
POST /compare
{
  "query": "What is the leave policy?",
  "employee_id": "EMP123"
}
```

## Environment Variables

```bash
ANTHROPIC_API_KEY=        # Your Claude API key
MODEL_NAME=               # claude-3-5-sonnet-20241022
QDRANT_HOST=localhost
QDRANT_PORT=6333
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## File Locations

```
.env                      # Configuration
data/knowledge_base/      # Add policy documents here
data/employee_db.json     # Employee data (mock)
logs/hr_assistant.log     # Application logs
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Qdrant connection error | `docker restart qdrant` |
| No documents retrieved | `python -m src.rag.ingestion` |
| API key error | Check `.env` has `ANTHROPIC_API_KEY` |
| Import errors | `pip install -r requirements.txt --upgrade` |

## URLs

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Qdrant**: http://localhost:6333
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

## Agent Types

| Type | Capabilities |
|------|-------------|
| `conversational` | Q&A only, no actions |
| `agentic` | Q&A + actions (leave, email, etc.) |

## Tools Available (Agentic Only)

- `query_company_policy` - Search policies
- `check_leave_balance` - Check remaining leaves
- `apply_leave` - Apply for leave
- `get_leave_history` - View past leaves
- `get_holiday_calendar` - Get holidays
- `calculate_working_days` - Calculate days
- `send_email` - Send notifications
- `is_working_day` - Check if working day
- `get_upcoming_holidays` - Next holidays

## Quick Test

```powershell
# Test health
curl http://localhost:8000/health

# Test query
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d '{"query":"How many casual leaves?","agent_type":"agentic"}'
```

## File Structure

```
src/
├── agents/         # RAG implementations
├── rag/           # Document processing
├── tools/         # Agent tools
├── api/           # FastAPI app
└── config/        # Settings

data/
├── knowledge_base/  # Policy docs
└── test_cases/      # Test data
```

## Need Help?

1. Check [README.md](README.md)
2. Check [QUICKSTART.md](QUICKSTART.md)
3. View API docs: http://localhost:8000/docs
4. Check logs: `logs/hr_assistant.log`

---
**Version**: 1.0.0 | **Last Updated**: Nov 2024
