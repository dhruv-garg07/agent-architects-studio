import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add parent dir to path to find gitmem imports if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_keys():
    """Load keys from .env manually to avoid dependency issues if python-dotenv not installed"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, val = line.strip().split('=', 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

def main():
    load_keys()
    
    # Check for DATABASE_URL (standard Postgres connection string)
    db_url = os.environ.get("DATABASE_URL")
    
    # If not found, try to construct from SUPABASE_URL if password is known (unlikely)
    if not db_url:
        print("DATABASE_URL not found in .env.")
        print("Please add DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres to your .env file")
        print("Or provide the connection string as an argument.")
        return

    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Read schema file
        schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gitmem', 'schema.sql')
        print(f"Reading schema from {schema_path}")
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            
        print("Executing schema...")
        # Split by command to run individually for better error reporting? 
        # Or just run all. sql script might have semicolons.
        
        cur.execute(schema_sql)
        
        print("✅ Schema initialized successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Failed to run SQL: {e}")

if __name__ == "__main__":
    main()
