"""Test cases for Orchestrator Agent functionality."""

import requests
import json
from datetime import datetime, timedelta

# API base URL
BASE_URL = "http://localhost:8001"


def test_health_check():
    """Test 1: Health Check"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_initiate_onboarding():
    """Test 2: Initiate Onboarding Workflow"""
    print("\n" + "="*60)
    print("TEST 2: Initiate New Employee Onboarding")
    print("="*60)
    
    # Calculate start date (7 days from now)
    start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    onboarding_request = {
        "tenant_id": "acme_corp",
        "employee_id": "EMP001",
        "employee_name": "John Doe",
        "employee_email": "john.doe@acmecorp.com",
        "role": "Software Engineer",
        "department": "Engineering",
        "start_date": start_date,
        "manager_id": "MGR001",
        "manager_email": "jane.manager@acmecorp.com",
        "metadata": {
            "location": "Remote",
            "employment_type": "Full-time",
            "team": "Backend Engineering",
            "level": "Senior"
        }
    }
    
    print("Request Payload:")
    print(json.dumps(onboarding_request, indent=2))
    print("\nSending request...")
    
    response = requests.post(
        f"{BASE_URL}/onboarding/initiate",
        json=onboarding_request
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        workflow = response.json()
        print("\n✅ Workflow Created Successfully!")
        print(f"Workflow ID: {workflow['workflow_id']}")
        print(f"Status: {workflow['status']}")
        print(f"Created At: {workflow['created_at']}")
        
        # Return workflow ID for subsequent tests
        return workflow['workflow_id']
    else:
        print(f"❌ Error: {response.text}")
        return None


def test_get_workflow(workflow_id):
    """Test 3: Retrieve Workflow Details"""
    print("\n" + "="*60)
    print("TEST 3: Get Workflow Details")
    print("="*60)
    
    if not workflow_id:
        print("⚠️  Skipping - No workflow ID available")
        return
    
    response = requests.get(f"{BASE_URL}/workflows/{workflow_id}")
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        workflow = response.json()
        print("\n✅ Workflow Retrieved!")
        print(f"Workflow ID: {workflow['workflow_id']}")
        print(f"Employee: {workflow['employee_name']}")
        print(f"Status: {workflow['status']}")
        print(f"Number of Tasks: {len(workflow.get('tasks', []))}")
        
        print("\nTasks Created:")
        for task in workflow.get('tasks', []):
            print(f"  - {task['task_type']} → {task['assigned_agent']} [{task['status']}]")
    else:
        print(f"❌ Error: {response.text}")


def test_list_workflows():
    """Test 4: List All Workflows"""
    print("\n" + "="*60)
    print("TEST 4: List All Workflows")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/workflows")
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        workflows = response.json()
        print(f"\n✅ Found {len(workflows)} workflow(s)")
        
        for wf in workflows:
            print(f"\n  Workflow: {wf['workflow_id']}")
            print(f"  Employee: {wf['employee_name']}")
            print(f"  Status: {wf['status']}")
            print(f"  Created: {wf['created_at']}")
    else:
        print(f"❌ Error: {response.text}")


def test_list_workflows_by_tenant():
    """Test 5: List Workflows by Tenant"""
    print("\n" + "="*60)
    print("TEST 5: List Workflows for Tenant 'acme_corp'")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/workflows?tenant_id=acme_corp")
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        workflows = response.json()
        print(f"\n✅ Found {len(workflows)} workflow(s) for acme_corp")
        
        for wf in workflows:
            print(f"  - {wf['employee_name']} ({wf['status']})")
    else:
        print(f"❌ Error: {response.text}")


def test_multiple_onboardings():
    """Test 6: Create Multiple Onboarding Workflows"""
    print("\n" + "="*60)
    print("TEST 6: Create Multiple Onboarding Workflows")
    print("="*60)
    
    employees = [
        {
            "employee_id": "EMP002",
            "employee_name": "Alice Smith",
            "employee_email": "alice.smith@acmecorp.com",
            "role": "Product Manager",
            "department": "Product"
        },
        {
            "employee_id": "EMP003",
            "employee_name": "Bob Johnson",
            "employee_email": "bob.johnson@acmecorp.com",
            "role": "DevOps Engineer",
            "department": "Engineering"
        }
    ]
    
    workflow_ids = []
    start_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    
    for emp in employees:
        request = {
            "tenant_id": "acme_corp",
            "employee_id": emp["employee_id"],
            "employee_name": emp["employee_name"],
            "employee_email": emp["employee_email"],
            "role": emp["role"],
            "department": emp["department"],
            "start_date": start_date,
            "manager_id": "MGR001",
            "manager_email": "jane.manager@acmecorp.com",
            "metadata": {"location": "Office", "employment_type": "Full-time"}
        }
        
        print(f"\nCreating workflow for {emp['employee_name']}...")
        response = requests.post(f"{BASE_URL}/onboarding/initiate", json=request)
        
        if response.status_code == 200:
            workflow = response.json()
            workflow_ids.append(workflow['workflow_id'])
            print(f"  ✅ {workflow['workflow_id']} - {workflow['status']}")
        else:
            print(f"  ❌ Failed: {response.text}")
    
    print(f"\n✅ Created {len(workflow_ids)} workflows")
    return workflow_ids


def run_all_tests():
    """Run all test cases"""
    print("\n" + "="*60)
    print("ORCHESTRATOR AGENT TEST SUITE")
    print("="*60)
    print("Testing MongoDB integration, Gemini AI planning, and API endpoints")
    
    # Test 1: Health Check
    if not test_health_check():
        print("\n❌ Health check failed. Is the agent running?")
        return
    
    # Test 2: Create first workflow
    workflow_id = test_initiate_onboarding()
    
    # Test 3: Retrieve workflow details
    test_get_workflow(workflow_id)
    
    # Test 4: List all workflows
    test_list_workflows()
    
    # Test 5: List by tenant
    test_list_workflows_by_tenant()
    
    # Test 6: Create multiple workflows
    test_multiple_onboardings()
    
    # Final summary
    print("\n" + "="*60)
    print("TEST SUITE COMPLETED")
    print("="*60)
    print("\n📊 What to Check Next:")
    print("1. MongoDB Compass - View 'agentichr' database")
    print("   - workflows collection (workflow records)")
    print("   - tasks collection (delegated tasks)")
    print("\n2. Redis - Check MCP message streams")
    print("   - agent_stream:provisioning_agent")
    print("   - agent_stream:scheduler_agent")
    print("   - agent_stream:liaison_agent")
    print("\n3. Logs - Check orchestrator.log for Gemini AI responses")
    print("   - Location: logs/orchestrator.log")
    print("\n⚠️  Note: Tasks will remain PENDING since other agents aren't built yet")


if __name__ == "__main__":
    try:
        run_all_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to Orchestrator Agent")
        print("Make sure the agent is running on http://localhost:8001")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
