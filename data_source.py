# -*- coding: utf-8 -*-
"""台股真實資料來源。

- 歷史 K 線 / 基本面：Yahoo Finance（yfinance），代碼加上 .TW（上市）或 .TWO（上櫃）
- 中文名稱與全市場清單：證交所 TWSE OpenAPI + 櫃買中心 TPEx OpenAPI
所有資料皆為真實市場資料，並加上記憶體 TTL 快取避免重複請求。
"""

import threading
import time

import pandas as pd
import requests
import yfinance as yf

from config import CACHE_TTL_HISTORY, CACHE_TTL_INFO, CACHE_TTL_NAMEMAP, DEFAULT_WATCHLIST

TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"

_cache = {}
_cache_lock = threading.Lock()


def _cache_get(key):
    with _cache_lock:
        item = _cache.get(key)
        if item and time.time() < item[0]:
            return item[1]
    return None


def _cache_set(key, value, ttl):
    with _cache_lock:
        _cache[key] = (time.time() + ttl, value)


def clear_cache(prefix=None):
    """清除快取（refresh 用）。prefix 為 None 時全清。"""
    with _cache_lock:
        if prefix is None:
            _cache.clear()
        else:
            for k in [k for k in _cache if k.startswith(prefix)]:
                _cache.pop(k, None)


# ---------------------------------------------------------------- 名稱對照表
def _fetch_json(url, timeout=25):
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.json()


def get_name_map():
    """回傳 {代碼: {'name': 中文名, 'market': 'TWSE'|'TPEX'}}，涵蓋上市 + 上櫃。"""
    cached = _cache_get("namemap")
    if cached:
        return cached

    mapping = {}
    try:
        for row in _fetch_json(TWSE_URL):
            code = str(row.get("Code", "")).strip()
            name = str(row.get("Name", "")).strip()
            if code and name:
                mapping[code] = {"name": name, "market": "TWSE"}
    except Exception as exc:  # 網路失敗時不阻斷主流程
        print("[warn] TWSE 名稱表取得失敗:", exc)

    try:
        for row in _fetch_json(TPEX_URL):
            code = str(row.get("SecuritiesCompanyCode") or row.get("Code") or "").strip()
            name = str(row.get("CompanyName") or row.get("Name") or "").strip()
            if code and name and code not in mapping:
                mapping[code] = {"name": name, "market": "TPEX"}
    except Exception as exc:
        print("[warn] TPEx 名稱表取得失敗:", exc)

    # 至少保底涵蓋預設清單
    for item in DEFAULT_WATCHLIST:
        mapping.setdefault(item["code"], {"name": item["name"], "market": item["market"]})

    if mapping:
        _cache_set("namemap", mapping, CACHE_TTL_NAMEMAP)
    return mapping


def resolve_stock(code):
    """由代碼解析出名稱與市場別；查不到回傳 None。"""
    code = str(code).strip().upper()
    info = get_name_map().get(code)
    if info:
        return {"code": code, "name": info["name"], "market": info["market"]}
    return None


def is_listed_symbol(code):
    """排除權證、牛熊證等衍生商品，只留個股、ETF 與特別股。"""
    code = str(code)
    if code.startswith("00"):          # ETF，例如 0050 / 00878 / 00400A
        return True
    if len(code) == 4 and code.isdigit():   # 一般個股
        return True
    if len(code) == 5 and code[:4].isdigit() and code[4].isalpha():  # 特別股，例如 2891B
        return True
    return False


def search_stocks(query, limit=15):
    """依代碼或名稱關鍵字搜尋全市場標的（不含權證）。"""
    query = str(query).strip()
    if not query:
        return []
    results = []
    for code, info in get_name_map().items():
        if not is_listed_symbol(code):
            continue
        if query in code or query in info["name"]:
            results.append({"code": code, "name": info["name"], "market": info["market"]})
    results.sort(key=lambda r: (not r["code"].startswith(query), len(r["code"]), r["code"]))
    return results[:limit]


# ---------------------------------------------------------------- 行情資料
def to_ticker(code, market="TWSE"):
    return "{}.{}".format(code, "TWO" if market == "TPEX" else "TW")


def get_history(code, market="TWSE", period="2y"):
    """取得日 K 歷史資料，回傳 DataFrame(Open/High/Low/Close/Volume)。"""
    key = "hist:{}:{}:{}".format(code, market, period)
    cached = _cache_get(key)
    if cached is not None:
        return cached.copy()

    ticker = to_ticker(code, market)
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)

    # 上市查無資料時自動改試上櫃，反之亦然
    if (df is None or df.empty) and market == "TWSE":
        df = yf.Ticker(to_ticker(code, "TPEX")).history(period=period, auto_adjust=False)
    elif (df is None or df.empty) and market == "TPEX":
        df = yf.Ticker(to_ticker(code, "TWSE")).history(period=period, auto_adjust=False)

    if df is None or df.empty:
        return pd.DataFrame()

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df = df[df["Close"] > 0]
    _cache_set(key, df, CACHE_TTL_HISTORY)
    return df.copy()


def get_fundamentals(code, market="TWSE"):
    """取得基本面資料（本益比、股價淨值比、殖利率、市值等）。"""
    key = "info:{}:{}".format(code, market)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    data = {}
    try:
        info = yf.Ticker(to_ticker(code, market)).info or {}
        div = info.get("dividendYield")
        # yfinance 有時回傳 0.0289（比例）、有時回傳 2.89（百分比），統一成百分比
        if div is not None and div < 1:
            div = div * 100
        data = {
            "long_name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb": info.get("priceToBook"),
            "dividend_yield": div,
            "roe": info.get("returnOnEquity"),
            "profit_margin": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "beta": info.get("beta"),
            "week52_high": info.get("fiftyTwoWeekHigh"),
            "week52_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception as exc:
        print("[warn] 基本面取得失敗 {}: {}".format(code, exc))

    _cache_set(key, data, CACHE_TTL_INFO)
    return data
