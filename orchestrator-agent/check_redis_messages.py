"""Check Redis streams for MCP messages published by Orchestrator."""

import redis
import json


def check_redis_streams():
    """Connect to Redis and display MCP messages."""
    print("\n" + "="*60)
    print("REDIS MCP MESSAGES VERIFICATION")
    print("="*60)
    
    try:
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Test connection
        r.ping()
        print("✅ Connected to Redis\n")
        
        # Check all agent streams
        agent_streams = [
            "agent_stream:orchestrator_agent",
            "agent_stream:liaison_agent",
            "agent_stream:provisioning_agent",
            "agent_stream:scheduler_agent",
            "agent_stream:guide_agent"
        ]
        
        total_messages = 0
        
        for stream_name in agent_streams:
            print(f"\n📨 Stream: {stream_name}")
            print("-" * 60)
            
            # Check if stream exists
            stream_length = r.xlen(stream_name)
            
            if stream_length == 0:
                print("  (empty)")
                continue
            
            total_messages += stream_length
            print(f"  Messages: {stream_length}\n")
            
            # Read last 5 messages
            messages = r.xrevrange(stream_name, count=5)
            
            for msg_id, msg_data in messages:
                print(f"  Message ID: {msg_id}")
                
                # Parse MCP message
                try:
                    mcp_msg = json.loads(msg_data.get('message', '{}'))
                    print(f"    Type: {mcp_msg.get('message_type', 'UNKNOWN')}")
                    print(f"    From: {mcp_msg.get('from_agent', 'UNKNOWN')}")
                    print(f"    To: {mcp_msg.get('to_agent', 'UNKNOWN')}")
                    print(f"    Workflow: {mcp_msg.get('workflow_id', 'N/A')}")
                    
                    if 'task' in mcp_msg:
                        task = mcp_msg['task']
                        print(f"    Task ID: {task.get('task_id', 'N/A')}")
                        print(f"    Task Type: {task.get('task_type', 'N/A')}")
                    
                    print()
                except json.JSONDecodeError:
                    print(f"    Raw Data: {msg_data}")
                    print()
        
        # Summary
        print("\n" + "="*60)
        print(f"📊 Total Messages in All Streams: {total_messages}")
        print("="*60)
        
        if total_messages == 0:
            print("\n⚠️  No messages found. Have you run test_workflows.py yet?")
        else:
            print("\n✅ MCP messages are being published correctly!")
            print("\nNote: Messages remain in streams until consumed by agents")
            print("Once other agents are built, they will process these messages")
        
    except redis.ConnectionError:
        print("\n❌ ERROR: Cannot connect to Redis")
        print("Make sure Redis is running on localhost:6379")
        print("Start with: docker run -d -p 6379:6379 redis:7-alpine")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")


if __name__ == "__main__":
    check_redis_streams()
