"""Quick diagnostic script to check .env loading."""

import os
import sys
from pathlib import Path

print("="*70)
print("GOOGLE API KEY DIAGNOSTIC")
print("="*70)

# Check if .env file exists
env_path = Path(".env")
print(f"\n1. Checking .env file:")
print(f"   Path: {env_path.absolute()}")
print(f"   Exists: {env_path.exists()}")

if env_path.exists():
    with open(env_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.strip().startswith("GOOGLE_API_KEY"):
                key_line = line.strip()
                if "=" in key_line:
                    key_value = key_line.split("=", 1)[1].strip()
                    if key_value:
                        print(f"   ✅ GOOGLE_API_KEY found in .env: {key_value[:20]}... (length: {len(key_value)})")
                    else:
                        print(f"   ❌ GOOGLE_API_KEY is empty in .env")
                break
        else:
            print(f"   ❌ GOOGLE_API_KEY not found in .env file")

# Check environment variable
print(f"\n2. Checking environment variable:")
env_var = os.getenv("GOOGLE_API_KEY")
if env_var:
    print(f"   ✅ GOOGLE_API_KEY in environment: {env_var[:20]}... (length: {len(env_var)})")
else:
    print(f"   ❌ GOOGLE_API_KEY not in environment variables")

# Try loading with dotenv
print(f"\n3. Testing dotenv loading:")
try:
    from dotenv import load_dotenv
    load_dotenv()
    env_var_after = os.getenv("GOOGLE_API_KEY")
    if env_var_after:
        print(f"   ✅ After load_dotenv(): {env_var_after[:20]}... (length: {len(env_var_after)})")
    else:
        print(f"   ❌ Still not loaded after load_dotenv()")
except ImportError:
    print(f"   ❌ python-dotenv not installed!")
    print(f"   Install it: pip install python-dotenv")

# Try loading settings
print(f"\n4. Testing settings import:")
try:
    from src.config.settings import settings
    print(f"   ✅ Settings imported successfully")
    if settings.google_api_key:
        print(f"   ✅ API Key in settings: {settings.google_api_key[:20]}... (length: {len(settings.google_api_key)})")
    else:
        print(f"   ❌ API Key is empty in settings")
except Exception as e:
    print(f"   ❌ Error importing settings: {e}")

# Try initializing liaison agent
print(f"\n5. Testing Liaison Agent initialization:")
try:
    from src.agent.liaison import liaison_agent
    print(f"   ✅ Liaison Agent initialized successfully")
    print(f"   Agent type: {liaison_agent.agent_type}")
except Exception as e:
    print(f"   ❌ Error initializing liaison agent: {e}")

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)
print("\nIf you see ❌ errors above:")
print("1. Make sure .env file exists in liaison-agent folder")
print("2. Make sure GOOGLE_API_KEY is set in .env")
print("3. Restart the uvicorn server to reload settings")
print("4. If still failing, check the API key is valid")
print("\n" + "="*70)
