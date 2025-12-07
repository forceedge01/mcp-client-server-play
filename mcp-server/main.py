from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
import json
import httpx
from bs4 import BeautifulSoup

load_dotenv()
USER_AGENT = "docs-app/1.0"
SERPER_URL="https://google.serper.dev/search"

docs_urls = {
    "langchain": "python.langchain.com/docs",
    "llama-index": "docs.llamaindex.ai/stable",
    "openai": "platform.openai.com/docs",
}

mcp = FastMCP('docs')

async def search_web(query: str) -> None|dict:
    payload = json.dumps({"q": query, "num": 2})
    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                SERPER_URL,
                headers=headers,
                data=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"organic": []}
        except Exception as e:
            raise Exception(f"Unable to call search_web: {e}")

async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text()
            return text
        except httpx.TimeoutException as e:
            return "Timeout error"
        except Exception as e:
            raise Exception(f"Unable to call fetch_url: {e}")

@mcp.tool()
async def get_docs(query: str, library: str) -> str:
    """
    Search the docs for a given query and library.
    Supports langchain, openai and llama-index.

    Args:
      query: The query to search for (e.g. "Chroma DB")
      library: The library to search in (e.g. "langchain")

    Returns:
      Text from the documentation.
    """
    if library not in docs_urls:
        raise ValueError("Library not supported")

    query = f"site:{docs_urls[library]} {query}"
    print(f'hitting: {query}')
    results = await search_web(query)

    if len(results["organic"]) == 0:
        return "no resutls found"
    
    text: str = ""
    for result in results["organic"]:
        text += await fetch_url(result["link"])
    print(text)
    return text

if __name__ == "__main__":
    mcp.run(transport='stdio')
