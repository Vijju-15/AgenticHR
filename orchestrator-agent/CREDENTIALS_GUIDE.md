# Getting Credentials for Orchestrator Agent

## 1. Google Gemini API Key

### Steps to Get Gemini API Key:

1. Go to **Google AI Studio**: https://aistudio.google.com/app/apikey

2. Sign in with your Google account

3. Click **"Get API Key"** or **"Create API Key"**

4. Select or create a Google Cloud project

5. Copy the API key (format: `AIzaSy...`)

6. Paste it in your `.env` file:
   ```
   GOOGLE_API_KEY=your-google-api-key-here
   ```

### Important Notes:
- **Free tier**: 15 requests per minute, 1500 requests per day
- **Gemini 2.0 Flash (Experimental)** is free during preview
- Keep your API key secret - never commit to Git
- Monitor usage at: https://aistudio.google.com/

### Pricing (if you exceed free tier):
- Gemini 2.0 Flash: $0.10 per 1M tokens (input), $0.40 per 1M tokens (output)
- Check latest pricing: https://ai.google.dev/pricing

---

## 2. PostgreSQL Setup

### Option A: Local Installation

1. **Download PostgreSQL**:
   - Go to: https://www.postgresql.org/download/windows/
   - Download installer (recommended: PostgreSQL 15 or 16)
   - Run installer

2. **During Installation**:
   - Set a strong password for `postgres` user
   - Note the port (default: 5432)
   - Complete installation

3. **Create Database**:
   ```powershell
   # Open psql
   psql -U postgres
   
   # Create database
   CREATE DATABASE agentichr;
   
   # Exit
   \q
   ```

4. **Update .env**:
   ```
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=agentichr
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password_here
   DATABASE_URL=postgresql://postgres:your_password_here@localhost:5432/agentichr
   ```

### Option B: Docker

```powershell
docker run -d \
  --name agentichr-postgres \
  -e POSTGRES_DB=agentichr \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  postgres:15-alpine
```

---

## 3. Redis Setup

### Option A: Docker (Recommended for Windows)

```powershell
docker run -d \
  --name agentichr-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### Option B: Windows Native

1. Download Redis for Windows:
   - https://github.com/microsoftarchive/redis/releases
   - Download `Redis-x64-xxx.msi`

2. Install and start Redis service

3. Verify:
   ```powershell
   redis-cli ping
   # Should return: PONG
   ```

### Update .env:
```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

---

## 4. n8n Setup (for External Tool Execution)

### Docker Setup:

```powershell
docker run -d \
  --name agentichr-n8n \
  -p 5678:5678 \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=admin \
  n8nio/n8n
```

### Access n8n:
- URL: http://localhost:5678
- Create workflows for:
  - HRIS integration
  - IT ticketing
  - Email notifications
  - Calendar scheduling

### Update .env:
```
N8N_BASE_URL=http://localhost:5678
N8N_APPROVAL_WEBHOOK=/webhook/approval
N8N_NOTIFICATION_WEBHOOK=/webhook/notification
```

---

## 5. Complete .env Configuration

Your final `.env` should look like:

```env
# Gemini AI
GOOGLE_API_KEY=your-google-api-key-here
GEMINI_MODEL=gemini-2.0-flash-exp

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=agentichr
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://postgres:your_secure_password@localhost:5432/agentichr

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
API_WORKERS=2

# Service URLs (will be configured later)
GUIDE_AGENT_URL=http://localhost:8000
LIAISON_AGENT_URL=http://localhost:8002
PROVISIONING_AGENT_URL=http://localhost:8003
SCHEDULER_AGENT_URL=http://localhost:8004

# n8n
N8N_BASE_URL=http://localhost:5678
N8N_APPROVAL_WEBHOOK=/webhook/approval
N8N_NOTIFICATION_WEBHOOK=/webhook/notification

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/orchestrator.log

# Environment
ENVIRONMENT=development

# Task Configuration
MAX_TASK_RETRIES=2
TASK_TIMEOUT_SECONDS=300
```

---

## 6. Verify Setup

### Check all services are running:

```powershell
# Check PostgreSQL
Test-NetConnection -ComputerName localhost -Port 5432

# Check Redis
Test-NetConnection -ComputerName localhost -Port 6379

# Check n8n
Test-NetConnection -ComputerName localhost -Port 5678
```

### Test Gemini API:

```python
import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash-exp")
response = model.generate_content("Hello!")
print(response.text)
```

---

## Cost Estimation

### Free Tier Usage:
- **Gemini 2.0 Flash**: 15 RPM, 1500 RPD (free during preview)
- **PostgreSQL**: Self-hosted (free)
- **Redis**: Self-hosted (free)
- **n8n**: Self-hosted (free)

### If you need more:
- **Google Cloud**: Start with $300 free credit
- **Managed PostgreSQL**: Consider Supabase (free tier), Railway ($5/month)
- **Managed Redis**: Upstash (free tier), Redis Cloud (free tier)
- **n8n Cloud**: $20/month (or keep self-hosted free)

---

## Security Notes

1. **Never commit .env to Git** - already in `.gitignore`
2. **Use strong passwords** for PostgreSQL
3. **Rotate API keys** regularly
4. **Enable authentication** for production deployments
5. **Use environment-specific configs** for dev/staging/prod

---

## Troubleshooting

### "Connection refused" errors:
- Verify service is running
- Check port is not in use
- Check firewall settings

### "Invalid API key":
- Verify key is correct in .env
- Check API key is enabled in Google Cloud
- Verify billing is enabled (if needed)

### Database connection errors:
- Verify PostgreSQL is running
- Check DATABASE_URL format
- Test connection with psql

---

## Next Steps

After setup:
1. Run `setup.ps1` to install dependencies
2. Verify all credentials in `.env`
3. Start the service: `python -m uvicorn src.main:app --reload --port 8001`
4. Test with: `python test_orchestrator.py`
5. Check logs: `logs/orchestrator.log`

