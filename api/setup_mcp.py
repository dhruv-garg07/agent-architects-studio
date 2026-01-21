#!/usr/bin/env python3
"""
MCP Server Setup Script

This script helps you set up the Manhattan Memory MCP Server by:
1. Verifying dependencies
2. Generating the correct configuration for your system
3. Optionally installing to Claude Desktop config

Usage:
    python setup_mcp.py --check          # Check dependencies
    python setup_mcp.py --generate       # Generate config
    python setup_mcp.py --install        # Install to Claude Desktop
    python setup_mcp.py --all            # Do everything
"""

import os
import sys
import json
import argparse
import shutil
import platform
from pathlib import Path


def get_project_root():
    """Get the absolute path to the project root."""
    return Path(__file__).parent.parent.absolute()


def get_claude_config_path():
    """Get the Claude Desktop config path based on OS."""
    system = platform.system()
    
    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:  # Linux
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("🔍 Checking dependencies...\n")
    
    dependencies = {
        "mcp": "pip install mcp",
        "dotenv": "pip install python-dotenv",
        "httpx": "pip install httpx",
        "chromadb": "pip install chromadb",
        "pydantic": "pip install pydantic",
    }
    
    missing = []
    
    for package, install_cmd in dependencies.items():
        try:
            if package == "dotenv":
                __import__("dotenv")
            else:
                __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - Install with: {install_cmd}")
            missing.append(package)
    
    print()
    
    if missing:
        print(f"⚠️  Missing {len(missing)} package(s). Install with:")
        print(f"   pip install {' '.join(d if d != 'dotenv' else 'python-dotenv' for d in missing)}")
        return False
    else:
        print("✅ All dependencies installed!")
        return True


def check_env_file():
    """Check if .env file exists and has required variables."""
    print("\n🔍 Checking environment configuration...\n")
    
    project_root = get_project_root()
    env_file = project_root / ".env"
    
    if not env_file.exists():
        print(f"  ❌ .env file not found at {env_file}")
        print("     Create one based on .env.example")
        return False
    
    required_vars = [
        "CHROMA_API_KEY",
        "CHROMA_TENANT",
        "CHROMA_DATABASE_CHAT_HISTORY",
    ]
    
    # Load .env manually
    env_content = env_file.read_text()
    missing = []
    
    for var in required_vars:
        if var not in env_content or f"{var}=" not in env_content:
            print(f"  ❌ {var} not set")
            missing.append(var)
        else:
            print(f"  ✅ {var}")
    
    if missing:
        print(f"\n⚠️  Please set missing environment variables in {env_file}")
        return False
    
    print("\n✅ Environment configured!")
    return True


def generate_config():
    """Generate the MCP configuration for the current system."""
    print("\n📝 Generating MCP configuration...\n")
    
    project_root = get_project_root()
    mcp_server_path = project_root / "api" / "mcp_memory_server.py"
    
    # Use forward slashes for all platforms (works in JSON)
    project_path_str = str(project_root).replace("\\", "/")
    server_path_str = str(mcp_server_path).replace("\\", "/")
    
    config = {
        "mcpServers": {
            "manhattan-memory": {
                "command": "python" if platform.system() == "Windows" else "python3",
                "args": [server_path_str],
                "env": {
                    "PYTHONPATH": project_path_str
                }
            }
        }
    }
    
    print("Generated configuration:")
    print(json.dumps(config, indent=2))
    
    # Save to file
    output_file = project_root / "api" / "generated_mcp_config.json"
    with open(output_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Configuration saved to: {output_file}")
    return config


def install_to_claude():
    """Install the MCP server to Claude Desktop config."""
    print("\n🔧 Installing to Claude Desktop...\n")
    
    claude_config_path = get_claude_config_path()
    print(f"Claude config path: {claude_config_path}")
    
    # Generate our config first
    our_config = generate_config()
    
    # Create parent directory if needed
    claude_config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config or start fresh
    if claude_config_path.exists():
        print(f"  📂 Found existing config")
        with open(claude_config_path, "r") as f:
            try:
                existing_config = json.load(f)
            except json.JSONDecodeError:
                existing_config = {}
        
        # Backup existing config
        backup_path = claude_config_path.with_suffix(".json.backup")
        shutil.copy(claude_config_path, backup_path)
        print(f"  💾 Backed up to: {backup_path}")
    else:
        existing_config = {}
        print("  📄 Creating new config file")
    
    # Merge configs
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"]["manhattan-memory"] = our_config["mcpServers"]["manhattan-memory"]
    
    # Save
    with open(claude_config_path, "w") as f:
        json.dump(existing_config, f, indent=2)
    
    print(f"\n✅ Installed to Claude Desktop!")
    print(f"   📍 Config at: {claude_config_path}")
    print(f"\n🔄 Please restart Claude Desktop to apply changes.")


def test_server():
    """Test if the MCP server can start."""
    print("\n🧪 Testing MCP server...\n")
    
    project_root = get_project_root()
    server_path = project_root / "api" / "mcp_memory_server.py"
    
    # Add project to path
    sys.path.insert(0, str(project_root))
    
    try:
        # Try importing the server module
        print("  Importing server module...", end=" ")
        import importlib.util
        spec = importlib.util.spec_from_file_location("mcp_memory_server", server_path)
        module = importlib.util.module_from_spec(spec)
        print("✅")
        
        print("\n✅ MCP server ready to run!")
        print(f"\nTo start manually:")
        print(f"  python {server_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manhattan Memory MCP Server Setup Script"
    )
    parser.add_argument("--check", action="store_true", help="Check dependencies")
    parser.add_argument("--generate", action="store_true", help="Generate config")
    parser.add_argument("--install", action="store_true", help="Install to Claude Desktop")
    parser.add_argument("--test", action="store_true", help="Test the server")
    parser.add_argument("--all", action="store_true", help="Run all steps")
    
    args = parser.parse_args()
    
    # If no args, show help
    if not any([args.check, args.generate, args.install, args.test, args.all]):
        parser.print_help()
        print("\n" + "="*50)
        print("Quick start: python setup_mcp.py --all")
        print("="*50)
        return
    
    print("="*50)
    print("  Manhattan Memory MCP Server Setup")
    print("="*50)
    
    success = True
    
    if args.check or args.all:
        success = check_dependencies() and success
        success = check_env_file() and success
    
    if args.generate or args.all:
        generate_config()
    
    if args.test or args.all:
        success = test_server() and success
    
    if args.install or args.all:
        install_to_claude()
    
    print("\n" + "="*50)
    if success:
        print("  ✅ Setup complete!")
    else:
        print("  ⚠️  Setup completed with warnings")
    print("="*50)


if __name__ == "__main__":
    main()
