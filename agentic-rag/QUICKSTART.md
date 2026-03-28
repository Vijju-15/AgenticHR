# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Automated Setup (Recommended)

```powershell
# Run the setup script
.\setup.ps1
```

This will:
- ✅ Check dependencies
- ✅ Create virtual environment
- ✅ Install all packages
- ✅ Start Qdrant database
- ✅ Ingest knowledge base

### Option 2: Manual Setup

#### 1. Set API Key

```powershell
# Copy environment file
cp .env.example .env

# Edit .env and add your Anthropic API key
# ANTHROPIC_API_KEY=your_key_here
```

#### 2. Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

#### 3. Start Qdrant

```powershell
# Using Docker
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant
```

#### 4. Ingest Documents

```powershell
python -m src.rag.ingestion
```

#### 5. Start API

```powershell
python -m src.api.main
```

## 📝 First Query

Open your browser:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

Or use curl:

```powershell
curl -X POST "http://localhost:8000/query" `
  -H "Content-Type: application/json" `
  -d '{
    "query": "How many casual leaves do I get per year?",
    "agent_type": "agentic"
  }'
```

## 🎯 Example Queries

### Information Queries
```json
{
  "query": "What is the leave policy?",
  "agent_type": "conversational"
}
```

### Action Queries (Agentic Only)
```json
{
  "query": "Check leave balance for employee EMP123",
  "employee_id": "EMP123",
  "agent_type": "agentic"
}
```

```json
{
  "query": "Apply sick leave from 2024-12-01 to 2024-12-03",
  "employee_id": "EMP123",
  "agent_type": "agentic"
}
```

## 🐳 Docker Quick Start

```powershell
cd docker
docker-compose up -d
```

All services will start:
- API: http://localhost:8000
- Qdrant: http://localhost:6333
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## 🧪 Run Tests

```powershell
pytest tests/ -v
```

## 📊 Compare Both Agents

```powershell
curl -X POST "http://localhost:8000/compare" `
  -H "Content-Type: application/json" `
  -d '{
    "query": "What holidays are there this month?",
    "employee_id": "EMP123"
  }'
```

## 🛠️ Troubleshooting

**Qdrant Connection Error?**
```powershell
docker ps | grep qdrant
docker restart qdrant
```

**Import Errors?**
```powershell
pip install -r requirements.txt --upgrade
```

**Need to re-ingest documents?**
```powershell
python -m src.rag.ingestion
```

## 📚 Next Steps

1. Read the full [README.md](README.md)
2. Explore API docs at `/docs`
3. Add your own policy documents to `data/knowledge_base/`
4. Customize tools in `src/tools/`
5. Integrate with N8N workflows

## 🎉 You're Ready!

Your HR Assistant Agent is now running and ready to help with:
- ✅ Answering policy questions
- ✅ Checking leave balances
- ✅ Applying for leaves
- ✅ Viewing holiday calendars
- ✅ And much more!

Enjoy! 🚀
