"""Call one forge tool and print EVERYTHING it returns (text, structured content, error flag)."""
import asyncio, json, sys
from mcp import Client
from mcp.client.stdio import StdioServerParameters

async def main(name, args):
    async with Client(StdioServerParameters(command=sys.executable, args=["server.py"]), read_timeout_seconds=240) as c:
        r = await c.call_tool(name, args)
        print("is_error:", r.is_error)
        for b in r.content:
            print(getattr(b, "text", None) or f"[{type(b).__name__}]")
        if r.structured_content:
            print("structured:", json.dumps(r.structured_content)[:3000])

name = sys.argv[1]
args = json.loads(open(sys.argv[2][1:], encoding="utf-8").read()) if sys.argv[2].startswith("@") else json.loads(sys.argv[2])
asyncio.run(main(name, args))
