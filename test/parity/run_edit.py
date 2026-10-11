"""Exercise every parity tool that works in EDIT mode against a sandbox folder, then clean up.
Prints PASS / FAIL per call; a call marked expect_error passes when the tool refuses."""
import asyncio
import json
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters

T = "Workspace.ForgeParityTest"
CALLS = [
    ("create_object", {"className": "Folder", "parent": "Workspace", "name": "ForgeParityTest"}),
    ("create_object", {"className": "Part", "parent": T, "name": "A",
                       "properties": {"Size": [4, 1, 2], "Color": "#ff8000", "Material": "Wood", "Anchored": True,
                                      "CFrame": {"position": [0, 600, 0]}}}),
    ("mass_create_objects", {"objects": [
        {"className": "Part", "parent": T, "name": "B", "properties": {"Anchored": True, "Position": [6, 600, 0]}},
        {"className": "Model", "parent": T, "name": "M"},
        {"className": "Script", "parent": T, "name": "S", "properties": {"Source": "print('parity hello')\n-- marker_xyz"}}]}),
    ("create_object", {"className": "NotAClass", "parent": T}, "expect_error"),
    ("get_file_tree", {"path": T, "maxDepth": 2}),
    ("search_files", {"query": "marker_xyz", "searchType": "content", "root": T}),
    ("search_files", {"query": "Part", "searchType": "type", "root": T}),
    ("get_services", {}),
    ("get_instance_children", {"instancePath": T}),
    ("get_descendants", {"instancePath": T, "classFilter": "BasePart"}),
    ("list_scripts", {"root": T}),
    ("set_property", {"instancePath": T + ".A", "propertyName": "Transparency", "propertyValue": 0.25}),
    ("set_property", {"instancePath": T + ".A", "propertyName": "Nope", "propertyValue": 1}, "expect_error"),
    ("mass_set_property", {"paths": [T + ".A", T + ".B"], "propertyName": "BrickColor", "propertyValue": "Bright red"}),
    ("mass_get_property", {"paths": [T + ".A", T + ".B"], "propertyName": "Position"}),
    ("search_by_property", {"propertyName": "Material", "propertyValue": "Wood", "root": T}),
    ("set_calculated_property", {"paths": [T + ".A", T + ".B"], "propertyName": "Position", "formula": "[i*10, 600, z]"}),
    ("set_relative_property", {"paths": [T + ".A", T + ".B"], "propertyName": "Position", "operation": "add", "value": [0, 5, 0]}),
    ("get_class_info", {"className": "ParticleEmitter"}),
    ("compare_instances", {"instancePathA": T + ".A", "instancePathB": T + ".B"}),
    ("clone_object", {"instancePath": T + ".A", "targetParentPath": T + ".M", "name": "A2"}),
    ("diff_subtree", {"pathA": T + ".A", "pathB": T + ".M.A2", "maxDepth": 1}),
    ("smart_duplicate", {"instancePath": T + ".B", "count": 3,
                         "options": {"namePattern": "B_{n}", "positionOffset": [0, 0, 3],
                                     "propertyVariations": {"Color": ["#ff0000", "#00ff00"]}}}),
    ("mass_duplicate", {"duplications": [{"instancePath": T + ".A", "count": 2, "options": {"namePattern": "AA{n}"}}]}),
    ("reparent_instance", {"sourcePath": T + ".B_1", "destinationPath": T + ".M"}),
    ("delete_object", {"instancePath": T + ".AA2"}),
    ("undo", {}),
    ("redo", {}),
    ("insert_service", {"name": "Teams"}),
    ("get_selection", {}),
    ("set_attribute", {"instancePath": T + ".A", "attributeName": "Spot", "attributeValue": [1, 2, 3]}),
    ("set_attribute", {"instancePath": T + ".A", "attributeName": "Tint", "attributeValue": "#123456", "valueType": "Color3"}),
    ("bulk_set_attributes", {"instancePath": T + ".A", "attributes": {"Hp": 50, "Boss": True, "Tag": "x"}}),
    ("attribute_schema_validate", {"targetPath": T + ".A", "schema": {"Hp": {"type": "number", "min": 0, "max": 40},
                                                                      "Missing": {"required": True}}}),
    ("delete_attribute", {"instancePath": T + ".A", "attributeName": "Tag"}),
    ("add_tag", {"instancePath": T + ".A", "tagName": "ForgeParity"}),
    ("get_tags", {"instancePath": T + ".A"}),
    ("get_tagged", {"tagName": "ForgeParity"}),
    ("remove_tag", {"instancePath": T + ".A", "tagName": "ForgeParity"}),
    ("collision_groups", {"op": "create", "name": "ForgeParityGroup"}),
    ("collision_groups", {"op": "set_collidable", "name": "ForgeParityGroup", "other": "Default", "collidable": False}),
    ("collision_groups", {"op": "assign", "name": "ForgeParityGroup", "paths": [T + ".A"]}),
    ("collision_groups", {"op": "list"}),
    ("collision_groups", {"op": "assign", "name": "Default", "paths": [T + ".A"]}),
    ("collision_groups", {"op": "remove", "name": "ForgeParityGroup"}),
    ("streamingenabled_audit", {}),
    ("get_output_log", {"maxEntries": 5}),
    ("get_studio_mode", {}),
    ("viewport_pick", {"x": 400, "y": 300}),
    ("script_editor", {"action": "list"}),
    ("script_editor", {"action": "read", "path": T + ".S"}),
    ("studio_activity", {}),
    ("get_handler_health", {}),
    ("studio_identity", {}),
    ("wait_for", {"condition": "workspace:FindFirstChild('ForgeParityTest') ~= nil", "timeout": 5}),
    ("debug_watch", {"instancePath": T + ".A", "seconds": 1}),
    ("terrain_get_materials", {}),
    ("terrain_fill_block", {"cframe": [0, 560, 0], "size": [8, 4, 8], "material": "Grass"}),
    ("terrain_fill_ball", {"center": [12, 560, 0], "radius": 3, "material": "Rock"}),
    ("terrain_fill_wedge", {"cframe": [24, 560, 0], "size": [4, 4, 4], "material": "Sand"}),
    ("terrain_fill_cylinder", {"cframe": [36, 560, 0], "height": 4, "radius": 2, "material": "Ice"}),
    ("terrain_read_voxels", {"min": [-6, 556, -6], "max": [40, 564, 6]}),
    ("terrain_fill_block", {"cframe": [18, 560, 0], "size": [60, 12, 16], "material": "Air"}),
    ("terrain_clear", {}, "expect_error"),
    ("lighting_get", {}),
    ("lighting_list_presets", {}),
    ("particle_create", {"parentPath": T + ".A", "name": "Sparks", "properties": {
        "Rate": 30, "Lifetime": [0.5, 1.5], "Size": [[0, 1], [1, 0]], "Color": [[0, "#ffcc66"], [1, "#ff3300"]], "Enabled": False}}),
    ("particle_tune", {"emitterPath": T + ".A.Sparks", "properties": {"Speed": [2, 6], "Rate": 10}}),
    ("sound_load_from_assetid", {"parentPath": T + ".A", "assetId": "9113585407", "name": "Breath", "volume": 0.3}),
    ("sound_set_eq", {"soundPath": T + ".A.Breath", "lowGain": 4, "highGain": -6}),
    ("sound_set_reverb", {"soundPath": T + ".A.Breath", "decayTime": 2.5, "wetLevel": -8}),
    ("tween_preview", {"targetPath": T + ".A", "tweenInfo": {"time": 0.5, "style": "Sine"}, "goal": {"Transparency": 0.8}, "revert": True}),
    ("textchat_list_channels", {}),
    ("material_list_variants", {}),
    ("search_materials", {"query": ""}),
    ("material_create_variant", {"name": "ForgeParityVariant", "baseMaterial": "Wood", "studsPerTile": 6}),
    ("profile_snapshot", {}),
    ("profile_start", {"intervalMs": 200}),
    ("profile_stop", {}),
    ("animation_load_keyframes", {"parentPath": T, "name": "KF", "keyframes": [{"time": 0, "poses": {"Torso": {"cframe": [0, 0, 0]}}}]}),
    ("export_build", {"instancePath": T + ".M", "outputId": "parity_test", "style": "forge_tests"}),
    ("list_library", {"style": "forge_tests"}),
    ("get_build", {"id": "forge_tests/parity_test"}),
    ("create_build", {"id": "forge_tests/crate", "palette": [{"color": "#8a6a40", "mat": "WoodPlanks"}],
                      "parts": [[0, 1, 0, 2, 2, 2, 0, 0, 0, 0, 0]]}),
    ("generate_build", {"id": "forge_tests/stairs", "palette": [{"color": "#888888", "mat": "Concrete"}],
                        "code": "for (let i = 0; i < 6; i++) box(0, 0.5 + i * 0.5 + 0.25, i * 1.0, 4, 0.5 + i * 0.5, 1);"}),
    ("import_build", {"buildData": "forge_tests/stairs", "targetPath": T, "position": [60, 600, 0]}),
    ("import_scene", {"sceneData": {"models": [{"id": "forge_tests/crate", "position": [70, 600, 0]},
                                               {"id": "forge_tests/crate", "position": [74, 600, 0]}]}, "targetPath": T}),
    ("opencloud_datastore", {"op": "list_stores", "universeId": 1}, "expect_error"),
    ("opencloud_universe", {"op": "restart_servers", "universeId": 1}, "expect_error"),
    ("place_publish", {"universeId": 1, "placeId": 1, "file": "nope.rbxl"}, "expect_error"),
    ("delete_object", {"instancePath": "Workspace.ForgeParityTest"}),
]


async def main(only):
    params = StdioServerParameters(command=sys.executable, args=["server.py"])
    fails = 0
    async with Client(params, read_timeout_seconds=240) as c:
        for item in CALLS:
            name, args = item[0], item[1]
            expect_err = len(item) > 2
            if only and name not in only and name not in ("create_object", "mass_create_objects", "delete_object"):
                continue
            try:
                r = await c.call_tool(name, args)
                body = " ".join(getattr(b, "text", "") or "" for b in r.content)
                err = r.is_error
            except Exception as e:  # noqa: BLE001
                body, err = f"EXC {e}", True
            ok = err == expect_err
            fails += 0 if ok else 1
            print(f"{'PASS' if ok else 'FAIL'}  {name:26} {body.replace(chr(10), ' ')[:170]}")
    print(f"\n{fails} failure(s) of {len(CALLS)} calls")


asyncio.run(main(set(sys.argv[1:])))
