with open('.env', 'rb') as f:
    content = f.read()
    print("First 200 bytes:", content[:200])
    print("\nFile starts with BOM?", content[:3])
