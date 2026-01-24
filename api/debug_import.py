
import sys
import os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    import mcp_compat
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
