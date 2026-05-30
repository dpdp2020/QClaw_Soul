# -*- coding: utf-8 -*-
"""
Triple Screen Daily Tracker v3.0
- Three-layer filtering: Fundamental → Technical → Volume Confirmation
- Data: Tencent Finance API (web.ifzq.gtimg.cn)
- Supports: A-share main/ChiNext/STAR前复权

Signal Hierarchy (v3.0):
  STRONG_BUY: BUY signal + MACD golden cross + volume breakout
  BUY:        BUY signal + MACD golden cross (or above signal)
  WATCH:      Weekly bullish but daily not confirmed
  NEUTRAL:    Trend unclear
  AVOID:      Weekly bearish or strong sell signals
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

# ============================================================
# MX Zixuan API (自选股同步)
# ============================================================
MX_MANAGE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/self-select/manage"

def sync_watchlist(add_list: list, remove_list: list, dry_run: bool = False) -> dict:
    """
    Sync watchlist: add STRONG_BUY/BUY stocks, remove AVOID stocks.
    Uses mx-zixuan API via Python requests (avoids PowerShell encoding issues).
    
    Args:
        add_list: list of (symbol, name) for BUY signals
        remove_list: list of (symbol, name) for AVOID signals
        dry_run: if True, only print actions without executing
    Returns dict with add_results and remove_results
    """
    apikey = os.environ.get("MX_APIKEY", "")
    if not apikey:
        print("  [WARN] MX_APIKEY not set, skipping watchlist sync")
        return {"added": [], "removed": [], "errors": ["MX_APIKEY not set"]}

    headers = {"Content-Type": "application/json", "apikey": apikey}
    results = {"added": [], "removed": [], "errors": [], "skipped": []}

    # --- Add BUY signals ---
    for symbol, name in add_list:
        if dry_run:
            print(f"  [DRY] Would add: {name}({symbol})")
            results["skipped"].append((symbol, name, "dry_run"))
            continue
        try:
            resp = requests.post(MX_MANAGE_URL, headers=headers,
                json={"query": f"把{symbol}添加到自选股三重滤网分组"}, timeout=30)
            data = resp.json()
            if data.get("code") == 0:
                print(f"  [+] Added to watchlist: {name}({symbol})")
                results["added"].append((symbol, name))
            else:
                msg = data.get("message", "")
                print(f"  [~] Add result: {name}({symbol}) -> {msg[:60]}")
                results["skipped"].append((symbol, name, msg))
        except Exception as e:
            print(f"  [!] Add failed: {name}({symbol}) -> {e}")
            results["errors"].append((symbol, name, str(e)))
        time.sleep(0.5)

    # --- Remove AVOID signals ---
    for symbol, name in remove_list:
        if dry_run:
            print(f"  [DRY] Would remove: {name}({symbol})")
            results["skipped"].append((symbol, name, "dry_run"))
            continue
        try:
            resp = requests.post(MX_MANAGE_URL, headers=headers,
                json={"query": f"把{symbol}从自选股三重滤网分组删除"}, timeout=30)
            data = resp.json()
            if data.get("code") == 0:
                print(f"  [-] Removed from watchlist: {name}({symbol})")
                results["removed"].append((symbol, name))
            else:
                msg = data.get("message", "")
                print(f"  [~] Remove result: {name}({symbol}) -> {msg[:60]}")
                results["skipped"].append((symbol, name, msg))
        except Exception as e:
            print(f"  [!] Remove failed: {name}({symbol}) -> {e}")
            results["errors"].append((symbol, name, str(e)))
        time.sleep(1.5)

    return results

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
WARN_VOL_NO_CONFIRM = "volume no confirm (< 1.5x 20d avg)"

def analyze_triple_screen(symbol: str, name: str, target_date: str = None) -> dict:
    result = {
        "symbol": symbol,
        "name": name,
        "signal": "NEUTRAL",
        "screen1": None,
        "screen2": None,
        "screen3": None,
        "screen_volume": None,
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
    vd = daily["volume"]
    ema13 = calc_ema(cd, 13)
    ema26 = calc_ema(cd, 26)
    bull_m = float(ema13.iloc[-1]) > float(ema26.iloc[-1])
    macd_vals = calc_macd(cd)
    macd = macd_vals[0]
    signal_line = macd_vals[1]
    m_now = float(macd.iloc[-1])
    m_prev = float(macd.iloc[-2]) if len(macd) >= 2 else 0
    macd_cross_up = m_now > 0 and m_prev < 0  # MACD golden cross
    macd_above_signal = m_now > float(signal_line.iloc[-1])

    # MACD histogram: positive and expanding (3 bars growing)
    macd_hist = macd - signal_line
    hist_vals = macd_hist.tail(3).values
    macd_expanding = len(hist_vals) >= 3 and all(not np.isnan(v) for v in hist_vals) and hist_vals[-1] > hist_vals[-2] > hist_vals[-3]
    macd_positive_expanding = macd_expanding and float(hist_vals[-1]) > 0
    # MACD histogram turning from negative to less-negative (momentum recovering)
    macd_momentum_recovering = float(hist_vals[-1]) > float(hist_vals[-2]) and not macd_positive_expanding

    high20 = float(daily["high"].tail(20).max())
    low20 = float(daily["low"].tail(20).min())
    ema13_last = float(ema13.iloc[-1])
    pos_in_band = None

    # Volume analysis (Screen 3 enhancement)
    vol_ma5 = vd.tail(5).mean()
    vol_ma20 = vd.tail(20).mean()
    vol_today = float(vd.iloc[-1])
    vol_ratio = vol_today / vol_ma20 if vol_ma20 > 0 else 1.0  # Volume ratio vs 20d avg
    price_above_high20 = None

    # Screen 3: Realtime position
    rt = get_realtime_quote(symbol)
    price = rt["price"] if rt else None
    prev_close = rt["prev_close"] if rt else None

    if price and (high20 - low20) > 0:
        pos_in_band = (price - low20) / (high20 - low20)
    elif price and daily is not None and not daily.empty:
        last_close = float(daily.iloc[-1]["close"])
        pos_in_band = (last_close - low20) / (high20 - low20) if (high20 - low20) > 0 else 0.5

    price_above_high20 = price is not None and price > high20

    result["screen3"] = {
        "price": round(price, 3) if price else None,
        "prev_close": round(prev_close, 3) if prev_close else None,
        "quote_date": rt["quote_date"] if rt else None,
        "high20": round(high20, 3),
        "low20": round(low20, 3),
        "pos_in_band": round(pos_in_band, 3) if pos_in_band is not None else None,
    }

    result["screen_volume"] = {
        "vol_ratio": round(vol_ratio, 2),
        "vol_ma5": round(float(vol_ma5), 0),
        "vol_ma20": round(float(vol_ma20), 0),
        "vol_today": round(vol_today, 0),
        "price_above_high20": price_above_high20,
        "macd_cross_up": macd_cross_up,
        "macd_above_signal": macd_above_signal,
    }

    # ============================================================
    # Scoring (v3.0 - stricter thresholds)
    # ============================================================
    buy_score = 0

    # --- Screen 1: Weekly trend (max 3 pts) ---
    if bull_w: buy_score += 2
    if slope13w > 0.01: buy_score += 1
    if slope13w < -0.01: buy_score -= 2

    # --- Screen 2: Daily momentum (max 6 pts) ---
    if bull_m: buy_score += 1
    if macd_cross_up: buy_score += 3       # MACD golden cross: strongest signal
    elif macd_positive_expanding: buy_score += 2  # MACD histogram positive & expanding
    elif macd_expanding: buy_score += 1    # MACD histogram expanding (could be negative)
    if macd_above_signal: buy_score += 1   # MACD above signal line
    if price_above_high20: buy_score += 1  # Breakout: mild

    # --- Screen 3: Position (max 1 pt) ---
    if pos_in_band is not None and 0.6 <= pos_in_band <= 0.9:
        buy_score += 1

    # --- Penalties ---
    if pos_in_band is not None and pos_in_band > 0.95:
        buy_score -= 1  # Overbought position

    # ============================================================
    # Signal determination (v3.0 - three-tier)
    # ============================================================
    # STRONG_BUY: high confidence, ready to act
    #   - Weekly bullish + MACD golden cross + volume breakout
    # BUY: solid signal, worth watching closely
    #   - Weekly bullish + MACD golden cross (or strong score)
    # WATCH: weekly bullish but daily not confirmed
    # NEUTRAL: unclear
    # AVOID: bearish

    if buy_score >= 7 and bull_w and (macd_cross_up or macd_positive_expanding):
        result["signal"] = "STRONG_BUY"
    elif buy_score >= 7 and bull_w and macd_above_signal and price_above_high20:
        result["signal"] = "STRONG_BUY"
    elif buy_score >= 6 and bull_w and (macd_cross_up or macd_positive_expanding):
        result["signal"] = "BUY"
    elif buy_score >= 6 and bull_w and macd_above_signal and price_above_high20:
        result["signal"] = "BUY"
    elif buy_score >= 6 and bull_w and macd_above_signal and vol_ratio >= 1.5:
        result["signal"] = "BUY"
    elif buy_score >= 3 and bull_w:
        result["signal"] = "WATCH"
    elif buy_score <= -3 or (not bull_w and slope13w < -0.01):
        result["signal"] = "AVOID"
    else:
        result["signal"] = "NEUTRAL"

    # Volume confirmation for STRONG_BUY / BUY
    vol_breakout = vol_ratio >= 1.5  # Volume >= 1.5x 20d average
    if result["signal"] == "STRONG_BUY" and not vol_breakout:
        # Downgrade to BUY if no volume confirmation
        result["signal"] = "BUY"
    if result["signal"] == "STRONG_BUY":
        result["screen_volume"]["vol_confirmed"] = True
    else:
        result["screen_volume"]["vol_confirmed"] = vol_breakout

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
    if not vol_breakout and result["signal"] in ("STRONG_BUY", "BUY"):
        result["warnings"].append(WARN_VOL_NO_CONFIRM)

    return result

# ============================================================
# Watch list - loaded from JSON config
# ============================================================

def load_watch_list(config_path: str = None, fundamental_filter: bool = True) -> list:
    """
    Load watch list from stock_pool.json with optional fundamental pre-filter (Layer 1).
    Returns list of (code, name, stock_info_dict) tuples.
    
    Layer 1 filters (when fundamental_filter=True):
    - Market cap >= 50 billion (exclude micro-caps)
    - Net profit growth >= 20% (C grade minimum)
    """
    default_paths = [
        os.environ.get("TRIPLE_SCREEN_STOCK_POOL"),
        r"D:\wujm\QClaw_data\workspace-strategy-analyst\stock_pool.json",
    ]
    paths_to_try = [config_path] if config_path else []
    paths_to_try.extend([p for p in default_paths if p])
    
    for path in paths_to_try:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                stocks = data.get("stocks", [])
                
                if fundamental_filter:
                    filtered = []
                    for s in stocks:
                        if not s.get("code") or not s.get("name"):
                            continue
                        cap = s.get("market_cap_billion")
                        pg = s.get("profit_growth")
                        rg = s.get("revenue_growth")
                        # Market cap: 50-2000 billion (Tier 1 + Tier 2, exclude mega caps >2000)
                        if cap is not None and cap < 50:
                            continue
                        # Profit growth >= 25% (B grade or above)
                        if pg is not None and pg < 0.25:
                            continue
                        # Revenue growth >= 20%
                        if rg is not None and rg < 0.20:
                            continue
                        filtered.append((s["code"], s["name"], s))
                    if filtered:
                        return filtered
                else:
                    watch_list = [(s["code"], s["name"], s) for s in stocks if s.get("code") and s.get("name")]
                    if watch_list:
                        return watch_list
            except Exception as e:
                print(f"Warning: Failed to load {path}: {e}")
    
    # Fallback to hardcoded list
    return [
        ("300394", "\u5929\u5b5a\u901a\u4fe1", {}),
        ("300308", "\u4e2d\u9645\u65ed\u521b", {}),
        ("300502", "\u65b0\u6613\u76db", {}),
        ("688012", "\u4e2d\u5fae\u516c\u53f8", {}),
        ("688072", "\u62d3\u8346\u79d1\u6280", {}),
        ("688120", "\u534e\u6d77\u6e05\u79d1", {}),
        ("300274", "\u9633\u5149\u7535\u6e90", {}),
        ("300750", "\u5b81\u5fb7\u65f6\u4ee3", {}),
        ("002371", "\u5317\u65b9\u534e\u521b", {}),
    ]

# Load watch list at module level
WATCH_LIST = load_watch_list()

SIGNAL_ARROW = {
    "STRONG_BUY": "[++]", "BUY": "[+]", "WATCH": "[~]", "NEUTRAL": "[-]", "AVOID": "[x]"
}

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
    print(f"  Triple Screen Daily Tracker v3.0  {today} ({today_dow})")
    if not trading:
        print(f"  *** Non-trading day (market closed) ***")
    
    # Show Layer 1 stats
    total_pool = len(load_watch_list(fundamental_filter=False))
    filtered_pool = len(WATCH_LIST)
    print(f"  Layer 1: {filtered_pool}/{total_pool} stocks passed fundamental filter")
    print(f"{'='*60}\n")

    all_results = []
    for idx, item in enumerate(WATCH_LIST):
        symbol, name = item[0], item[1]
        if idx > 0:
            time.sleep(0.3)
        print(f"Analyzing {name}({symbol}) ...")
        try:
            r = analyze_triple_screen(symbol, name)
            # Attach fundamental info
            if len(item) > 2 and item[2]:
                r["fundamental"] = {
                    "industry": item[2].get("industry", ""),
                    "market_cap_billion": item[2].get("market_cap_billion"),
                    "revenue_growth": item[2].get("revenue_growth"),
                    "profit_growth": item[2].get("profit_growth"),
                }
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
            vol_info = r.get("screen_volume", {})
            vol_ratio = vol_info.get("vol_ratio", 0)
            bull_mark = "[W]" if bull else "[D]"
            if not trading and price:
                price_str = f" last={price}"
            else:
                price_str = f" now={price}" if price else ""
            prev_str = f" prev={prev}" if prev else ""
            pos_str = f" B{pos:.0%}" if pos is not None else ""
            chg_str = f" {((price-prev)/prev*100):+.2f}%" if (price and prev) else ""
            vol_str = f" V{vol_ratio:.1f}x" if vol_ratio else ""
            print(f"  {bull_mark} {arrow} {sig}{price_str}{prev_str}{chg_str}{pos_str}{vol_str}{err_str}{warn_str}")
        except Exception as e:
            print(f"  [ERR] exception: {e}")
            all_results.append({"symbol": symbol, "name": name, "signal": "ERROR", "errors": [str(e)]})

    print(f"\n{'-'*60}")
    print(f"  Summary: STRONG_BUY > BUY > WATCH > NEUTRAL > AVOID")
    print(f"{'-'*60}")

    strong_buy = [r for r in all_results if r.get("signal") == "STRONG_BUY"]
    buy_list = [r for r in all_results if r.get("signal") == "BUY"]
    watch_list = [r for r in all_results if r.get("signal") == "WATCH"]
    avoid_list = [r for r in all_results if r.get("signal") == "AVOID"]
    neutral_list = [r for r in all_results if r.get("signal") == "NEUTRAL"]
    error_list = [r for r in all_results if r.get("signal") == "ERROR"]

    def print_stock_list(label, lst, show_details=False):
        if not lst:
            return
        print(f"\n  [{label}] ({len(lst)} stocks):")
        for r in lst:
            p = r["screen3"]["price"] if r.get("screen3") else None
            prev = r["screen3"]["prev_close"] if r.get("screen3") else None
            if not trading and p:
                pstr = f" last={p}"
            else:
                pstr = f" now={p}" if p else ""
            prstr = f" (prev={prev})" if prev else ""
            chg = f" {((p-prev)/prev*100):+.2f}%" if (p and prev) else ""
            fund = r.get("fundamental", {})
            cap_str = f" [{fund.get('market_cap_billion', 0):.0f}\u4ebf]" if fund.get('market_cap_billion') else ""
            vol_info = r.get("screen_volume", {})
            vol_str = f" V{vol_info.get('vol_ratio', 0):.1f}x" if vol_info.get('vol_ratio') else ""
            warns = f" | {'; '.join(r['warnings'])}" if r.get('warnings') else ""
            print(f"    - {r['name']}({r['symbol']}){pstr}{prstr}{chg}{cap_str}{vol_str}{warns if show_details else ''}")

    print_stock_list("STRONG_BUY", strong_buy, show_details=True)
    print_stock_list("BUY", buy_list, show_details=True)
    print_stock_list("WATCH", watch_list)
    print_stock_list("AVOID", avoid_list)
    
    if neutral_list:
        print(f"\n  [NEUTRAL] ({len(neutral_list)} stocks)")
    if error_list:
        print(f"\n  [DATA ERROR] ({len(error_list)} stocks):")
        for r in error_list:
            err = r['errors'][0] if r.get('errors') else 'unknown'
            print(f"    - {r['name']}({r['symbol']}): {err}")

    time.sleep(1)
    out = {"date": today, "version": "3.0", "layer1_filtered": filtered_pool, "layer1_total": total_pool, "results": all_results}
    out_file = f"triple_screen_tech_{today.replace('-','')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nSaved: {out_file}")

    # 【修复】自动复制到标准文件名，供策略官/交易官读取
    import shutil
    target_file = "triple_screen_tech.json"
    shutil.copy(out_file, target_file)
    print(f"Copied to {target_file}")
    print(f"Layer 1: {filtered_pool}/{total_pool} | Total: {len(all_results)} | STRONG_BUY:{len(strong_buy)} BUY:{len(buy_list)} WATCH:{len(watch_list)} AVOID:{len(avoid_list)}")

    # --- Sync watchlist via MX API ---
    if trading:
        print(f"\n{'='*60}")
        print(f"  Syncing watchlist via MX API...")
        print(f"{'='*60}")
        add_stocks = [(r["symbol"], r["name"]) for r in strong_buy]
        remove_stocks = [(r["symbol"], r["name"]) for r in avoid_list]
        if not add_stocks and not remove_stocks:
            print("  No changes needed.")
        else:
            sync_result = sync_watchlist(add_stocks, remove_stocks)
            added = len(sync_result["added"])
            removed = len(sync_result["removed"])
            skipped = len(sync_result["skipped"])
            errors = len(sync_result["errors"])
            print(f"\n  Watchlist sync done: +{added} -{removed} ~{skipped} !{errors}")
    else:
        print(f"\n  [Skip watchlist sync: non-trading day]")

if __name__ == "__main__":
    main()
