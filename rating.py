# -*- coding: utf-8 -*-
"""五大構面評分引擎：趨勢 / 動能 / 量能 / 風險 / 價值，總分 100。

每個構面都回傳 0~滿分 的連續分數與可讀的理由，讓排序結果可被檢驗。
"""

from config import GRADE_BANDS, WEIGHTS


def _scale(value, low, high):
    """把 value 由 [low, high] 線性映射到 [0, 1]，超出範圍夾住。"""
    if value is None:
        return 0.5
    if high == low:
        return 0.5
    ratio = (value - low) / (high - low)
    return max(0.0, min(1.0, ratio))


def _band(value, ideal_low, ideal_high, hard_low, hard_high):
    """理想區間內給滿分，往外側線性衰減到 0。"""
    if value is None:
        return 0.5
    if ideal_low <= value <= ideal_high:
        return 1.0
    if value < ideal_low:
        return _scale(value, hard_low, ideal_low)
    return 1.0 - _scale(value, ideal_high, hard_high)


# ------------------------------------------------------------------ 趨勢 30
def score_trend(s):
    reasons = []
    close = s["close"]
    parts = []

    ma20 = s.get("ma20")
    if ma20:
        dev = (close / ma20 - 1) * 100
        parts.append(_scale(dev, -8, 8) * 10)
        reasons.append("站上月線 +{:.1f}%".format(dev) if dev >= 0 else "跌破月線 {:.1f}%".format(dev))
    else:
        parts.append(5)

    ma60 = s.get("ma60")
    if ma60:
        dev = (close / ma60 - 1) * 100
        parts.append(_scale(dev, -15, 15) * 8)
        reasons.append("季線之上 +{:.1f}%".format(dev) if dev >= 0 else "季線之下 {:.1f}%".format(dev))
    else:
        parts.append(4)

    ma5, ma20v = s.get("ma5"), s.get("ma20")
    if ma5 and ma20v:
        spread = (ma5 / ma20v - 1) * 100
        parts.append(_scale(spread, -5, 5) * 6)
        if spread > 0.5:
            reasons.append("短均線向上發散")
        elif spread < -0.5:
            reasons.append("短均線走弱")
    else:
        parts.append(3)

    slope = s.get("ma20_slope")
    if slope is not None:
        parts.append(_scale(slope, -12, 12) * 6)
        reasons.append("月線月斜率 {:+.1f}%".format(slope))
    else:
        parts.append(3)

    return round(sum(parts), 1), reasons


# ------------------------------------------------------------------ 動能 25
def score_momentum(s):
    reasons = []
    parts = []

    r = s.get("rsi14")
    # RSI 以 55~70 為最佳；過熱（>80）與弱勢（<40）都扣分
    parts.append(_band(r, 55, 70, 30, 88) * 10)
    if r is not None:
        if r >= 80:
            reasons.append("RSI {:.0f} 過熱".format(r))
        elif r >= 55:
            reasons.append("RSI {:.0f} 多方動能".format(r))
        elif r <= 40:
            reasons.append("RSI {:.0f} 動能不足".format(r))
        else:
            reasons.append("RSI {:.0f} 中性".format(r))

    hist, hist_prev = s.get("macd_hist"), s.get("macd_hist_prev", 0)
    if hist is not None:
        base = 4.5 if hist > 0 else 1.5
        base += 3.5 if hist > hist_prev else 0.0
        parts.append(min(8.0, base))
        if hist > 0 and hist > hist_prev:
            reasons.append("MACD 紅柱擴大")
        elif hist > 0:
            reasons.append("MACD 位於零軸上")
        elif hist > hist_prev:
            reasons.append("MACD 綠柱收斂")
        else:
            reasons.append("MACD 空方轉強")
    else:
        parts.append(4)

    ret20 = s.get("ret_20d")
    parts.append(_scale(ret20, -15, 20) * 7)
    if ret20 is not None:
        reasons.append("近 20 日 {:+.1f}%".format(ret20))

    return round(sum(parts), 1), reasons


