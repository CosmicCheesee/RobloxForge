"""Generate the GitHub Pages site (docs/index.html) from the server's own tool list.

Run from the repo root with Studio open (so the bridged tools are listed too):
    .venv/Scripts/python tools/gen_site.py
"""
import asyncio
import html
import json
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GROUPS = [
    ("Animation", lambda n: n.startswith("anim_") or n.startswith("animation_")),
    ("UI design, build and audit", lambda n: n.startswith("ui_")),
    ("Play like a player", lambda n: n.startswith("play_") or n in {"studio_filmstrip", "character_navigation"}),
    ("Modelling and visual checks", lambda n: n.startswith(("model_", "parts_")) or n in {"map_plan"}),
    ("Build library", lambda n: n in {"export_build", "create_build", "generate_build", "import_build", "list_library",
                                       "get_build", "import_scene"}),
    ("Open Cloud (live game)", lambda n: n.startswith("opencloud_") or n == "place_publish"),
    ("Terrain", lambda n: n.startswith("terrain_")),
    ("Lighting, effects, sound and materials", lambda n: n.startswith(("lighting_", "particle_", "sound_", "material_",
                                                                         "textchat_")) or n in {"tween_preview",
                                                                                                 "search_materials",
                                                                                                 "humanoid_description_apply"}),
    ("Measuring performance", lambda n: n.startswith(("perf_", "profile_", "capture_")) or n in {"get_memory_breakdown",
                                                                                                   "get_scene_analysis",
                                                                                                   "streamingenabled_audit"}),
    ("Playtests, tests and debugging", lambda n: n in {"start_playtest", "stop_playtest", "get_playtest_output",
                                                         "run_script_in_play_mode", "run_tests", "wait_for", "debug_watch",
                                                         "debug_collisions", "solo_playtest", "multiplayer_playtest",
                                                         "get_runtime_logs", "get_output_log", "breakpoints",
                                                         "eval_server_runtime", "eval_client_runtime", "game_selftest",
                                                         "get_studio_mode", "viewport_pick", "set_network_profile",
                                                         "get_simulation_state", "reset_simulation_state",
                                                         "simulate_keyboard_input", "simulate_mouse_input",
                                                         "set_device_simulator", "get_device_simulator_state"}),
    ("Scripts, source and repo", lambda n: "script" in n or n.startswith(("source_", "repo_", "rojo_")) or n in {
        "luau_check", "notes_search", "grep_scripts", "find_and_replace_in_scripts", "execute_luau",
        "execute_luau_from_file", "list_scripts"}),
    ("Assets and files", lambda n: "asset" in n or n in {"insert_model", "import_rbxm", "export_rbxm", "generate_model"}),
    ("Instances, properties, attributes and tags", lambda n: True),
]

STUDIO_NAMES = {"forge_status", "get_handler_health", "studio_identity", "studio_activity", "get_connected_instances",
                "manage_instance", "get_place_info", "get_request_status", "get_roblox_docs", "get_roblox_skills",
                "manage_monetization"}


