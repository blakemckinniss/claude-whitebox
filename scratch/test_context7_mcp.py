#!/usr/bin/env python3
"""
Test script to understand Context7 MCP protocol
"""
import os
import json
import subprocess

# Try to use Claude Desktop's MCP protocol
api_key = os.getenv("CONTEXT7_API_KEY")
print(f"API Key: {api_key[:20]}..." if api_key else "No API key")

# Context7 is an MCP server - it needs to be installed and run as a subprocess
# The MCP protocol uses stdio communication, not REST

# Check if we have the MCP server available
try:
    # Option 1: Try npx if the npm package exists
    result = subprocess.run(
        ["npx", "-y", "mcp-context7", "--help"],
        capture_output=True,
        timeout=10
    )
    print("NPX output:", result.stdout.decode()[:200])
    print("NPX error:", result.stderr.decode()[:200])
except Exception as e:
    print(f"NPX attempt failed: {e}")

# Context7 appears to be MCP-only (no REST API)
print("\n=== FINDINGS ===")
print("Context7 is an MCP (Model Context Protocol) server")
print("It uses stdio communication, not HTTP REST API")
print("Designed for Claude Desktop integration, not standalone CLI usage")
print("\nFor CLI documentation retrieval, better options:")
print("1. Use Tavily (research.py) - already working")
print("2. Use direct web scraping of docs sites")
print("3. Use GitHub API for README/docs")
