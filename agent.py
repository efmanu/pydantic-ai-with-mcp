"""
agent.py - PydanticAI Agent that passes context via HTTP headers

Context (user_id, token) is passed via HTTP headers to MCP server,
NOT through the LLM conversation.

Usage: 
1. Start MCP server: python mcp_server.py
2. Run agent: python agent.py
"""

import asyncio
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
import os

model = OpenAIChatModel(
    'deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv('DEEPSEEK_API_KEY'))
)

# Define the context type - stored here, not passed to LLM
class UserContext(BaseModel):
    """Context containing user information"""
    user_id: str
    token: str


async def run_with_context(user_context: UserContext, prompt: str):
    """
    Run agent with context passed via headers.
    
    Creates a new MCP server connection with the appropriate headers for this context.
    """
    # Create MCP server connection with headers for this specific user context
    server = MCPServerStreamableHTTP(
        'http://localhost:8000/mcp',
        headers={
            "X-User-ID": user_context.user_id,
            "Authorization": f"Bearer {user_context.token}"
        }
    )
    
    # Create agent with this specific server connection
    agent = Agent(
        model,
        deps_type=UserContext,
        toolsets=[server]
    )
    
    print(f"\n[Agent] Running with context: user_id={user_context.user_id}")
    print(f"[Agent] Headers: X-User-ID={user_context.user_id}, Authorization=Bearer {user_context.token}")
    print(f"[Agent] Prompt: {prompt}")
    
    result = await agent.run(prompt, deps=user_context)
    
    print(f"[Agent] Response: {result.output}\n")
    return result


async def main():
    # Example 1: Alice with valid token
    print("=" * 60)
    print("Example 1: Alice with valid token")
    print("=" * 60)
    alice_context = UserContext(
        user_id="Alice",
        token="secret-token-123"
    )
    await run_with_context(alice_context, "Please greet me")
    
    # Example 2: Bob with morning greeting
    print("=" * 60)
    print("Example 2: Bob with morning greeting")
    print("=" * 60)
    bob_context = UserContext(
        user_id="Bob",
        token="secret-token-123"
    )
    await run_with_context(bob_context, "Give me a morning greeting")
    
    # Example 3: Charlie with invalid token (will fail)
    print("=" * 60)
    print("Example 3: Charlie with invalid token (should fail)")
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