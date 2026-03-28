"""Verify MongoDB data after running tests."""

from pymongo import MongoClient
import json
from datetime import datetime


def verify_mongodb():
    """Connect to MongoDB and display stored data."""
    print("\n" + "="*60)
    print("MONGODB DATA VERIFICATION")
    print("="*60)
    
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017")
    db = client["agentichr"]
    
    # Check workflows collection
    print("\n📋 WORKFLOWS COLLECTION:")
    print("-" * 60)
    workflows = list(db.workflows.find())
    
    if not workflows:
        print("⚠️  No workflows found")
    else:
        print(f"Found {len(workflows)} workflow(s)\n")
        
        for wf in workflows:
            print(f"Workflow ID: {wf['workflow_id']}")
            print(f"  Tenant: {wf['tenant_id']}")
            print(f"  Employee: {wf['employee_name']} ({wf['employee_email']})")
            print(f"  Role: {wf['role']} - {wf['department']}")
            print(f"  Status: {wf['status']}")
            print(f"  Start Date: {wf['start_date']}")
            print(f"  Created: {wf['created_at']}")
            if wf.get('metadata'):
                print(f"  Metadata: {json.dumps(wf['metadata'], indent=4)}")
            print()
    
    # Check tasks collection
    print("\n📝 TASKS COLLECTION:")
    print("-" * 60)
    tasks = list(db.tasks.find())
    
    if not tasks:
        print("⚠️  No tasks found")
    else:
        print(f"Found {len(tasks)} task(s)\n")
        
        # Group by workflow
        from collections import defaultdict
        tasks_by_workflow = defaultdict(list)
        
        for task in tasks:
            tasks_by_workflow[task['workflow_id']].append(task)
        
        for workflow_id, task_list in tasks_by_workflow.items():
            print(f"Workflow: {workflow_id}")
            for task in task_list:
                print(f"  ✓ Task: {task['task_id']}")
                print(f"    Type: {task['task_type']}")
                print(f"    Agent: {task['assigned_agent']}")
                print(f"    Status: {task['status']}")
                print(f"    Payload: {json.dumps(task.get('payload', {}), indent=6)}")
                print(f"    Retry Count: {task['retry_count']}/{task['max_retries']}")
                print()
    
    # Collection statistics
    print("\n📊 STATISTICS:")
    print("-" * 60)
    print(f"Total Workflows: {db.workflows.count_documents({})}")
    print(f"Total Tasks: {db.tasks.count_documents({})}")
    print(f"\nWorkflows by Status:")
    for status in ["CREATED", "INITIATED", "PROVISIONING_PENDING", "SCHEDULING_PENDING", "ACTIVE", "COMPLETED", "FAILED"]:
        count = db.workflows.count_documents({"status": status})
        if count > 0:
            print(f"  {status}: {count}")
    
    print(f"\nTasks by Status:")
    for status in ["PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "RETRYING"]:
        count = db.tasks.count_documents({"status": status})
        if count > 0:
            print(f"  {status}: {count}")
    
    # Index information
    print("\n🔍 INDEXES:")
    print("-" * 60)
    print("Workflows Collection:")
    for idx in db.workflows.list_indexes():
        print(f"  - {idx['name']}: {list(idx['key'].keys())}")
    
    print("\nTasks Collection:")
    for idx in db.tasks.list_indexes():
        print(f"  - {idx['name']}: {list(idx['key'].keys())}")
    
    client.close()


if __name__ == "__main__":
    try:
        verify_mongodb()
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("Make sure MongoDB is running on localhost:27017")
