"""n8n Webhook client for external integrations."""

import httpx
from typing import Dict, Any, Optional
from loguru import logger
import time

from src.config.settings import settings


class N8nWebhookClient:
    """Client for calling n8n webhooks."""
    
    def __init__(self):
        """Initialize n8n webhook client."""
        self.base_url = settings.n8n_webhook_base_url
        self.timeout = settings.webhook_timeout_seconds
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay_seconds
        
        self.headers = {}
        if settings.n8n_api_key:
            self.headers['Authorization'] = f'Bearer {settings.n8n_api_key}'
        
        logger.info(f"n8n webhook client initialized with base URL: {self.base_url}")
    
    async def call_webhook(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        retry: bool = True
    ) -> Dict[str, Any]:
        """
        Call n8n webhook endpoint.
        
        Args:
            endpoint: Webhook endpoint path (e.g., '/create-hr-record')
            payload: Payload to send
            retry: Whether to retry on failure
            
        Returns:
            Response data from webhook
            
        Raises:
            Exception: If webhook call fails
        """
        url = f"{self.base_url}{endpoint}"
        
        attempt = 0
        max_attempts = self.max_retries + 1 if retry else 1
        
        while attempt < max_attempts:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.info(f"Calling n8n webhook: {url} (attempt {attempt + 1}/{max_attempts})")
                    
                    response = await client.post(
                        url,
                        json=payload,
                        headers=self.headers
                    )
                    
                    response.raise_for_status()
                    
                    result = response.json()
                    logger.info(f"Webhook call successful: {endpoint}")
                    return result
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling webhook {endpoint}: {e.response.status_code} - {e.response.text}")
                
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise Exception(f"Webhook validation error: {e.response.text}")
                
                attempt += 1
                if attempt < max_attempts:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"Webhook call failed after {max_attempts} attempts: {str(e)}")
                    
            except httpx.RequestError as e:
                logger.error(f"Network error calling webhook {endpoint}: {e}")
                
                attempt += 1
                if attempt < max_attempts:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    raise Exception(f"Network error after {max_attempts} attempts: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Unexpected error calling webhook {endpoint}: {e}")
                raise
    
    # ── Employee Setup methods (repurposed from old IT-provisioning) ─────

    async def employee_setup(
        self,
        task_type: str,
        tenant_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generic employee setup webhook call.

        All employee-setup task types route through the /employee-setup n8n
        webhook which replaces the old /provisioning endpoint.

        Args:
            task_type: One of create_employee_record | generate_employee_id |
                       assign_department | send_welcome_credentials |
                       initialize_onboarding | create_onboarding_checklist
            tenant_id: Tenant identifier
            payload:   Task-specific data

        Returns:
            Webhook response (unwrapped from n8n envelope if needed)
        """
        body = {
            "task_type": task_type,
            "tenant_id": tenant_id,
            "payload":   payload,
        }
        return await self.call_webhook("/employee-setup", body)

    # ── Legacy aliases (kept for backward-compat during transition) ───────

    async def create_hr_record(self, tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Backward-compat alias → employee_setup(create_employee_record)."""
        return await self.employee_setup("create_employee_record", tenant_id, data)

    async def generate_employee_id(self, tenant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Backward-compat alias → employee_setup(generate_employee_id)."""
        return await self.employee_setup("generate_employee_id", tenant_id, data)


# Singleton instance
n8n_client = N8nWebhookClient()
