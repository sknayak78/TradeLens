"""Static market seed data for TradeLens.

The market/opportunities/stocks data is inherently mocked for this MVP.
It lives here so the API can serve consistent, canonical values without a
live market feed. Watchlist / Trades / Settings are stored in SQLite.
"""
from __future__ import annotations
from typing import Dict, List


STOCKS: List[Dict] = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "price": 2934.55, "changePct": 1.24, "score": 88, "trend": "bullish", "rsi": 62.4, "ema20": 2891.32, "vwap": 2918.75, "volume": 4820000, "sector": "Energy"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "price": 4102.10, "changePct": 0.42, "score": 79, "trend": "bullish", "rsi": 58.1, "ema20": 4056.80, "vwap": 4080.15, "volume": 1580000, "sector": "IT"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "price": 1548.90, "changePct": -0.32, "score": 71, "trend": "neutral", "rsi": 48.9, "ema20": 1552.20, "vwap": 1550.50, "volume": 8720000, "sector": "Banking"},
    {"symbol": "INFY", "name": "Infosys", "price": 1732.65, "changePct": 1.87, "score": 84, "trend": "bullish", "rsi": 64.2, "ema20": 1698.44, "vwap": 1715.20, "volume": 5210000, "sector": "IT"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "price": 1189.25, "changePct": 0.94, "score": 82, "trend": "bullish", "rsi": 60.5, "ema20": 1172.80, "vwap": 1181.60, "volume": 6420000, "sector": "Banking"},
    {"symbol": "SBIN", "name": "State Bank of India", "price": 812.40, "changePct": -1.12, "score": 58, "trend": "bearish", "rsi": 42.8, "ema20": 823.15, "vwap": 819.30, "volume": 9210000, "sector": "Banking"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "price": 1615.75, "changePct": 2.14, "score": 90, "trend": "bullish", "rsi": 68.7, "ema20": 1568.20, "vwap": 1592.40, "volume": 3820000, "sector": "Telecom"},
    {"symbol": "LT", "name": "Larsen & Toubro", "price": 3654.20, "changePct": 0.68, "score": 77, "trend": "bullish", "rsi": 56.3, "ema20": 3620.15, "vwap": 3638.90, "volume": 1120000, "sector": "Infra"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "price": 2415.60, "changePct": -0.45, "score": 62, "trend": "neutral", "rsi": 45.6, "ema20": 2428.30, "vwap": 2422.10, "volume": 1450000, "sector": "FMCG"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "price": 1782.55, "changePct": 0.28, "score": 68, "trend": "neutral", "rsi": 51.4, "ema20": 1775.20, "vwap": 1780.85, "volume": 2150000, "sector": "Banking"},
    {"symbol": "AXISBANK", "name": "Axis Bank", "price": 1148.30, "changePct": 1.42, "score": 81, "trend": "bullish", "rsi": 63.2, "ema20": 1122.40, "vwap": 1138.10, "volume": 4820000, "sector": "Banking"},
    {"symbol": "ITC", "name": "ITC Ltd", "price": 462.85, "changePct": -0.78, "score": 55, "trend": "bearish", "rsi": 43.1, "ema20": 468.20, "vwap": 465.90, "volume": 12480000, "sector": "FMCG"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki", "price": 12480.90, "changePct": 1.85, "score": 86, "trend": "bullish", "rsi": 66.9, "ema20": 12210.60, "vwap": 12345.20, "volume": 480000, "sector": "Auto"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors", "price": 972.65, "changePct": 3.24, "score": 92, "trend": "bullish", "rsi": 72.4, "ema20": 928.40, "vwap": 950.30, "volume": 15420000, "sector": "Auto"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharma", "price": 1725.30, "changePct": 0.56, "score": 74, "trend": "bullish", "rsi": 57.8, "ema20": 1710.20, "vwap": 1718.60, "volume": 2140000, "sector": "Pharma"},
    {"symbol": "ASIANPAINT", "name": "Asian Paints", "price": 2814.55, "changePct": -1.68, "score": 46, "trend": "bearish", "rsi": 38.4, "ema20": 2862.30, "vwap": 2842.15, "volume": 950000, "sector": "FMCG"},
    {"symbol": "WIPRO", "name": "Wipro", "price": 552.80, "changePct": 0.85, "score": 69, "trend": "bullish", "rsi": 54.6, "ema20": 546.20, "vwap": 549.85, "volume": 6820000, "sector": "IT"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises", "price": 2895.40, "changePct": 4.12, "score": 94, "trend": "bullish", "rsi": 74.8, "ema20": 2758.60, "vwap": 2820.30, "volume": 3820000, "sector": "Conglomerate"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "price": 7154.20, "changePct": -0.92, "score": 63, "trend": "neutral", "rsi": 46.2, "ema20": 7215.30, "vwap": 7188.60, "volume": 780000, "sector": "NBFC"},
    {"symbol": "NESTLEIND", "name": "Nestle India", "price": 2245.75, "changePct": 0.14, "score": 66, "trend": "neutral", "rsi": 50.8, "ema20": 2242.30, "vwap": 2243.90, "volume": 320000, "sector": "FMCG"},
    {"symbol": "ONGC", "name": "ONGC", "price": 274.80, "changePct": 1.94, "score": 78, "trend": "bullish", "rsi": 61.5, "ema20": 268.40, "vwap": 271.60, "volume": 18420000, "sector": "Energy"},
    {"symbol": "POWERGRID", "name": "Power Grid", "price": 328.65, "changePct": 0.72, "score": 72, "trend": "bullish", "rsi": 55.9, "ema20": 325.20, "vwap": 326.90, "volume": 8250000, "sector": "Utilities"},
    {"symbol": "NTPC", "name": "NTPC", "price": 372.40, "changePct": 1.35, "score": 76, "trend": "bullish", "rsi": 59.4, "ema20": 366.80, "vwap": 369.60, "volume": 12480000, "sector": "Utilities"},
    {"symbol": "TITAN", "name": "Titan Company", "price": 3452.80, "changePct": -0.34, "score": 65, "trend": "neutral", "rsi": 48.5, "ema20": 3465.20, "vwap": 3459.10, "volume": 620000, "sector": "Consumer"},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "price": 10842.60, "changePct": 0.92, "score": 75, "trend": "bullish", "rsi": 58.7, "ema20": 10745.30, "vwap": 10794.20, "volume": 180000, "sector": "Cement"},
    {"symbol": "M&M", "name": "Mahindra & Mahindra", "price": 2865.40, "changePct": 2.34, "score": 87, "trend": "bullish", "rsi": 67.8, "ema20": 2798.60, "vwap": 2832.15, "volume": 1420000, "sector": "Auto"},
    {"symbol": "JSWSTEEL", "name": "JSW Steel", "price": 918.35, "changePct": -1.42, "score": 52, "trend": "bearish", "rsi": 40.6, "ema20": 932.20, "vwap": 926.40, "volume": 4820000, "sector": "Metals"},
    {"symbol": "TATASTEEL", "name": "Tata Steel", "price": 148.75, "changePct": 0.34, "score": 61, "trend": "neutral", "rsi": 49.8, "ema20": 148.20, "vwap": 148.45, "volume": 32480000, "sector": "Metals"},
    {"symbol": "COALINDIA", "name": "Coal India", "price": 435.60, "changePct": 1.68, "score": 80, "trend": "bullish", "rsi": 62.1, "ema20": 428.40, "vwap": 432.10, "volume": 6820000, "sector": "Mining"},
    {"symbol": "HCLTECH", "name": "HCL Technologies", "price": 1682.30, "changePct": 0.94, "score": 78, "trend": "bullish", "rsi": 58.9, "ema20": 1668.20, "vwap": 1675.60, "volume": 2140000, "sector": "IT"},
    {"symbol": "TECHM", "name": "Tech Mahindra", "price": 1618.90, "changePct": -0.22, "score": 64, "trend": "neutral", "rsi": 49.2, "ema20": 1622.40, "vwap": 1620.60, "volume": 1820000, "sector": "IT"},
    {"symbol": "DRREDDY", "name": "Dr Reddys Labs", "price": 1284.55, "changePct": 1.24, "score": 75, "trend": "bullish", "rsi": 58.3, "ema20": 1268.90, "vwap": 1276.20, "volume": 1120000, "sector": "Pharma"},
    {"symbol": "CIPLA", "name": "Cipla", "price": 1512.75, "changePct": 0.68, "score": 71, "trend": "bullish", "rsi": 55.4, "ema20": 1502.10, "vwap": 1507.30, "volume": 1450000, "sector": "Pharma"},
    {"symbol": "GRASIM", "name": "Grasim Industries", "price": 2568.90, "changePct": -0.85, "score": 58, "trend": "bearish", "rsi": 43.6, "ema20": 2592.40, "vwap": 2580.20, "volume": 820000, "sector": "Cement"},
    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv", "price": 1685.30, "changePct": -1.24, "score": 55, "trend": "bearish", "rsi": 41.8, "ema20": 1706.20, "vwap": 1695.80, "volume": 1240000, "sector": "NBFC"},
    {"symbol": "EICHERMOT", "name": "Eicher Motors", "price": 4820.65, "changePct": 2.68, "score": 89, "trend": "bullish", "rsi": 69.4, "ema20": 4695.20, "vwap": 4756.30, "volume": 380000, "sector": "Auto"},
    {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp", "price": 4762.40, "changePct": 1.42, "score": 82, "trend": "bullish", "rsi": 63.7, "ema20": 4695.20, "vwap": 4728.60, "volume": 620000, "sector": "Auto"},
    {"symbol": "BRITANNIA", "name": "Britannia Industries", "price": 5148.90, "changePct": 0.24, "score": 67, "trend": "neutral", "rsi": 51.2, "ema20": 5136.40, "vwap": 5142.60, "volume": 280000, "sector": "FMCG"},
    {"symbol": "DIVISLAB", "name": "Divis Laboratories", "price": 5842.30, "changePct": 1.86, "score": 85, "trend": "bullish", "rsi": 66.5, "ema20": 5720.40, "vwap": 5781.20, "volume": 420000, "sector": "Pharma"},
    {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals", "price": 6754.20, "changePct": 0.92, "score": 76, "trend": "bullish", "rsi": 58.4, "ema20": 6685.30, "vwap": 6719.60, "volume": 320000, "sector": "Healthcare"},
]


STOCKS_BY_SYMBOL: Dict[str, Dict] = {s["symbol"]: s for s in STOCKS}


def _augment_with_intraday_fields() -> None:
    """Add ``day_high`` and ``avg_volume`` to every stock so the analysis
    engine has consistent inputs. Deterministic based on existing fields.
    """
    for s in STOCKS:
        change_pct = s["changePct"]
        price = s["price"]
        volume = s["volume"]
        rsi = s["rsi"]

        # Day high: momentum stocks (high RSI + strong close) sit near the
        # high; laggards and weak stocks sit further away. Only strong stocks
        # will trigger the 'within 1% of day high' rule.
        if rsi >= 68 and change_pct >= 1.5:
            high_mult = 1.003
        elif rsi >= 60 and change_pct >= 1.0:
            high_mult = 1.007
        elif change_pct >= 0.5:
            high_mult = 1.013
        elif change_pct >= 0:
            high_mult = 1.020
        else:
            high_mult = 1.025 + min(abs(change_pct) * 0.003, 0.02)
        s["day_high"] = round(price * high_mult, 2)

        # Average volume: strong bullish moves trade well above average,
        # neutral days sit near average, weak days trade below average
        # (which fails the volume rule).
        if change_pct >= 2.0 and rsi >= 60:
            avg_mult = 0.65
        elif change_pct >= 1.0:
            avg_mult = 0.85
        elif change_pct >= 0.3:
            avg_mult = 1.02
        elif change_pct >= 0:
            avg_mult = 1.10
        else:
            avg_mult = 1.25
        s["avg_volume"] = int(volume * avg_mult)


_augment_with_intraday_fields()


DEFAULT_WATCHLIST_SYMBOLS: List[str] = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "TATAMOTORS",
    "BHARTIARTL", "SBIN", "ITC", "MARUTI", "ADANIENT",
]


MARKET_INDICES: List[Dict] = [
    {"name": "Nifty 50", "symbol": "NIFTY", "value": 22648.20, "changePct": 0.68},
    {"name": "Bank Nifty", "symbol": "BANKNIFTY", "value": 48521.35, "changePct": 0.42},
    {"name": "India VIX", "symbol": "INDIAVIX", "value": 13.85, "changePct": -2.14},
]


TODAYS_FOCUS: List[Dict] = [
    {
        "key": "bestSetup",
        "label": "Best Setup",
        "symbol": "RELIANCE",
        "name": "Reliance Industries",
        "note": "Cup & handle confirmed. Entry above 2940 with tight stop at 2905.",
        "changePct": 1.24,
    },
    {
        "key": "momentum",
        "label": "Momentum Stock",
        "symbol": "TATAMOTORS",
        "name": "Tata Motors",
        "note": "RSI 72 with sustained volume. Momentum leader in auto sector.",
        "changePct": 3.24,
    },
    {
        "key": "breakout",
        "label": "Watch for Breakout",
        "symbol": "ADANIENT",
        "name": "Adani Enterprises",
        "note": "Pressing against 2900 resistance. Break with volume targets 3050.",
        "changePct": 4.12,
    },
    {
        "key": "avoid",
        "label": "Avoid Today",
        "symbol": "ASIANPAINT",
        "name": "Asian Paints",
        "note": "Breakdown below 20-EMA. RSI 38 signals continued weakness.",
        "changePct": -1.68,
    },
]


OPPORTUNITIES: List[Dict] = [
    {"symbol": "ADANIENT",  "score": 94, "reason": "Breakout above 20-day EMA on strong volume"},
    {"symbol": "TATAMOTORS", "score": 92, "reason": "RSI momentum crossing 70 with volume surge"},
    {"symbol": "BHARTIARTL", "score": 90, "reason": "Bullish flag pattern, target 1680"},
    {"symbol": "EICHERMOT", "score": 89, "reason": "Higher highs, sector rotation into auto"},
    {"symbol": "RELIANCE",  "score": 88, "reason": "VWAP support holding, upward channel"},
    {"symbol": "M&M",       "score": 87, "reason": "Consolidation breakout with positive divergence"},
    {"symbol": "MARUTI",    "score": 86, "reason": "Golden cross confirmed on daily chart"},
    {"symbol": "DIVISLAB",  "score": 85, "reason": "Pharma rally, RSI 66 with room to run"},
    {"symbol": "INFY",      "score": 84, "reason": "Above VWAP, IT sector strength returning"},
    {"symbol": "AXISBANK",  "score": 81, "reason": "Bank Nifty leadership, cup & handle pattern"},
]


INSIGHTS: Dict[str, Dict] = {
    "RELIANCE": {
        "support": 2890,
        "resistance": 2985,
        "aiInsight": "Reliance is trading above its 20-EMA with expanding volume. Momentum indicators align bullish; look for continuation above 2940 for a swing to 2985. Manage risk with a stop below 2890 VWAP support.",
        "series": [
            {"t": "09:15", "v": 2905.2}, {"t": "09:45", "v": 2912.5},
            {"t": "10:15", "v": 2908.9}, {"t": "10:45", "v": 2918.6},
            {"t": "11:15", "v": 2921.1}, {"t": "11:45", "v": 2915.4},
            {"t": "12:15", "v": 2920.8}, {"t": "12:45", "v": 2927.3},
            {"t": "13:15", "v": 2925.6}, {"t": "13:45", "v": 2931.2},
            {"t": "14:15", "v": 2929.4}, {"t": "14:45", "v": 2933.9},
            {"t": "15:15", "v": 2934.55},
        ],
    },
    "TATAMOTORS": {
        "support": 940,
        "resistance": 985,
        "aiInsight": "Tata Motors is in a strong up-trend with RSI at 72. Rising volume confirms conviction. Watch for a shallow pullback to 960 as re-entry; invalidation below 940.",
        "series": [
            {"t": "09:15", "v": 942.5}, {"t": "09:45", "v": 948.2},
            {"t": "10:15", "v": 955.6}, {"t": "10:45", "v": 951.4},
            {"t": "11:15", "v": 958.9}, {"t": "11:45", "v": 963.1},
            {"t": "12:15", "v": 960.7}, {"t": "12:45", "v": 966.3},
            {"t": "13:15", "v": 969.8}, {"t": "13:45", "v": 968.4},
            {"t": "14:15", "v": 971.2}, {"t": "14:45", "v": 972.9},
            {"t": "15:15", "v": 972.65},
        ],
    },
    "ADANIENT": {
        "support": 2820,
        "resistance": 2920,
        "aiInsight": "ADANIENT is testing multi-month resistance at 2920 with expanding range. A decisive close above 2920 opens 3050. Below 2820 the setup invalidates.",
        "series": [
            {"t": "09:15", "v": 2782.1}, {"t": "09:45", "v": 2801.4},
            {"t": "10:15", "v": 2818.6}, {"t": "10:45", "v": 2832.2},
            {"t": "11:15", "v": 2841.8}, {"t": "11:45", "v": 2855.6},
            {"t": "12:15", "v": 2864.3}, {"t": "12:45", "v": 2872.5},
            {"t": "13:15", "v": 2880.9}, {"t": "13:45", "v": 2885.7},
            {"t": "14:15", "v": 2891.4}, {"t": "14:45", "v": 2894.2},
            {"t": "15:15", "v": 2895.40},
        ],
    },
    "ASIANPAINT": {
        "support": 2790,
        "resistance": 2870,
        "aiInsight": "ASIANPAINT lost its 20-EMA with RSI at 38. Rally attempts into 2870 are selling opportunities. Below 2790 the next demand zone sits at 2710.",
        "series": [
            {"t": "09:15", "v": 2865.4}, {"t": "09:45", "v": 2858.2},
            {"t": "10:15", "v": 2851.6}, {"t": "10:45", "v": 2844.9},
            {"t": "11:15", "v": 2836.3}, {"t": "11:45", "v": 2828.7},
            {"t": "12:15", "v": 2831.2}, {"t": "12:45", "v": 2824.5},
            {"t": "13:15", "v": 2819.1}, {"t": "13:45", "v": 2822.8},
            {"t": "14:15", "v": 2817.4}, {"t": "14:45", "v": 2815.6},
            {"t": "15:15", "v": 2814.55},
        ],
    },
}


def synthesize_insight(symbol: str) -> Dict:
    """Generate a plausible chart/insight for symbols without curated data."""
    import math

    stock = STOCKS_BY_SYMBOL.get(symbol)
    base_price = stock["price"] if stock else 1000.0
    trend = stock["trend"] if stock else "neutral"
    support = round(base_price * 0.985, 2)
    resistance = round(base_price * 1.02, 2)
    start = base_price * 0.99
    times = [
        "09:15", "09:45", "10:15", "10:45", "11:15", "11:45",
        "12:15", "12:45", "13:15", "13:45", "14:15", "14:45", "15:15",
    ]
    series = []
    n = len(times) - 1
    for i, t in enumerate(times):
        progress = i / n
        drift = (base_price - start) * progress
        noise = math.sin(i * 1.3 + len(symbol)) * base_price * 0.0025
        series.append({"t": t, "v": round(start + drift + noise, 2)})

    trend_label = {
        "bullish": "constructive",
        "bearish": "weak",
    }.get(trend, "range-bound")

    return {
        "support": support,
        "resistance": resistance,
        "aiInsight": (
            f"{symbol} is currently {trend_label}. Price is trading near "
            f"{base_price:,.2f} with support at {support:,.2f} and resistance "
            f"at {resistance:,.2f}. Wait for confirmation before initiating a position."
        ),
        "series": series,
    }
