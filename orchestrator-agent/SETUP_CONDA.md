# Quick Setup Guide for Conda Environment

## **Option 1: No Docker Required (Simpler)**

### Step 1: Activate your conda environment
```cmd
conda activate agenticHR
```

### Step 2: Install dependencies
```cmd
cd C:\AgenticHR\orchestrator-agent
pip install -r requirements.txt
```

### Step 3: Configure .env file
1. Copy `.env.example` to `.env`
2. Edit `.env` and add:
   - `GOOGLE_API_KEY=your_key_here` (Get from: https://aistudio.google.com/app/apikey)
   - `POSTGRES_PASSWORD=your_password`
   - Update `DATABASE_URL` with your password

### Step 4: Install Redis & PostgreSQL

#### Redis (Choose one):
**Option A - Windows Native:**
- Download: https://github.com/tporadowski/redis/releases
- Install and start Redis service

**Option B - Cloud (Free):**
- Upstash: https://upstash.com/ (free tier)
- Update in `.env`: `REDIS_HOST=your-upstash-url`

**Option C - WSL:**
```bash
wsl
sudo apt update && sudo apt install redis-server
sudo service redis-server start
```

#### PostgreSQL (Choose one):
**Option A - Windows Native:**
- Download: https://www.postgresql.org/download/windows/
- Install PostgreSQL
- Create database:
  ```sql
  psql -U postgres
  CREATE DATABASE agentichr;
  \q
  ```

**Option B - Cloud (Free):**
- Supabase: https://supabase.com/ (free tier)
- Get connection string and update `DATABASE_URL` in `.env`

**Option C - WSL:**
```bash
wsl
sudo apt update && sudo apt install postgresql
sudo service postgresql start
sudo -u postgres psql -c "CREATE DATABASE agentichr;"
```

### Step 5: Start the agent
```cmd
# Using CMD (recommended)
start-conda.cmd

# Or using PowerShell
start-conda.ps1
```

---

## **Option 2: Using Docker (If you have Docker Desktop)**

### Install Docker Desktop
1. Download: https://www.docker.com/products/docker-desktop
2. Install and start Docker Desktop
3. Wait for it to fully start (check system tray)

### Start services with Docker
```powershell
# Start Redis
docker run -d --name agentichr-redis -p 6379:6379 redis:7-alpine

# Start PostgreSQL
docker run -d --name agentichr-postgres `
  -e POSTGRES_DB=agentichr `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=your_password `
  -p 5432:5432 `
  postgres:15-alpine
```

### Then start the agent
```cmd
conda activate agenticHR
start-conda.cmd
```

---

## **Testing**

```powershell
# Check health
curl http://localhost:8001/health

# Or open in browser
start http://localhost:8001/docs
```

---

## **Stop Services**

### Stop Orchestrator Agent:
- Press `Ctrl+C` in the terminal

### Stop Docker containers (if using Docker):
```powershell
docker stop agentichr-redis agentichr-postgres
docker rm agentichr-redis agentichr-postgres
```

### Stop native services:
- Redis: Stop from Services (Windows) or `sudo service redis-server stop` (WSL)
- PostgreSQL: Stop from Services (Windows) or `sudo service postgresql stop` (WSL)

---

## **Recommended Approach for Development**

For simplest setup without Docker:

1. **Use cloud services (FREE)**:
   - **Redis**: Upstash (https://upstash.com/)
   - **PostgreSQL**: Supabase (https://supabase.com/)

2. **Update .env**:
   ```env
   GOOGLE_API_KEY=AIza...your_key
   
   # Upstash Redis
   REDIS_HOST=your-redis-url.upstash.io
   REDIS_PORT=6379
   REDIS_PASSWORD=your_upstash_password
   
   # Supabase PostgreSQL
   DATABASE_URL=postgresql://postgres:your_password@db.your-project.supabase.co:5432/postgres
   ```

3. **Start agent**:
   ```cmd
   conda activate agenticHR
   cd C:\AgenticHR\orchestrator-agent
   start-conda.cmd
   ```

**This way you don't need Docker at all!** ✅
