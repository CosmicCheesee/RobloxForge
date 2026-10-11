"""The bridge to Roblox Studio.

RobloxForge does not ship its own Studio plugin. It launches the robloxstudio-mcp server (which
owns the Studio plugin, the HTTP bridge on port 58741 and the playtest peers) as a child MCP server
over stdio, re-exports every one of its tools unchanged, and builds the higher-level tools on top of
its execute_luau / eval_*_runtime / capture_screenshot primitives.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import mcp_types as types
from mcp import Client
from mcp.client.stdio import StdioServerParameters

LUAU_DIR = Path(__file__).parent / "luau"


class ForgeError(Exception):
    pass


def child_params() -> StdioServerParameters:
    """FORGE_CHILD_CMD overrides the child command line (space separated)."""
    cmd = os.environ.get("FORGE_CHILD_CMD")
    if cmd:
        parts = cmd.split()
        return StdioServerParameters(command=parts[0], args=parts[1:])
    if os.name == "nt":
        return StdioServerParameters(command="cmd", args=["/c", "npx", "-y", "@chrrxs/robloxstudio-mcp@latest"])
    return StdioServerParameters(command="npx", args=["-y", "@chrrxs/robloxstudio-mcp@latest"])


def long_string(s: str) -> str:
    """A Luau long-string literal that cannot be closed early by its own content."""
    level = 2
    while ("]" + "=" * level + "]") in s:
        level += 1
    eq = "=" * level
    return f"[{eq}[{s}]{eq}]"


def template(name: str, args: dict | None = None) -> str:
    src = (LUAU_DIR / f"{name}.luau").read_text(encoding="utf-8")
    token = "JSONDecode(__ARGS__)"
    if token in src:
        src = src.replace(token, f"JSONDecode({long_string(json.dumps(args or {}))})", 1)
    return src


class Studio:
    def __init__(self):
        self.child: Client | None = None
        self.tools: dict[str, types.Tool] = {}
        self.error: str | None = None

    def need(self):
        if self.child is None:
            raise ForgeError(f"Studio bridge is not running ({self.error or 'not started'}). "
                             "Check that Node/npx works and Studio has the MCP plugin enabled.")

    async def call(self, name: str, args: dict, timeout: float | None = None) -> types.CallToolResult:
        self.need()
        if name not in self.tools:
            raise ForgeError(f"the Studio bridge has no tool named {name}")
        return await self.child.call_tool(name, args, read_timeout_seconds=timeout)

    async def luau(self, code: str, peer: str = "edit", timeout: float = 60):
        """Run Luau on a peer and return its decoded return value.

        peer: "edit" (the Studio edit DataModel), "server" or "client" (a running playtest; "client-2"
        etc. for multiplayer)."""
        if peer == "edit":
            res = await self.call("execute_luau", {"code": code}, timeout)
        elif peer == "server":
            res = await self.call("eval_server_runtime", {"code": code}, timeout)
        elif peer.startswith("client"):
            target = peer if "-" in peer else "client-1"
            res = await self.call("eval_client_runtime", {"code": code, "target": target}, timeout)
        else:
            raise ForgeError(f"unknown peer {peer!r} (edit, server, client, client-N)")
        sc = res.structured_content or {}
        text = " ".join(getattr(b, "text", "") for b in res.content)
        if res.is_error:
            raise ForgeError(f"{peer}: {sc.get('message') or sc.get('error') or text or 'tool error'}")
        if "returnValue" in sc or sc.get("success") is False:   # execute_luau
            if sc.get("success") is False:
                detail = {k: v for k, v in sc.items() if k != "success"}
                raise ForgeError(f"{peer}: {json.dumps(detail, default=str)[:1500]}")
            val = sc["returnValue"]
        elif "result" in sc:                          # eval_*_runtime
            if sc.get("ok") is False:
                raise ForgeError(f"{peer}: {sc.get('error') or sc.get('message') or sc}")
            val = sc["result"]
        else:
            val = sc or text
        if isinstance(val, str):
            try:
                return json.loads(val)
            except ValueError:
                return val
        return val

    async def run(self, name: str, args: dict | None = None, peer: str = "edit", timeout: float = 60):
        val = await self.luau(template(name, args), peer, timeout)
        if isinstance(val, dict) and val.get("error"):
            raise ForgeError(str(val["error"]))
        return val

    async def screenshot(self) -> bytes:
        res = await self.call("capture_screenshot", {"format": "jpeg", "quality": 85}, 60)
        for b in res.content:
            if isinstance(b, types.ImageContent):
                return base64.b64decode(b.data)
        sc = res.structured_content or {}
        raise ForgeError(f"screenshot returned no image: {sc.get('message') or sc}")
