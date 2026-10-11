"""Parity tools that change shared state (restored afterwards), touch the disk, or need a playtest.
Set FORGE_TEST_PLAYER to your Roblox username (the character name in a solo playtest)."""
import asyncio, json, os, shutil, sys, tempfile
from pathlib import Path
from mcp import Client
from mcp.client.stdio import StdioServerParameters

TMP = Path(tempfile.mkdtemp(prefix="forge_parity_"))
ME = os.environ.get("FORGE_TEST_PLAYER", "Player1")
F = "ServerStorage.ForgeParityScripts"


async def call(c, name, args, expect_error=False, show=170):
    try:
        r = await c.call_tool(name, args)
        body = " ".join(getattr(b, "text", "") or "" for b in r.content)
        err = r.is_error
    except Exception as e:  # noqa: BLE001
        body, err = f"EXC {e}", True
    ok = err == expect_error
    print(f"{'PASS' if ok else 'FAIL'}  {name:26} {body.replace(chr(10), ' ')[:show]}")
    try:
        return ok, json.loads(body)
    except ValueError:
        return ok, body


async def main():
    fails = 0
    async with Client(StdioServerParameters(command=sys.executable, args=["server.py"]), read_timeout_seconds=300) as c:
        async def t(*a, **k):
            nonlocal fails
            ok, v = await call(c, *a, **k)
            fails += 0 if ok else 1
            return v
        # ---- lighting, restored
        saved = (await t("lighting_get", {}))["lighting"]
        await t("lighting_set_preset", {"preset": "horror"})
        await t("lighting_set", {"properties": {"Brightness": 1.5, "ClockTime": 9}})
        await t("lighting_set", {"properties": saved})
        after = (await t("lighting_get", {}))["lighting"]
        diff = {k for k in saved if json.dumps(saved[k]) != json.dumps(after.get(k))}
        print("      lighting restored exactly:", not diff, sorted(diff)[:8])
        # ---- text chat, restored
        await t("textchat_create_command", {"name": "ForgeParityCmd", "primaryAlias": "/forgeparity"})
        await t("textchat_list_channels", {})
        await t("delete_object", {"instancePath": "TextChatService.TextChatCommands.ForgeParityCmd"})
        # ---- scripts on disk
        await t("create_object", {"className": "Folder", "parent": "ServerStorage", "name": "ForgeParityScripts"})
        await t("create_object", {"className": "ModuleScript", "parent": F, "name": "Mod", "properties": {"Source": "return {v = 1}"}})
        await t("create_object", {"className": "Script", "parent": F, "name": "Run", "properties": {"Source": "print('run')"}})
        out = TMP / "pull"
        await t("source_pull", {"out_dir": str(out), "roots": [F], "dry_run": True})
        await t("source_pull", {"out_dir": str(out), "roots": [F]})
        mod = next(out.rglob("Mod.lua"))
        mod.write_text("return {v = 2}", encoding="utf-8")
        await t("source_push", {"in_dir": str(out), "dry_run": True})
        await t("source_push", {"in_dir": str(out)})
        await t("search_files", {"query": "v = 2", "searchType": "content", "root": F})
        await t("source_snapshot", {"dir": str(TMP / "snap"), "roots": [F], "message": "parity test"})
        lf = TMP / "two.luau"
        lf.write_text("return 1 + 1", encoding="utf-8")
        await t("execute_luau_from_file", {"file": str(lf)})
        sf = TMP / "Hello.server.lua"
        sf.write_text("print('from a file')", encoding="utf-8")
        await t("insert_asset_from_file", {"file": str(sf), "parentPath": F})
        await t("list_scripts", {"root": F})
        await t("delete_object", {"instancePath": F})
        # ---- store model (Roblox-made only), removed again
        await t("create_object", {"className": "Folder", "parent": "Workspace", "name": "ForgeParityStore"})
        await t("insert_model", {"query": "crate", "parentPath": "Workspace.ForgeParityStore", "position": {"x": 0, "y": 700, "z": 0}}, show=260)
        await t("get_descendants", {"instancePath": "Workspace.ForgeParityStore", "classFilter": "LuaSourceContainer"})
        await t("delete_object", {"instancePath": "Workspace.ForgeParityStore"})
        # ---- sound preview (quiet)
        sp = await t("sound_play_preview", {"assetId": "9113585407", "volume": 0.15})
        if isinstance(sp, dict) and sp.get("soundId"):
            await t("sound_stop_preview", {"soundId": sp["soundId"]})
        # ---- a playtest
        await t("start_playtest", {"mode": "play"})
        await asyncio.sleep(6)
        await t("get_playtest_output", {"tail": 5})
        await t("get_studio_mode", {})
        await t("profile_snapshot", {"peer": "server"})
        await t("profile_start", {"peer": "server", "intervalMs": 200})
        await asyncio.sleep(1.5)
        await t("profile_stop", {"peer": "server"})
        await t("animation_list_tracks", {"targetPath": "Workspace." + ME, "peer": "server"})
        await t("debug_watch", {"instancePath": "Workspace", "seconds": 2, "peer": "server"})
        await t("debug_collisions", {"instancePath": "Workspace." + ME, "seconds": 2, "peer": "server"})
        await t("character_navigation", {"position": [10, 0, 10], "timeout": 8, "peer": "client"})
        await t("viewport_pick", {"x": 400, "y": 300, "peer": "client"})
        await t("wait_for", {"condition": "#game:GetService('Players'):GetPlayers() > 0", "peer": "server", "timeout": 10})
        await t("stop_playtest", {}, show=300)
        await t("run_script_in_play_mode", {"code": "print('hello from play mode') return 6 * 7", "settle": 4}, show=300)
        await t("run_tests", {"seconds": 80}, show=400)
    shutil.rmtree(TMP, ignore_errors=True)
    print(f"\n{fails} failure(s)")


asyncio.run(main())
