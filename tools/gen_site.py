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

from robloxforge.groups import ORDER, TITLES, group_of  # noqa: E402


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")])
    async with Client(params, read_timeout_seconds=120) as c:
        tools = (await c.list_tools()).tools
    from robloxforge import server
    native = set(server.NATIVE)
    by = {}
    for t in tools:
        by.setdefault(group_of(t.name), []).append(t)
    cards = []
    for g in ORDER:
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
            rows.append(f'<li data-k="{html.escape((t.name + " " + desc + " " + g).lower())}"><code>{html.escape(t.name)}</code>'
                        f'{badge}<p>{html.escape(first)}</p>'
                        + (f'<small>{html.escape(props)}</small>' if props else "") + "</li>")
        cards.append(f'<section><h2>{html.escape(TITLES[g])} <span>{len(ts)} &middot; group <code>{g}</code></span></h2>'
                     f'<ul>{"".join(rows)}</ul></section>')
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
<div class="cta"><a href="https://github.com/CosmicCheesee/RobloxForge">GitHub</a><a class="alt" href="setup.html">Connect your AI</a><a class="alt" href="#tools">All tools</a></div>
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
python connect.py</pre>
<p>Works with Claude Code and Claude Desktop, Codex CLI and the ChatGPT desktop app, Gemini CLI, VS Code Copilot,
Cursor, Devin Desktop / Windsurf, Zed and LM Studio. <a href="setup.html"><b>Step-by-step guide for your app &rarr;</b></a></p>
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
