"""Tool groups: one place that says which family every tool belongs to.

Used by the site generator (to lay out the catalogue) and by the server (to expose only some groups, for apps
with a tool limit -- Devin Desktop / Windsurf caps an agent at 100 tools -- or small local models that do
better with a short list). Select with FORGE_TOOLS or "tools" in forge.local.json:
    all                       every tool (default)
    core                      studio, instances, scripts, playtest  (under 100)
    studio,instances,ui,...   any list of the group keys below
"""
from __future__ import annotations

ORDER = ["studio", "instances", "scripts", "playtest", "modelling", "ui", "play", "animation", "world", "terrain",
         "perf", "assets", "builds", "cloud"]

TITLES = {
    "studio": "Studio and session", "instances": "Instances, properties, attributes and tags",
    "scripts": "Scripts, source and repo", "playtest": "Playtests, tests and debugging",
    "modelling": "Modelling and visual checks", "ui": "UI design, build and audit", "play": "Play like a player",
    "animation": "Animation", "world": "Lighting, effects, sound and materials", "terrain": "Terrain",
    "perf": "Measuring performance", "assets": "Assets and files", "builds": "Build library",
    "cloud": "Open Cloud (live game)",
}

PROFILES = {"core": ["studio", "instances", "scripts", "playtest"]}

_STUDIO = {"forge_status", "get_handler_health", "studio_identity", "studio_activity", "get_connected_instances",
           "manage_instance", "get_place_info", "get_request_status", "get_roblox_docs", "get_roblox_skills",
           "manage_monetization"}
_PLAYTEST = {"start_playtest", "stop_playtest", "get_playtest_output", "run_script_in_play_mode", "run_tests",
             "wait_for", "debug_watch", "debug_collisions", "solo_playtest", "multiplayer_playtest", "get_runtime_logs",
             "get_output_log", "breakpoints", "eval_server_runtime", "eval_client_runtime", "game_selftest",
             "get_studio_mode", "viewport_pick", "set_network_profile", "get_simulation_state", "reset_simulation_state",
             "simulate_keyboard_input", "simulate_mouse_input", "set_device_simulator", "get_device_simulator_state"}
_BUILDS = {"export_build", "create_build", "generate_build", "import_build", "list_library", "get_build", "import_scene"}
_SCRIPTS = {"luau_check", "notes_search", "grep_scripts", "find_and_replace_in_scripts", "execute_luau",
            "execute_luau_from_file", "list_scripts"}
_WORLD = {"tween_preview", "search_materials", "humanoid_description_apply"}
_PERF = {"get_memory_breakdown", "get_scene_analysis", "streamingenabled_audit"}


def group_of(name: str) -> str:
    if name in _STUDIO:
        return "studio"
    if name.startswith(("anim_", "animation_")):
        return "animation"
    if name.startswith("ui_"):
        return "ui"
    if name.startswith("play_") or name in {"studio_filmstrip", "character_navigation"}:
        return "play"
    if name.startswith(("model_", "parts_")) or name == "map_plan":
        return "modelling"
    if name in _BUILDS:
        return "builds"
    if name.startswith("opencloud_") or name == "place_publish":
        return "cloud"
    if name.startswith("terrain_"):
        return "terrain"
    if name.startswith(("lighting_", "particle_", "sound_", "material_", "textchat_")) or name in _WORLD:
        return "world"
    if name.startswith(("perf_", "profile_", "capture_")) or name in _PERF:
        return "perf"
    if name in _PLAYTEST:
        return "playtest"
    if "script" in name or name.startswith(("source_", "repo_", "rojo_")) or name in _SCRIPTS:
        return "scripts"
    if "asset" in name or name in {"insert_model", "import_rbxm", "export_rbxm", "generate_model"}:
        return "assets"
    return "instances"


def selection(spec: str | None) -> set[str] | None:
    """None = everything. Unknown keys are ignored (and reported by forge_status)."""
    if not spec or spec.strip().lower() == "all":
        return None
    keys = set()
    for part in spec.replace(" ", "").lower().split(","):
        keys.update(PROFILES.get(part, [part]))
    keys.add("studio")       # forge_status and friends are always there, so a trimmed setup can still be checked
    return keys
