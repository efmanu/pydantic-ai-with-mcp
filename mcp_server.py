"""
mcp_server.py - FastMCP Server with Middleware to Extract JSON Metadata from Headers

Run with: python mcp_server.py
"""

import json
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError

# Create MCP server
mcp = FastMCP(name="GreetingServer")


class MetadataExtractionMiddleware(Middleware):
    """
    Middleware to extract user metadata from HTTP headers.
    Expects a JSON-encoded string in the 'X-Metadata' header.
    """
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        # Extract headers from the HTTP request
        headers = get_http_headers()
        
        # Get metadata from header (JSON-encoded string)
        metadata_json = headers.get("x-metadata")
        
        if not metadata_json:
            raise ToolError("Missing metadata header")
        
        try:
            # Decode JSON metadata
            metadata = json.loads(metadata_json)
            print(f"[Middleware] Extracted metadata: {metadata}")
            
            # Validate token if present
            token = metadata.get("token")
            if not token or token != "secret-token-123":
                raise ToolError("Unauthorized: Invalid or missing token in metadata")
            
            # Store entire metadata in FastMCP state so tools can access it
            if context.fastmcp_context:
                # Store the entire metadata dict
                context.fastmcp_context.set_state("metadata", metadata)
                
                # Optionally store individual fields for convenience
                context.fastmcp_context.set_state("user_id", metadata.get("user_id"))
                context.fastmcp_context.set_state("token", metadata.get("token"))
                
                # Store any additional fields
                for key, value in metadata.items():
                    if key not in ["user_id", "token"]:
                        context.fastmcp_context.set_state(key, value)
        
        except json.JSONDecodeError as e:
            raise ToolError(f"Invalid metadata JSON: {e}")
        
        # Continue to the tool
        result = await call_next(context)
        return result


# Add middleware to server
mcp.add_middleware(MetadataExtractionMiddleware())


@mcp.tool()
def greet() -> str:
    """
    Greet the user. Username is automatically retrieved from request metadata.
    
    Returns:
        A personalized greeting message
    """
    from fastmcp.server.dependencies import get_context
    
    # Access the metadata from state (set by middleware)
    ctx = get_context()
    metadata = ctx.get_state("metadata")
    user_id = metadata.get("user_id", "Guest")
    
    return f"Hello, {user_id}! Welcome to our FastMCP service. It's great to meet you!"


@mcp.tool()
def greet_with_time(time_of_day: str) -> str:
    """
    Greet the user with a time-appropriate message.
    Username is automatically retrieved from request metadata.
    
    Args:
        time_of_day: Time of day (morning, afternoon, evening, night)
        
    Returns:
        A personalized time-based greeting
    """
    from fastmcp.server.dependencies import get_context
    
    # Access the metadata from state (set by middleware)
    ctx = get_context()
    metadata = ctx.get_state("metadata")
    user_id = metadata.get("user_id", "Guest")
    
    greetings = {
        "morning": f"Good morning, {user_id}! Hope you have a wonderful day ahead!",
        "afternoon": f"Good afternoon, {user_id}! Hope your day is going well!",
        "evening": f"Good evening, {user_id}! Hope you had a great day!",
        "night": f"Good night, {user_id}! Sweet dreams!"
    }
    return greetings.get(time_of_day.lower(), f"Hello, {user_id}!")


@mcp.tool()
def get_user_info() -> str:
    """
    Get all user information from metadata.
    Demonstrates accessing any field from the metadata.
    
    Returns:
        A string with all user information
    """
    from fastmcp.server.dependencies import get_context
    
    # Access the full metadata
    ctx = get_context()
    metadata = ctx.get_state("metadata")
    
    # Build response with all metadata fields
    info_parts = []
    for key, value in metadata.items():
        if key != "token":  # Don't expose token
            info_parts.append(f"{key}: {value}")
    
    return "User Info:\n" + "\n".join(info_parts)


if __name__ == "__main__":
    # Run the server over HTTP
    mcp.run(transport="http", host="127.0.0.1", port=8000)