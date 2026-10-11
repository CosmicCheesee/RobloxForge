"""Spec -> standalone Luau. The output does not depend on RobloxForge: a `make` helper, a build()
function, and (fx=True) a small runtime that animates every ForgeFx-tagged control:

  button/item/tab  hover lift, press squish, release -- fast in, slow out
  toggle           knob slides, track recolours, ForgeOn flips, onToggle(handler)
  slider           drag along the track, ForgeValue updates, onSlide(handler)
  input            focus ring in the accent colour
  tab              selecting one deselects its siblings
  dismiss          ForgeRole="dismiss" closes the gui
  open/close       the whole gui fades + scales through a CanvasGroup (the HudRest method):
                   0.12 s in, 0.32 s out -- the Backroom rule "fast in, slow out, never blink"
  keep_enabled     re-asserts ScreenGui.Enabled on Heartbeat while open (HANDOFF: Enabled has
                   several owners in the Backroom place) and sets HubKeep
"""
from __future__ import annotations

from .schema import hex_rgb


def _n(x):
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int) or (isinstance(x, float) and x.is_integer()):
        return str(int(x))
    return f"{x:.4f}".rstrip("0").rstrip(".")


def _s(text):
    out = ['"']
    for ch in str(text):
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 32:
            out.append(f"\\{ord(ch)}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _rgb(c):
    return f"Color3.fromRGB({c[0]}, {c[1]}, {c[2]})"


def literal(p):
    t = p[1]
    if t == "udim2":
        v = p[2]
        return f"UDim2.new({_n(v[0])}, {_n(v[1])}, {_n(v[2])}, {_n(v[3])})"
    if t == "udim":
        return f"UDim.new({_n(p[2][0])}, {_n(p[2][1])})"
    if t == "vec2":
        return f"Vector2.new({_n(p[2][0])}, {_n(p[2][1])})"
    if t == "color":
        return _rgb(p[2])
    if t in ("num", "bool"):
        return _n(p[2])
    if t == "str":
        return _s(p[2])
    if t == "enum":
        return f"Enum.{p[2]}.{p[3]}"
    if t == "font":
        return f'Font.new("rbxasset://fonts/families/{p[2]}.json", Enum.FontWeight.{p[3]}, Enum.FontStyle.{p[4]})'
    if t == "cseq":
        ks = ", ".join(f"ColorSequenceKeypoint.new({_n(k[0])}, {_rgb(k[1])})" for k in p[2])
        return f"ColorSequence.new({{{ks}}})"
    if t == "nseq":
        ks = ", ".join(f"NumberSequenceKeypoint.new({_n(k[0])}, {_n(k[1])})" for k in p[2])
        return f"NumberSequence.new({{{ks}}})"
    raise ValueError(t)


def _node(n, ind, wrap_root=False):
    pad = "\t" * ind
    props = [f"Name = {_s(n['name'])}"] + [f"{p[0]} = {literal(p)}" for p in n["props"]]
    attrs = n.get("attrs") or {}
    a = ("{" + ", ".join(f"{k} = {_n(v) if not isinstance(v, str) else _s(v)}" for k, v in attrs.items()) + "}") if attrs else "nil"
    kids = n["children"]
    if wrap_root and n["type"] == "ScreenGui":
        # every child of the gui goes inside one CanvasGroup so open/close can fade it in one pass
        kids = [{"type": "CanvasGroup", "name": "ForgeRoot", "attrs": {},
                 "props": [["Size", "udim2", [1, 0, 1, 0]], ["BackgroundTransparency", "num", 1],
                           ["BorderSizePixel", "num", 0]], "children": kids}]
    head = f'make("{n["type"]}", {{{", ".join(props)}}}, {a}'
    if not kids:
        return pad + head + ", {})"
    inner = ",\n".join(_node(k, ind + 1) for k in kids)
    return f"{pad}{head}, {{\n{inner},\n{pad}}})"


RUNTIME = r'''
-- ===== RUNTIME: hover / press / focus / toggle / slider / tabs / open / close =====
-- Tagged by attribute (ForgeFx, ForgeRole), so hand-made controls opt in the same way.
local FAST = TweenInfo.new(0.10, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local SLOW = TweenInfo.new(0.28, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local OPEN = TweenInfo.new(0.12, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local CLOSE = TweenInfo.new(0.32, Enum.EasingStyle.Quad, Enum.EasingDirection.In)

local function tween(o, info, goal)
	local t = TweenService:Create(o, info, goal)
	t:Play()
	return t
end

local function scaleOf(o)
	local s = o:FindFirstChild("ForgeScale")
	if not s then
		s = Instance.new("UIScale")
		s.Name = "ForgeScale"
		s.Parent = o
	end
	return s
end

local function hoverable(o)
	local base, baseT = o.BackgroundColor3, o.BackgroundTransparency
	local s = scaleOf(o)
	local over = false
	local function rest()
		local selected = o:GetAttribute("ForgeSelected")
		if selected then return end
		tween(o, SLOW, {BackgroundColor3 = base, BackgroundTransparency = baseT})
	end
	o.MouseEnter:Connect(function()
		over = true
		if o:GetAttribute("ForgeSelected") then return end
		if baseT >= 0.99 then
			tween(o, FAST, {BackgroundColor3 = THEME.surface2, BackgroundTransparency = 0.35})
		else
			tween(o, FAST, {BackgroundColor3 = base:Lerp(Color3.new(1, 1, 1), 0.08)})
		end
	end)
	o.MouseLeave:Connect(function()
		over = false
		rest()
		tween(s, SLOW, {Scale = 1})
	end)
	o.MouseButton1Down:Connect(function() tween(s, FAST, {Scale = 0.97}) end)
	o.MouseButton1Up:Connect(function()
		tween(s, SLOW, {Scale = 1})
		if not over then rest() end
	end)
end

local function setTab(tab)
	local par = tab.Parent
	if not par then return end
	for _, t in ipairs(par:GetChildren()) do
		if t:GetAttribute("ForgeFx") == "tab" then
			local on = t == tab
			t:SetAttribute("ForgeSelected", on)
			local pill = t:GetAttribute("ForgeTabStyle") ~= "underline"
			tween(t, FAST, {TextColor3 = on and THEME.text or THEME.muted,
				BackgroundColor3 = THEME.raised, BackgroundTransparency = (on and pill) and 0 or 1})
			local u = t:FindFirstChild("Underline")
			if u then u.Visible = on end
		end
	end
end

local function toggle(track, handlers)
	local rail = track:FindFirstChild("Rail") or track
	local knob = rail:FindFirstChild("Knob")
	local strokeObj = rail:FindFirstChildOfClass("UIStroke")
	track.Activated:Connect(function()
		local on = not track:GetAttribute("ForgeOn")
		track:SetAttribute("ForgeOn", on)
		tween(rail, FAST, {BackgroundColor3 = on and THEME.accent or THEME.surface2})
		if knob then
			local w = knob.Size.X.Offset
			tween(knob, FAST, {Position = on and UDim2.new(1, -(w + 3), 0.5, 0) or UDim2.new(0, 3, 0.5, 0),
				BackgroundColor3 = on and Color3.new(1, 1, 1) or THEME.muted})
		end
		if strokeObj then
			strokeObj.Enabled = not on
		elseif not on then
			local st = Instance.new("UIStroke")
			st.Color = THEME.border
			st.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
			st.Parent = rail
			strokeObj = st
		end
		if handlers.onToggle then handlers.onToggle(track, on) end
	end)
end

local function slider(o, handlers)
	local track = o:FindFirstChild("Track")
	local fill = track and track:FindFirstChild("Fill")
	local knob = o:FindFirstChild("Knob")
	local label = o.Parent and o.Parent:FindFirstChild("Value", true)
	if not (track and fill and knob) then return end
	local dragging = false
	local function setFrom(x)
		local p, w = track.AbsolutePosition.X, track.AbsoluteSize.X
		if w <= 0 then return end
		local v = math.clamp((x - p) / w, 0, 1)
		o:SetAttribute("ForgeValue", v)
		fill.Size = UDim2.new(v, 0, 1, 0)
		knob.Position = UDim2.new(v, 0, 0.5, 0)
		if label and label:IsA("TextLabel") then label.Text = ("%d%%"):format(math.floor(v * 100 + 0.5)) end
		if handlers.onSlide then handlers.onSlide(o, v) end
	end
	o.InputBegan:Connect(function(input)
		if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
			dragging = true
			setFrom(input.Position.X)
			tween(scaleOf(knob), FAST, {Scale = 1.15})
		end
	end)
	UserInputService.InputChanged:Connect(function(input)
		if dragging and (input.UserInputType == Enum.UserInputType.MouseMovement or input.UserInputType == Enum.UserInputType.Touch) then
			setFrom(input.Position.X)
		end
	end)
	UserInputService.InputEnded:Connect(function(input)
		if dragging and (input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch) then
			dragging = false
			tween(scaleOf(knob), SLOW, {Scale = 1})
		end
	end)
end

local function focusRing(box)
	local field = box.Parent
	local ring = field and field:FindFirstChildOfClass("UIStroke")
	if not ring then return end
	local base = ring.Color
	box.Focused:Connect(function() tween(ring, FAST, {Color = THEME.accent}) end)
	box.FocusLost:Connect(function() tween(ring, SLOW, {Color = base}) end)
end

local keepConn = {}
function M.open(gui)
	local root = gui:FindFirstChild("ForgeRoot")
	gui.Enabled = true
	if root and root:IsA("CanvasGroup") then
		root.GroupTransparency = 1
		local s = scaleOf(root)
		s.Scale = 0.97
		tween(root, OPEN, {GroupTransparency = 0})
		tween(s, OPEN, {Scale = 1})
	end
	if KEEP_ENABLED and not keepConn[gui] then
		gui:SetAttribute("HubKeep", true)
		keepConn[gui] = RunService.Heartbeat:Connect(function()
			if not gui.Enabled then gui.Enabled = true end
		end)
	end
end

function M.close(gui)
	if keepConn[gui] then keepConn[gui]:Disconnect(); keepConn[gui] = nil; gui:SetAttribute("HubKeep", nil) end
	local root = gui:FindFirstChild("ForgeRoot")
	if root and root:IsA("CanvasGroup") then
		local t = tween(root, CLOSE, {GroupTransparency = 1})
		tween(scaleOf(root), CLOSE, {Scale = 0.98})
		t.Completed:Connect(function(state)
			if state == Enum.PlaybackState.Completed then gui.Enabled = false end
		end)
	else
		gui.Enabled = false
	end
end

-- handlers: {[controlName] = function(control) end, default = function(control) end,
--            onToggle = function(track, on) end, onSlide = function(slider, value) end}
function M.wire(gui, handlers)
	handlers = handlers or {}
	for _, o in ipairs(gui:GetDescendants()) do
		local fx = o:GetAttribute("ForgeFx")
		if fx == "button" or fx == "item" or fx == "tab" then
			hoverable(o)
			o.Activated:Connect(function()
				if fx == "tab" then setTab(o) end
				local h = handlers[o.Name] or handlers.default
				if h then h(o) end
			end)
		elseif fx == "toggle" then
			toggle(o, handlers)
		elseif fx == "slider" then
			slider(o, handlers)
		elseif fx == "input" then
			focusRing(o)
		end
		if o:GetAttribute("ForgeRole") == "dismiss" and o:IsA("GuiButton") then
			o.Activated:Connect(function() M.close(gui) end)
		end
	end
end
'''


def generate(spec, theme, kind="module", fx=True, keep_enabled=False, source_note=""):
    """spec: normalized tree (root ScreenGui). Returns Luau source."""
    colors = {k: hex_rgb(v) for k, v in theme["color"].items()}
    th = ",\n".join(f"\t{k} = {_rgb(v)}" for k, v in colors.items())
    lines = [
        f"-- Generated by RobloxForge ui_codegen{(' -- ' + source_note) if source_note else ''}.",
        f"-- Theme: {theme.get('name', 'custom')}. Regenerate from the spec, or edit by hand: nothing here depends on RobloxForge.",
        "-- Controls are tagged with ForgeFx / ForgeRole attributes; M.wire(gui, handlers) gives them behaviour.",
        'local TweenService = game:GetService("TweenService")',
        'local UserInputService = game:GetService("UserInputService")',
        'local RunService = game:GetService("RunService")',
        "",
        f"local KEEP_ENABLED = {'true' if keep_enabled else 'false'}",
        "local THEME = {", th, "}",
        "",
        "local M = {}",
        "M.THEME = THEME",
        "",
        "local function make(class, props, attrs, children)",
        "\tlocal o = Instance.new(class)",
        "\tfor k, v in pairs(props) do",
        "\t\to[k] = v",
        "\tend",
        "\tif attrs then",
        "\t\tfor k, v in pairs(attrs) do",
        "\t\t\to:SetAttribute(k, v)",
        "\t\tend",
        "\tend",
        "\tfor _, c in ipairs(children) do",
        "\t\tc.Parent = o",
        "\tend",
        "\treturn o",
        "end",
        "",
        "function M.build()",
        "\treturn " + _node(spec, 1, wrap_root=fx).lstrip("\t"),
        "end",
    ]
    if fx:
        lines.append(RUNTIME)
    else:
        lines += ["function M.open(gui) gui.Enabled = true end", "function M.close(gui) gui.Enabled = false end",
                  "function M.wire() end"]
    if kind == "localscript":
        lines += ["",
                  "-- ===== MOUNT =====",
                  'local Players = game:GetService("Players")',
                  "local gui = M.build()",
                  "gui.Enabled = false",
                  "M.wire(gui, {",
                  "\tdefault = function(control) print(\"[ui] \" .. control.Name) end,",
                  "})",
                  'gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")',
                  "M.open(gui)"]
    else:
        lines += ["", "return M"]
    return "\n".join(lines) + "\n"
