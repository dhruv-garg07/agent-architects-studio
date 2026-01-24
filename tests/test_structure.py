import sys
import os
from unittest.mock import MagicMock

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Supabase
sys.modules['supabase'] = MagicMock()

from gitmem.core.memory_store import MemoryStore

def test_structure():
    store = MemoryStore()
    # Mock DB behavior
    store.db.count_memories = MagicMock(return_value=10)
    
    structure = store.get_folder_structure_stats("test_agent")
    print(structure)
    if structure['structure']['context']['episodic']['count'] == 10:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    test_structure()
