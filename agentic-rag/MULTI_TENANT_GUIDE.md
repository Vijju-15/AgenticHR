# Multi-Tenant HR Assistant Guide

## 🎯 Overview

The Multi-Tenant HR Assistant allows **any company** to upload their own HR policies and get a personalized AI-powered assistant for onboarding freshers and interns. Each company's data is completely isolated, and the agent adapts to their specific policies.

## ✨ Key Features

- **Company Isolation**: Each company gets its own dedicated knowledge base (separate Qdrant collection)
- **Dynamic Document Upload**: Upload PDF, DOCX, TXT, or MD policy files
- **Personalized Agents**: Agent responses are tailored to each company's policies
- **N8N Integration Ready**: Special endpoints for workflow automation
- **Onboarding Focus**: Designed specifically for helping freshers/interns during onboarding

## 🚀 Quick Start

### 1. Start the Services

```powershell
# Start Qdrant (Vector Database)
docker-compose up -d qdrant

# Start the API
python -m uvicorn src.api.main:app --reload
```

### 2. Create a Company

```bash
curl -X POST "http://localhost:8000/companies" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme Corp",
    "company_id": "acme",
    "metadata": {
      "industry": "Technology",
      "size": "50-200"
    }
  }'
```

### 3. Upload Policy Documents

```bash
# Single file upload
curl -X POST "http://localhost:8000/upload" \
  -F "company_id=acme" \
  -F "file=@leave_policy.pdf" \
  -F "doc_type=leave_policy"

# Multiple files at once
curl -X POST "http://localhost:8000/upload-multiple" \
  -F "company_id=acme" \
  -F "files=@leave_policy.pdf" \
  -F "files=@working_hours.docx" \
  -F "files=@faq.md"
```

### 4. Query the Agent

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How many casual leave days do I get?",
    "company_id": "acme",
    "employee_id": "EMP001"
  }'
```

## 📋 API Endpoints

### Company Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/companies` | POST | Create a new company |
| `/companies` | GET | List all companies |
| `/companies/{id}` | GET | Get company details |
| `/companies/{id}` | DELETE | Delete a company |
| `/companies/{id}/stats` | GET | Get knowledge base statistics |

### Document Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload a single policy document |
| `/upload-multiple` | POST | Upload multiple documents at once |
| `/companies/{id}/documents` | DELETE | Clear all documents for a company |

### Agent Queries

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | POST | Ask the agent a question |

### N8N Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/n8n/onboard-company` | POST | Create company + upload docs in one call |
| `/n8n/company-ready/{id}` | GET | Check if company is ready to use |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | System metrics |

## 🔄 N8N Workflow Examples

### Example 1: Onboard New Company

**Workflow Steps:**
1. HR uploads company info + policy files via form
2. N8N calls `/n8n/onboard-company`
3. System creates company + processes documents
4. Send confirmation email to HR

**N8N HTTP Request Node Configuration:**
```json
{
  "url": "http://localhost:8000/n8n/onboard-company",
  "method": "POST",
  "bodyParameters": {
    "parameters": [
      {
        "name": "company_name",
        "value": "={{$json.companyName}}"
      },
      {
        "name": "company_id",
        "value": "={{$json.companyId}}"
      }
    ]
  },
  "sendBinaryData": true,
  "binaryPropertyName": "files"
}
```

### Example 2: Fresher Onboarding Assistant

**Workflow Steps:**
1. New employee joins (trigger from HR system)
2. N8N checks if company is ready: `/n8n/company-ready/{id}`
3. Send welcome email with chatbot link
4. Employee asks questions → N8N calls `/query`
5. Agent responds with company-specific answers

**Query Node:**
```json
{
  "url": "http://localhost:8000/query",
  "method": "POST",
  "body": {
    "query": "={{$json.userQuestion}}",
    "company_id": "={{$json.companyId}}",
    "employee_id": "={{$json.employeeId}}",
    "session_id": "={{$json.sessionId}}"
  }
}
```

## 📤 Supported Document Formats

- **PDF** (.pdf) - Best for formatted policy documents
- **Word** (.docx, .doc) - Editable policy documents
- **Text** (.txt) - Plain text policies
- **Markdown** (.md) - Structured documentation

## 🔒 Data Isolation

Each company's data is stored in a separate Qdrant collection:
- Collection naming: `hr_policies_{company_id}`
- No cross-company data leakage
- Company-specific retrieval and responses

## 💡 Use Cases

### 1. Fresher Onboarding
```
Employee: "What are the working hours?"
Agent: "At Acme Corp, working hours are 9 AM to 6 PM with flexible 
        arrival between 8:30-10:30 AM as per your leave policy."
```

### 2. Leave Policy Questions
```
Employee: "How do I apply for sick leave?"
Agent: "I can help you apply for sick leave. You have 10 sick leave 
        days available. Would you like to apply now? Please provide 
        the dates and reason."
```

