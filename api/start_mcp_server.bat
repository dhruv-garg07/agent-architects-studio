@echo off
REM Manhattan Memory MCP Server Launcher
REM This script starts the MCP server for Claude Desktop integration

echo ============================================
echo  Manhattan Memory MCP Server
echo ============================================
echo.

REM Set the working directory
cd /d "%~dp0.."

REM Set PYTHONPATH to include the project root
set PYTHONPATH=%cd%

echo Starting MCP server...
echo PYTHONPATH: %PYTHONPATH%
echo.

REM Run the MCP server
python api\mcp_memory_server.py

pause