# ------------------------------------------------------------------ 量能 15
def score_volume(s):
    reasons = []
    parts = []

    v5, v20 = s.get("vol_ma5"), s.get("vol_ma20")
    if v5 and v20:
        ratio = v5 / v20
        # 1.0~2.0 倍為健康放量；超過 3 倍多為追高爆量
        parts.append(_band(ratio, 1.0, 2.0, 0.4, 3.5) * 9)
        reasons.append("5日均量 / 20日均量 = {:.2f}".format(ratio))
    else:
        parts.append(4.5)

    # 量價配合：上漲且放量最佳
    today_v, change_pct = s.get("volume"), s.get("change_pct", 0)
    if today_v and v20:
        today_ratio = today_v / v20
        if change_pct > 0:
            parts.append(_band(today_ratio, 1.0, 2.5, 0.4, 4.0) * 6)
            reasons.append("今日量增價漲" if today_ratio > 1.1 else "今日價漲量縮")
        else:
            # 下跌時量縮較健康
            parts.append((1 - _scale(today_ratio, 0.8, 2.5)) * 6)
            reasons.append("今日量增價跌" if today_ratio > 1.2 else "今日跌勢量縮")
    else:
        parts.append(3)

    return round(sum(parts), 1), reasons


# ------------------------------------------------------------------ 風險 15
def score_risk(s):
    """分數越高代表風險越低。"""
    reasons = []
    parts = []

    atr, close = s.get("atr14"), s.get("close")
    if atr and close:
        atr_pct = atr / close * 100
        parts.append((1 - _scale(atr_pct, 1.0, 6.0)) * 8)
        reasons.append("日均波動 {:.1f}%".format(atr_pct))
    else:
        parts.append(4)

    mdd = s.get("mdd_60d")
    if mdd is not None:
        parts.append((1 - _scale(mdd, 5, 35)) * 7)
        reasons.append("近 60 日最大回撤 -{:.1f}%".format(mdd))
    else:
        parts.append(3.5)

    return round(sum(parts), 1), reasons


# ------------------------------------------------------------------ 價值 15
def score_value(f):
    reasons = []
    parts = []

    pe = f.get("pe")
    if pe and pe > 0:
        parts.append((1 - _scale(pe, 8, 45)) * 6)
        reasons.append("本益比 {:.1f} 倍".format(pe))
    else:
        parts.append(3)
        reasons.append("本益比無資料")

    pb = f.get("pb")
    if pb and pb > 0:
        parts.append((1 - _scale(pb, 0.8, 6.0)) * 4)
        reasons.append("股價淨值比 {:.2f}".format(pb))
    else:
        parts.append(2)

    dy = f.get("dividend_yield")
    if dy is not None and dy > 0:
        parts.append(_scale(dy, 0.5, 6.0) * 5)
        reasons.append("殖利率 {:.2f}%".format(dy))
    else:
        parts.append(2)

    return round(sum(parts), 1), reasons


# ------------------------------------------------------------------ 綜合
def grade_of(total):
    for threshold, grade, label in GRADE_BANDS:
        if total >= threshold:
            return grade, label
    return "D", "弱勢"


def evaluate(snap, fundamentals):
    """回傳完整評分結果（總分、分級、各構面分數與理由）。"""
    if not snap:
        return None

    trend, r_trend = score_trend(snap)
    mom, r_mom = score_momentum(snap)
    vol, r_vol = score_volume(snap)
    risk, r_risk = score_risk(snap)
    value, r_value = score_value(fundamentals or {})

    total = round(trend + mom + vol + risk + value, 1)
    grade, label = grade_of(total)

    return {
        "total": total,
        "grade": grade,
        "label": label,
        "breakdown": [
            {"key": "trend",    "name": "趨勢結構", "score": trend, "max": WEIGHTS["trend"],    "reasons": r_trend},
            {"key": "momentum", "name": "動能表現", "score": mom,   "max": WEIGHTS["momentum"], "reasons": r_mom},
            {"key": "volume",   "name": "量能結構", "score": vol,   "max": WEIGHTS["volume"],   "reasons": r_vol},
            {"key": "risk",     "name": "風險控制", "score": risk,  "max": WEIGHTS["risk"],     "reasons": r_risk},
            {"key": "value",    "name": "價值評估", "score": value, "max": WEIGHTS["value"],    "reasons": r_value},
        ],
    }
