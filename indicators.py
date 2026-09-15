# -*- coding: utf-8 -*-
"""技術指標計算（純 pandas 實作，不依賴 TA-Lib）。"""

import numpy as np
import pandas as pd


def sma(series, n):
    return series.rolling(n, min_periods=max(2, n // 2)).mean()


def ema(series, n):
    return series.ewm(span=n, adjust=False).mean()


def rsi(series, n=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)


def macd(series, fast=12, slow=26, signal=9):
    dif = ema(series, fast) - ema(series, slow)
    dea = ema(dif, signal)
    hist = (dif - dea) * 2
    return dif, dea, hist


def kdj(df, n=9, k_period=3, d_period=3):
    low_n = df["Low"].rolling(n, min_periods=1).min()
    high_n = df["High"].rolling(n, min_periods=1).max()
    rsv = (df["Close"] - low_n) / (high_n - low_n).replace(0, np.nan) * 100
    rsv = rsv.fillna(50)
    k = rsv.ewm(alpha=1 / k_period, adjust=False).mean()
    d = k.ewm(alpha=1 / d_period, adjust=False).mean()
    return k, d


def bollinger(series, n=20, k=2):
    mid = sma(series, n)
    std = series.rolling(n, min_periods=2).std()
    return mid + k * std, mid, mid - k * std


def atr(df, n=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def max_drawdown(series):
    """回傳期間最大回撤（正數百分比）。"""
    if series.empty:
        return 0.0
    running_max = series.cummax()
    dd = (series / running_max - 1) * 100
    return float(abs(dd.min()))


def compute_all(df):
    """一次算出所有指標，回傳附加欄位後的 DataFrame。"""
    out = df.copy()
    close = out["Close"]

    out["MA5"] = sma(close, 5)
    out["MA10"] = sma(close, 10)
    out["MA20"] = sma(close, 20)
    out["MA60"] = sma(close, 60)
    out["MA120"] = sma(close, 120)

    out["VOL_MA5"] = sma(out["Volume"], 5)
    out["VOL_MA20"] = sma(out["Volume"], 20)

    out["RSI14"] = rsi(close, 14)
    out["DIF"], out["DEA"], out["MACD_HIST"] = macd(close)
    out["K"], out["D"] = kdj(out)
    out["BB_UP"], out["BB_MID"], out["BB_LOW"] = bollinger(close)
    out["ATR14"] = atr(out)
    return out


def snapshot(df_ind):
    """把最新一筆指標整理成扁平的 dict，供評分與前端使用。"""
    if df_ind.empty:
        return {}

    last = df_ind.iloc[-1]
    close = float(last["Close"])
    prev_close = float(df_ind["Close"].iloc[-2]) if len(df_ind) >= 2 else close

    def pct_change(days):
        if len(df_ind) <= days:
            return None
        base = float(df_ind["Close"].iloc[-1 - days])
        return (close / base - 1) * 100 if base else None

    def val(name):
        v = last.get(name)
        return None if v is None or pd.isna(v) else float(v)

    window60 = df_ind["Close"].tail(60)
    window252 = df_ind["Close"].tail(252)

    return {
        "date": df_ind.index[-1].strftime("%Y-%m-%d"),
        "close": close,
        "open": float(last["Open"]),
        "high": float(last["High"]),
        "low": float(last["Low"]),
        "prev_close": prev_close,
        "change": close - prev_close,
        "change_pct": (close / prev_close - 1) * 100 if prev_close else 0.0,
        "volume": int(last["Volume"]),
        "volume_lots": int(last["Volume"] // 1000),
        "ma5": val("MA5"), "ma10": val("MA10"), "ma20": val("MA20"),
        "ma60": val("MA60"), "ma120": val("MA120"),
        "vol_ma5": val("VOL_MA5"), "vol_ma20": val("VOL_MA20"),
        "rsi14": val("RSI14"),
        "dif": val("DIF"), "dea": val("DEA"), "macd_hist": val("MACD_HIST"),
        "macd_hist_prev": float(df_ind["MACD_HIST"].iloc[-2]) if len(df_ind) >= 2 else 0.0,
        "k": val("K"), "d": val("D"),
        "bb_up": val("BB_UP"), "bb_low": val("BB_LOW"),
        "atr14": val("ATR14"),
        "ret_5d": pct_change(5),
        "ret_20d": pct_change(20),
        "ret_60d": pct_change(60),
        "ma20_slope": ((float(last["MA20"]) / float(df_ind["MA20"].iloc[-21]) - 1) * 100)
        if len(df_ind) >= 21 and not pd.isna(df_ind["MA20"].iloc[-21]) and df_ind["MA20"].iloc[-21] else None,
        "mdd_60d": max_drawdown(window60),
        "high_60d": float(window60.max()),
        "low_60d": float(window60.min()),
        "high_252d": float(window252.max()),
        "low_252d": float(window252.min()),
    }
