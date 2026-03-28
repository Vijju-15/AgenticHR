"""Redis client for inter-agent message streaming."""

import redis
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from loguru import logger

from src.config.settings import settings
from src.schemas.mcp_message import MCPMessage, TaskResult, AgentType, MessageType
import uuid


class RedisClient:
    """Redis Stream client for MCP message passing."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True,
        )
        self.stream_prefix = "agent_stream"
        self.agent_name = "scheduler_agent"
        logger.info("Redis client initialized for Scheduler Agent")

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_message(self, message: MCPMessage) -> str:
        """
        Publish message to a named agent stream.

        Args:
            message: MCP message to publish

        Returns:
            Redis stream message ID
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
            result: Completed task result

        Returns:
            Redis stream message ID
        """
        message = MCPMessage(
            message_id=f"msg_{uuid.uuid4().hex[:12]}",
            workflow_id=result.workflow_id,
            tenant_id=result.tenant_id,
            from_agent=AgentType.SCHEDULER,
            to_agent=AgentType.ORCHESTRATOR,
            message_type=MessageType.TASK_RESULT,
            data={
                "task_id": result.task_id,
                "status": result.status,
                "result": result.result,
                "error": result.error,
                "retry_possible": result.retry_possible,
            },
        )
        return self.publish_message(message)

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def read_messages(
        self,
        count: int = 10,
        block: int = 0,
        last_id: str = ">",
    ) -> List[Dict[str, Any]]:
        """
        Read messages from the scheduler agent stream.

        Args:
            count:   Maximum messages to consume per call
            block:   Block milliseconds waiting for new data (0 = no block)
            last_id: '>' reads only new/undelivered messages

        Returns:
            List of parsed message dicts
        """
        stream_name = f"{self.stream_prefix}:{self.agent_name}"
        consumer_group = f"{self.agent_name}_group"
        consumer_name = f"{self.agent_name}_consumer"

        try:
            # Create consumer group on first use (idempotent)
            try:
                self.redis_client.xgroup_create(
                    stream_name, consumer_group, id="0", mkstream=True
                )
                logger.info(f"Created consumer group {consumer_group}")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

            messages = self.redis_client.xreadgroup(
                groupname=consumer_group,
                consumername=consumer_name,
                streams={stream_name: last_id},
                count=count,
                block=block,
            )

            parsed: List[Dict[str, Any]] = []
            for _stream, msg_list in messages:
                for msg_id, msg_data in msg_list:
                    try:
                        payload = json.loads(msg_data["message"])
                        parsed.append({"id": msg_id, "stream": _stream, "data": payload})
                        # Acknowledge message immediately after reading
                        self.redis_client.xack(stream_name, consumer_group, msg_id)
                    except Exception as e:
                        logger.error(f"Error parsing message {msg_id}: {e}")
                        self.publish_to_dlq(stream_name, msg_id, msg_data, str(e))

            return parsed

        except Exception as e:
            logger.error(f"Error reading messages: {e}")
            return []

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Ping Redis to verify connectivity."""
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
