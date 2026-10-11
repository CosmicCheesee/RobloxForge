"""Play tools: drive the game the way a player does -- focus Studio, start a session, hold keys, look
with the real mouse, walk somewhere, interact, and read back what the player can see."""
from __future__ import annotations

import asyncio
import json
import math
import time

from .render import contact_sheet
from .server import PEER, STUDIO, image, text, tool
from .studio import ForgeError, long_string

try:
    from . import winctl
except ImportError:  # pragma: no cover
    winctl = None


def _need_win():
    if winctl is None:
        raise ForgeError("window control is Windows-only")


async def _focus():
    _need_win()
    st = await asyncio.to_thread(winctl.focus)
    if not st.get("ok"):
        raise ForgeError(f"could not bring Studio to the front: {st}")
    return st


STATE_LUAU = r"""
local A = game:GetService("HttpService"):JSONDecode(__A__)
local Players = game:GetService("Players")
local CS = game:GetService("CollectionService")
local UIS = game:GetService("UserInputService")
local lp = Players.LocalPlayer
if not lp then return {error = "run on a playtest client"} end
local ch = lp.Character
local hrp = ch and ch:FindFirstChild("HumanoidRootPart")
local hum = ch and ch:FindFirstChildOfClass("Humanoid")
local cam = workspace.CurrentCamera
if not cam then return {error = "no camera"} end
local cf = cam.CFrame
local lv = cf.LookVector
local out = {
	cam = {cf.X, cf.Y, cf.Z}, yaw = math.deg(math.atan2(-lv.X, -lv.Z)), pitch = math.deg(math.asin(math.clamp(lv.Y, -1, 1))),
	camType = cam.CameraType.Name, mouse = UIS.MouseBehavior.Name, fov = cam.FieldOfView,
}
if hrp then
	local p = hrp.Position
	local v = hrp.AssemblyLinearVelocity
	out.pos = {p.X, p.Y, p.Z}
	out.speed = Vector3.new(v.X, 0, v.Z).Magnitude
end
if hum then out.health = hum.Health; out.maxHealth = hum.MaxHealth end
if A.lite then
	-- steering for play_goto: of a fan of headings toward the target, the first that is clear ahead
	if hrp and A.target then
		local params = RaycastParams.new()
		params.FilterType = Enum.RaycastFilterType.Exclude
		params.FilterDescendantsInstances = {ch, cam}
		local p = hrp.Position
		local to = Vector3.new(A.target[1] - p.X, 0, A.target[3] - p.Z)
		local dist = to.Magnitude
		out.dist = dist
		if dist > 0.01 then
			local base = math.atan2(-to.X, -to.Z)
			local look = math.min(dist, A.probe or 9)
			for _, off in ipairs({0, 20, -20, 40, -40, 60, -60, 85, -85, 115, -115, 150, -150, 180}) do
				local a = base + math.rad(off)
				local d = Vector3.new(-math.sin(a), 0, -math.cos(a))
				local clear = true
				for _, h in ipairs({0.2, 1.6}) do
					for _, side in ipairs({-0.9, 0, 0.9}) do
						local o = p + Vector3.new(0, h - 1.2, 0) + d:Cross(Vector3.yAxis) * side
						local hit = workspace:Raycast(o, d * look, params)
						if hit and hit.Instance.CanCollide then clear = false break end
					end
					if not clear then break end
				end
				if clear then out.steer = math.deg(a); out.steerOff = off break end
			end
		end
	end
	return out
end
-- what the crosshair is on
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Exclude
params.FilterDescendantsInstances = {ch, cam}
local hit = workspace:Raycast(cf.Position, lv * (A.reach or 80), params)
if hit then
	local m = hit.Instance:FindFirstAncestorOfClass("Model")
	out.crosshair = {part = hit.Instance:GetFullName(), model = m and m.Name or nil, dist = (hit.Position - cf.Position).Magnitude}
end
-- nearby interactables: tagged doors/slits/card rooms, proximity prompts, loot
local near = {}
local p0 = hrp and hrp.Position or cf.Position
local function posOf(inst)
	if inst:IsA("BasePart") then return inst.Position end
	if inst:IsA("Model") then return inst:GetPivot().Position end
	if inst:IsA("Attachment") then return inst.WorldPosition end
	return nil
end
for _, tag in ipairs(A.tags or {"Door", "Slit", "CardRoom"}) do
	for _, inst in ipairs(CS:GetTagged(tag)) do
		local q = posOf(inst)
		if q and (q - p0).Magnitude < (A.radius or 25) and #near < 20 then
			near[#near + 1] = {kind = tag, path = inst:GetFullName(), dist = math.floor((q - p0).Magnitude * 10) / 10}
		end
	end
end
local op = OverlapParams.new()
op.FilterType = Enum.RaycastFilterType.Exclude
op.FilterDescendantsInstances = {ch}
local seen = {}
for _, part in ipairs(workspace:GetPartBoundsInRadius(p0, math.min(A.radius or 25, 30), op)) do
	local m = part:FindFirstAncestorOfClass("Model")
	if m and not seen[m] and (m:GetAttribute("LootId") ~= nil or m:GetAttribute("Grabbable") ~= nil) and #near < 40 then
		seen[m] = true
		near[#near + 1] = {kind = m:GetAttribute("LootId") ~= nil and "loot" or "grabbable", path = m:GetFullName(),
			dist = math.floor((m:GetPivot().Position - p0).Magnitude * 10) / 10}
	end
	local pp = part:FindFirstChildOfClass("ProximityPrompt")
	if pp and #near < 40 then
		near[#near + 1] = {kind = "prompt", path = pp:GetFullName(), action = pp.ActionText, key = pp.KeyboardKeyCode.Name}
	end
end
table.sort(near, function(a, b) return (a.dist or 0) < (b.dist or 0) end)
out.nearby = near
-- attributes: only the ones asked for (A.attrs = list of names), else the non-zero / non-empty ones, capped
local attrs, n = {}, 0
local want
if A.attrs then want = {} for _, k in ipairs(A.attrs) do want[k] = true end end
for _, src in ipairs({lp, ch}) do
	if src then
		for k, v in pairs(src:GetAttributes()) do
			local t = typeof(v)
			if (t == "number" or t == "boolean" or t == "string") and n < (A.maxAttrs or 30) then
				local interesting = want and want[k] or (not want and v ~= 0 and v ~= "" and v ~= false)
				if interesting then attrs[k] = v; n += 1 end
			end
		end
	end
end
out.attributes = attrs
return out
"""


