# Gmail & Google Sheets Integration Setup Guide

This guide will help you set up Gmail and Google Sheets integrations for your n8n Agentic RAG workflow.

## Overview

The workflow now includes:
- **Gmail**: Sends formatted email notifications with RAG responses
- **Google Sheets**: Logs all interactions to a spreadsheet for analytics

---

## Prerequisites

- Google Account with Gmail enabled
- Access to Google Cloud Console
- n8n instance running

---

## Part 1: Google Cloud Project Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Enter project name: `n8n-agentic-rag`
4. Click **Create**

### Step 2: Enable Required APIs

1. In your project, go to **APIs & Services** → **Library**
2. Search and enable the following APIs:
   - **Gmail API**
   - **Google Sheets API**

### Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. If prompted, configure the OAuth consent screen first:
   - User Type: **External**
   - App name: `n8n Agentic RAG`
   - User support email: Your email
   - Developer contact: Your email
   - Click **Save and Continue**
   - Scopes: Add the following scopes:
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/spreadsheets`
   - Click **Save and Continue**
   - Test users: Add your email
   - Click **Save and Continue**

4. Back to **Create OAuth client ID**:
   - Application type: **Web application**
   - Name: `n8n OAuth Client`
   - Authorized redirect URIs: `https://your-n8n-domain.com/rest/oauth2-credential/callback`
     - For local testing: `http://localhost:5678/rest/oauth2-credential/callback`
   - Click **Create**

5. **Copy** the Client ID and Client Secret

---

## Part 2: n8n Gmail Credential Setup

### Step 1: Create Gmail OAuth2 Credential in n8n

1. In n8n, go to **Settings** → **Credentials**
2. Click **Add Credential**
3. Search for **Gmail OAuth2 API**
4. Fill in the details:
   - **Credential Name**: `Gmail - Agentic RAG`
   - **Client ID**: (paste from Google Cloud Console)
   - **Client Secret**: (paste from Google Cloud Console)
5. Click **Connect my account**
6. Sign in with your Google account
7. Grant the requested permissions
8. Click **Save**

### Step 2: Configure Gmail Node in Workflow

The Gmail node is already configured in the workflow. You just need to:

1. Open the workflow in n8n
2. Click on the **Send to Gmail** node
3. In the **Credential to connect with** dropdown, select your Gmail credential
4. Update the **Send To** field if needed:
   - Default: `={{ $json.user_email || 'admin@company.com' }}`
   - You can hardcode an email: `your-email@gmail.com`
   - Or use a dynamic field from your input

---

## Part 3: Google Sheets Setup

### Step 1: Create Google Spreadsheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new spreadsheet
3. Name it: `Agentic RAG Logs`
4. Rename the first sheet to: `RAG_Logs`
5. Add the following column headers in Row 1:
   - A1: `timestamp`
   - B1: `user_id`
   - C1: `company_id`
   - D1: `query`
   - E1: `response`
   - F1: `agent_type`

6. **Copy the Spreadsheet ID** from the URL:
   - URL format: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`
   - Example: If URL is `https://docs.google.com/spreadsheets/d/1ABC123xyz/edit`
   - Spreadsheet ID is: `1ABC123xyz`

### Step 2: Create Google Sheets OAuth2 Credential in n8n

1. In n8n, go to **Settings** → **Credentials**
2. Click **Add Credential**
3. Search for **Google Sheets OAuth2 API**
4. Fill in the details:
   - **Credential Name**: `Google Sheets - Agentic RAG`
   - **Client ID**: (same as Gmail)
   - **Client Secret**: (same as Gmail)
5. Click **Connect my account**
6. Sign in with your Google account
7. Grant the requested permissions
8. Click **Save**

### Step 3: Configure Google Sheets Node in Workflow

1. Open the workflow in n8n
2. Click on the **Log to Google Sheets** node
3. Select your Google Sheets credential
4. Set the **Document ID**:
   - Click on the field
   - Select **Expression**
   - Enter: `1ABC123xyz` (your spreadsheet ID)
   - Or use environment variable: `={{ $env.GOOGLE_SHEETS_DOC_ID }}`
5. Set the **Sheet Name**: `RAG_Logs`

---

## Part 4: Environment Variables (Optional)

If you want to use environment variables in n8n:

### Option 1: Docker Environment Variables

If running n8n in Docker, edit your `docker-compose.yml`:

