# Test All AgenticHR Workflows
# Run this after importing all n8n workflows

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   Testing AgenticHR Workflows" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test 1: Direct n8n Webhook
Write-Host "Test 1: n8n Webhook - Create HR Record" -ForegroundColor Yellow
curl.exe -X POST http://localhost:5678/webhook/create-hr-record `
  -H "Content-Type: application/json" `
  -d "@test-payloads/test-webhook-hr.json"
Write-Host "`n"

# Test 2: Provisioning Agent API
Write-Host "Test 2: Provisioning Agent - Execute Task" -ForegroundColor Yellow
curl.exe -X POST http://localhost:8003/api/v1/execute-task `
  -H "Content-Type: application/json" `
  -d "@test-payloads/test-hr-record.json"
Write-Host "`n"

# Test 3: Orchestrator - Full Workflow
Write-Host "Test 3: Orchestrator - Initiate Onboarding" -ForegroundColor Yellow
curl.exe -X POST http://localhost:8001/onboarding/initiate `
  -H "Content-Type: application/json" `
  -d "@test-payloads/test-onboarding.json"
Write-Host "`n"

Write-Host "========================================" -ForegroundColor Green
Write-Host "   Testing Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green
