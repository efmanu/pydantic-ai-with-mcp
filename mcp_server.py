"""
mcp_server.py - FastMCP Server with Middleware to Extract Context from Headers

Run with: python mcp_server.py
"""

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from fastmcp.exceptions import ToolError

# Create MCP server
mcp = FastMCP(name="GreetingServer")


class ContextExtractionMiddleware(Middleware):
    """
    Middleware to extract user context from HTTP headers.
    This makes the context available to all tools without going through the LLM.
    """
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        # Extract headers from the HTTP request
        headers = get_http_headers()
        
        # Get user context from headers
        user_id = headers.get("x-user-id")
        token = headers.get("authorization")
        
        print(f"[Middleware] Extracted context - User ID: {user_id}, Token: {token}")
        
        # Validate token (optional)
        if not token or token != "Bearer secret-token-123":
            raise ToolError("Unauthorized: Invalid or missing token")
        
        # Store context in FastMCP state so tools can access it
        if context.fastmcp_context:
            context.fastmcp_context.set_state("user_id", user_id)
            context.fastmcp_context.set_state("token", token)
        
        # Continue to the tool
        result = await call_next(context)
        return result


# Add middleware to server
mcp.add_middleware(ContextExtractionMiddleware())


@mcp.tool()
def greet() -> str:
    """
    Greet the user. Username is automatically retrieved from request context.
    
    Returns:
        A personalized greeting message
    """
    from fastmcp.server.dependencies import get_context
    
    # Access the user_id from state (set by middleware)
    ctx = get_context()
    user_id = ctx.get_state("user_id")
    
    return f"Hello, {user_id}! Welcome to our FastMCP service. It's great to meet you!"


@mcp.tool()
def greet_with_time(time_of_day: str) -> str:
    """
    Greet the user with a time-appropriate message.
    Username is automatically retrieved from request context.
    
    Args:
        time_of_day: Time of day (morning, afternoon, evening, night)
        
    Returns:
        A personalized time-based greeting
    """
    from fastmcp.server.dependencies import get_context
    
    # Access the user_id from state (set by middleware)
    ctx = get_context()
    user_id = ctx.get_state("user_id")
    
    greetings = {
        "morning": f"Good morning, {user_id}! Hope you have a wonderful day ahead!",
        "afternoon": f"Good afternoon, {user_id}! Hope your day is going well!",
        "evening": f"Good evening, {user_id}! Hope you had a great day!",
        "night": f"Good night, {user_id}! Sweet dreams!"
    }
    return greetings.get(time_of_day.lower(), f"Hello, {user_id}!")


if __name__ == "__main__":
    # Run the server over HTTP
    mcp.run(transport="http", host="127.0.0.1", port=8000)