async def state(lite=False, target=None, peer="client", **extra):
    args = {"lite": lite, "target": target} | extra
    code = STATE_LUAU.replace("__A__", long_string(json.dumps(args)), 1)
    val = await STUDIO.luau(code, peer, 30)
    if isinstance(val, dict) and val.get("error"):
        raise ForgeError(val["error"])
    return val


VIEW = {"offset": None}   # screen pixel = viewport pixel + offset (found by _capture)

MOUSE_LUAU = """
local UIS = game:GetService("UserInputService")
local m = UIS:GetMouseLocation()
local cam = workspace.CurrentCamera
local vp = cam and cam.ViewportSize or Vector2.zero
return {m.X, m.Y, vp.X, vp.Y, UIS.MouseBehavior.Name}
"""


async def _capture(peer="client"):
    """Give the game view real OS focus so first-person mouse lock engages. In a Studio playtest the lock
    only takes hold once the viewport itself has focus (normally your click into it), and until then the
    game sees mouse events with zero delta. Find where the viewport is on screen -- place the cursor twice
    and require Roblox to see the same displacement -- then middle-click its centre (bound to nothing)."""
    await _focus()
    _, _, _, (l, t, r, b) = winctl.main_window()
    cx, cy = (l + r) // 2, (t + b) // 2
    found = None
    for (px, py) in [(cx, cy), (cx - 200, cy), (cx + 200, cy - 100), (l + (r - l) // 3, t + (b - t) // 2)]:
        await asyncio.to_thread(winctl.set_cursor, px, py)
        await asyncio.sleep(0.12)
        m1 = await STUDIO.luau(MOUSE_LUAU, peer, 15)
        await asyncio.to_thread(winctl.set_cursor, px + 40, py + 30)
        await asyncio.sleep(0.12)
        m2 = await STUDIO.luau(MOUSE_LUAU, peer, 15)
        if abs((m2[0] - m1[0]) - 40) <= 2 and abs((m2[1] - m1[1]) - 30) <= 2:
            found = (px - m1[0], py - m1[1], m1[2], m1[3])
            break
    if not found:
        raise ForgeError("could not find the game view on screen -- is the Game tab visible in Studio?")
    ox, oy, vw, vh = found
    VIEW["offset"] = (ox, oy)
    await asyncio.to_thread(winctl.middle_click, ox + vw / 2, oy + vh / 2)
    await asyncio.sleep(0.25)
    return {"viewport_on_screen": [ox, oy, vw, vh]}


def _wrap(a):
    return (a + 180) % 360 - 180


# calibration survives between calls: pixels of mouse motion per degree, signed
CAL = {"yaw": None, "pitch": None}


async def look(yaw=None, pitch=None, dyaw=None, dpitch=None, peer="client", tol=1.5, drag=False, _retry=True):
    _need_win()
    if VIEW["offset"] is None:
        await _capture(peer)
    s = await state(True, peer=peer)
    ty = s["yaw"] + dyaw if dyaw is not None else (yaw if yaw is not None else s["yaw"])
    tp = s["pitch"] + dpitch if dpitch is not None else (pitch if pitch is not None else s["pitch"])
    tp = max(-80, min(80, tp))
    if drag:
        await asyncio.to_thread(winctl.right_button, True)
    try:
        for _ in range(10):
            ey, ep = _wrap(ty - s["yaw"]), tp - s["pitch"]
            if abs(ey) <= tol and abs(ep) <= tol:
                break
            ky = CAL["yaw"] or -8.0
            kp = CAL["pitch"] or -8.0
            dx = ey * ky if abs(ey) > tol else 0
            dy = ep * kp if abs(ep) > tol else 0
            dx = max(-1500, min(1500, dx))
            dy = max(-800, min(800, dy))
            before = s
            await asyncio.to_thread(winctl.mouse_move, dx, dy)
            await asyncio.sleep(0.06)
            s = await state(True, peer=peer)
            gy, gp = _wrap(s["yaw"] - before["yaw"]), s["pitch"] - before["pitch"]
            if abs(dx) > 20 and abs(gy) > 0.5:
                CAL["yaw"] = dx / gy
            if abs(dy) > 20 and abs(gp) > 0.5:
                CAL["pitch"] = dy / gp
            if abs(dx) > 20 and abs(gy) < 0.2 and abs(dy) < 20:
                if _retry:
                    VIEW["offset"] = None
                    await _capture(peer)
                    return await look(ty, tp, None, None, peer, tol, drag, _retry=False)
                raise ForgeError("the camera did not turn even after capturing the game view -- is the mouse "
                                 "locked by the game (first person)? try drag=true for a third-person camera")
    finally:
        if drag:
            await asyncio.to_thread(winctl.right_button, False)
    return s


async def keys(down, up):
    for k in down:
        await STUDIO.call("simulate_keyboard_input", {"keyCode": k, "action": "press"}, 15)
    return lambda: _release(up)


async def _release(ks):
    for k in ks:
        await STUDIO.call("simulate_keyboard_input", {"keyCode": k, "action": "release"}, 15)


# ---------------------------------------------------------------- tools
@tool("play_focus", "Bring the Roblox Studio window to the front (restoring it if minimised) so keyboard/mouse input "
      "reaches the game. capture=true also gives the game view real OS focus (a middle-click at its centre, which "
      "the game binds to nothing) so first-person mouse lock engages -- play_look does that by itself when needed.",
      {"status_only": {"type": "boolean"}, "capture": {"type": "boolean"}, "peer": PEER})
async def play_focus(a):
    _need_win()
    if a.get("status_only"):
        return [text(winctl.status())]
    st = await _focus()
    if a.get("capture"):
        st |= await _capture(a.get("peer", "client"))
    return [text(st)]


@tool("play_start", "Start a solo playtest and get into the game: waits for the client and character, focuses "
      "Studio, and clicks the title-screen button whose text contains `click_text` (default 'play'; '' to skip).",
      {"click_text": {"type": "string"}, "timeout": {"type": "number"}})
async def play_start(a):
    st = await STUDIO.call("solo_playtest", {"action": "status"}, 30)
    running = "running" in json.dumps(st.structured_content or {}).lower() and "client" in json.dumps(st.structured_content or {})
    if not running:
        await STUDIO.call("solo_playtest", {"action": "start", "mode": "play"}, 120)
    deadline = time.time() + float(a.get("timeout", 60))
    while time.time() < deadline:
        try:
            ok = await STUDIO.luau('local lp = game:GetService("Players").LocalPlayer '
                                   'return lp ~= nil and lp.Character ~= nil and lp.Character:FindFirstChild("HumanoidRootPart") ~= nil',
                                   "client", 15)
            if ok is True:
                break
        except ForgeError:
            pass
        await asyncio.sleep(1)
    else:
        raise ForgeError("client never got a character")
    if winctl:
        await _focus()
    clicked = None
    phrase = a.get("click_text", "play")
    if phrase:
        from .ui_tools import ui_click_text
        for _ in range(12):
            try:
                r = await ui_click_text({"pattern": phrase})
                clicked = r[0].text
                break
            except ForgeError:
                await asyncio.sleep(1)
    await asyncio.sleep(2)
    s = await state(peer="client")
    return [text({"clicked": clicked, "state": s})]


@tool("play_stop", "Stop the running playtest.", {})
async def play_stop(a):
    r = await STUDIO.call("solo_playtest", {"action": "stop"}, 60)
    return [text(r.structured_content or "stopped")]


@tool("play_state", "What the player is doing and what they can reach: position, speed, health, camera yaw/pitch, "
      "mouse mode, what the crosshair is on, nearby doors / slits / card rooms / prompts / loot / grabbables, and the "
      "player's and character's attributes.",
      {"radius": {"type": "number"}, "tags": {"type": "array", "items": {"type": "string"}},
       "attrs": {"type": "array", "items": {"type": "string"}, "description": "attribute names to report (default: non-empty ones)"},
       "peer": PEER}, read_only=True)
async def play_state(a):
    extra = {k: a[k] for k in ("radius", "tags", "attrs") if k in a}
    return [text(await state(peer=a.get("peer", "client"), **extra))]


@tool("play_see", "One call to see the game as the player does: a screenshot plus play_state.", {"peer": PEER},
      read_only=True)
async def play_see(a):
    s = await state(peer=a.get("peer", "client"))
    shot = await STUDIO.screenshot()
    return [text(s), image(shot, "image/jpeg")]


@tool("play_keys", "Press keys like a player: a list of steps run in order. Steps: {hold: ['W','LeftShift'], for: 2.0} "
      "| {tap: 'E'} | {tap: 'Space', times: 2} | {wait: 0.5} | {text: 'hello'}. KeyCode names (W, A, S, D, Space, "
      "LeftShift, LeftControl, E, F, Q, One..Nine, Return, Tab). Focuses Studio first. Max 60 s in total.",
      {"steps": {"type": "array", "items": {"type": "object"}}, "focus": {"type": "boolean", "description": "default true"}},
      ["steps"])
async def play_keys(a):
    if a.get("focus", True) and winctl:
        await _focus()
    total, log = 0.0, []
    for st in a["steps"]:
        if total > 60:
            raise ForgeError("more than 60 s of input in one call -- split it")
        if "hold" in st:
            ks = st["hold"] if isinstance(st["hold"], list) else [st["hold"]]
            dur = min(float(st.get("for", 0.5)), 30)
            rel = await keys(ks, list(reversed(ks)))
            try:
                await asyncio.sleep(dur)
            finally:
                await rel()
            total += dur
            log.append(f"held {'+'.join(ks)} {dur}s")
        elif "tap" in st:
            for _ in range(int(st.get("times", 1))):
                await STUDIO.call("simulate_keyboard_input", {"keyCode": st["tap"], "action": "press"}, 15)
                await asyncio.sleep(float(st.get("hold_for", 0.08)))
                await STUDIO.call("simulate_keyboard_input", {"keyCode": st["tap"], "action": "release"}, 15)
                await asyncio.sleep(0.08)
            log.append(f"tapped {st['tap']} x{st.get('times', 1)}")
        elif "wait" in st:
            d = min(float(st["wait"]), 20)
            await asyncio.sleep(d)
            total += d
            log.append(f"waited {d}s")
        elif "text" in st:
            await STUDIO.call("simulate_keyboard_input", {"text": str(st["text"])}, 15)
            log.append(f"typed {len(str(st['text']))} chars")
        else:
            raise ForgeError(f"unknown step {st}")
    return [text(log)]


@tool("play_look", "Turn the player's view with the REAL mouse (OS-level, only while Studio is in front). Absolute "
      "yaw/pitch in degrees (yaw 0 = looking -Z, 90 = looking -X), relative dyaw/dpitch, or `at`: a world point or an "
      "instance path to face. Closed-loop: it self-calibrates and stops within ~1.5 deg. drag=true holds the right "
      "button for third-person cameras.",
      {"yaw": {"type": "number"}, "pitch": {"type": "number"}, "dyaw": {"type": "number"}, "dpitch": {"type": "number"},
       "at": {"description": "[x,y,z] or a dotted instance path"}, "drag": {"type": "boolean"}, "peer": PEER})
async def play_look(a):
    await _focus()
    peer = a.get("peer", "client")
    yaw, pitch = a.get("yaw"), a.get("pitch")
    if a.get("at") is not None:
        tgt = await _point_of(a["at"], peer)
        s = await state(True, peer=peer)
        d = [tgt[i] - s["cam"][i] for i in range(3)]
        yaw = math.degrees(math.atan2(-d[0], -d[2]))
        pitch = math.degrees(math.atan2(d[1], math.hypot(d[0], d[2])))
    s = await look(yaw, pitch, a.get("dyaw"), a.get("dpitch"), peer, drag=bool(a.get("drag")))
    return [text({"yaw": round(s["yaw"], 1), "pitch": round(s["pitch"], 1), "calibration_px_per_deg": CAL})]


async def _point_of(at, peer):
    if isinstance(at, list) and len(at) == 3:
        return [float(x) for x in at]
    if not isinstance(at, str):
        raise ForgeError("at: [x,y,z] or an instance path")
    code = """
local path = %s
local cur = game
for name in string.gmatch(path, "[^%%.]+") do
	if not cur then break end
	if not (cur == game and name == "game") then cur = cur:FindFirstChild(name) end
end
if not cur then return {error = "not found: " .. path} end
local p
if cur:IsA("BasePart") then p = cur.Position elseif cur:IsA("Model") then p = cur:GetPivot().Position
elseif cur:IsA("Attachment") then p = cur.WorldPosition end
if not p then return {error = "has no position: " .. path} end
return {p.X, p.Y, p.Z}
""" % long_string(at)
    v = await STUDIO.luau(code, peer, 20)
    if isinstance(v, dict) and v.get("error"):
        raise ForgeError(v["error"])
    return v


@tool("play_goto", "Walk the player to a point (or an instance) with real keys and mouse: faces the clearest heading "
      "toward the target (ray fan), walks/sprints in short legs, jumps or strafes when stuck. Reports the path taken.",
      {"to": {"description": "[x,y,z] or an instance path"}, "tolerance": {"type": "number", "description": "studs, default 4"},
       "sprint": {"type": "boolean"}, "timeout": {"type": "number", "description": "seconds, default 40 (max 120)"},
       "peer": PEER}, ["to"])
async def play_goto(a):
    peer = a.get("peer", "client")
    tgt = await _point_of(a["to"], peer)
    tol = float(a.get("tolerance", 4))
    await _focus()
    deadline = time.time() + min(float(a.get("timeout", 40)), 120)
    trail, stuck, last = [], 0, None
    move_keys = ["W", "LeftShift"] if a.get("sprint") else ["W"]
    while time.time() < deadline:
        s = await state(True, target=tgt, peer=peer)
        if "pos" not in s:
            raise ForgeError("no character")
        trail.append([round(s["pos"][0], 1), round(s["pos"][2], 1)])
        if s.get("dist", 1e9) <= tol:
            return [text({"arrived": True, "dist": round(s["dist"], 1), "legs": len(trail), "trail": trail[-12:]})]
        heading = s.get("steer")
        if heading is None:
            heading = math.degrees(math.atan2(-(tgt[0] - s["pos"][0]), -(tgt[2] - s["pos"][2])))
        if abs(_wrap(heading - s["yaw"])) > 8:
            await look(heading, 0 if abs(s["pitch"]) > 25 else None, peer=peer, tol=4)
        leg = max(0.25, min(1.2, s.get("dist", 10) / (24 if a.get("sprint") else 14)))
        rel = await keys(move_keys, list(reversed(move_keys)))
        try:
            await asyncio.sleep(leg)
        finally:
            await rel()
        if last is not None and math.dist(last, s["pos"]) < 0.6:
            stuck += 1
            fix = [{"tap": "Space"}] if stuck % 2 else [{"hold": "A" if stuck % 4 == 2 else "D", "for": 0.45}]
            await play_keys({"steps": fix, "focus": False})
            if stuck >= 8:
                return [text({"arrived": False, "reason": "stuck", "dist": round(s.get("dist", -1), 1), "trail": trail[-12:]})]
        else:
            stuck = 0
        last = s["pos"]
    s = await state(True, target=tgt, peer=peer)
    return [text({"arrived": False, "reason": "timeout", "dist": round(s.get("dist", -1), 1), "trail": trail[-12:]})]


@tool("play_interact", "Interact like a player: optionally face a target (instance path or point) first, then press the "
      "interact key (E by default).", {"at": {"description": "[x,y,z] or instance path"}, "key": {"type": "string"},
                                        "peer": PEER})
async def play_interact(a):
    peer = a.get("peer", "client")
    await _focus()
    if a.get("at") is not None:
        tgt = await _point_of(a["at"], peer)
        s = await state(True, peer=peer)
        d = [tgt[i] - s["cam"][i] for i in range(3)]
        await look(math.degrees(math.atan2(-d[0], -d[2])), math.degrees(math.atan2(d[1], math.hypot(d[0], d[2]))), peer=peer)
    k = a.get("key", "E")
    await STUDIO.call("simulate_keyboard_input", {"keyCode": k, "action": "press"}, 15)
    await asyncio.sleep(0.12)
    await STUDIO.call("simulate_keyboard_input", {"keyCode": k, "action": "release"}, 15)
    await asyncio.sleep(0.4)
    return [text(await state(peer=peer))]


@tool("studio_filmstrip", "Several screenshots in a row as one contact sheet -- check an animation, a transition, a "
      "flicker or motion. count 2-12, interval seconds (each capture also takes ~0.2-0.5 s).",
      {"count": {"type": "integer"}, "interval": {"type": "number"}}, read_only=True)
async def studio_filmstrip(a):
    n = max(2, min(12, int(a.get("count", 6))))
    iv = max(0.0, float(a.get("interval", 0.25)))
    shots, labels, t0 = [], [], time.time()
    for i in range(n):
        shots.append(await STUDIO.screenshot())
        labels.append(f"t+{time.time() - t0:.2f}s")
        if i < n - 1:
            await asyncio.sleep(iv)
    return [image(contact_sheet(shots, labels, cols=min(4, n), width=640), "image/jpeg")]
