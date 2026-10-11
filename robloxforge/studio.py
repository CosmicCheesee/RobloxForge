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


# ===== THE STUDIO BRIDGE IS PINNED =====
# robloxstudio-mcp is started with npx. It used to be `@latest`, which meant every launch could pick up a new
# release: unreviewed code running on this machine with full access to the open place, and a reply shape
# that RobloxForge parses could change under it without notice. It is pinned to the version RobloxForge was
# tested against; upgrade on purpose with FORGE_BRIDGE_VERSION or "bridge_version" in forge.local.json.
BRIDGE_PKG = "@chrrxs/robloxstudio-mcp"
BRIDGE_VERSION = "3.2.0"


def _local_cfg() -> dict:
    f = Path(__file__).resolve().parent.parent / "forge.local.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    except ValueError:
        return {}


def _find_npx() -> str | None:
    """The full path to npx. Desktop apps start servers with a minimal PATH, so a bare `npx` that works in a
    terminal can fail there; look in the usual Node install locations as well."""
    import glob
    import shutil
    for name in ("npx.cmd", "npx") if os.name == "nt" else ("npx",):
        hit = shutil.which(name)
        if hit:
            return hit
    home = Path.home()
    cands = ["C:/Program Files/nodejs/npx.cmd", str(home / "AppData/Roaming/npm/npx.cmd"),
             "/opt/homebrew/bin/npx", "/usr/local/bin/npx", "/usr/bin/npx"]
    cands += sorted(glob.glob(str(home / ".nvm/versions/node/*/bin/npx")), reverse=True)
    cands += sorted(glob.glob(str(home / "AppData/Roaming/nvm/*/npx.cmd")), reverse=True)
    for c in cands:
        if Path(c).is_file():
            return c
    return None


def child_params() -> StdioServerParameters:
    """FORGE_CHILD_CMD overrides the child command line (space separated)."""
    cmd = os.environ.get("FORGE_CHILD_CMD")
    if cmd:
        parts = cmd.split()
        return StdioServerParameters(command=parts[0], args=parts[1:])
    ver = os.environ.get("FORGE_BRIDGE_VERSION") or _local_cfg().get("bridge_version") or BRIDGE_VERSION
    pkg = f"{BRIDGE_PKG}@{ver}"
    npx = _find_npx()
    env = dict(os.environ)
    if npx:
        # npx needs node beside it on PATH (on macOS it is a `#!/usr/bin/env node` script)
        env["PATH"] = str(Path(npx).parent) + os.pathsep + env.get("PATH", "")
    # --auto-install-plugin puts the matching Studio plugin in place (and keeps it matched to the pinned version)
    if os.name == "nt":
        return StdioServerParameters(command="cmd", args=["/c", npx or "npx", "-y", pkg, "--auto-install-plugin"], env=env)
    return StdioServerParameters(command=npx or "npx", args=["-y", pkg, "--auto-install-plugin"], env=env)


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
