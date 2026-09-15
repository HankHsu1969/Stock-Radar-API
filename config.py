# -*- coding: utf-8 -*-
"""全域設定：預設觀察清單、快取時間、評分權重。"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WATCHLIST_FILE = os.path.join(BASE_DIR, "watchlist.json")

# 預設 20 支台股熱門標的（權值股 + 高人氣族群）
DEFAULT_WATCHLIST = [
    {"code": "2330", "name": "台積電",   "market": "TWSE"},
    {"code": "2317", "name": "鴻海",     "market": "TWSE"},
    {"code": "2454", "name": "聯發科",   "market": "TWSE"},
    {"code": "2308", "name": "台達電",   "market": "TWSE"},
    {"code": "2382", "name": "廣達",     "market": "TWSE"},
    {"code": "3231", "name": "緯創",     "market": "TWSE"},
    {"code": "2357", "name": "華碩",     "market": "TWSE"},
    {"code": "2379", "name": "瑞昱",     "market": "TWSE"},
    {"code": "3034", "name": "聯詠",     "market": "TWSE"},
    {"code": "3008", "name": "大立光",   "market": "TWSE"},
    {"code": "2412", "name": "中華電",   "market": "TWSE"},
    {"code": "2881", "name": "富邦金",   "market": "TWSE"},
    {"code": "2882", "name": "國泰金",   "market": "TWSE"},
    {"code": "2891", "name": "中信金",   "market": "TWSE"},
    {"code": "2886", "name": "兆豐金",   "market": "TWSE"},
    {"code": "1301", "name": "台塑",     "market": "TWSE"},
    {"code": "1303", "name": "南亞",     "market": "TWSE"},
    {"code": "2002", "name": "中鋼",     "market": "TWSE"},
    {"code": "2603", "name": "長榮",     "market": "TWSE"},
    {"code": "1216", "name": "統一",     "market": "TWSE"},
]

# ---- 快取秒數 ----
CACHE_TTL_HISTORY = 15 * 60      # K 線歷史資料
CACHE_TTL_INFO = 60 * 60         # 基本面資料（PE/PB/殖利率）
CACHE_TTL_NAMEMAP = 12 * 60 * 60  # 全市場代碼→名稱對照表

# ---- 評分權重（總分 100）----
WEIGHTS = {
    "trend": 30,      # 趨勢結構
    "momentum": 25,   # 動能
    "volume": 15,     # 量能
    "risk": 15,       # 風險控制（波動 / 回撤，分數越高代表風險越低）
    "value": 15,      # 價值面
}

# 評等分級門檻
GRADE_BANDS = [
    (82, "A+", "極強"),
    (74, "A",  "強勢"),
    (66, "B+", "偏多"),
    (58, "B",  "中性偏多"),
    (50, "C+", "中性"),
    (42, "C",  "偏弱"),
    (0,  "D",  "弱勢"),
]

MAX_WORKERS = 6
