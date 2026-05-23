"""Tool registrations for poggio-ai-mcp.

Each submodule exposes a `register(mcp)` function that attaches its tools to
the FastMCP instance. server.py imports and calls each one.
"""

from . import campaigns, config, counsel, lit_search, runs

__all__ = ["campaigns", "config", "counsel", "lit_search", "runs"]
