"""Test script for Provisioning Agent."""

import asyncio
import httpx
from loguru import logger

BASE_URL = "http://localhost:8003"


async def test_health():
    """Test health endpoint."""
    logger.info("Testing health endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/health")
        logger.info(f"Health: {response.json()}")
        assert response.status_code == 200


async def test_status():
    """Test status endpoint."""
    logger.info("Testing status endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/status")
        logger.info(f"Status: {response.json()}")
        assert response.status_code == 200


async def test_execute_task():
    """Test direct task execution."""
    logger.info("Testing task execution...")
    
    task_request = {
        "workflow_id": "WF_test_001",
        "tenant_id": "acme_corp",
        "task": {
            "task_id": "task_hr_001",
            "task_type": "create_hr_record",
            "payload": {
                "employee_name": "John Doe",
                "employee_email": "john.doe@acme.com",
                "role": "Software Engineer",
                "department": "Engineering",
                "start_date": "2026-03-01"
            },
            "priority": 5,
            "retry_count": 0
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/execute-task",
                json=task_request
            )
            logger.info(f"Task execution response: {response.json()}")
            
            if response.status_code == 200:
                logger.success("✅ Task executed successfully")
            else:
                logger.warning(f"⚠️  Task execution returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Task execution failed: {e}")


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("🧪 Testing Provisioning Agent")
    logger.info("=" * 60)
    
    try:
        await test_health()
        await test_status()
        
        # Note: This will fail if n8n is not running
        # await test_execute_task()
        
        logger.success("✅ All basic tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
