# -*- coding: utf-8 -*-
"""台股智慧篩選雷達 — Flask WebUI 主程式。

啟動：python app.py  →  http://127.0.0.1:5000
資料來源：Yahoo Finance（K 線 / 基本面）、TWSE & TPEx OpenAPI（中文名稱與全市場清單）
"""

import os
import traceback
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from threading import Timer

from flask import Flask, jsonify, render_template, request

import data_source as ds
import indicators as ind
import rating
import store
from config import MAX_WORKERS

app = Flask(__name__)
app.json.ensure_ascii = False


# ---------------------------------------------------------------- 核心運算
def analyze_stock(stock, period="1y"):
    """抓取單一標的的真實資料並完成評分。"""
    code, market = stock["code"], stock.get("market", "TWSE")
    result = {
        "code": code,
        "name": stock.get("name", code),
        "market": market,
        "ok": False,
        "error": None,
    }
    try:
        df = ds.get_history(code, market, period="2y")
        if df.empty:
            result["error"] = "查無歷史行情資料"
            return result

        df_ind = ind.compute_all(df)
        snap = ind.snapshot(df_ind)
        fundamentals = ds.get_fundamentals(code, market)
        score = rating.evaluate(snap, fundamentals)

        result.update({
            "ok": True,
            "quote": snap,
            "fundamentals": fundamentals,
            "rating": score,
        })
    except Exception as exc:
        result["error"] = str(exc)
        traceback.print_exc()
    return result


def analyze_many(stocks):
    """多執行緒並行抓取，並依總分由高到低排序。"""
    if not stocks:
        return []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(analyze_stock, stocks))

    ok_items = [r for r in results if r["ok"]]
    bad_items = [r for r in results if not r["ok"]]
    ok_items.sort(key=lambda r: r["rating"]["total"], reverse=True)
    for i, item in enumerate(ok_items, 1):
        item["rank"] = i
    for item in bad_items:
        item["rank"] = None
    return ok_items + bad_items


# ---------------------------------------------------------------- 頁面
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/stock/<code>")
def stock_detail(code):
    stock = ds.resolve_stock(code) or {"code": code, "name": code, "market": "TWSE"}
    return render_template("detail.html", stock=stock)


# ---------------------------------------------------------------- API
@app.route("/api/watchlist", methods=["GET"])
def api_watchlist():
    if request.args.get("refresh") == "1":
        ds.clear_cache("hist:")
        ds.clear_cache("info:")
    items = store.load()
    return jsonify({"ok": True, "count": len(items), "stocks": analyze_many(items)})


@app.route("/api/watchlist", methods=["POST"])
def api_watchlist_add():
    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip().upper()
    if not code:
        return jsonify({"ok": False, "error": "請輸入股票代碼"}), 400

    stock = ds.resolve_stock(code)
    if not stock:
        # 名稱表可能尚未涵蓋（如興櫃），直接以 Yahoo 驗證是否有行情
        if ds.get_history(code, "TWSE", period="1mo").empty:
            return jsonify({"ok": False, "error": "查無此股票代碼：{}".format(code)}), 404
        stock = {"code": code, "name": code, "market": "TWSE"}

    items, added = store.add(stock)
    if not added:
        return jsonify({"ok": False, "error": "{} {} 已在觀察清單中".format(stock["code"], stock["name"])}), 409
    return jsonify({"ok": True, "added": stock, "count": len(items)})


@app.route("/api/watchlist/<code>", methods=["DELETE"])
def api_watchlist_remove(code):
    items, changed = store.remove(code)
    if not changed:
        return jsonify({"ok": False, "error": "清單中沒有 {}".format(code)}), 404
    return jsonify({"ok": True, "count": len(items)})


@app.route("/api/watchlist/reset", methods=["POST"])
def api_watchlist_reset():
    items = store.reset()
    return jsonify({"ok": True, "count": len(items)})


@app.route("/api/search")
def api_search():
    query = request.args.get("q", "")
    return jsonify({"ok": True, "results": ds.search_stocks(query)})


@app.route("/api/stock/<code>")
def api_stock(code):
    """個股詳細資料：K 線序列 + 指標 + 基本面 + 評分。"""
    period = request.args.get("period", "1y")
    if period not in ("3mo", "6mo", "1y", "2y", "5y"):
        period = "1y"

    stock = ds.resolve_stock(code) or {"code": code, "name": code, "market": "TWSE"}
    df = ds.get_history(stock["code"], stock["market"], period="2y")
    if df.empty:
        return jsonify({"ok": False, "error": "查無 {} 的行情資料".format(code)}), 404

    df_ind = ind.compute_all(df)
    snap = ind.snapshot(df_ind)
    fundamentals = ds.get_fundamentals(stock["code"], stock["market"])
    score = rating.evaluate(snap, fundamentals)

    # 依選定期間裁切要畫的 K 線根數
    bars = {"3mo": 63, "6mo": 125, "1y": 250, "2y": 500, "5y": 1250}[period]
    view = df_ind.tail(bars)

    def series(col):
        return [None if v != v else round(float(v), 2) for v in view[col]]

    candles = [
        [round(float(o), 2), round(float(c), 2), round(float(l), 2), round(float(h), 2)]
        for o, c, l, h in zip(view["Open"], view["Close"], view["Low"], view["High"])
    ]

    return jsonify({
        "ok": True,
        "stock": stock,
        "period": period,
        "quote": snap,
        "fundamentals": fundamentals,
        "rating": score,
        "chart": {
            "dates": [d.strftime("%Y-%m-%d") for d in view.index],
            "candles": candles,
            "volume": [int(v) for v in view["Volume"]],
            "ma5": series("MA5"), "ma20": series("MA20"), "ma60": series("MA60"),
            "dif": series("DIF"), "dea": series("DEA"), "macd_hist": series("MACD_HIST"),
            "k": series("K"), "d": series("D"), "rsi": series("RSI14"),
            "bb_up": series("BB_UP"), "bb_low": series("BB_LOW"),
        },
    })


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    print("=" * 56)
    print("  台股智慧篩選雷達  Stock Radar")
    print("  http://127.0.0.1:5000")
    print("=" * 56)
    if os.environ.get("STOCK_RADAR_NO_BROWSER") != "1":
        Timer(1.2, _open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
