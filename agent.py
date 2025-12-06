"""
agent.py - PydanticAI Agent that passes context as JSON metadata in headers

Context is JSON-encoded and passed via X-Metadata header to MCP server,
NOT through the LLM conversation.

Usage: 
1. Start MCP server: python mcp_server.py
2. Run agent: python agent.py
"""

import asyncio
import json
from typing import Any
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP


from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
import os

model = OpenAIChatModel(
    'deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv('DEEPSEEK_API_KEY'))
)

# Define the context type - can contain any fields!
class UserContext(BaseModel):
    """
    Context containing user information.
    This can have any fields - they'll all be passed as JSON metadata.
    """
    user_id: str
    token: str
    # Add any additional fields you want
    role: str | None = None
    organization: str | None = None
    preferences: dict[str, Any] | None = None
    
    model_config = ConfigDict(extra="allow")


async def run_with_context(user_context: UserContext, prompt: str):
    """
    Run agent with context passed via JSON metadata header.
    
    All fields from user_context are JSON-encoded and sent in X-Metadata header.
    """
    # Convert context to dict and then to JSON string
    metadata_dict = user_context.model_dump()
    metadata_json = json.dumps(metadata_dict)
    
    print(f"\n[Agent] Running with context:")
    print(f"[Agent] Metadata: {json.dumps(metadata_dict, indent=2)}")
    print(f"[Agent] Prompt: {prompt}")
    
    # Create MCP server connection with JSON metadata in header
    server = MCPServerStreamableHTTP(
        'http://localhost:8000/mcp',
        headers={
            "X-Metadata": metadata_json
        }
    )
    
    # Create agent with this specific server connection
    agent = Agent(
        model,
        deps_type=UserContext,
        toolsets=[server]
    )
    
    result = await agent.run(prompt, deps=user_context)
    
    print(f"[Agent] Response: {result.output}\n")
    return result


async def main():
    # Example 1: Simple context with just user_id and token
    print("=" * 60)
    print("Example 1: Simple context (Alice)")
    print("=" * 60)
    alice_context = UserContext(
        user_id="Alice",
        token="secret-token-123"
    )
    await run_with_context(alice_context, "Please greet me")
    
    # Example 2: Rich context with additional fields
    print("=" * 60)
    print("Example 2: Rich context (Bob with role and org)")
    print("=" * 60)
    bob_context = UserContext(
        user_id="Bob",
        token="secret-token-123",
        role="admin",
        organization="Acme Corp",
        preferences={
            "theme": "dark",
            "language": "en"
        }
    )
    await run_with_context(bob_context, "Give me a morning greeting")
    await run_with_context(bob_context, "Show me my user info")
    
    # Example 3: Different context structure
    print("=" * 60)
    print("Example 3: Custom fields (Carol)")
    print("=" * 60)
    carol_context = UserContext(
        user_id="Carol",
        token="secret-token-123",
        role="developer",
        organization="Tech Startup"
    )
    await run_with_context(carol_context, "Get my user information")
    
    # Example 4: Invalid token (will fail)
    print("=" * 60)
    print("Example 4: Invalid token (should fail)")
    print("=" * 60)
    charlie_context = UserContext(
        user_id="Charlie",
        token="wrong-token"
    )
    try:
        await run_with_context(charlie_context, "Greet me")
    except Exception as e:
        print(f"[Agent] Error (expected): {e}")


if __name__ == "__main__":
    asyncio.run(main())