"""Test script for Orchestrator Agent."""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"


def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def test_initiate_onboarding():
    """Test onboarding initiation."""
    print("Testing onboarding initiation...")
    
    payload = {
        "tenant_id": "acme_corp",
        "employee_id": "EMP001",
        "employee_name": "Alice Johnson",
        "employee_email": "alice.johnson@acme.com",
        "role": "Software Engineer",
        "department": "Engineering",
        "start_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        "manager_id": "MGR001",
        "manager_email": "manager@acme.com",
        "metadata": {
            "location": "Remote",
            "employment_type": "Full-time"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/onboarding/initiate",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    
    if response.status_code == 200:
        return response.json()["workflow_id"]
    return None


def test_get_workflow(workflow_id):
    """Test get workflow details."""
    print(f"Testing get workflow {workflow_id}...")
    
    response = requests.get(f"{BASE_URL}/workflows/{workflow_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_list_workflows():
    """Test list workflows."""
    print("Testing list workflows...")
    
    response = requests.get(f"{BASE_URL}/workflows?limit=10")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_task_result():
    """Test receiving task result."""
    print("Testing task result submission...")
    
    payload = {
        "task_id": "TASK_test123",
        "workflow_id": "WF_test_xxx",
        "tenant_id": "acme_corp",
        "from_agent": "provisioning_agent",
        "status": "success",
        "result": {
            "hris_record_id": "HRIS_12345",
            "created_at": datetime.now().isoformat()
        },
        "error": None,
        "retry_possible": True
    }
    
    response = requests.post(
        f"{BASE_URL}/tasks/result",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


if __name__ == "__main__":
    print("=" * 50)
    print("Orchestrator Agent Test Suite")
    print("=" * 50)
    print()
    
    try:
        # Test health
        test_health()
        
        # Test onboarding initiation
        workflow_id = test_initiate_onboarding()
        
        if workflow_id:
            # Test get workflow
            import time
            time.sleep(2)  # Wait for processing
            test_get_workflow(workflow_id)
        
        # Test list workflows
        test_list_workflows()
        
        print("=" * 50)
        print("All tests completed!")
        print("=" * 50)
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to Orchestrator Agent")
        print("Make sure the service is running on http://localhost:8001")
    except Exception as e:
        print(f"ERROR: {e}")
