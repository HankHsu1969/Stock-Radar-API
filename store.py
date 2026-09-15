# -*- coding: utf-8 -*-
"""觀察清單持久化（watchlist.json）。"""

import json
import os
import threading

from config import DEFAULT_WATCHLIST, WATCHLIST_FILE

_lock = threading.Lock()


def load():
    with _lock:
        if not os.path.exists(WATCHLIST_FILE):
            _write(DEFAULT_WATCHLIST)
            return [dict(x) for x in DEFAULT_WATCHLIST]
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list) and data:
                return data
        except Exception as exc:
            print("[warn] watchlist.json 讀取失敗，改用預設清單:", exc)
        return [dict(x) for x in DEFAULT_WATCHLIST]


def _write(items):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


def save(items):
    with _lock:
        _write(items)


def add(stock):
    items = load()
    if any(x["code"] == stock["code"] for x in items):
        return items, False
    items.append(stock)
    save(items)
    return items, True


def remove(code):
    items = load()
    remaining = [x for x in items if x["code"] != str(code)]
    changed = len(remaining) != len(items)
    if changed:
        save(remaining)
    return remaining, changed


def reset():
    items = [dict(x) for x in DEFAULT_WATCHLIST]
    save(items)
    return items
