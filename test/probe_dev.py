import asyncio, json, sys
sys.path.insert(0, '.')
from mcp import Client
from robloxforge.studio import child_params
async def main():
    async with Client(child_params(), read_timeout_seconds=90) as c:
        r = await c.call_tool("get_device_simulator_state", {"target": "edit", "includeDeviceList": True})
        [print(d["DeviceId"], d["DeviceForm"], d["Width"], d["Height"], d["ResolutionScale"]) for d in r.structured_content["devices"]]
asyncio.run(main())
