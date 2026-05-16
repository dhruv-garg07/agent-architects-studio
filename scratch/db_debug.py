import os
import sys
from supabase import create_client
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

client = create_client(url, key)
agent_id = "0fae3e0c-10de-4022-9007-7e306e1013eb"

print(f"--- COMMITS for {agent_id} ---")
commits = client.table('gitmem_commits').select('*').eq('agent_id', agent_id).execute()
for c in commits.data:
    print(c)

print(f"--- REFS for {agent_id} ---")
refs = client.table('gitmem_refs').select('*').eq('repo_id', agent_id).execute()
for r in refs.data:
    print(r)
