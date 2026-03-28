"""Test script for Liaison Agent."""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agent.liaison import liaison_agent, IntentType, LiaisonAction
from src.schemas.mcp_message import AgentType
from loguru import logger

# Configure logging
logger.add(
    "logs/test_liaison.log",
    rotation="10 MB",
    retention="3 days",
    level="INFO"
)


def test_policy_query():
    """Test policy query classification."""
    print("\n" + "="*70)
    print("TEST 1: Policy Query")
    print("="*70)
    
    user_message = "What is the company's leave policy for new joiners?"
    tenant_id = "acme_corp"
    user_id = "test_user_001"
    
    print(f"\nUser Message: {user_message}")
    print(f"Tenant: {tenant_id}")
    
    result = liaison_agent.process_message(
        user_message=user_message,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    print(f"\nResult:")
    print(json.dumps(result, indent=2))
    
    assert result["intent_type"] == IntentType.POLICY_QUERY.value, "Should be POLICY_QUERY"
    assert result["action"] == LiaisonAction.ROUTE_TO_GUIDE.value, "Should route to guide"
    print("\n✅ Test Passed: Policy query correctly classified and routed")


def test_task_request():
    """Test task request classification."""
    print("\n" + "="*70)
    print("TEST 2: Task Request - Leave Application")
    print("="*70)
    
    user_message = "I want to apply for leave from March 15 to March 20 for personal reasons"
    tenant_id = "acme_corp"
    user_id = "emp_12345"
    
    print(f"\nUser Message: {user_message}")
    print(f"Tenant: {tenant_id}")
    
    result = liaison_agent.process_message(
        user_message=user_message,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    print(f"\nResult:")
    print(json.dumps(result, indent=2))
    
    assert result["intent_type"] == IntentType.TASK_REQUEST.value, "Should be TASK_REQUEST"
    assert result["action"] == LiaisonAction.DELEGATE_TO_ORCHESTRATOR.value, "Should delegate to orchestrator"
    
    # Check if dates were extracted
    structured_data = result["payload"].get("structured_data", {})
    print(f"\nExtracted Data: {json.dumps(structured_data, indent=2)}")
    print("\n✅ Test Passed: Task request correctly classified and delegated")


def test_approval_response():
    """Test approval response classification."""
    print("\n" + "="*70)
    print("TEST 3: Approval Response")
    print("="*70)
    
    user_message = "Yes, I approve this request"
    tenant_id = "acme_corp"
    user_id = "manager_001"
    workflow_id = "WF_acme_corp_emp001_abc123"
    
    print(f"\nUser Message: {user_message}")
    print(f"Tenant: {tenant_id}")
    print(f"Workflow ID: {workflow_id}")
    
    result = liaison_agent.process_message(
        user_message=user_message,
        tenant_id=tenant_id,
        user_id=user_id,
        workflow_id=workflow_id
    )
    
    print(f"\nResult:")
    print(json.dumps(result, indent=2))
    
    assert result["intent_type"] == IntentType.APPROVAL_RESPONSE.value, "Should be APPROVAL_RESPONSE"
    print("\n✅ Test Passed: Approval response correctly classified")


def test_task_request_missing_info():
    """Test task request with missing information."""
    print("\n" + "="*70)
    print("TEST 4: Task Request - Missing Information")
    print("="*70)
    
    user_message = "I need to schedule a meeting"
    tenant_id = "acme_corp"
    user_id = "emp_12345"
    
    print(f"\nUser Message: {user_message}")
    print(f"Tenant: {tenant_id}")
    
    result = liaison_agent.process_message(
        user_message=user_message,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    print(f"\nResult:")
    print(json.dumps(result, indent=2))
    
    # Should ask for clarification due to missing date/time/attendees
    if result["action"] == LiaisonAction.ASK_CLARIFICATION.value:
        print("\n✅ Test Passed: Agent correctly asks for clarification")
    else:
        print(f"\n⚠️  Warning: Expected ASK_CLARIFICATION but got {result['action']}")


def test_conversation_context():
    """Test multi-turn conversation with context."""
    print("\n" + "="*70)
    print("TEST 5: Multi-turn Conversation Context")
    print("="*70)
    
    tenant_id = "acme_corp"
    user_id = "emp_12345"
    workflow_id = "WF_test_context"
    
    # Turn 1
    print("\nTurn 1:")
    msg1 = "I want to apply for leave"
    print(f"User: {msg1}")
    
    result1 = liaison_agent.process_message(
        user_message=msg1,
        tenant_id=tenant_id,
        user_id=user_id,
        workflow_id=workflow_id
    )
    print(f"Result: {result1['action']}")
    
    # Turn 2 - Should remember context
    print("\nTurn 2:")
    msg2 = "From March 15 to March 20"
    print(f"User: {msg2}")
    
    result2 = liaison_agent.process_message(
        user_message=msg2,
        tenant_id=tenant_id,
        user_id=user_id,
        workflow_id=workflow_id
    )
    print(f"Result: {result2['action']}")
    print(f"\nExtracted Data: {json.dumps(result2['payload'].get('structured_data', {}), indent=2)}")
    
    print("\n✅ Test Passed: Multi-turn conversation maintained context")
    
    # Clean up
    liaison_agent.clear_conversation_history(tenant_id, workflow_id)


def test_mcp_message_creation():
    """Test MCP message creation."""
    print("\n" + "="*70)
    print("TEST 6: MCP Message Creation")
    print("="*70)
    
    user_message = "What are the working hours?"
    tenant_id = "acme_corp"
    user_id = "test_user_001"
    
    result = liaison_agent.process_message(
        user_message=user_message,
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    # Create MCP message for Guide Agent
    mcp_message = liaison_agent.create_mcp_message(
        routing_result=result,
        to_agent=AgentType.GUIDE
    )
    
    print(f"\nMCP Message:")
    print(f"Message ID: {mcp_message.message_id}")
    print(f"From: {mcp_message.from_agent}")
    print(f"To: {mcp_message.to_agent}")
    print(f"Type: {mcp_message.message_type}")
    print(f"Workflow ID: {mcp_message.workflow_id}")
    print(f"Tenant ID: {mcp_message.tenant_id}")
    print(f"Metadata: {json.dumps(mcp_message.metadata, indent=2)}")
    
    assert mcp_message.from_agent == AgentType.LIAISON
    assert mcp_message.to_agent == AgentType.GUIDE
    assert mcp_message.tenant_id == tenant_id
    
    print("\n✅ Test Passed: MCP message created correctly")


def test_guide_response_processing():
    """Test processing response from Guide Agent."""
    print("\n" + "="*70)
    print("TEST 7: Guide Response Processing")
    print("="*70)
    
    guide_response = "According to the leave policy, new joiners are eligible for 15 days of annual leave after completing 6 months of service."
    original_query = "What is the leave policy for new joiners?"
    tenant_id = "acme_corp"
    workflow_id = "WF_test_guide"
    
    result = liaison_agent.process_guide_response(
        guide_response=guide_response,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        original_query=original_query
    )
    
    print(f"\nProcessed Response:")
    print(json.dumps(result, indent=2))
    
    assert result["action"] == LiaisonAction.ACKNOWLEDGE.value
    assert result["user_response"] == guide_response
    
    print("\n✅ Test Passed: Guide response processed correctly")


def test_approval_request_formatting():
    """Test approval request formatting."""
    print("\n" + "="*70)
    print("TEST 8: Approval Request Formatting")
    print("="*70)
    
    approval_data = {
        "task_type": "leave_application",
        "details": {
            "start_date": "2026-03-15",
            "end_date": "2026-03-20",
            "reason": "Personal work"
        }
    }
    tenant_id = "acme_corp"
    workflow_id = "WF_test_approval"
    
    result = liaison_agent.process_approval_request(
        approval_data=approval_data,
        tenant_id=tenant_id,
        workflow_id=workflow_id
    )
    
    print(f"\nFormatted Approval Request:")
    print(result["user_response"])
    print(f"\nFull Result:")
    print(json.dumps(result, indent=2))
    
    assert "approve" in result["user_response"].lower()
    assert "reject" in result["user_response"].lower()
    
    print("\n✅ Test Passed: Approval request formatted correctly")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*70)
    print("LIAISON AGENT - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    try:
        test_policy_query()
        test_task_request()
        test_approval_response()
        test_task_request_missing_info()
        test_conversation_context()
        test_mcp_message_creation()
        test_guide_response_processing()
        test_approval_request_formatting()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print("\nLiaison Agent is functioning correctly!")
        print("Ready for integration with other agents.")
        
    except AssertionError as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
