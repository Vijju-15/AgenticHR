# Test Unified n8n Workflow
# Tests all 8 task types + error handling through the unified Switch-based workflow

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  Testing Unified Provisioning Workflow" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location C:\AgenticHR

$tests = @(
    @{ Name = "Create HR Record";          File = "test-payloads/unified/test-hr-record.json";             ExpectError = $false },
    @{ Name = "Create IT Ticket";          File = "test-payloads/unified/test-it-ticket.json";             ExpectError = $false },
    @{ Name = "Assign Access Roles";       File = "test-payloads/unified/test-assign-access.json";         ExpectError = $false },
    @{ Name = "Generate Employee ID";      File = "test-payloads/unified/test-generate-id.json";           ExpectError = $false },
    @{ Name = "Create Email Account";      File = "test-payloads/unified/test-create-email.json";          ExpectError = $false },
    @{ Name = "Request Laptop";            File = "test-payloads/unified/test-request-laptop.json";        ExpectError = $false },
    @{ Name = "Schedule Induction";        File = "test-payloads/unified/test-schedule-induction.json";    ExpectError = $false },
    @{ Name = "Initiate Conversation";     File = "test-payloads/unified/test-initiate-conversation.json"; ExpectError = $false },
    @{ Name = "Error Handling (Unknown)";  File = "test-payloads/unified/test-error-handling.json";        ExpectError = $true }
)

$passed = 0
$failed = 0
$testNum = 1
$url = "http://localhost:5678/webhook/provisioning"

Write-Host "Webhook URL: $url" -ForegroundColor Gray
Write-Host ""

foreach ($test in $tests) {
    Write-Host "[$testNum/$($tests.Count)] $($test.Name)" -ForegroundColor Yellow -NoNewline

    try {
        $body = Get-Content $test.File -Raw
        $response = Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $body -ErrorAction Stop

        if ($test.ExpectError) {
            if ($response.status -eq "error") {
                Write-Host "  PASS" -ForegroundColor Green
                Write-Host "       Error handled: $($response.message)" -ForegroundColor Gray
                $passed++
            } else {
                Write-Host "  FAIL" -ForegroundColor Red
                Write-Host "       Expected error status but got: $($response.status)" -ForegroundColor Gray
                $failed++
            }
        } else {
            if ($response.status -eq "success") {
                Write-Host "  PASS" -ForegroundColor Green
                Write-Host "       Task: $($response.task_type)" -ForegroundColor Gray
                $passed++
            } else {
                Write-Host "  FAIL" -ForegroundColor Red
                Write-Host "       Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
                $failed++
            }
        }

    } catch {
        # Try to read error body for JSON status field
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $errorBody = $reader.ReadToEnd() | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($test.ExpectError -and $errorBody.status -eq 'error') {
                Write-Host "  PASS" -ForegroundColor Green
                Write-Host "       Error handled: $($errorBody.message)" -ForegroundColor Gray
                $passed++
            } elseif ($test.ExpectError) {
                Write-Host "  PASS" -ForegroundColor Green
                Write-Host "       HTTP error returned (expected for unknown task)" -ForegroundColor Gray
                $passed++
            } else {
                Write-Host "  FAIL" -ForegroundColor Red
                Write-Host "       Error: $($_.Exception.Message)" -ForegroundColor Gray
                $failed++
            }
        } catch {
            if ($test.ExpectError) {
                Write-Host "  PASS" -ForegroundColor Green
                Write-Host "       HTTP error returned (expected)" -ForegroundColor Gray
                $passed++
            } else {
                Write-Host "  FAIL" -ForegroundColor Red
                Write-Host "       Error: $($_.Exception.Message)" -ForegroundColor Gray
                $failed++
            }
        }
    }

    $testNum++
    Start-Sleep -Milliseconds 300
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Total:  $($tests.Count)" -ForegroundColor White
Write-Host "Passed: $passed" -ForegroundColor Green

if ($failed -gt 0) {
    Write-Host "Failed: $failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Some tests failed. Check the output above." -ForegroundColor Red
} else {
    Write-Host "Failed: $failed" -ForegroundColor Green
    Write-Host ""
    Write-Host "All tests passed! Unified workflow is working correctly." -ForegroundColor Green
}

Write-Host ""
Write-Host "View executions: http://localhost:5678/executions" -ForegroundColor Cyan
Write-Host ""
