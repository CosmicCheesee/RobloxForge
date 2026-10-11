# RobloxForge

**One MCP server for building Roblox games with an AI agent** -- 204 tools for Roblox Studio: control and
playtests, modelling with numeric audits, a UI designer with an offline layout engine, animation checks,
performance measurement, script sync to disk, Open Cloud, and offline rendering that works even when Studio
cannot draw.

**Site:** https://cosmiccheesee.github.io/RobloxForge -- the full tool catalogue.

- **Everything the other Roblox MCP servers have.** Surveyed against 6xvl/robloxstudio-mcp-server,
  EL4CTEO/rbx-studio-mcp, drgost1/robloxstudio-mcp, bdidk235/RobloxStudioMCP, kolvian/roblox-mcp-server and
  Roblox's own studio-rust-mcp-server; tool names follow 6xvl so prompts carry over.
- **It cannot crash your playtest.** Studio pauses on any error inside an eval, even under `pcall`. Every
  input is validated (in Python, and against the engine's own reflection data) before Luau runs.
- **It can see without Studio.** A perspective renderer with a depth buffer, a UI layout engine and an animation
  sampler that steps rigs in edit mode -- visual checks keep working on a remote or minimised Studio.
- **Built while making a real game** (a Backrooms-style horror game), so the tools are the ones that came up:
  prop and in-hand checks, HUD audits, moving-fps tests, A/B profiling with pinned seeds.

## Quick start

Needs Windows or macOS with Roblox Studio, Python 3.11+, Node.js (for `npx`), and the Studio MCP plugin that
`@chrrxs/robloxstudio-mcp` installs (`--auto-install-plugin`, or see its README).

```
git clone https://github.com/CosmicCheesee/RobloxForge
cd RobloxForge
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt        # macOS/Linux: .venv/bin/python
claude mcp add robloxforge -s user -- <full path>/.venv/Scripts/python.exe <full path>/server.py
```

Open Studio with the plugin enabled, start a new Claude Code session, and `/mcp` lists RobloxForge.
`forge_status` checks the bridge, the connected Studio, Rojo and git in one call.

**Configuration** (all optional): copy `forge.local.example.json` to `forge.local.json` (git-ignored) or set the
matching environment variables -- `repo` / `FORGE_REPO` (your Rojo project, for the repo tools), `selene` /
`FORGE_SELENE`, `rojo` / `FORGE_ROJO`, `rojo_port` / `FORGE_ROJO_PORT`. Open Cloud tools read an API key from
`FORGE_OPENCLOUD_KEY` or `~/.robloxforge/opencloud_key`.

## How it is built

```
Claude Code ──stdio──▶ RobloxForge (Python, MCP SDK v2 low-level Server)
                         ├── 155 native tools (this repo)
                         └── child MCP client ──stdio──▶ robloxstudio-mcp (npx)
                                                          └── HTTP :58741 ──▶ Studio plugin
                                                                              (edit / server / client peers)
```

An MCP server is a process that speaks JSON-RPC 2.0 over stdio (or HTTP). It answers `initialize`,
`tools/list` (name, description, JSON-Schema input) and `tools/call` (content blocks: text, image,
structured JSON; `isError` for failures). RobloxForge uses the low-level `mcp.server.Server` with
`on_list_tools` / `on_call_tool` handlers, because it has to re-publish another server's tools with
their own JSON schemas. Its lifespan starts robloxstudio-mcp as a **child MCP server** and keeps a
client session to it. Every child tool is re-exported unchanged, and the native tools are built on
the child's primitives (`execute_luau`, `eval_server_runtime`, `eval_client_runtime`,
`capture_screenshot`, `capture_script_profiler`). That reuses its Studio plugin and playtest-peer
bridge instead of forking it. If the child can't start, the native offline tools still work.

## Tools

**Bridged (49):** everything robloxstudio-mcp has. That includes `execute_luau`, `eval_*_runtime`,
playtests, `capture_screenshot`, mouse/keyboard input, profilers, script editing, assets, docs,
`get_scene_analysis` and rbxm import/export.

**Modelling**

| tool | what |
|---|---|
| `model_build` | Builds a Model from a part list, validated in Python first so the Luau never throws. Then runs both audits. Leaves an undo waypoint in edit mode. |
| `model_export` | Model → part list in pivot space (round-trips with `model_build`). |
| `model_audit` | Visual-pass numeric audit in Studio: ZFIGHT / FLOAT / HIDDEN / GROUND. |
| `model_seat` | Seats a model by its lowest *true* corner onto the surface below, or onto `floor_y`. |
| `parts_audit` | The same z-fight/floating audit offline, before anything is built. |

