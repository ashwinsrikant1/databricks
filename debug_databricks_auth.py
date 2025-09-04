#!/usr/bin/env python3

import os
print("=== DEBUGGING DATABRICKS AUTHENTICATION ===")

# Check environment
print(f"1. Current working directory: {os.getcwd()}")
print(f"2. E2_DEMO_FIELD_ENG_PAT env var: {os.getenv('E2_DEMO_FIELD_ENG_PAT', 'NOT SET')}")

# Check if we can detect Databricks environment
print("\n3. Testing Databricks environment detection:")
try:
    import databricks.sdk.runtime as dbr
    print("   ✓ databricks.sdk.runtime import successful - WE ARE IN DATABRICKS")
    in_databricks = True
except ImportError as e:
    print(f"   ✗ databricks.sdk.runtime import failed - WE ARE NOT IN DATABRICKS: {e}")
    in_databricks = False

# Try different authentication methods
print("\n4. Testing WorkspaceClient creation:")
from databricks.sdk import WorkspaceClient

if in_databricks:
    print("   Attempting default authentication (no tokens needed)...")
    try:
        client = WorkspaceClient()
        print("   ✓ Default authentication successful!")
    except Exception as e:
        print(f"   ✗ Default authentication failed: {e}")
        
        # Try with explicit host (sometimes needed)
        print("   Trying with explicit host...")
        try:
            client = WorkspaceClient(host="https://e2-demo-field-eng.cloud.databricks.com")
            print("   ✓ Authentication with explicit host successful!")
        except Exception as e2:
            print(f"   ✗ Authentication with explicit host failed: {e2}")
else:
    print("   Attempting PAT token authentication...")
    token = os.getenv('E2_DEMO_FIELD_ENG_PAT')
    if token:
        try:
            client = WorkspaceClient(
                host="https://e2-demo-field-eng.cloud.databricks.com",
                token=token
            )
            print("   ✓ PAT token authentication successful!")
        except Exception as e:
            print(f"   ✗ PAT token authentication failed: {e}")
    else:
        print("   ✗ No PAT token available")

print("\n5. System information:")
print(f"   Python executable: {os.sys.executable}")
print(f"   Python path: {os.sys.path[:3]}...")  # First few entries

print("\n=== END DEBUG ===")