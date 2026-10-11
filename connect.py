"""RobloxForge setup and connector.

    python connect.py                 set up (venv + packages), check Node and Studio, list every AI app
    python connect.py <app>           connect RobloxForge to that app (writes its config, with a backup)
    python connect.py <app> --print   only show what would be added, change nothing
    python connect.py <app> --tools core   expose only some tool groups (see robloxforge/groups.py)
    python connect.py check           run the server once and report how many tools it exposes

Apps: claude-code, claude-desktop, codex (Codex CLI + ChatGPT desktop app), gemini, cursor, vscode,
      windsurf (Devin Desktop / Windsurf), zed, lmstudio

Only the standard library is used here, so this runs before anything is installed.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WIN = os.name == "nt"
MAC = sys.platform == "darwin"
HOME = Path.home()
APPDATA = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if WIN else "bin/python")
SERVER = ROOT / "server.py"
NAME = "robloxforge"

# Tool calls that run a playtest or wait on the game can take a few minutes; a client's default may be 60 s.
TOOL_TIMEOUT_S = 300
START_TIMEOUT_S = 120     # the first start downloads the Studio bridge through npx


def say(msg=""):
    print(msg)


def ok(msg):
    print(f"  [ok]   {msg}")


def warn(msg):
    print(f"  [!]    {msg}")


TOOLS = None             # --tools value, or None for every tool


def server_entry():
    e = {"command": str(VENV_PY), "args": [str(SERVER)]}
    if TOOLS:
        e["env"] = {"FORGE_TOOLS": TOOLS}
    return e


def _backup(path: Path):
    if path.exists():
        b = path.with_name(path.name + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, b)
        ok(f"backed up the old file to {b.name}")


def _merge_json(path: Path, key: str, entry: dict, dry: bool):
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except ValueError:
            warn(f"{path} is not valid JSON (comments?) -- add this by hand under \"{key}\":")
            say(json.dumps({NAME: entry}, indent=2))
            return False
    data.setdefault(key, {})[NAME] = entry
    if dry:
        say(f"would write to {path}:")
        say(json.dumps({key: {NAME: entry}}, indent=2))
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    ok(f"added '{NAME}' to {path}")
    return True


def _run(cmd: list[str], dry: bool):
    say("  > " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    if dry:
        return True
    exe = shutil.which(cmd[0]) or (shutil.which(cmd[0] + ".cmd") if WIN else None)
    if not exe:
        warn(f"'{cmd[0]}' was not found on PATH -- run the command above yourself once it is installed")
        return False
    r = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out:
        say("    " + out.replace("\n", "\n    ")[:800])
    return r.returncode == 0


# ---------------------------------------------------------------- one function per app
def claude_code(dry):
    env = ["-e", f"FORGE_TOOLS={TOOLS}"] if TOOLS else []
    return _run(["claude", "mcp", "add", NAME, "-s", "user", *env, "--", str(VENV_PY), str(SERVER)], dry)


def claude_desktop(dry):
    if MAC:
        path = HOME / "Library/Application Support/Claude/claude_desktop_config.json"
    elif WIN:
        path = APPDATA / "Claude" / "claude_desktop_config.json"
        if not path.parent.exists():
            # Microsoft Store / MSIX installs keep it under Packages\
            hits = list((HOME / "AppData/Local/Packages").glob("*Claude*/LocalCache/Roaming/Claude"))
            if hits:
                path = hits[0] / "claude_desktop_config.json"
    else:
        path = HOME / ".config/Claude/claude_desktop_config.json"
    return _merge_json(path, "mcpServers", server_entry(), dry)


def codex(dry):
    path = HOME / ".codex" / "config.toml"
    block = (f"\n[mcp_servers.{NAME}]\ncommand = {json.dumps(str(VENV_PY))}\nargs = [{json.dumps(str(SERVER))}]\n"
             f"startup_timeout_sec = {START_TIMEOUT_S}\ntool_timeout_sec = {TOOL_TIMEOUT_S}\n")
    if TOOLS:
        block += f"\n[mcp_servers.{NAME}.env]\nFORGE_TOOLS = {json.dumps(TOOLS)}\n"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if f"[mcp_servers.{NAME}]" in text:
        ok(f"{path} already has [mcp_servers.{NAME}] -- leaving it as it is")
        return True
    if dry:
        say(f"would append to {path}:{block}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(block)
    ok(f"added [mcp_servers.{NAME}] to {path}")
    return True


def gemini(dry):
    # Gemini's own default tool timeout (10 minutes) is already long enough
    return _merge_json(HOME / ".gemini" / "settings.json", "mcpServers", server_entry(), dry)


def cursor(dry):
    return _merge_json(HOME / ".cursor" / "mcp.json", "mcpServers", {"type": "stdio"} | server_entry(), dry)


def vscode(dry):
    # The user-profile mcp.json ("MCP: Open User Configuration"), written directly: passing JSON through
    # `code --add-mcp` breaks on Windows quoting.
    if MAC:
        user = HOME / "Library/Application Support/Code/User"
    elif WIN:
        user = APPDATA / "Code" / "User"
    else:
        user = HOME / ".config/Code/User"
    if not user.exists():
        warn(f"VS Code's settings folder was not found ({user}) -- open VS Code once and run this again")
        return False
    return _merge_json(user / "mcp.json", "servers", {"type": "stdio"} | server_entry(), dry)


def windsurf(dry):
    # Windsurf's Cascade now ships as Devin Desktop; older Windsurf installs keep the old path.
    new = (APPDATA / "devin" / "mcp_config.json") if WIN else (Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "devin" / "mcp_config.json")
    old = HOME / ".codeium" / "windsurf" / "mcp_config.json"
    path = old if (old.exists() and not new.exists()) else new
    global TOOLS
    if not TOOLS:
        TOOLS = "core"
        say("  Cascade can use at most 100 tools in total, so this adds the 95-tool 'core' set")
        say("  (Studio, instances, scripts, playtests). Use --tools to pick other groups.")
    return _merge_json(path, "mcpServers", server_entry(), dry)


def zed(dry):
    say("  Zed's settings file can contain comments, so this one is safest added in the app:")
    say("  Settings > AI > MCP Servers > Add Server > Add Local Server, then paste:")
    say(json.dumps({NAME: server_entry() | {"env": {}}}, indent=2))
    return True


def lmstudio(dry):
    say("  In LM Studio: right-hand sidebar > Program tab > Install > Edit mcp.json, and add inside \"mcpServers\":")
    say(json.dumps({NAME: server_entry()}, indent=2)[1:-1])
    return True


APPS = {
    "claude-code": ("Claude Code (terminal)", claude_code),
    "claude-desktop": ("Claude Desktop app", claude_desktop),
    "codex": ("OpenAI Codex CLI and the ChatGPT desktop app (Codex)", codex),
    "gemini": ("Google Gemini CLI", gemini),
    "cursor": ("Cursor", cursor),
    "vscode": ("VS Code with GitHub Copilot", vscode),
    "windsurf": ("Devin Desktop / Windsurf", windsurf),
    "zed": ("Zed", zed),
    "lmstudio": ("LM Studio", lmstudio),
}


# ---------------------------------------------------------------- setup and checks
def setup():
    say("RobloxForge setup")
    say(f"  folder: {ROOT}")
    if sys.version_info < (3, 11):
        warn(f"Python {platform.python_version()} -- RobloxForge needs 3.11 or newer")
        return False
    ok(f"Python {platform.python_version()}")
    if not VENV_PY.exists():
        say("  creating the virtual environment (.venv) ...")
        subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True)
    ok(".venv")
    say("  installing packages (mcp, numpy, pillow) ...")
    r = subprocess.run([str(VENV_PY), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        warn("pip failed:\n" + r.stderr[-1500:])
        return False
    ok("packages installed")
    node = shutil.which("node")
    if node:
        v = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
        ok(f"Node {v} (needed for the Studio bridge)")
    else:
        warn("Node.js not found -- install the LTS from nodejs.org; RobloxForge's Studio tools need it")
    say("")
    say("  Roblox Studio: the first time RobloxForge starts, the Studio bridge installs its plugin. Restart Studio")
    say("  once after that, and keep a place open while you work.")
    return True


def check():
    say("starting the server once to count its tools (Studio does not need to be open) ...")
    code = ("import asyncio,sys\nfrom mcp import Client\nfrom mcp.client.stdio import StdioServerParameters\n"
            "async def m():\n  async with Client(StdioServerParameters(command=sys.executable,args=[sys.argv[1]]),"
            "read_timeout_seconds=120) as c:\n    print(len((await c.list_tools()).tools))\nasyncio.run(m())\n")
    r = subprocess.run([str(VENV_PY), "-c", code, str(SERVER)], capture_output=True, text=True, timeout=240)
    n = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "?"
    if r.returncode == 0:
        ok(f"RobloxForge answered with {n} tools (49 of them need Studio open with the plugin)")
    else:
        warn("the server did not start:\n" + r.stderr[-1500:])


def menu():
    say("")
    say("Connect it to your AI app -- run one of these:")
    for key, (label, _) in APPS.items():
        say(f"  python connect.py {key:<15} {label}")
    say("")
    say("Add --print to see what would change without changing anything. Restart the app afterwards.")
    say("Add --tools core (or e.g. --tools ui,animation) to expose fewer tools; apps with a tool limit need it.")
    say("Step-by-step guide for every app: https://cosmiccheesee.github.io/RobloxForge/setup.html")


def main(argv):
    if not argv:
        if setup():
            menu()
        return
    if argv[0] == "check":
        check()
        return
    key = argv[0]
    if key not in APPS:
        say(f"unknown app '{key}'")
        menu()
        sys.exit(2)
    if not VENV_PY.exists():
        warn("run `python connect.py` first, to set up the .venv")
        sys.exit(1)
    label, fn = APPS[key]
    dry = "--print" in argv
    global TOOLS
    for i, a in enumerate(argv):
        if a.startswith("--tools="):
            TOOLS = a.split("=", 1)[1]
        elif a == "--tools" and i + 1 < len(argv):
            TOOLS = argv[i + 1]
    say(f"{label}: {'showing' if dry else 'adding'} RobloxForge")
    if fn(dry) and not dry:
        say("")
        say("Done. Fully quit and reopen the app (desktop apps: also from the system tray) so it starts RobloxForge.")


if __name__ == "__main__":
    main(sys.argv[1:])
