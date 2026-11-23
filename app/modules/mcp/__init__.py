"""MitraBooks MCP server: exposes read-only accounting tools to AI clients.

Any MCP-capable client (Claude, ChatGPT, Cursor, Gemini CLI, Antigravity, ...) can
connect to ``/api/v1/mcp`` with a personal access token. Each tool forwards to an
existing GET route of this API, so every auth, role, module-gate and tenant check
that protects the web app also protects the AI client.
"""
