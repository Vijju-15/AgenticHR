# Test All 8 n8n Workflows
# Comprehensive testing script for AgenticHR

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   Testing All 8 n8n Workflows" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test counter
$testNumber = 1

# Function to run test
function Run-Test {
    param(
        [string]$TestName,
        [string]$URL,
        [string]$PayloadFile
    )
    
    Write-Host "Test $script:testNumber: $TestName" -ForegroundColor Yellow
    Write-Host "URL: $URL" -ForegroundColor Gray
    Write-Host "Payload: $PayloadFile" -ForegroundColor Gray
    Write-Host ""
    
    curl.exe -X POST $URL -H "Content-Type: application/json" -d "@$PayloadFile"
    
    Write-Host "`n" -ForegroundColor Green
    Write-Host "-----------------------------------`n" -ForegroundColor DarkGray
    
    $script:testNumber++
    Start-Sleep -Milliseconds 500
}

Write-Host "SECTION A: Direct n8n Webhook Tests" -ForegroundColor Magenta
Write-Host "====================================`n" -ForegroundColor Magenta

# 1. Create HR Record
Run-Test `
    -TestName "Create HR Record (n8n direct)" `
    -URL "http://localhost:5678/webhook/create-hr-record" `
    -PayloadFile "test-payloads/test-webhook-hr.json"

# 2. Create IT Ticket
Run-Test `
    -TestName "Create IT Ticket (n8n direct)" `
    -URL "http://localhost:5678/webhook/create-it-ticket" `
    -PayloadFile "test-payloads/test-webhook-it-ticket.json"

# 3. Assign Access
Run-Test `
    -TestName "Assign Access (n8n direct)" `
    -URL "http://localhost:5678/webhook/assign-access" `
    -PayloadFile "test-payloads/test-webhook-access.json"

# 4. Generate Employee ID
Run-Test `
    -TestName "Generate Employee ID (n8n direct)" `
    -URL "http://localhost:5678/webhook/generate-employee-id" `
    -PayloadFile "test-payloads/test-webhook-generate-id.json"

# 5. Create Email
Run-Test `
    -TestName "Create Email Account (n8n direct)" `
    -URL "http://localhost:5678/webhook/create-email" `
    -PayloadFile "test-payloads/test-webhook-email.json"

# 6. Request Laptop
Run-Test `
    -TestName "Request Laptop (n8n direct)" `
    -URL "http://localhost:5678/webhook/request-laptop" `
    -PayloadFile "test-payloads/test-webhook-laptop.json"

# 7. Schedule Induction
Run-Test `
    -TestName "Schedule Induction (n8n direct)" `
    -URL "http://localhost:5678/webhook/schedule-induction" `
    -PayloadFile "test-payloads/test-webhook-schedule.json"

# 8. Initiate Conversation
Run-Test `
    -TestName "Initiate Conversation (n8n direct)" `
    -URL "http://localhost:5678/webhook/initiate-conversation" `
    -PayloadFile "test-payloads/test-webhook-conversation.json"

Write-Host "`nSECTION B: Provisioning Agent API Tests" -ForegroundColor Magenta
Write-Host "========================================`n" -ForegroundColor Magenta

# 9. Create HR Record via Agent
Run-Test `
    -TestName "Create HR Record (via Provisioning Agent)" `
    -URL "http://localhost:8003/api/v1/execute-task" `
    -PayloadFile "test-payloads/test-hr-record.json"

# 10. Assign Access via Agent
Run-Test `
    -TestName "Assign Access (via Provisioning Agent)" `
    -URL "http://localhost:8003/api/v1/execute-task" `
    -PayloadFile "test-payloads/test-assign-access.json"

# 11. Generate Employee ID via Agent
Run-Test `
    -TestName "Generate Employee ID (via Provisioning Agent)" `
    -URL "http://localhost:8003/api/v1/execute-task" `
    -PayloadFile "test-payloads/test-generate-id.json"

# 12. Create Email via Agent
Run-Test `
    -TestName "Create Email (via Provisioning Agent)" `
    -URL "http://localhost:8003/api/v1/execute-task" `
    -PayloadFile "test-payloads/test-create-email.json"

# 13. Request Laptop via Agent
Run-Test `
    -TestName "Request Laptop (via Provisioning Agent)" `
    -URL "http://localhost:8003/api/v1/execute-task" `
    -PayloadFile "test-payloads/test-request-laptop.json"

Write-Host "`nSECTION C: Full Orchestrator Workflow Test" -ForegroundColor Magenta
Write-Host "==========================================`n" -ForegroundColor Magenta

# 14. Complete Onboarding Workflow
Run-Test `
    -TestName "Complete Onboarding (Orchestrator → Provisioning → n8n)" `
    -URL "http://localhost:8001/onboarding/initiate" `
    -PayloadFile "test-payloads/test-onboarding.json"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "   Testing Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nTotal Tests Run: $($testNumber - 1)" -ForegroundColor Cyan
Write-Host "`nCheck n8n Executions page for results:" -ForegroundColor Yellow
Write-Host "http://localhost:5678 → Executions tab`n" -ForegroundColor White
