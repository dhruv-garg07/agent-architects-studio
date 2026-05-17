import os
import sys
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

load_dotenv(os.path.join(project_root, '.env'))

from supabase import create_client

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(url, key)

try:
    resp = supabase.table('api_keys').select('*').limit(1).execute()
    print("Data returned:")
    print(resp.data)
except Exception as e:
    print("Error querying table:", e)
