"""Drive a RobloxForge server over stdio the way Claude Code would: list tools, call some."""
import asyncio
import json
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp_types import ImageContent, TextContent


async def main(script, calls):
    params = StdioServerParameters(command=sys.executable, args=[script])
    async with Client(params, read_timeout_seconds=120) as c:
        tools = (await c.list_tools()).tools
        print(f"{len(tools)} tools:", ", ".join(t.name for t in tools))
        for name, args in calls:
            r = await c.call_tool(name, args)
            print(f"--- {name} error={r.is_error}")
            for b in r.content:
                if isinstance(b, TextContent):
                    print(b.text[:1500])
                elif isinstance(b, ImageContent):
                    import base64, os
                    out = os.path.join(os.environ.get("FORGE_TEST_OUT", "."), f"{name}_{abs(hash(b.data)) % 10000}.{b.mime_type.split('/')[1]}")
                    open(out, "wb").write(base64.b64decode(b.data))
                    print(f"[image {b.mime_type} -> {out}]")


if __name__ == "__main__":
    script = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else "[]"
    if arg.startswith("@"):
        arg = open(arg[1:], encoding="utf-8").read()
    calls = json.loads(arg)
    asyncio.run(main(script, calls))
