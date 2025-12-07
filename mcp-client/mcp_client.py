from typing import Optional
from contextlib import AsyncExitStack
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from utils.logger import logger
from datetime import datetime
import json
import os

from anthropic import Anthropic
from anthropic.types import Message

class MCPClient:
    session: Optional[ClientSession]
    exit_stack: AsyncExitStack
    llm: Anthropic
    tools: list
    messages: list[str, str]

    def __init__(self) -> None:
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm = Anthropic()
        self.tools = []
        self.messages = []
        self.logger = logger

    async def connect(self, server_script_path: str) -> bool:
        try:
            is_python = server_script_path.endswith('.py')
            is_js = server_script_path.endswith('js')
            if not(is_python or is_js):
                raise ValueError("Server script must be py or js")
            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command, args=[server_script_path], env=None
            )

            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            await self.session.initialize()
            self.logger.info("connected to MCP server")

            mcp_tools = await self.get_mcp_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in mcp_tools
            ]

            self.logger.info(f"Avialbale tools {self.tools}")
            print('is this being reported?')
            return True
        except Exception as e:
            self.logger.error(f"Error connecting to MCP server: {e}")
            traceback.print_exc()
            raise

    async def get_mcp_tools(self) -> list:
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            self.logger.error(f"Error getting mcp tools {e}")
            raise

    async def process_query(self, query: str) -> list:
        try:
            self.logger.info("Processing query")
            user_message = {
                "role": "user",
                "content": query
            }
            self.messages = [user_message]
            while(True):
                response = await self.call_llm()

                if response.content[0].type == "text" and len(response.content) == 1:
                    assistant_message = {
                        "role": "assistant",
                        "content": response.content[0].text,
                    }
                    self.messages.append(assistant_message)
                    break

                assistant_message = {
                    "role": "assistant",
                    "content": response.to_dict()["content"],
                }
                self.messages.append(assistant_message)

                for content in response.content:
                    
                    if content.type == "tool_use":
                        tool_name = content.name
                        tool_args = content.input
                        tool_use_id = content.id
                        self.logger.info(f"Calling tool {tool_name} with args {tool_args}")

                        result = await self.session.call_tool(
                            tool_name, tool_args
                        )
                        self.messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result.content,
                            }]
                        })
            return self.messages
        except Exception as e:
            self.logger.info("Problem processing")
            raise

    async def call_llm(self) -> list:
        try:
            self.logger.info(f'Calling llm with {len(self.messages)} messages')
            return self.llm.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=self.messages,
                tools=self.tools,
            )
        except Exception as e:
            self.logger.info("Problem calling llm")
            raise

    async def cleanup(self) -> None:
        try:
            await self.exit_stack.aclose()
            self.logger.info("Disconnected from MCP server")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            traceback.print_exc()
            raise
