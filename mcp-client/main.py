from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from contextlib import asynccontextmanager
from mcp_client import MCPClient
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    server_script_path: str = "/home/forceedge01/lab/first-mcp/mcp-server/main.py"

settings = Settings()

@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    client = MCPClient()
    try:
        connected = await client.connect(settings.server_script_path)
        if not connected:
            raise HTTPException(
                status_code=500, details="failed"
            )
        app.state.client = client
        yield
    except Exception as e:
        print(f"Something went wrong {e}")
        raise e
    finally:
        await client.cleanup()

app = FastAPI(title="MCP Client API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

class QueryRequest(BaseModel):
    query: str

class Message(BaseModel):
    role: str
    content: Any

class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any]

@app.post('/query')
async def process_query(request: QueryRequest) -> Dict:
    print('Getting here?')
    messages = await app.state.client.process_query(request.query)
    return {"messages": messages}

@app.get("/tools")
async def get_tools():
    """Get the list of available tools"""
    try:
        tools = await app.state.client.get_mcp_tools()
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in tools
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)