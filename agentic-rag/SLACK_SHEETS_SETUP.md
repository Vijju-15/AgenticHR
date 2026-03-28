# 🔧 Slack & Google Sheets Integration Setup Guide

## 📊 Current Status

✅ **Core Workflow:** Working perfectly!  
⏸️ **Slack Integration:** Disabled (needs OAuth scopes)  
⏸️ **Google Sheets Integration:** Disabled (needs configuration)

---

## 🎯 Slack Integration Setup

### Step 1: Create a Slack App

1. Go to: https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name it: `Agentic RAG Bot`
4. Select your workspace

### Step 2: Add OAuth Scopes

1. In your Slack app, go to **"OAuth & Permissions"**
2. Scroll to **"Scopes"** → **"Bot Token Scopes"**
3. Click **"Add an OAuth Scope"** and add:
   - ✅ `chat:write` (Send messages as bot)
   - ✅ `chat:write.public` (Send messages to public channels)
   - ✅ `channels:read` (View basic channel info)

### Step 3: Install App to Workspace

1. Scroll to top of **"OAuth & Permissions"**
2. Click **"Install to Workspace"**
3. Authorize the app
4. **Copy the "Bot User OAuth Token"** (starts with `xoxb-`)

### Step 4: Configure in n8n

1. In n8n, go to **Credentials** → **Add Credential**
2. Select **"Slack OAuth2 API"**
3. Paste the **Bot User OAuth Token**
4. Save

### Step 5: Enable Slack Node

1. Open your workflow
2. Click on **"Send to Slack"** node
3. Uncheck **"Disabled"**
4. Select your Slack credential
5. Test with a channel like `#general`

---

## 📊 Google Sheets Integration Setup

### Step 1: Create a Google Sheets Document

1. Go to: https://docs.google.com/spreadsheets
2. Create a new spreadsheet: `RAG_Logs`
3. Create a sheet tab named: `RAG_Logs`
4. Add column headers in Row 1:
   - `timestamp`
   - `user_id`
   - `company_id`
   - `query`
   - `response`
   - `agent_type`

### Step 2: Get the Spreadsheet ID

From the URL:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
```
Copy the **SPREADSHEET_ID_HERE** part

### Step 3: Set Up Google Cloud OAuth

1. Go to: https://console.cloud.google.com
2. Create a new project or select existing
3. Enable **Google Sheets API**
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `https://YOUR_N8N_URL/rest/oauth2-credential/callback`

### Step 4: Configure in n8n

1. In n8n, go to **Credentials** → **Add Credential**
2. Select **"Google Sheets OAuth2 API"**
3. Enter Client ID and Client Secret from Google Cloud
4. Click **"Connect my account"**
5. Authorize access
6. Save

### Step 5: Set Environment Variable

In n8n, set:
```bash
GOOGLE_SHEETS_DOC_ID=your_spreadsheet_id_here
```

Or update the workflow JSON to use the ID directly.

### Step 6: Enable Google Sheets Node

1. Open your workflow
2. Click on **"Log to Google Sheets"** node
3. Uncheck **"Disabled"**
4. Select your Google Sheets credential
5. Select your spreadsheet

---

## 🚀 Quick Test Without Integrations

Your workflow **already works** without Slack and Google Sheets! Just:

1. Import the updated workflow
2. Add test input:
```json
{
  "message": "What is the leave policy?",
  "company_id": "acme_corp",
  "user_id": "test_user"
}
```
3. Execute!

You'll get the AI response in the **Log Interaction** node output.

---

## 📝 Alternative: Simple Logging Without Google Sheets

If you don't want to set up Google Sheets, you can:

1. Check the **n8n execution logs** - they're already being logged via `console.log`
2. Use the **Log Interaction** node output
3. Set up a different database (PostgreSQL, MySQL, etc.)

---

## ✅ Production Checklist

- [x] Core RAG system working
- [x] API endpoints functional
- [x] n8n workflow connected to API
- [x] Input validation working
- [x] Response formatting working
- [x] Console logging enabled
- [ ] Slack integration (optional)
- [ ] Google Sheets logging (optional)

---

## 🎉 Your System is Production Ready!

The core functionality is **fully operational**. Slack and Google Sheets are **nice-to-have** features that you can add later when you need them.

**Current Capabilities:**
✅ Multi-tenant RAG queries
✅ Agentic tool usage
✅ Session management
✅ Company isolation
✅ n8n workflow automation
✅ Console logging
