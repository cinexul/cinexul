#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号抓取 · cinexul/cinexul
==========================
在 GitHub Actions 里运行,把公开数据冲洗进 profile/live.json:
账号年龄 / 公开仓库 / star 合计 / 语言字节占比 / 近期 push。

铁律:README 是公开页面,这里只允许出现"本来就公开"的信息。
/users/{login}/repos 端点无论带不带 token 都只返回公开仓库,
私有仓库的名字、提交信息永远不会进入渲染数据。

任何一步失败都保留 live.json 里的旧值(宁可数据旧,不可页面裂)。
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "profile" / "live.json"
CFG = json.loads((ROOT / "profile" / "config.json").read_text("utf-8"))
LOGIN = CFG["login"]

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
CTX = ssl.create_default_context()


def get(url: str, accept: str = "application/vnd.github+json", timeout: int = 20):
    req = urllib.request.Request(url, headers={
        "Accept": accept,
        "User-Agent": f"{LOGIN}-profile-darkroom",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN and url.startswith(API) else {}),
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()


def get_json(url: str):
    return json.loads(get(url))


def main() -> None:
    live = json.loads(LIVE.read_text("utf-8"))
    now = datetime.now(timezone.utc)
    live["develop_no"] = int(live.get("develop_no", 0)) + 1
    live["develop_ts"] = now.strftime("%Y-%m-%d %H:%M UTC")
    live["develop_date"] = now.strftime("%Y-%m-%d")

    # ── 账号 ──
    try:
        u = get_json(f"{API}/users/{LOGIN}")
        created = datetime.fromisoformat(u["created_at"].replace("Z", "+00:00"))
        live["est_year"] = str(created.year)
        live["days_in_darkroom"] = max((now - created).days, 1)
        live["followers"] = u.get("followers", live.get("followers", 0))
        live["public_repos"] = u.get("public_repos", live.get("public_repos", 0))
    except Exception as e:
        print(f"[warn] user: {e}")

    # ── 公开仓库:star 与语言 ──
    try:
        repos = get_json(f"{API}/users/{LOGIN}/repos?per_page=100&type=owner")
        repos = [r for r in repos if not r.get("fork")]
        live["stars_total"] = sum(r.get("stargazers_count", 0) for r in repos)
        agg: dict[str, int] = {}
        for r in repos:
            try:
                for lang, n in get_json(f"{API}/repos/{LOGIN}/{r['name']}/languages").items():
                    agg[lang] = agg.get(lang, 0) + n
            except Exception as e:
                print(f"[warn] languages {r['name']}: {e}")
        if agg:
            live["languages"] = [{"name": k, "bytes": v} for k, v in
                                 sorted(agg.items(), key=lambda kv: -kv[1])[:6]]
            live["languages_source"] = "github linguist"
    except Exception as e:
        print(f"[warn] repos: {e}")

    # ── 近期 push(公开事件流,只作计数) ──
    try:
        events = get_json(f"{API}/users/{LOGIN}/events/public?per_page=100")
        live["pushes_recent"] = sum(1 for ev in events if ev.get("type") == "PushEvent") or \
            live.get("pushes_recent", 0)
    except Exception as e:
        print(f"[warn] events: {e}")

    LIVE.write_text(json.dumps(live, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"develop №{live['develop_no']} · langs={len(live.get('languages', []))} "
          f"· days={live.get('days_in_darkroom')}")


if __name__ == "__main__":
    main()
