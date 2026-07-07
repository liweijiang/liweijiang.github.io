"""
Minimal MCP server.

Exposes one tool (`add`), one more useful tool (`get_weather`, faked),
and one resource (`greeting://{name}`). Uses the official MCP Python SDK's
FastMCP helper, which handles the JSON-RPC/transport plumbing for you so you
just write normal Python functions.

Setup:
    pip install "mcp[cli]"

Run it directly over stdio (how a local harness launches it):
    python minimal_mcp_server.py

Or inspect it interactively with the MCP dev inspector:
    mcp dev minimal_mcp_server.py
"""

from mcp.server.fastmcp import FastMCP

# The server's name is how clients identify it.
mcp = FastMCP("minimal-demo")


# --- A TOOL ---------------------------------------------------------------
# The @mcp.tool() decorator turns this function into an MCP tool.
# Type hints become the JSON input schema the model sees; the docstring
# becomes the tool description. That's the whole contract.
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


# --- ANOTHER TOOL (pretend it hits a real API) ----------------------------
@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    In a real server this would call a weather API; here it's faked
    so the example runs with no credentials.
    """
    fake_db = {
        "london": "12C, light rain",
        "tokyo": "21C, clear",
        "san francisco": "17C, foggy",
    }
    return fake_db.get(city.lower(), f"No data for {city!r}.")


# --- A RESOURCE -----------------------------------------------------------
# Resources are read-only data addressed by URI. The {name} in the URI
# template becomes a function parameter. Clients read these rather than
# "call" them.
@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Return a personalized greeting."""
    return f"Hello, {name}! This came from an MCP resource."


if __name__ == "__main__":
    # Default transport is stdio: the harness runs this file as a subprocess
    # and exchanges JSON-RPC messages over stdin/stdout.
    mcp.run()
