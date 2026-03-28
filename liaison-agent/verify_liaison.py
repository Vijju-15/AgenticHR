"""Quick verification script for Liaison Agent."""

import os
import sys
from pathlib import Path

print("="*70)
print("LIAISON AGENT - VERIFICATION SCRIPT")
print("="*70)

# Check Python version
print("\n1. Checking Python version...")
py_version = sys.version_info
print(f"   Python {py_version.major}.{py_version.minor}.{py_version.micro}")
if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 10):
    print("   ❌ Python 3.10+ required")
    sys.exit(1)
else:
    print("   ✅ Python version OK")

# Check required files
print("\n2. Checking required files...")
required_files = [
    "src/agent/liaison.py",
    "src/api/main.py",
    "src/schemas/liaison_message.py",
    "src/schemas/mcp_message.py",
    "src/config/settings.py",
    "src/messaging/redis_client.py"
]

all_files_exist = True
for file in required_files:
    if Path(file).exists():
        print(f"   ✅ {file}")
    else:
        print(f"   ❌ {file} NOT FOUND")
        all_files_exist = False

if not all_files_exist:
    print("\n   Some required files are missing!")
    sys.exit(1)

# Check dependencies
print("\n3. Checking required dependencies...")
required_packages = [
    ("google.generativeai", "google-generativeai"),
    ("pydantic", "pydantic"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("redis", "redis"),
    ("loguru", "loguru"),
    ("pydantic_settings", "pydantic-settings")
]

missing_packages = []
for module_name, package_name in required_packages:
    try:
        __import__(module_name)
        print(f"   ✅ {package_name}")
    except ImportError:
        print(f"   ❌ {package_name} NOT INSTALLED")
        missing_packages.append(package_name)

if missing_packages:
    print(f"\n   Missing packages: {', '.join(missing_packages)}")
    print(f"   Install with: setup.bat")
    sys.exit(1)

# Check environment variables
print("\n4. Checking environment configuration...")
env_file = Path(".env")
if env_file.exists():
    print(f"   ✅ .env file found")
    # Try to load it
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print(f"   ✅ .env loaded successfully")
    except ImportError:
        print(f"   ⚠️  python-dotenv not installed (optional)")
    except Exception as e:
        print(f"   ❌ Error loading .env: {e}")
else:
    print(f"   ⚠️  .env file not found")
    print(f"   Create .env from .env.template")

# Check critical env vars
critical_vars = ["GOOGLE_API_KEY"]
for var in critical_vars:
    if os.getenv(var):
        print(f"   ✅ {var} configured")
    else:
        print(f"   ⚠️  {var} not set")

# Try to import Liaison Agent
print("\n5. Testing Liaison Agent import...")
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from src.agent.liaison import liaison_agent, IntentType, LiaisonAction
    print(f"   ✅ Liaison Agent imported successfully")
    print(f"   Agent Type: {liaison_agent.agent_type}")
except Exception as e:
    print(f"   ❌ Failed to import Liaison Agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try to import schemas
print("\n6. Testing schema imports...")
try:
    from src.schemas.liaison_message import (
        UserMessage, LiaisonResponse, ApprovalResponse,
        PolicyQueryRequest, TaskDelegationRequest
    )
    print(f"   ✅ Liaison message schemas imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import schemas: {e}")
    sys.exit(1)

# Try to import API
print("\n7. Testing API import...")
try:
    from src.api.main import app
    print(f"   ✅ Liaison API imported successfully")
    print(f"   App Title: {app.title}")
except Exception as e:
    print(f"   ❌ Failed to import API: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check Redis connection (if available)
print("\n8. Testing Redis connection (optional)...")
try:
    from src.messaging.redis_client import redis_client
    # Try to ping
    redis_client.redis_client.ping()
    print(f"   ✅ Redis connection OK")
except Exception as e:
    print(f"   ⚠️  Redis not available: {e}")
    print(f"   This is OK for local testing, but required for production")

# Summary
print("\n" + "="*70)
print("VERIFICATION SUMMARY")
print("="*70)
print("\n✅ All core components verified successfully!")
print("\nLiaison Agent is ready to use.")
print("\nNext steps:")
print("  1. Ensure .env file has GOOGLE_API_KEY")
print("  2. Start Redis server (if not running)")
print("  3. Run tests: python test_liaison.py")
print("  4. Start agent: start_liaison.bat")
print("  5. Test API: http://localhost:8002/docs")
print("\n" + "="*70)