**Visual aid**

| tool | what |
|---|---|
| `model_shots` | Real Studio screenshots from N angles, auto-framed, in a temporary lit booth, as one labelled contact sheet. Works in edit mode and on a playtest client. |
| `parts_render` | Offline flat-shaded orthographic render of a part list (front/back/left/right/top/iso). |
| `map_plan` | Top-down floor plan around a point or player: walls, floors, furniture, players with facing. |

**Scripting / repo**

| tool | what |
|---|---|
| `repo_lint` | selene from the repo root: errors in full, warnings grouped by rule. |
| `luau_check` | Parses and lints a Luau snippet before it goes to an eval. |
| `repo_drift` | Compares every Studio script with the Rojo files on disk (length + Adler-32). |
| `rojo_status` | Checks `rojo serve` on :34872, and starts it detached with `start: true`. |
| `notes_search` | Regex search over HANDOFF / MapGeneratorNotes / ambience / audio notes. |

**Measuring**

| tool | what |
|---|---|
| `perf_snapshot` | fps, worst frame, GPU/CPU ms, draw/shadow calls, tris, instances, memory. Warns when Studio is unfocused. |
| `perf_glide` | Repeatable moving test through fresh chunks: fps, worst frame, worst second, per second, chunk arrivals. |
| `profile_summary` | Script profiler → total Lua ms/s, per-script ms/s, hot lines. |
| `game_selftest` | The place's SelfTest verdict. |
| `forge_status` | Bridge, connected Studio instances, Rojo, git state. |

**UI: design, see, build, check, ship, drive** (`robloxforge/ui/`, `ui_tools.py`)

