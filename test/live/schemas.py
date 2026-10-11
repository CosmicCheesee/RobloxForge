import asyncio, json, sys
from mcp import Client
from mcp.client.stdio import StdioServerParameters
async def main(names):
    async with Client(StdioServerParameters(command=sys.executable, args=["server.py"]), read_timeout_seconds=120) as c:
        for t in (await c.list_tools()).tools:
            if t.name in names:
                print(t.name, json.dumps(t.input_schema.get("properties", {}))[:700], "req", t.input_schema.get("required"))
asyncio.run(main(sys.argv[1:]))
