
import sys
import os
sys.path.append(os.path.abspath('.'))
try:
    from api import mcp_compat
    print("Success")
except Exception:
    import traceback
    traceback.print_exc()
