# -*- coding: utf-8 -*-
"""
Triple Screen Daily Tracker v2.1
- Data: Tencent Finance API (web.ifzq.gtimg.cn)
- Supports: A-share main/ChiNext/STAR前复权
"""
import sys
import json
import os
import re
import warnings
import time
from datetime import datetime, timedelta

import requests
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ============================================================
# Market data API (Tencent Finance, supports forward adjustment)
# ============================================================
_session = requests.Session()
_session.trust_env = False
_session.proxies = {"http": None, "https": None}
_session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def _fetch(url: str, timeout: int = 15) -> str:
    r = _session.get(url, timeout=timeout)
    r.encoding = "utf-8"
    return r.text

def _parse_kline(raw: str, prefix: str, key: str) -> list:
    """Parse Tencent K-line API response. Compatible with ChiNext (qfqday/qfqweek) and STAR (day/week)."""
    try:
        raw2 = re.sub(r"^[^=]+=", "", raw)
        data = json.loads(raw2)
        if data.get("code") != 0:
            return []
        for v in data.get("data", {}).values():
            if isinstance(v, dict):
                if key in v:
                    return v[key]
                if key.startswith("qfq") and key[3:] in v:
                    return v[key[3:]]
        return []
    except Exception:
        return []

def get_weekly_kline(symbol: str, count: int = 80, max_retries: int = 3) -> pd.DataFrame:
    prefix = "sz" if symbol.startswith(("0", "3", "4", "8")) else "sh"
    end = datetime.today().strftime("%Y-%m-%d")
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?_var=kline_weekqfq&param={prefix}{symbol},week,,{end},{count},qfq&r=0.2")
    for attempt in range(1, max_retries + 1):
        try:
            rows = _parse_kline(_fetch(url), prefix, "qfqweek")
            if rows:
                # Truncate to 6 cols: some rows may include dividend info as 7th col
                rows = [r[:6] for r in rows]
                df = pd.DataFrame(rows, columns=["date","open","close","high","low","volume"])
                df["date"] = pd.to_datetime(df["date"])
                for col in ["open","close","high","low","volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.sort_values("date").reset_index(drop=True)
                return df
        except Exception:
            pass
        if attempt < max_retries:
            time.sleep(0.5 * attempt)
    return pd.DataFrame()

def get_daily_kline(symbol: str, count: int = 120, max_retries: int = 3) -> pd.DataFrame:
    prefix = "sz" if symbol.startswith(("0", "3", "4", "8")) else "sh"
    end = datetime.today().strftime("%Y-%m-%d")
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?_var=kline_dayqfq&param={prefix}{symbol},day,,{end},{count},qfq&r=0.3")
    for attempt in range(1, max_retries + 1):
        try:
            rows = _parse_kline(_fetch(url), prefix, "qfqday")
            if rows:
                # Truncate to 6 cols: some rows may include dividend info as 7th col
                rows = [r[:6] for r in rows]
                df = pd.DataFrame(rows, columns=["date","open","close","high","low","volume"])
                df["date"] = pd.to_datetime(df["date"])
                for col in ["open","close","high","low","volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.sort_values("date").reset_index(drop=True)
                return df
        except Exception:
            pass
        if attempt < max_retries:
            time.sleep(0.5 * attempt)
    return pd.DataFrame()

def get_prev_close_from_kline(daily_df: pd.DataFrame) -> float | None:
    """Get the most recent completed trading day's close from daily kline."""
    if daily_df is None or daily_df.empty:
        return None
    today = datetime.today().date()
    last_row = daily_df.iloc[-1]
    last_date = last_row["date"].date()
    if last_date == today:
        # If last kline row is today, use the previous row as prev_close
        if len(daily_df) >= 2:
            return float(daily_df.iloc[-2]["close"])
        return None
    else:
        return float(last_row["close"])

# ============================================================
# Indicators
# ============================================================
def calc_ema(series: pd.Series, n: int) -> pd.Series:
    return series.ewm(span=n, adjust=False).mean()

def calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def slope_norm(series: pd.Series, n: int = 3) -> float:
    if len(series) < n:
        return 0.0
    prices = series.iloc[-n:].values
    if np.any(np.isnan(prices)):
        return 0.0
    x = np.arange(n)
    slope = np.polyfit(x, prices, 1)[0]
    baseline = np.mean(prices)
    return float(slope / baseline) if baseline != 0 else 0.0

def get_realtime_quote(symbol: str) -> dict | None:
    prefix = "sz" if symbol.startswith(("0", "3", "4", "8")) else "sh"
    url = f"https://qt.gtimg.cn/q={prefix}{symbol}"
    try:
        text = _fetch(url, timeout=10)
        parts = text.strip().split("~")
        if len(parts) < 10:
            return None
        return {
            "name": parts[1],
            "price": float(parts[3]),
            "prev_close": float(parts[4]),
            "open": float(parts[5]),
            "volume": float(parts[6]) * 100,
            "bid1": float(parts[9]),
            "ask1": float(parts[19]),
            "quote_date": parts[30],
        }
    except Exception:
        return None

# ============================================================
# Triple Screen Core
# ============================================================
WARN_BREAK_EMA13 = "break daily ema13, watch stop"
WARN_MACD_WEAK = "macd momentum weak"
WARN_ABOVE_HIGH20 = "break 20d high, strong signal"
WARN_BREAK_PREVCLOSE2 = "break prev close 2%, weak signal"
WARN_WEEK_EMA13_DOWN = "weekly ema13 sloping down, caution"

def analyze_triple_screen(symbol: str, name: str, target_date: str = None) -> dict:
    result = {
        "symbol": symbol,
        "name": name,
        "signal": "NEUTRAL",
        "screen1": None,
        "screen2": None,
        "screen3": None,
        "warnings": [],
        "errors": [],
    }

    # Screen 1: Weekly trend
    weekly = get_weekly_kline(symbol, count=80)
    if weekly is None or weekly.empty:
        result["errors"].append("weekly kline unavailable")
        return result

    cw = weekly["close"]
    ema13w = calc_ema(cw, 13)
    ema26w = calc_ema(cw, 26)
    slope13w = slope_norm(ema13w, 3)
    slope26w = slope_norm(ema26w, 3)
    bull_w = float(ema13w.iloc[-1]) > float(ema26w.iloc[-1]) and slope13w > 0
    result["screen1"] = {
        "ema13": round(float(ema13w.iloc[-1]), 3),
        "ema26": round(float(ema26w.iloc[-1]), 3),
        "ema13_slope": round(slope13w, 4),
        "ema26_slope": round(slope26w, 4),
        "bullish": bull_w,
        "weekly_close": round(float(cw.iloc[-1]), 3),
    }

    # Screen 2: Daily momentum
    daily = get_daily_kline(symbol, count=120)
    if daily is None or daily.empty:
        result["errors"].append("daily kline unavailable")
        return result

    cd = daily["close"]
    ema13 = calc_ema(cd, 13)
    ema26 = calc_ema(cd, 26)
    bull_m = float(ema13.iloc[-1]) > float(ema26.iloc[-1])
    macd_vals = calc_macd(cd)
    macd = macd_vals[0]
    signal_line = macd_vals[1]
    m_now = float(macd.iloc[-1])
    m_prev = float(macd.iloc[-2]) if len(macd) >= 2 else 0

    high20 = float(daily["high"].tail(20).max())
    low20 = float(daily["low"].tail(20).min())
    ema13_last = float(ema13.iloc[-1])
    pos_in_band = None

    # Screen 3: Realtime position
    rt = get_realtime_quote(symbol)
    price = rt["price"] if rt else None
    prev_close = rt["prev_close"] if rt else None

    if price and (high20 - low20) > 0:
        pos_in_band = (price - low20) / (high20 - low20)
    elif price and daily is not None and not daily.empty:
        last_close = float(daily.iloc[-1]["close"])
        pos_in_band = (last_close - low20) / (high20 - low20) if (high20 - low20) > 0 else 0.5

    result["screen3"] = {
        "price": round(price, 3) if price else None,
        "prev_close": round(prev_close, 3) if prev_close else None,
        "quote_date": rt["quote_date"] if rt else None,
        "high20": round(high20, 3),
        "low20": round(low20, 3),
        "pos_in_band": round(pos_in_band, 3) if pos_in_band is not None else None,
    }

    # Scoring
    buy_score = 0
    if bull_w: buy_score += 2
    if slope13w > 0.01: buy_score += 1
    if slope13w < -0.01: buy_score -= 2
    if bull_m: buy_score += 2
    if m_now > float(signal_line.iloc[-1]): buy_score += 1
    if m_now > 0 and m_prev < 0: buy_score += 2
    if pos_in_band is not None and 0.6 <= pos_in_band <= 0.9: buy_score += 1
    if price and price > high20: buy_score += 2

    if buy_score >= 6 and bull_w:
        result["signal"] = "BUY"
    elif buy_score >= 3 and bull_w:
        result["signal"] = "WATCH"
    elif buy_score <= -3 or (not bull_w and slope13w < -0.01):
        result["signal"] = "AVOID"

    # Warnings
    if not bull_w and slope13w < -0.005:
        result["warnings"].append(WARN_WEEK_EMA13_DOWN)
    if bull_m and m_now < 0.01:
        result["warnings"].append(WARN_MACD_WEAK)
    if price and price < ema13_last * 0.97:
        result["warnings"].append(WARN_BREAK_EMA13)
    if price and price > high20:
        result["warnings"].append(WARN_ABOVE_HIGH20)
    if price and prev_close and price < prev_close * 0.97:
        result["warnings"].append(WARN_BREAK_PREVCLOSE2)

    return result

# ============================================================
# Watch list
# ============================================================
WATCH_LIST = [
    ("300394", "天孚通信"),
    ("300308", "中际旭创"),
    ("300502", "新易盛"),
    ("688012", "中微公司"),
    ("688072", "拓荆科技"),
    ("688120", "华海清科"),
    ("300274", "阳光电源"),
    ("300750", "宁德时代"),
    ("002371", "北方华创"),
]

SIGNAL_EMOJI = {"BUY": "BUY", "WATCH": "WATCH", "NEUTRAL": "NEUT", "AVOID": "AVOID"}
SIGNAL_ARROW = {"BUY": "[+]", "WATCH": "[~]", "NEUTRAL": "[-]", "AVOID": "[x]"}

# ============================================================
# Main
# ============================================================
def is_trading_day() -> bool:
    """Simple check: weekends are not trading days. For holidays, check kline."""
    dow = datetime.today().weekday()
    return dow < 5  # Mon=0 ... Fri=4

def main():
    # Fix Windows GBK terminal encoding
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    today = datetime.today().strftime("%Y-%m-%d")
    today_dow = datetime.today().strftime("%A")
    trading = is_trading_day()
    print(f"\n{'='*60}")
    print(f"  Triple Screen Daily Tracker  {today} ({today_dow})")
    if not trading:
        print(f"  *** Non-trading day (market closed) ***")
    print(f"{'='*60}\n")

    all_results = []
    for idx, (symbol, name) in enumerate(WATCH_LIST):
        if idx > 0:
            time.sleep(0.3)  # Rate limit between stocks
        print(f"Analyzing {name}({symbol}) ...")
        try:
            r = analyze_triple_screen(symbol, name)
            all_results.append(r)
            err_str = f" [ERR: {r['errors'][0]}]" if r["errors"] else ""
            warn_str = f" | {'; '.join(r['warnings'])}" if r["warnings"] else ""
            sig = r["signal"]
            arrow = SIGNAL_ARROW.get(sig, "[-]")
            price = r["screen3"]["price"] if r["screen3"] else None
            prev = r["screen3"]["prev_close"] if r["screen3"] else None
            qdate = r["screen3"]["quote_date"] if r["screen3"] else None
            pos = r["screen3"]["pos_in_band"] if r["screen3"] else None
            bull = r["screen1"]["bullish"] if r["screen1"] else False
            bull_mark = "[W]" if bull else "[D]"
            # On non-trading days, label price as 'last close' not 'current'
            if not trading and price:
                price_str = f" last={price}"
            else:
                price_str = f" now={price}" if price else ""
            prev_str = f" prev={prev}" if prev else ""
            pos_str = f" B{pos:.0%}" if pos is not None else ""
            chg_str = f" {((price-prev)/prev*100):+.2f}%" if (price and prev) else ""
            print(f"  {bull_mark} {arrow} {sig}{price_str}{prev_str}{chg_str}{pos_str}{err_str}{warn_str}")
            if qdate:
                print(f"       quote_date={qdate}")
        except Exception as e:
            print(f"  [ERR] exception: {e}")
            all_results.append({"symbol": symbol, "name": name, "signal": "ERROR", "errors": [str(e)]})

    print(f"\n{'-'*60}")
    print(f"  Summary: BUY signals first, then WATCH")
    print(f"{'-'*60}")

    buy_list = [r for r in all_results if r.get("signal") == "BUY"]
    watch_list = [r for r in all_results if r.get("signal") == "WATCH"]
    avoid_list = [r for r in all_results if r.get("signal") == "AVOID"]
    neutral_list = [r for r in all_results if r.get("signal") == "NEUTRAL"]
    error_list = [r for r in all_results if r.get("signal") == "ERROR"]

    for label, lst in [("BUY", buy_list), ("WATCH", watch_list), ("AVOID", avoid_list)]:
        if lst:
            print(f"\n  [{label}] ({len(lst)} stocks):")
            for r in lst:
                p = r["screen3"]["price"] if r["screen3"] else None
                prev = r["screen3"]["prev_close"] if r["screen3"] else None
                if not trading and p:
                    pstr = f" last={p}"
                else:
                    pstr = f" now={p}" if p else ""
                prstr = f" (prev={prev})" if prev else ""
                chg = f" {((p-prev)/prev*100):+.2f}%" if (p and prev) else ""
                print(f"    - {r['name']}({r['symbol']}){pstr}{prstr}{chg}")
    if neutral_list:
        print(f"\n  [NEUTRAL] ({len(neutral_list)} stocks):")
        for r in neutral_list:
            p = r["screen3"]["price"] if r["screen3"] else None
            prev = r["screen3"]["prev_close"] if r["screen3"] else None
            if not trading and p:
                pstr = f" last={p}"
            else:
                pstr = f" now={p}" if p else ""
            prstr = f" (prev={prev})" if prev else ""
            chg = f" {((p-prev)/prev*100):+.2f}%" if (p and prev) else ""
            warns = f" | {'; '.join(r['warnings'])}" if r['warnings'] else ""
            print(f"    - {r['name']}({r['symbol']}){pstr}{prstr}{chg}{warns}")
    if error_list:
        print(f"\n  [DATA ERROR] ({len(error_list)} stocks):")
        for r in error_list:
            err = r['errors'][0] if r.get('errors') else 'unknown'
            print(f"    - {r['name']}({r['symbol']}): {err}")

    time.sleep(1)
    out = {"date": today, "results": all_results}
    out_file = f"triple_screen_tech_{today.replace('-','')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nSaved: {out_file}")
    print(f"Total: {len(all_results)} | BUY:{len(buy_list)} WATCH:{len(watch_list)} AVOID:{len(avoid_list)}")

if __name__ == "__main__":
    main()
