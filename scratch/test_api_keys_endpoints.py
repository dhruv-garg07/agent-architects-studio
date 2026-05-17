import os
import sys
import json
from unittest.mock import MagicMock, patch

# Adjust path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'api'))

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

# Mock Supabase connection if needed, but let's use the real one since the database is real and we have credentials!
# Let's see if we can use the real database with the real user.
# Wait, current_user.id must exist in our profiles/auth.users table.
# Let's use the user_id we inspected earlier: "2cdaa777-c623-4912-96ff-6449e8bca7ed".
# Yes! We know that user_id exists and has a row in profiles.

mock_user = MagicMock()
mock_user.id = "2cdaa777-c623-4912-96ff-6449e8bca7ed"
mock_user.is_authenticated = True

from index import app

# Create test client
client = app.test_client()

# Disable CSRF/login_required requirements or patch _get_user
@app.login_manager.request_loader
def load_user_from_request(request):
    return mock_user

# We will run the tests in a patched environment
print("Starting API Endpoints Test...")

with patch('flask_login.utils._get_user', return_value=mock_user), \
     patch('flask_login.current_user', mock_user):
    
    # 1. Test creating an API Key
    print("\n1. Creating a new API Key via POST /api/keys...")
    create_payload = {
        "name": "Verification Test Key",
        "expiration": "Never"
    }
    res_create = client.post('/api/keys', data=json.dumps(create_payload), content_type='application/json')
    print("Create Status Code:", res_create.status_code)
    create_data = json.loads(res_create.data.decode('utf-8'))
    print("Create Response Data:", create_data)
    
    assert res_create.status_code == 201, f"Failed to create key: {res_create.status_code}"
    assert create_data['ok'] is True
    created_key_id = create_data['id']
    created_key_val = create_data['key']
    print(f"Success! Created Key ID: {created_key_id}, Plaintext Key: {created_key_val}")

    # 2. Test listing API Keys via GET /api/keys
    print("\n2. Fetching API Keys list via GET /api/keys...")
    res_list = client.get('/api/keys')
    print("List Status Code:", res_list.status_code)
    list_data = json.loads(res_list.data.decode('utf-8'))
    
    assert res_list.status_code == 200, f"Failed to list keys: {res_list.status_code}"
    print(f"Success! Received {len(list_data)} keys.")
    
    # Find the key we just created in the list
    found_key = None
    legacy_key = None
    for key in list_data:
        if key['id'] == created_key_id:
            found_key = key
        elif not key.get('key') and key.get('masked_key'):
            legacy_key = key
            
    print("\n3. Verifying the created key in the list:")
    assert found_key is not None, "Created key was not found in the list!"
    print("Found created key in the list:")
    print("  Name:", found_key['name'])
    print("  Masked Key:", found_key['masked_key'])
    print("  Decrypted Key Returned:", found_key['key'])
    
    assert found_key['key'] == created_key_val, "Decrypted key does not match the generated key!"
    print("Success! Decrypted key matches the generated plaintext key perfectly.")
    
    if legacy_key:
        print("\n4. Verifying a legacy key in the list:")
        print("  Name:", legacy_key['name'])
        print("  Masked Key:", legacy_key['masked_key'])
        print("  Decrypted Key (should be None):", legacy_key['key'])
        assert legacy_key['key'] is None, "Legacy key should not be decryptable!"
        print("Success! Legacy key returns key=None as expected.")
    
    # 5. Clean up: Revoke the test key
    print(f"\n5. Cleaning up: Revoking the created test key {created_key_id}...")
    res_delete = client.delete(f'/api/keys/{created_key_id}')
    print("Delete Status Code:", res_delete.status_code)
    assert res_delete.status_code == 200
    print("Success! Cleaned up and revoked the key.")

print("\nAll backend verification tests completed successfully!")