### 3. Company-Specific FAQs
```
Employee: "Is remote work allowed?"
Agent: "According to Acme Corp's working hours policy, employees can 
        work from home up to 2 days per week with manager approval."
```

## 🛠️ Advanced Configuration

### Custom Metadata

Add custom metadata when creating a company:

```json
{
  "company_name": "Tech Startup Inc",
  "company_id": "techstartup",
  "metadata": {
    "industry": "SaaS",
    "employee_count": 25,
    "onboarding_coordinator": "hr@techstartup.com",
    "policy_version": "2024-v1",
    "custom_leave_rules": true
  }
}
```

### Batch Processing

For companies with many documents:

```python
import requests

company_id = "acme"
policy_files = [
    "leave_policy.pdf",
    "working_hours.docx",
    "code_of_conduct.pdf",
    "benefits_guide.pdf",
    "faq.md"
]

files = [('files', open(f, 'rb')) for f in policy_files]
response = requests.post(
    "http://localhost:8000/upload-multiple",
    files=files,
    data={"company_id": company_id}
)
```

## 🔍 Monitoring

### Check Company Status

```bash
curl http://localhost:8000/companies/acme/stats
```

**Response:**
```json
{
  "company_id": "acme",
  "collection_name": "hr_policies_acme",
  "total_vectors": 156,
  "indexed_documents": 3,
  "last_updated": "2024-01-15T10:30:00"
}
```

### System Metrics

```bash
curl http://localhost:8000/metrics
```

## 🚨 Troubleshooting

### Company Not Found
- **Issue**: `404: Company not found`
- **Solution**: Create company first using `/companies` endpoint

### No Documents Indexed
- **Issue**: Agent says "I don't have information about that"
- **Solution**: Upload policy documents using `/upload` endpoint
- **Check**: Call `/companies/{id}/stats` to verify documents are indexed

### File Upload Errors
- **Issue**: `400: Unsupported file type`
- **Solution**: Only PDF, DOCX, TXT, MD files are supported
- **Check**: Verify file extension

### Vector Database Connection
- **Issue**: `500: Error connecting to Qdrant`
- **Solution**: Start Qdrant with `docker-compose up -d qdrant`
- **Check**: Verify Qdrant is running on port 6333

## 📊 Example: Complete Company Setup

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# Step 1: Create Company
company_data = {
    "company_name": "Global Tech Solutions",
    "company_id": "globaltech",
    "metadata": {
        "industry": "IT Services",
        "size": "100-500"
    }
}
response = requests.post(f"{BASE_URL}/companies", json=company_data)
print(f"Company created: {response.json()}")

# Step 2: Upload Documents
files = [
    ('files', open('policies/leave_policy.pdf', 'rb')),
    ('files', open('policies/working_hours.docx', 'rb')),
    ('files', open('policies/faq.md', 'rb'))
]
response = requests.post(
    f"{BASE_URL}/upload-multiple",
    files=files,
    data={"company_id": "globaltech"}
)
print(f"Documents uploaded: {response.json()}")

# Step 3: Check Status
response = requests.get(f"{BASE_URL}/companies/globaltech/stats")
print(f"Company stats: {response.json()}")

# Step 4: Test Query
query_data = {
    "query": "How many casual leave days do I get?",
    "company_id": "globaltech",
    "employee_id": "EMP123"
}
response = requests.post(f"{BASE_URL}/query", json=query_data)
print(f"Agent response: {response.json()['answer']}")
```

## 🎓 Best Practices

1. **Company ID Naming**: Use lowercase, alphanumeric, no spaces (e.g., `acme_corp`)
2. **Document Organization**: Upload related policies in batches
3. **Document Types**: Always specify `doc_type` for better organization
4. **Error Handling**: Always check response status codes
5. **Testing**: Use `/health` endpoint to verify system is ready
6. **Sessions**: Use consistent `session_id` for multi-turn conversations

## 📝 Next Steps

1. **Add your Anthropic API key** to `.env` file:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

2. **Start Qdrant**:
   ```powershell
   docker-compose up -d qdrant
   ```

3. **Run the API**:
   ```powershell
   python -m uvicorn src.api.main:app --reload
   ```

4. **Open the interactive docs**:
   - http://localhost:8000/docs (Swagger UI)
   - http://localhost:8000/redoc (ReDoc)

5. **Create your first company and upload documents!**

## 🤝 Support

For issues or questions:
- Check the logs in `logs/hr_agent.log`
- Use `/health` endpoint to verify system status
- Check `/metrics` for system statistics
- Verify Qdrant is running: `docker ps | grep qdrant`

---

**Congratulations!** Your Multi-Tenant HR Assistant is ready to help freshers and interns across multiple companies! 🎉