def group_of(name):
    if name in STUDIO_NAMES:
        return "Studio and session"
    for g, test in GROUPS:
        if test(name):
            return g
    return "Other"


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")])
    async with Client(params, read_timeout_seconds=120) as c:
        tools = (await c.list_tools()).tools
    from robloxforge import server
    native = set(server.NATIVE)
    by = {}
    for t in tools:
        by.setdefault(group_of(t.name), []).append(t)
    order = ["Studio and session"] + [g for g, _ in GROUPS]
    cards = []
    for g in order:
        ts = sorted(by.get(g, []), key=lambda t: t.name)
        if not ts:
            continue
        rows = []
        for t in ts:
            desc = (t.description or "").strip()
            first = desc.split(". ")[0]
            if len(first) > 230:
                first = first[:230].rsplit(" ", 1)[0].rstrip(",;:-") + "..."
            elif not first.endswith((".", ")")):
                first += "."
            props = ", ".join(sorted((t.input_schema or {}).get("properties", {}).keys()))
            badge = '<span class="b n">forge</span>' if t.name in native else '<span class="b s">bridge</span>'
            rows.append(f'<li data-k="{html.escape((t.name + " " + desc).lower())}"><code>{html.escape(t.name)}</code>'
                        f'{badge}<p>{html.escape(first)}</p>'
                        + (f'<small>{html.escape(props)}</small>' if props else "") + "</li>")
        cards.append(f'<section><h2>{html.escape(g)} <span>{len(ts)}</span></h2><ul>{"".join(rows)}</ul></section>')
    total = len(tools)
    page = TEMPLATE.replace("{{TOTAL}}", str(total)).replace("{{NATIVE}}", str(len(native))) \
        .replace("{{BRIDGED}}", str(total - len(native))).replace("{{CARDS}}", "\n".join(cards))
    out = ROOT / "docs"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"docs/index.html: {total} tools ({len(native)} native)")


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>RobloxForge -- an MCP server for building Roblox games with AI</title>
<meta name="description" content="RobloxForge: {{TOTAL}} MCP tools for Roblox Studio -- control, modelling audits, UI design, animation checks, performance, Open Cloud and offline rendering.">
<style>
:root{--bg:#0e0f12;--panel:#16181d;--line:#262a33;--text:#e8e6df;--muted:#9a9a93;--accent:#e9c46a;--accent2:#7fb7ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--accent2)}code{font:13px ui-monospace,SFMono-Regular,Consolas,monospace}
header{padding:64px 24px 36px;max-width:1100px;margin:auto}
h1{font-size:44px;margin:0 0 8px;letter-spacing:-.5px}h1 b{color:var(--accent)}
.lede{font-size:18px;color:var(--muted);max-width:760px}
.stats{display:flex;gap:28px;margin:26px 0 8px;flex-wrap:wrap}.stats div{font-size:13px;color:var(--muted)}.stats b{display:block;font-size:28px;color:var(--text)}
.cta{display:flex;gap:10px;margin-top:22px;flex-wrap:wrap}.cta a{background:var(--accent);color:#1a1505;padding:10px 16px;border-radius:9px;text-decoration:none;font-weight:600}
.cta a.alt{background:var(--panel);color:var(--text);border:1px solid var(--line)}
main{max-width:1100px;margin:auto;padding:0 24px 80px}
.why{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:10px 0 34px}
.why div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}.why h3{margin:0 0 6px;font-size:15px}.why p{margin:0;color:var(--muted);font-size:14px}
pre{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;overflow:auto;font:13px/1.6 ui-monospace,Consolas,monospace}
#q{width:100%;padding:12px 14px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--text);font-size:15px;margin:14px 0 18px}
section{margin:0 0 26px}h2{font-size:18px;border-bottom:1px solid var(--line);padding-bottom:8px}h2 span{color:var(--muted);font-weight:400;font-size:14px}
ul{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}
li{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}li p{margin:6px 0 4px;color:var(--muted);font-size:13.5px}li small{color:#6e6e68;font-size:12px}
.b{font-size:10.5px;margin-left:8px;padding:2px 7px;border-radius:99px;vertical-align:2px}.b.n{background:#3a3220;color:var(--accent)}.b.s{background:#14304d;color:var(--accent2)}
footer{color:var(--muted);font-size:13px;text-align:center;padding:30px}
</style></head><body>
<header>
<h1>Roblox<b>Forge</b></h1>
<p class="lede">One MCP server for building Roblox games with an AI agent. Studio control and playtests, modelling with
numeric audits, a UI designer with an offline layout engine, animation checks, performance measurement, script sync to
disk, Open Cloud -- and offline rendering that keeps working when Studio cannot draw.</p>
<div class="stats"><div><b>{{TOTAL}}</b>tools</div><div><b>{{NATIVE}}</b>native</div><div><b>{{BRIDGED}}</b>bridged from robloxstudio-mcp</div><div><b>MIT</b>licence</div></div>
<div class="cta"><a href="https://github.com/CosmicCheesee/RobloxForge">GitHub</a><a class="alt" href="#start">Quick start</a><a class="alt" href="#tools">All tools</a></div>
</header>
<main>
<div class="why">
<div><h3>A superset</h3><p>Everything the other Roblox MCP servers offer -- surveyed against six of them -- with the same tool names where they came from.</p></div>
<div><h3>Won't freeze your playtest</h3><p>Studio pauses on any eval error, even under pcall. Every input is checked in Python and against the engine's reflection data before Luau runs.</p></div>
<div><h3>Sees without Studio</h3><p>A depth-buffered perspective renderer, a UI layout engine and an edit-mode animation sampler: visual checks work on a remote or minimised Studio.</p></div>
<div><h3>Built on a real game</h3><p>Prop and in-hand checks, HUD audits, moving-fps tests and seed-pinned A/B profiling came out of shipping one.</p></div>
</div>
<h2 id="start">Quick start</h2>
<pre>git clone https://github.com/CosmicCheesee/RobloxForge
cd RobloxForge
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
claude mcp add robloxforge -s user -- &lt;full path&gt;/.venv/Scripts/python.exe &lt;full path&gt;/server.py</pre>
<p>Needs Roblox Studio with the robloxstudio-mcp plugin, Python 3.11+ and Node.js. Start a new Claude Code session and <code>/mcp</code> lists RobloxForge; <code>forge_status</code> checks everything in one call.</p>
<h2 id="tools">All {{TOTAL}} tools</h2>
<input id="q" placeholder="Filter tools -- try terrain, playtest, animation, ui, datastore" autocomplete="off">
{{CARDS}}
</main>
<footer>RobloxForge &middot; MIT &middot; generated from the server's own tool list by tools/gen_site.py</footer>
<script>
const q=document.getElementById('q');q.addEventListener('input',()=>{const v=q.value.trim().toLowerCase();
document.querySelectorAll('li').forEach(li=>{li.style.display=!v||li.dataset.k.includes(v)?'':'none'});
document.querySelectorAll('section').forEach(s=>{const any=[...s.querySelectorAll('li')].some(l=>l.style.display!=='none');s.style.display=any?'':'none'})});
</script>
</body></html>
"""

asyncio.run(main())
