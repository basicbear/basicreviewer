"""MCP server implementation using FastMCP."""

from fastmcp import FastMCP


def create_server() -> FastMCP:
    """Create and configure the FastMCP server.

    Returns:
        Configured FastMCP server instance
    """
    from .organizational import register_organizational_endpoints
    from .summary import register_summary_endpoints

    mcp = FastMCP("crev")

    register_summary_endpoints(mcp)
    register_organizational_endpoints(mcp)

    return mcp
