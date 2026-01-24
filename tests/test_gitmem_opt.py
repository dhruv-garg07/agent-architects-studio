import sys
import os
import time
import unittest
from unittest.mock import MagicMock, patch

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Supabase
# We need to mock SupabaseClient before importing supabase_connector
sys.modules['supabase'] = MagicMock()

from gitmem.core.memory_store import MemoryStore
from gitmem.api import websocket_events
from flask import Flask

class TestGitMemOptimizations(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        # Mock DB behavior
        self.store.db.count_memories = MagicMock(return_value=10)
        
    def test_get_folder_structure_stats(self):
        print("Testing get_folder_structure_stats...")
        agent_id = "test_agent"
        structure = self.store.get_folder_structure_stats(agent_id)
        
        self.assertIn('structure', structure)
        self.assertIn('context', structure['structure'])
        self.assertEqual(structure['structure']['context']['episodic']['count'], 10)
        
        # Verify db was called with filters
        self.store.db.count_memories.assert_any_call(agent_id, 'episodic')
        self.store.db.count_memories.assert_any_call(agent_id, 'semantic')

    def test_websocket_rate_limit(self):
        print("Testing WebSocket rate limiting...")
        # Mock request context
        app = Flask(__name__)
        
        with app.test_request_context():
            # Mock socketio
            socketio = MagicMock()
            websocket_events.init_websocket(socketio)
            
            # Since we can't easily trigger the decorated function directly via socketio mock 
            # without triggering the event system, we will access the function if possible.
            # But the decorator wraps it.
            
            # We can verify logic by calling the inner logic if we could extract it, 
            # or integrated test. 
            # Let's import the customized dictionary
            from gitmem.api.websocket_events import _last_stats_request, handle_request_stats
            
            # Mock request.sid
            with patch('gitmem.api.websocket_events.request') as mock_req:
                mock_req.sid = "client_1"
                
                # Mock route dependencies
                with patch('gitmem.api.routes.store') as mock_store:
                     mock_store.count_memories.return_value = 100
                     
                     # First call - should succeed
                     handle_request_stats()
                     # It emits 'stats_update'
                     
                     # Check emit calls (socketio.emit was not captured because handle_request_stats is not bound to our mock socketio in this unit test way easily)
                     # Wait, we need to capture 'emit' which is imported in websocket_events
                     
                with patch('gitmem.api.websocket_events.emit') as mock_emit:
                    # Reset time check for "client_1" if any
                    if "client_1" in _last_stats_request:
                        del _last_stats_request["client_1"]
                        
                    # Call 1
                    handle_request_stats()
                    self.assertTrue(mock_emit.called)
                    mock_emit.reset_mock()
                    
                    # Call 2 (Immediate) - should be blocked
                    handle_request_stats()
                    self.assertFalse(mock_emit.called)
                    
                    # Wait/Sleep (mock time?)
                    # We can patch time.time
                    with patch('gitmem.api.websocket_events.time.time') as mock_time:
                         mock_time.return_value = time.time() + 10 # 10 seconds later
                         handle_request_stats()
                         self.assertTrue(mock_emit.called)

if __name__ == '__main__':
    unittest.main()
