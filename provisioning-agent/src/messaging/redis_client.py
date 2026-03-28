"""Redis client for inter-agent message streaming."""

import redis
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from loguru import logger

from src.config.settings import settings
from src.schemas.mcp_message import MCPMessage, TaskResult


class RedisClient:
    """Redis Stream client for MCP message passing."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        self.stream_prefix = "agent_stream"
        self.agent_name = "provisioning_agent"
        logger.info("Redis client initialized for Provisioning Agent")
    
    def publish_message(self, message: MCPMessage) -> str:
        """
        Publish message to agent stream.
        
        Args:
            message: MCP message to publish
            
        Returns:
            Message ID
        """
        stream_name = f"{self.stream_prefix}:{message.to_agent.value}"
        
        try:
            message_data = {
                "message": json.dumps(message.model_dump(), default=str)
            }
            
            message_id = self.redis_client.xadd(stream_name, message_data, maxlen=5000)
            logger.info(f"Published message {message.message_id} to {stream_name}")
            return message_id
            
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            raise
    
    def publish_task_result(self, result: TaskResult) -> str:
        """
        Publish task result back to Orchestrator.
        
        Args:
            result: Task result to publish
            
        Returns:
            Message ID
        """
        from src.schemas.mcp_message import MessageType, AgentType
        import uuid
        
        message = MCPMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            workflow_id=result.workflow_id,
            tenant_id=result.tenant_id,
            from_agent=AgentType.PROVISIONING,
            to_agent=AgentType.ORCHESTRATOR,
            message_type=MessageType.TASK_RESULT,
            data={
                "task_id": result.task_id,
                "status": result.status,
                "result": result.result,
                "error": result.error,
                "retry_possible": result.retry_possible
            }
        )
        
        return self.publish_message(message)
    
    def read_messages(
        self,
        count: int = 10,
        block: int = 0,
        last_id: str = ">"
    ) -> List[Dict[str, Any]]:
        """
        Read messages from provisioning agent stream.
        
        Args:
            count: Number of messages to read
            block: Block time in milliseconds (0 = don't block)
            last_id: Last message ID read (use '>' for new messages)
            
        Returns:
            List of messages
        """
        stream_name = f"{self.stream_prefix}:{self.agent_name}"
        consumer_group = f"{self.agent_name}_group"
        consumer_name = f"{self.agent_name}_consumer"
        
        try:
            # Create consumer group if not exists
            try:
                self.redis_client.xgroup_create(
                    stream_name,
                    consumer_group,
                    id='0',
                    mkstream=True
                )
                logger.info(f"Created consumer group {consumer_group}")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
            
            # Read messages
            messages = self.redis_client.xreadgroup(
                groupname=consumer_group,
                consumername=consumer_name,
                streams={stream_name: last_id},
                count=count,
                block=block
            )
            
            parsed_messages = []
            for stream, msg_list in messages:
                for msg_id, msg_data in msg_list:
                    try:
                        message_json = json.loads(msg_data['message'])
                        parsed_messages.append({
                            'id': msg_id,
                            'stream': stream,
                            'data': message_json
                        })
                        
                        # Acknowledge message
                        self.redis_client.xack(stream_name, consumer_group, msg_id)
                        
                    except Exception as e:
                        logger.error(f"Error parsing message {msg_id}: {e}")
                        self.publish_to_dlq(stream_name, msg_id, msg_data, str(e))
            
            return parsed_messages
            
        except Exception as e:
            logger.error(f"Error reading messages: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def publish_to_dlq(self, stream_name: str, msg_id: str, raw_data: dict, error: str):
        """Send an unparseable message to the dead-letter queue stream."""
        dlq_stream = f"{self.stream_prefix}:dlq"
        try:
            self.redis_client.xadd(
                dlq_stream,
                {
                    "original_stream": stream_name,
                    "original_msg_id": msg_id,
                    "error": error,
                    "raw_data": json.dumps(raw_data, default=str),
                    "failed_at": datetime.now(timezone.utc).isoformat()
                },
                maxlen=1000
            )
            logger.warning(f"Published message {msg_id} from {stream_name} to DLQ")
        except Exception as dlq_err:
            logger.error(f"Failed to publish to DLQ: {dlq_err}")

    def get_stream_info(self, agent_name: str) -> dict:
        """Get stream length/info."""
        stream_name = f"{self.stream_prefix}:{agent_name}"
        try:
            return self.redis_client.xinfo_stream(stream_name)
        except Exception:
            return {}


# Singleton instance
redis_client = RedisClient()
