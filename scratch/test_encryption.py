import os
import sys
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'api'))

load_dotenv(os.path.join(project_root, '.env'))

from key_utils import encrypt_api_key, decrypt_api_key

test_key = "sk-test-key-1234567890"
print("Original key:", test_key)

encrypted = encrypt_api_key(test_key)
print("Encrypted key:", encrypted)

decrypted = decrypt_api_key(encrypted)
print("Decrypted key:", decrypted)

assert test_key == decrypted, "Test failed! Decrypted key does not match original."
print("Test passed successfully!")
