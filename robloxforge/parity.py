"""Parity tools: everything the other Roblox Studio MCP servers offer that RobloxForge did not.

Surveyed 2026-10-11: 6xvl/robloxstudio-mcp-server (143 tools), EL4CTEO/rbx-studio-mcp (35),
drgost1/robloxstudio-mcp (51), bdidk235/RobloxStudioMCP (16 extended), kolvian/roblox-mcp-server (9) and
Roblox's own studio-rust-mcp-server (6). Names follow 6xvl where a tool came from there, so prompts written
for that server work here unchanged.

DATA-DRIVEN: a tool is a row -- name, description, schema and a short Luau body -- registered by `L()`.
Every body runs after `luau/_prelude.luau`, which resolves paths, converts JSON to Roblox values through
ReflectionService (so a wrong property name or type is a message, never a throw: Studio pauses on any eval
error) and back. Bodies return a table; `{error = ...}` becomes a tool error.
"""
from __future__ import annotations

import json

from .server import PEER, STUDIO, text, tool
from .studio import LUAU_DIR, ForgeError, long_string

PRELUDE = (LUAU_DIR / "_prelude.luau").read_text(encoding="utf-8")


def code_for(body: str, args: dict) -> str:
    return PRELUDE.replace("JSONDecode(__ARGS__)", f"JSONDecode({long_string(json.dumps(args))})", 1) + "\n" + body


async def run_body(body: str, args: dict, peer: str = "edit", timeout: float = 60):
    val = await STUDIO.luau(code_for(body, args), peer, timeout)
    if isinstance(val, dict) and val.get("error"):
        raise ForgeError(str(val["error"]))
    return val


BODIES: dict[str, str] = {}


def L(name, description, props, body, required=None, ro=False, destructive=False, timeout=60, peer=True):
    """Register a Luau-bodied tool."""
    BODIES[name] = body
    schema = dict(props or {})
    if peer:
        schema["peer"] = PEER

    async def handler(a, _body=body, _t=timeout):
        args = {k: v for k, v in a.items() if k != "peer"}
        return [text(await run_body(_body, args, a.get("peer", "edit"), _t))]

    tool(name, description, schema, required, read_only=ro, destructive=destructive)(handler)
    return handler


S = {"type": "string"}
N = {"type": "number"}
B = {"type": "boolean"}
O = {"type": "object"}
ARR = {"type": "array"}
PATH = {"type": "string", "description": "instance path, dot notation (game.Workspace.Model or Workspace.Model)"}
ANY = {"description": "a JSON value; converted to the property's real type (Vector3 [x,y,z], Color3 '#hex' or [r,g,b], "
       "UDim2 [sx,ox,sy,oy], CFrame [x,y,z] / 12 numbers / {position, rotation|lookAt}, Enum 'Name', NumberSequence "
       "[[t,v],...], ColorSequence [[t,'#hex'],...], NumberRange [min,max], Instance 'path', Font {family,weight,style})"}

from . import parity_instances, parity_play, parity_world, parity_builds, parity_cloud  # noqa: E402,F401