| tool | what |
|---|---|
| `ui_components` | The 46-component library (buttons, cards, modals, inputs, toggles, sliders, tabs, lists, chat, toasts, HUD meters, hotbars, slots, crosshairs, dialogue, shop tiles...). Lists them, or expands one into plain nodes. |
| `ui_template` | 11 complete, responsive screens: hud, pause_menu, settings, inventory, shop, dialog, title_menu, loading, leaderboard, results, notifications. Returns the spec, plus a render with the audit at desktop and phone. |
| `ui_theme` | Design tokens: presets modern-dark / modern-light / glass / terminal / backroom (mirrors the game's UITheme), a WCAG contrast report, and saving custom themes. |
| `ui_render` | **Offline** render of a spec at any screen sizes, through a real layout engine (UDim2, anchors, padding, list/flex/wrap, grids, auto-size, constraints, corners, strokes, gradients, text). Runs an automatic audit; `save_to` keeps the PNG for later diffs. |
| `ui_build` | Builds a spec in Studio (StarterGui in edit, PlayerGui on a client), then runs the live audit. Every class/property/enum is whitelisted and verified against the engine, so a build cannot throw. |
| `ui_export` | Any existing GUI → spec (only non-default props). Game UIs come from a playtest client (`PlayerGui.X`). |
| `ui_audit` | Live audit on the real layout: OVERFLOW, TINY, CONTRAST (WCAG vs the actual backdrop; glyphs need 3:1), NOBACKDROP, OFFSCREEN, CLIPPED, OVERLAP, TOUCH, FIXED, INVISIBLE. Also a census of colours/sizes/fonts/radii and UI perf (CanvasGroup texture, TextScaled, gradients). |
| `ui_preview` | Real Studio screenshots across Studio's own device presets (iPhone 14, iPad, laptop, console...), isolated from other GUIs. |
| `ui_codegen` | Spec or live GUI → standalone Luau (module or self-mounting LocalScript) with an interaction runtime: hover/press, focus rings, toggles, draggable sliders, tabs, click-away dismiss, CanvasGroup fade+scale open/close (fast in, slow out), optional Heartbeat `Enabled` keep-alive. Writes into the repo and lints it. |
| `ui_tree` / `ui_at` | Compact outline of a GUI; which on-screen objects sit under a pixel. |
| `ui_click` / `ui_click_text` / `ui_type` | Drive a UI by path or by visible text (spacing-insensitive: "P L A Y" matches "play"), or type into a TextBox. |
| `ui_style_scan` | Repo-wide census of hard-coded colours (near-duplicates grouped), text sizes, fonts and radii: the map for moving a game onto one theme. |
| `ui_diff` | Visual regression between two images: changed-pixel share, regions, highlighted diff. |
| `ui_destroy` | Remove a preview GUI. |

Glyphs, measured in the engine: × ✓ ○ ◆ ♥ ★ ▶ ↑ ↓ ← → ⬆ ⬇ ∞ ⚙ ☀ ☂ ◉ ☗ ⚠ ✚ … and colour emoji all render.
✕ ✦ ♜ ⟳ ✎ ☰ render as **empty boxes**, and ✖ ✔ as near-invisible dark emoji; ui_build and ui_render warn about these.

**Play: drive the game like a player** (`play_tools.py`, `winctl.py`)

| tool | what |
|---|---|
| `play_focus` | Brings Studio to the front. `capture=true` also gives the game view real OS focus (a middle-click, which the game binds to nothing) so first-person mouse lock engages. |
| `play_start` / `play_stop` | Start a playtest, wait for the character, click the title-screen button (default "play"). |
| `play_keys` | Key steps: hold W+Shift for 2 s, tap E, wait, type text. |
| `play_look` | Real OS mouse-look, closed-loop on the camera angle, self-calibrating; to an angle, by a delta, or at a point/instance. **Only moves the mouse while Studio is the foreground window.** |
| `play_goto` | Walk to a point or instance: ray-fan steering toward the clearest heading, short legs, jump/strafe when stuck. |
| `play_state` / `play_see` | Position, speed, health, camera, crosshair target, nearby doors/slits/card rooms/prompts/loot, chosen attributes; `play_see` adds a screenshot. |
| `play_interact` | Face a target, press E. |
| `studio_filmstrip` | N screenshots over time as one sheet, for checking motion and animation (about 1 frame per second). |

**Animation** (`anim_tools.py`, `render3d.py`). None of these needs a playtest or Studio rendering: a clone of the
rig is stepped with `Animator:StepAnimations` in edit mode, in a booth that is always removed, and the pictures
come from an offline perspective renderer with a real depth buffer.

| tool | what |
|---|---|
| `anim_rig` | `audit`: Motor6D tree, Animator, root, anchored or unjointed parts, a Part1 driven twice, i.e. every reason a rig will not animate. `r6`: build a standard R6 test dummy. `remove`: delete the dummies. |
| `anim_build` | Author a KeyframeSequence from JSON (`keyframes: [{t, poses: {PartName: {rot, pos, easing, dir}}}]`, `loop`, `priority`, `markers`). Poses are nested along the rig's joint tree the way the Animation Editor saves them, it is saved under `ServerStorage.ForgeAnimations`, and it is registered at once so it plays with no upload. Warns about part names the rig does not have. |
| `anim_inspect` | Clip summary: length, loop, priority, keyframe times, parts posed, markers. Takes a path or an asset id. |
| `anim_sample` | Every part's CFrame (relative to the root) and every joint Transform at chosen times or at an fps. |
| `anim_filmstrip` | The motion as an offline filmstrip, N evenly spaced poses per row, one row per view (front/back/left/right/iso/top), with a floor at the rest foot level. Anything that goes through the floor is drawn red. |
| `anim_trace` | Numeric check of a motion: **floor penetration** (below the rest pose, with 0.08 tolerance for box corners dipping as a limb swings), **pops** (a step more than 4× the part's median turn rate and over 900°/s), **loop seams** (looped clips whose last pose does not meet the first), **limbs through each other** (OBB penetration, jointed neighbours excepted). |

Verified on an R6 dummy: a clean walk cycle traces clean, and a clip with a leg pushed 1.2 studs into the floor,
a 170° snap in 0.05 s and an open loop reports exactly those three faults, and no others.

**Parity: everything the other Roblox MCP servers have** (`parity*.py`, `luau/_prelude.luau`)

Surveyed 2026-10-11: 6xvl/robloxstudio-mcp-server (143 tools), EL4CTEO/rbx-studio-mcp (35), drgost1/robloxstudio-mcp
(51), bdidk235/RobloxStudioMCP, kolvian/roblox-mcp-server and Roblox's own studio-rust-mcp-server. Names follow 6xvl
where a tool came from there. Data-driven: each tool is one row (schema + a short Luau body) on a shared prelude
that converts JSON to real Roblox types and checks properties against ReflectionService first, so a wrong name or
type comes back as a message instead of an error that pauses Studio. ReflectionService is incomplete (it hides
`Script.Source`, and under-reports write permission), so unknown properties fall back to the live value's type and
"read-only" is only reported after a guarded write actually fails.

| group | tools |
|---|---|
| browse / inspect | `get_file_tree` `search_files` (name / class / script content) `get_services` `get_instance_children` `get_descendants` `list_scripts` `search_by_property` `get_class_info` (reflection) `compare_instances` `diff_subtree` `get_selection` |
| edit | `set_property` `mass_set_property` `mass_get_property` `set_calculated_property` (safe arithmetic formulas over i, n, x/y/z) `set_relative_property` `create_object` `mass_create_objects` `delete_object` `clone_object` `reparent_instance` `smart_duplicate` `mass_duplicate` `insert_service` `undo` `redo` |
| attributes / tags / physics | `set_attribute` `bulk_set_attributes` `delete_attribute` `attribute_schema_validate` `get_tags` `add_tag` `remove_tag` `get_tagged` `collision_groups` `streamingenabled_audit` |
| play / test / debug | `start_playtest` `get_playtest_output` `stop_playtest` (captured output) `get_output_log` `get_studio_mode` `run_script_in_play_mode` `run_tests` (SelfTest pass/fail) `wait_for` `character_navigation` `debug_watch` `debug_collisions` `viewport_pick` |
| scripts / files | `script_editor` (tabs, unsaved text, open at line, undoable edits) `source_pull` `source_push` `source_snapshot` (git) `execute_luau_from_file` `insert_asset_from_file` `insert_model` (Roblox-made models by default) `studio_activity` `get_handler_health` `studio_identity` |
| world | `terrain_fill_block/ball/wedge/cylinder` `terrain_clear` (confirm) `terrain_get_materials` `terrain_read_voxels` `lighting_get/set` `lighting_list_presets` `lighting_set_preset` (day dusk night horror studio backrooms) `particle_create/tune` `sound_play_preview` `sound_stop_preview` `sound_load_from_assetid` `sound_set_eq` `sound_set_reverb` `tween_preview` `textchat_configure` `textchat_create_command` `textchat_list_channels` `material_list_variants` `search_materials` `material_create_variant` `material_override_base` `humanoid_description_apply` `animation_play/stop/list_tracks/load_keyframes` `profile_snapshot/start/stop` |
| build library | `export_build` `create_build` `generate_build` (JS generator in a sandboxed Node process) `import_build` `import_scene` `list_library` `get_build` |
| Open Cloud (key in `FORGE_OPENCLOUD_KEY`; live changes need `confirm=true`) | `opencloud_datastore` (list/get/set/delete/increment) `opencloud_message` `opencloud_universe` (info, restart servers) `opencloud_bans` `place_publish` |

Not added, on purpose: 6xvl's own NOT-SUPPORTED stubs (generate_mesh / generate_material / generate_procedural_model,
wally_list, package_publish, physics_bake), its plugin-internal `reload_plugin` and `debugger`, and `place_check`
(needs the published place file, which an Open Cloud key cannot download).

Tests: `test/parity/run_edit.py` (91 calls in a sandbox folder, all pass) and `test/parity/run_state.py` (lighting
restored exactly, chat command, script sync round trip + git, files, store insert, sound, a playtest, play-mode code,
the SelfTest run).

### Part-list format

```json
{"n": "Leg", "sz": [0.2, 2.5, 0.2], "off": [1.8, 1.25, -1], "rot": [0, 0, 0],
 "shape": "Block|Cylinder|Ball|Wedge|CornerWedge", "color": [60, 60, 60] or "#3c3c3c",
 "mat": "Metal", "tr": 0, "cc": true, "primary": true}
```

- `rot` is in degrees, applied as `CFrame.Angles` (R = Rx·Ry·Rz).
- Cylinders run along local X.
- Front is −Z.
- Wedges rise toward +Z.

## Setup details

If robloxstudio-mcp is also registered on its own, RobloxForge's copy goes into proxy mode behind it on :58741
and still works; remove the standalone entry to avoid listing its 49 tools twice. `FORGE_CHILD_CMD` overrides
the child command line.

## Rules baked in

- **Never let an eval throw.** Studio's debugger pauses on errors inside evals, even under `pcall`, and that freezes
  the playtest. Every template nil-checks its lookups, and every input is validated in Python first.
- **Keep `perf_glide` short.** Each run is capped at 25 s, because the eval bridge times out at ~30 s, and a killed
  run would leave the body anchored.
- **Don't trust unfocused fps.** An unfocused Studio reads exactly 60 fps. `perf_snapshot` says so instead of
  reporting a phantom number.

## Test

```
.venv\Scripts\python test_client.py server.py "[[\"forge_status\",{}]]"
```

## Credits and licence

The Studio bridge is [robloxstudio-mcp](https://www.npmjs.com/package/@chrrxs/robloxstudio-mcp), run as a child
server and re-exported unchanged. The parity layer follows the tool sets of the servers listed above.
RobloxForge itself is MIT licensed -- see [LICENSE](LICENSE).
