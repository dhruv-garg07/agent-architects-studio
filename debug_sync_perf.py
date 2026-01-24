
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load envs
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
TARGET_USER_ID = "4703ac7e-d657-496f-99f1-c3c9caf2ff81"

if not url or not key:
    print("Error: Supabase credentials missing")
    sys.exit(1)

print(f"Connecting to Supabase...", flush=True)
start_conn = time.time()
supabase = create_client(url, key)
print(f"Connected in {time.time() - start_conn:.4f}s", flush=True)

def test_sync_logic():
    try:
        # 1. Fetch Owned Agents
        print("\n--- Step 1: Fetch Owned Agents ---", flush=True)
        t0 = time.time()
        res = supabase.table('agent_profiles').select('id').eq('creator_id', TARGET_USER_ID).execute()
        my_agents = set()
        if res.data:
            for row in res.data:
                my_agents.add(row['id'])
        print(f"Fetched {len(my_agents)} agents in {time.time() - t0:.4f}s", flush=True)

        # 2. Scan Memories
        print("\n--- Step 2: Scan Recent Memories (Limit 50) ---", flush=True)
        t1 = time.time()
        mem_res = supabase.table('gitmem_memories').select('agent_id').order('created_at', desc=True).limit(50).execute()
        memory_agents = set()
        if mem_res.data:
            for row in mem_res.data:
                if row.get('agent_id'):
                    memory_agents.add(row['agent_id'])
        print(f"Scanned 50 memories, found {len(memory_agents)} unique agents in {time.time() - t1:.4f}s", flush=True)

        # 3. Check Candidates
        print("\n--- Step 3: Check Candidates ---", flush=True)
        t2 = time.time()
        candidates = memory_agents - my_agents
        print(f"Candidates to check: {len(candidates)}", flush=True)
        
        if candidates:
            # Check strict existence in DB
            existing_res = supabase.table('agent_profiles').select('id').in_('id', list(candidates)).execute()
            existing_ids = set(r['id'] for r in existing_res.data) if existing_res.data else set()
            orphans = candidates - existing_ids
            print(f"Checked candidates in {time.time() - t2:.4f}s. Orphans found: {len(orphans)}", flush=True)
        else:
            print("No candidates to check.", flush=True)

        # 4. Local FS Simulation
        print("\n--- Step 4: Local FS Simulation ---", flush=True)
        t3 = time.time()
        # Mock root path
        root_path = "./headers_test_data" 
        agents_dir = os.path.join(root_path, "agents")
        # Don't actually create detailed structure, just measure overhead of loop
        if not os.path.exists(agents_dir):
            os.makedirs(agents_dir, exist_ok=True)
            
        count = 0
        for aid in my_agents:
            agent_path = os.path.join(agents_dir, aid)
            if not os.path.exists(agent_path):
                 # os.makedirs(agent_path, exist_ok=True) # Skip actual IO to avoid pollution, just logic
                 pass
            count += 1
        print(f"Processed loop for {count} agents in {time.time() - t3:.4f}s", flush=True)

    except Exception as e:
        print(f"CRASH: {e}", flush=True)

if __name__ == "__main__":
    test_sync_logic()