```yaml
services:
  n8n:
    environment:
      - GOOGLE_SHEETS_DOC_ID=1ABC123xyz
      - GMAIL_DEFAULT_RECIPIENT=admin@company.com
```

### Option 2: n8n Environment File

Create a `.env` file in your n8n directory:

```bash
GOOGLE_SHEETS_DOC_ID=1ABC123xyz
GMAIL_DEFAULT_RECIPIENT=admin@company.com
```

Then restart n8n.

---

## Part 5: Testing the Integration

### Test Input Format

Use this JSON in the n8n manual trigger:

```json
{
  "message": "What is the leave policy?",
  "company_id": "acme_corp",
  "user_id": "test_user",
  "user_email": "your-email@gmail.com"
}
```

### Expected Results

1. **Gmail**: You should receive an email with:
   - Subject: "Agentic RAG Response - Acme Corporation"
   - Formatted HTML content with the query and answer
   - Company details and tools used

2. **Google Sheets**: A new row should be added with:
   - Current timestamp
   - User ID
   - Company ID
   - Query text
   - Response text
   - Agent type

---

## Troubleshooting

### Gmail Issues

**Error: "Insufficient Permission"**
- Go to Google Cloud Console → OAuth consent screen
- Add the scope: `https://www.googleapis.com/auth/gmail.send`
- Reconnect your credential in n8n

**Error: "Access blocked: n8n Agentic RAG has not completed the Google verification process"**
- For testing, add your email to **Test users** in OAuth consent screen
- For production, submit your app for verification

**Emails not sending**
- Check Gmail sent folder
- Verify the recipient email address is valid
- Check n8n execution logs for errors

### Google Sheets Issues

**Error: "Spreadsheet not found"**
- Verify the Spreadsheet ID is correct
- Ensure the Google account has access to the spreadsheet
- Make sure the spreadsheet is not in Trash

**Error: "Sheet not found"**
- Verify the sheet name is exactly `RAG_Logs` (case-sensitive)
- Check for extra spaces in the sheet name

**Rows not being added**
- Verify all column names match exactly
- Check the credentials are authorized
- Review n8n execution logs

---

## Alternative: Using Gmail App Password (Simpler but Less Secure)

If you prefer a simpler setup without OAuth:

1. Enable 2-Step Verification on your Google Account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate an app password for "Mail"
4. Use the **Gmail (SMTP)** credential in n8n instead of OAuth2:
   - User: your-email@gmail.com
   - Password: (16-character app password)

**Note**: This method only works for sending emails, not for Google Sheets.

---

## Security Best Practices

1. **OAuth Scopes**: Only grant the minimum required scopes
2. **Credentials**: Never share your Client Secret or OAuth tokens
3. **Access**: Limit access to the Google Spreadsheet to authorized users only
4. **Test Users**: Keep your app in testing mode unless you need public access
5. **Rotation**: Periodically rotate your OAuth credentials

---

## Workflow Input Schema

The workflow now accepts these fields:

```json
{
  "message": "string (required) - The user's query",
  "company_id": "string (required) - Company identifier",
  "user_id": "string (optional) - User identifier",
  "user_email": "string (optional) - Email for notifications",
  "session_id": "string (optional) - Session identifier"
}
```

---

## Production Considerations

### Rate Limits

- **Gmail API**: 
  - 15,000 quota units per minute per user
  - ~1 billion quota units per day
  - 1 send = 100 quota units
  - Limit: ~150,000 emails/day

- **Google Sheets API**:
  - 100 requests per 100 seconds per user
  - 500 requests per 100 seconds per project

### Optimization

1. **Batch Logging**: Consider batching Google Sheets updates
2. **Email Throttling**: Implement rate limiting for email notifications
3. **Error Handling**: Add retry logic for API failures
4. **Monitoring**: Set up alerts for failed executions

---

## Summary

You now have:
- ✅ Gmail integration for email notifications
- ✅ Google Sheets integration for interaction logging
- ✅ OAuth2 authentication for secure access
- ✅ Formatted HTML emails with query responses
- ✅ Automated logging to spreadsheet

All interactions are now:
1. Processed by the Agentic RAG system
2. Sent via email to the user
3. Logged to Google Sheets for analytics
4. Tracked with timestamps and metadata

For questions or issues, refer to the [n8n Gmail documentation](https://docs.n8n.io/integrations/builtin/credentials/google/) and [Google Sheets documentation](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.googlesheets/).
