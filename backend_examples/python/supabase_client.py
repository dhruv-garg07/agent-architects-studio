"""Supabase client configuration for Python backend."""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lmlwkkbzkikrkshriaqm.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtbHdra2J6a2lrcmtzaHJpYXFtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYxNDEzMDUsImV4cCI6MjA3MTcxNzMwNX0.v2dO6pscKXPxCmjUCAQW0EXVTV_iAN9BWQ7crX4yNUc")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_supabase_client() -> Client:
    """Get the Supabase client instance."""
    return supabase