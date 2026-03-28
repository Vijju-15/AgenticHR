import os
from anthropic import Anthropic

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("Set ANTHROPIC_API_KEY in your environment before running this script")

try:
    client = Anthropic(api_key=api_key)
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello, Claude! Just testing the connection. Please respond with 'Connection successful!'"}
        ]
    )
    
    print("SUCCESS!")
    print(f"Response: {message.content[0].text}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    print(traceback.format_exc())
