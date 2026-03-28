"""Redis client for inter-agent message streaming."""

import redis
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from loguru import logger

from src.config.settings import settings
from src.schemas.mcp_message import MCPMessage


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
        logger.info("Redis client initialized")
    
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
    
    def read_messages(
        self,
        agent_name: str,
        count: int = 10,
        block: int = 0,
        last_id: str = ">"
    ) -> list:
        """
        Read messages from agent stream.
        
        Args:
            agent_name: Agent name to read from
            count: Number of messages to read
            block: Block time in milliseconds (0 = don't block)
            last_id: Last message ID read (use '>' for new messages)
            
        Returns:
            List of messages
        """
        stream_name = f"{self.stream_prefix}:{agent_name}"
        consumer_group = f"{agent_name}_group"
        consumer_name = f"{agent_name}_consumer"
        
        try:
            # Create consumer group if not exists
            try:
                self.redis_client.xgroup_create(
                    stream_name,
                    consumer_group,
                    id="0",
                    mkstream=True
                )
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
            
            # Read messages
            messages = self.redis_client.xreadgroup(
                consumer_group,
                consumer_name,
                {stream_name: last_id},
                count=count,
                block=block
            )
            
            parsed_messages = []
            for stream, msgs in messages:
                for msg_id, msg_data in msgs:
                    try:
                        message_json = json.loads(msg_data["message"])
                        message = MCPMessage(**message_json)
                        parsed_messages.append((msg_id, message))
                    except Exception as e:
                        logger.error(f"Error parsing message {msg_id}: {e}")
                        self.publish_to_dlq(stream_name, msg_id, msg_data, str(e))
            
            return parsed_messages
            
        except Exception as e:
            logger.error(f"Error reading messages: {e}")
            return []
    
    def acknowledge_message(self, stream_name: str, consumer_group: str, message_id: str):
        """Acknowledge message processing."""
        try:
            self.redis_client.xack(stream_name, consumer_group, message_id)
            logger.debug(f"Acknowledged message {message_id}")
        except Exception as e:
            logger.error(f"Error acknowledging message: {e}")
    
    def get_stream_info(self, agent_name: str) -> Dict[str, Any]:
        """Get stream information."""
        stream_name = f"{self.stream_prefix}:{agent_name}"
        try:
            return self.redis_client.xinfo_stream(stream_name)
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return {}

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

    def health_check(self) -> bool:
        """Return True if Redis is reachable."""
        try:
            return self.redis_client.ping()
        except Exception:
            return False


# Global Redis client instance
redis_client = RedisClient()
