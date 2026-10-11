"""Parity: Roblox Open Cloud -- live data stores, messaging, universe ops (restart servers), bans, and place
publishing (EL4CTEO's datastore/universe tools, 6xvl's place_publish).

KEY: an Open Cloud API key from the Creator Dashboard, in FORGE_OPENCLOUD_KEY or ~/.robloxforge/opencloud_key.
Grant it only the scopes you need. Anything that CHANGES a live game (writes, deletes, restarts, bans, publishes)
also needs confirm=true on the call -- these act on real players, not on Studio.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .parity import B, N, O, S
from .server import text, tool
from .studio import ForgeError

API = "https://apis.roblox.com"
KEYFILE = Path.home() / ".robloxforge" / "opencloud_key"


def _key():
    k = os.environ.get("FORGE_OPENCLOUD_KEY") or (KEYFILE.read_text(encoding="utf-8").strip() if KEYFILE.is_file() else "")
    if not k:
        raise ForgeError("no Open Cloud API key: create one at create.roblox.com > Open Cloud > API Keys with the scopes "
                         f"this tool needs, then set FORGE_OPENCLOUD_KEY or write it to {KEYFILE}")
    return k


def _confirm(a, what):
    if a.get("confirm") is not True:
        raise ForgeError(f"{what} changes the LIVE game -- call again with confirm=true")


async def _req(method, url, *, params=None, body=None, raw=None, headers=None):
    h = {"x-api-key": _key()}
    h.update(headers or {})
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    data = raw
    if data is None and body is not None:
        data = json.dumps(body).encode("utf-8")
        h.setdefault("content-type", "application/json")

    def go():
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers or {})

    status, payload, rh = await asyncio.to_thread(go)
    try:
        out = json.loads(payload.decode("utf-8") or "null")
    except (ValueError, UnicodeDecodeError):
        out = payload[:2000].decode("utf-8", "replace")
    if status >= 400:
        raise ForgeError(f"Open Cloud {method} {url.split('?')[0]} -> {status}: {json.dumps(out)[:600]}")
    return {"status": status, "data": out, "headers": {k: v for k, v in rh.items() if k.lower().startswith("roblox-")}}


@tool("opencloud_datastore", "Live standard data stores through Open Cloud: op = list_stores | list_keys | get | set | "
      "delete | increment. set/delete/increment need confirm=true. Scope defaults to 'global'.",
      {"op": {"type": "string", "enum": ["list_stores", "list_keys", "get", "set", "delete", "increment"]},
       "universeId": N, "datastore": S, "key": S, "value": {"description": "JSON value for set"}, "incrementBy": N,
       "scope": S, "prefix": S, "limit": N, "cursor": S, "confirm": B}, ["op", "universeId"])
async def opencloud_datastore(a):
    u = int(a["universeId"])
    base = f"{API}/datastores/v1/universes/{u}/standard-datastores"
    op, scope = a["op"], a.get("scope", "global")
    if op == "list_stores":
        p = {"limit": int(a.get("limit", 50))}
        if a.get("prefix"):
            p["prefix"] = a["prefix"]
        if a.get("cursor"):
            p["cursor"] = a["cursor"]
        return [text(await _req("GET", base, params=p))]
    if not a.get("datastore"):
        raise ForgeError("datastore is required")
    p = {"datastoreName": a["datastore"], "scope": scope}
    if op == "list_keys":
        p["limit"] = int(a.get("limit", 50))
        if a.get("prefix"):
            p["prefix"] = a["prefix"]
        if a.get("cursor"):
            p["cursor"] = a["cursor"]
        return [text(await _req("GET", f"{base}/datastore/entries", params=p))]
    if not a.get("key"):
        raise ForgeError("key is required")
    p["entryKey"] = a["key"]
    if op == "get":
        return [text(await _req("GET", f"{base}/datastore/entries/entry", params=p))]
    if op == "set":
        _confirm(a, "writing a live data store entry")
        raw = json.dumps(a.get("value")).encode("utf-8")
        md5 = base64.b64encode(hashlib.md5(raw).digest()).decode()
        return [text(await _req("POST", f"{base}/datastore/entries/entry", params=p, raw=raw,
                                headers={"content-type": "application/json", "content-md5": md5}))]
    if op == "delete":
        _confirm(a, "deleting a live data store entry")
        return [text(await _req("DELETE", f"{base}/datastore/entries/entry", params=p))]
    if op == "increment":
        _confirm(a, "incrementing a live data store entry")
        p["incrementBy"] = float(a.get("incrementBy", 1))
        return [text(await _req("POST", f"{base}/datastore/entries/entry/increment", params=p))]
    raise ForgeError(f"unknown op {op}")


@tool("opencloud_message", "Publish a MessagingService message to every live server of a universe (needs confirm=true).",
      {"universeId": N, "topic": S, "message": S, "confirm": B}, ["universeId", "topic", "message"])
async def opencloud_message(a):
    _confirm(a, "messaging live servers")
    return [text(await _req("POST", f"{API}/messaging-service/v1/universes/{int(a['universeId'])}/topics/{a['topic']}",
                            body={"message": a["message"]}))]


@tool("opencloud_universe", "Universe info and operations through Open Cloud: op = get | restart_servers "
      "(shuts every live server down so players rejoin the latest version; needs confirm=true).",
      {"op": {"type": "string", "enum": ["get", "restart_servers"]}, "universeId": N, "confirm": B}, ["op", "universeId"])
async def opencloud_universe(a):
    u = int(a["universeId"])
    if a["op"] == "get":
        return [text(await _req("GET", f"{API}/cloud/v2/universes/{u}"))]
    _confirm(a, "restarting every live server")
    return [text(await _req("POST", f"{API}/cloud/v2/universes/{u}:restartServers", body={}))]


@tool("opencloud_bans", "Experience bans through Open Cloud user restrictions: op = list | get | ban | unban. "
      "ban/unban need confirm=true. duration in seconds (omit for permanent).",
      {"op": {"type": "string", "enum": ["list", "get", "ban", "unban"]}, "universeId": N, "userId": N,
       "duration": N, "displayReason": S, "privateReason": S, "excludeAltAccounts": B, "confirm": B}, ["op", "universeId"])
async def opencloud_bans(a):
    u = int(a["universeId"])
    base = f"{API}/cloud/v2/universes/{u}/user-restrictions"
    if a["op"] == "list":
        return [text(await _req("GET", base, params={"maxPageSize": 100}))]
    if not a.get("userId"):
        raise ForgeError("userId is required")
    url = f"{base}/{int(a['userId'])}"
    if a["op"] == "get":
        return [text(await _req("GET", url))]
    _confirm(a, "changing a player's ban")
    active = a["op"] == "ban"
    gr = {"active": active}
    if active:
        if a.get("duration"):
            gr["duration"] = f"{int(a['duration'])}s"
        gr["displayReason"] = a.get("displayReason", "")
        gr["privateReason"] = a.get("privateReason", "")
        gr["excludeAltAccounts"] = bool(a.get("excludeAltAccounts", False))
    return [text(await _req("PATCH", url, params={"updateMask": "gameJoinRestriction"}, body={"gameJoinRestriction": gr}))]


@tool("place_publish", "Publish (or save) a place file to Roblox through Open Cloud: file = a saved .rbxl or .rbxlx. "
      "versionType Published makes it live; Saved only stores a version. Needs confirm=true.",
      {"universeId": N, "placeId": N, "file": S, "versionType": {"type": "string", "enum": ["Saved", "Published"]},
       "confirm": B}, ["universeId", "placeId", "file"], destructive=True)
async def place_publish(a):
    f = Path(a["file"])
    if not f.is_file() or f.suffix.lower() not in (".rbxl", ".rbxlx"):
        raise ForgeError("file must be an existing .rbxl or .rbxlx")
    vt = a.get("versionType", "Saved")
    if vt == "Published":
        _confirm(a, "publishing a new live version")
    ctype = "application/xml" if f.suffix.lower() == ".rbxlx" else "application/octet-stream"
    return [text(await _req("POST", f"{API}/universes/v1/{int(a['universeId'])}/places/{int(a['placeId'])}/versions",
                            params={"versionType": vt}, raw=f.read_bytes(), headers={"content-type": ctype}))]
