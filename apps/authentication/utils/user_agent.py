"""Parse user agent strings for session display."""

from __future__ import annotations

import re


def parse_user_agent(user_agent: str) -> dict[str, str]:
    ua = (user_agent or "")[:500]
    browser = _detect_browser(ua)
    os_name = _detect_os(ua)
    device = "Mobile" if _is_mobile(ua) else "Desktop"
    label = f"{browser} on {os_name}"
    if device == "Mobile":
        label = f"{browser} · {os_name} · Mobile"
    return {
        "browser": browser,
        "os_name": os_name,
        "device_label": label,
    }


def _is_mobile(ua: str) -> bool:
    return bool(re.search(r"Mobile|Android|iPhone|iPad", ua, re.I))


def _detect_browser(ua: str) -> str:
    if "Edg/" in ua or "Edge/" in ua:
        return "Microsoft Edge"
    if "Chrome/" in ua and "Chromium" not in ua:
        return "Chrome"
    if "Firefox/" in ua:
        return "Firefox"
    if "Safari/" in ua and "Chrome" not in ua:
        return "Safari"
    if "OPR/" in ua or "Opera" in ua:
        return "Opera"
    return "Unknown Browser"


def _detect_os(ua: str) -> str:
    if "Windows NT" in ua:
        return "Windows"
    if "Mac OS X" in ua or "Macintosh" in ua:
        return "macOS"
    if "Android" in ua:
        return "Android"
    if "iPhone" in ua or "iPad" in ua:
        return "iOS"
    if "Linux" in ua:
        return "Linux"
    return "Unknown OS"
