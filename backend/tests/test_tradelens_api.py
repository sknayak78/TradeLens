"""TradeLens backend API tests (pytest)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lens-trading-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# --- Health ---
def test_health(s):
    r = s.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


# --- Watchlist ---
def test_watchlist_list_enriched(s):
    r = s.get(f"{API}/watchlist", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) >= 5
    row = data[0]
    for k in ["symbol", "name", "price", "rsi", "ema20", "vwap", "score", "trend", "changePct"]:
        assert k in row, f"missing {k}"


def test_watchlist_add_and_duplicate(s):
    # cleanup first
    s.delete(f"{API}/watchlist/WIPRO", timeout=15)
    r = s.post(f"{API}/watchlist", json={"symbol": "WIPRO"}, timeout=15)
    assert r.status_code in (200, 201), r.text
    # duplicate
    r2 = s.post(f"{API}/watchlist", json={"symbol": "WIPRO"}, timeout=15)
    assert r2.status_code == 409, r2.text
    # verify in list
    lst = s.get(f"{API}/watchlist", timeout=15).json()
    assert any(x["symbol"] == "WIPRO" for x in lst)


def test_watchlist_delete(s):
    # ensure exists
    s.post(f"{API}/watchlist", json={"symbol": "WIPRO"}, timeout=15)
    r = s.delete(f"{API}/watchlist/WIPRO", timeout=15)
    assert r.status_code == 204
    r2 = s.delete(f"{API}/watchlist/WIPRO", timeout=15)
    assert r2.status_code == 404


# --- Trades ---
def test_trades_crud(s):
    payload = {
        "symbol": "RELIANCE",
        "trade_date": "2026-01-15T00:00:00",
        "entry_price": 100,
        "exit_price": 110,
        "quantity": 10,
        "notes": "TEST_trade",
    }
    r = s.post(f"{API}/trades", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert "id" in body and "pnl" in body and "side" in body
    assert body["side"] == "LONG"
    assert body["pnl"] == pytest.approx((110 - 100) * 10, rel=1e-3)
    tid = body["id"]

    lst = s.get(f"{API}/trades", timeout=15).json()
    assert isinstance(lst, list) and any(t["id"] == tid for t in lst)
    # newest first: created id should be first (or within top for same date)
    ids = [t["id"] for t in lst]
    assert tid in ids

    dr = s.delete(f"{API}/trades/{tid}", timeout=15)
    assert dr.status_code == 204
    dr2 = s.delete(f"{API}/trades/{tid}", timeout=15)
    assert dr2.status_code == 404


def test_trade_short_side(s):
    r = s.post(f"{API}/trades", json={
        "symbol": "TCS", "trade_date": "2026-01-15T00:00:00",
        "entry_price": 200, "exit_price": 180, "quantity": 5, "notes": "TEST_short"
    }, timeout=15).json()
    assert r["side"] == "SHORT"
    s.delete(f"{API}/trades/{r['id']}", timeout=15)


# --- Settings ---
def test_settings_get_and_put(s):
    r = s.get(f"{API}/settings", timeout=15)
    assert r.status_code == 200
    data = r.json()
    for k in ["capital", "risk_per_trade", "preferred_timeframe"]:
        assert k in data
    # update
    new = {"capital": 500000, "risk_per_trade": 1.5, "preferred_timeframe": "1W"}
    r2 = s.put(f"{API}/settings", json=new, timeout=15)
    assert r2.status_code == 200
    updated = r2.json()
    assert updated["capital"] == 500000
    assert updated["preferred_timeframe"] == "1W"
    # persistence
    r3 = s.get(f"{API}/settings", timeout=15).json()
    assert r3["capital"] == 500000
    assert r3["preferred_timeframe"] == "1W"


# --- Market ---
def test_market_summary(s):
    r = s.get(f"{API}/market-summary", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert len(d["indices"]) == 3
    assert len(d["todaysFocus"]) == 4
    assert d["status"] == "open"
    assert "asOf" in d


def test_opportunities(s):
    r = s.get(f"{API}/opportunities", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 10
    for k in ["symbol", "name", "strengthScore", "trend", "price", "changePct", "reason"]:
        assert k in data[0], f"missing {k}"


def test_stock_detail_curated(s):
    r = s.get(f"{API}/stock/RELIANCE", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert len(d["series"]) == 13
    assert "support" in d and "resistance" in d


def test_stock_detail_synth(s):
    r = s.get(f"{API}/stock/TCS", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert len(d["series"]) == 13


def test_stock_detail_404(s):
    r = s.get(f"{API}/stock/NOTREAL", timeout=15)
    assert r.status_code == 404


def test_stocks_search(s):
    r = s.get(f"{API}/stocks?q=ADAN", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert any(x["symbol"] == "ADANIENT" for x in data)


# --- Analysis Engine (unit) ---
def test_analysis_service_unit():
    """Test StockAnalysisService.analyse directly on RELIANCE synthetic snapshot."""
    import sys, os as _os
    sys.path.insert(0, "/app/backend")
    from analysis.service import service as svc
    from seed_data import STOCKS_BY_SYMBOL

    stock = STOCKS_BY_SYMBOL["RELIANCE"]
    a = svc.analyse(stock)

    assert a.trend in ("bullish", "bearish", "neutral")
    assert 0 <= a.strength_score <= 100
    assert a.stars in (2, 3, 4, 5)
    assert isinstance(a.classification, str) and a.classification
    assert a.trade_setup in ("Momentum", "Breakout", "Pullback", "Trend Continuation", "Consolidation")
    assert a.risk_level in ("Low", "Medium", "High")
    assert a.suggested_action in ("Watch", "Buy on Breakout", "Wait", "Avoid")
    words = a.insight.split()
    assert len(words) <= 60
    low = a.insight.lower()
    for banned in ("guaranteed", "certain", "sure shot"):
        assert banned not in low, f"insight contains banned word '{banned}': {a.insight}"


def test_analysis_no_llm_imports():
    """Ensure the analysis module doesn't import LLM libs / make network calls."""
    import pathlib
    src = pathlib.Path("/app/backend/analysis").rglob("*.py")
    banned = ("openai", "anthropic", "requests", "httpx", "urllib", "litellm", "emergentintegrations")
    for f in src:
        text = f.read_text().lower()
        for b in banned:
            assert b not in text, f"{f} contains banned import '{b}'"


# --- Rankings ---
def test_rankings_shape_and_order(s):
    r = s.get(f"{API}/opportunities", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 10
    required = ["rank", "symbol", "name", "price", "changePct", "strengthScore",
                "stars", "classification", "trend", "tradeSetup", "riskLevel",
                "suggestedAction", "insight", "reason"]
    for i, row in enumerate(data):
        for k in required:
            assert k in row, f"row {i} missing {k}"
        assert row["rank"] == i + 1
        assert 0 <= row["strengthScore"] <= 100
        assert row["stars"] in (2, 3, 4, 5)
        assert row["tradeSetup"] in ("Momentum", "Breakout", "Pullback", "Trend Continuation", "Consolidation")
        assert row["riskLevel"] in ("Low", "Medium", "High")
        assert row["suggestedAction"] in ("Watch", "Buy on Breakout", "Wait", "Avoid")
        low = row["insight"].lower()
        for banned in ("guaranteed", "certain", "sure shot"):
            assert banned not in low
    # scores descending
    scores = [row["strengthScore"] for row in data]
    assert scores == sorted(scores, reverse=True), f"not descending: {scores}"


# --- Stock detail analysis fields ---
@pytest.mark.parametrize("sym", ["RELIANCE", "TCS"])
def test_stock_detail_has_analysis_fields(s, sym):
    r = s.get(f"{API}/stock/{sym}", timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ["strengthScore", "stars", "classification", "tradeSetup",
              "riskLevel", "suggestedAction", "insight"]:
        assert k in d, f"{sym} missing {k}"
    assert 0 <= d["strengthScore"] <= 100
    assert d["stars"] in (2, 3, 4, 5)
    assert d["tradeSetup"] in ("Momentum", "Breakout", "Pullback", "Trend Continuation", "Consolidation")
    assert d["riskLevel"] in ("Low", "Medium", "High")
    assert d["suggestedAction"] in ("Watch", "Buy on Breakout", "Wait", "Avoid")


# --- Watchlist analysis enrichment ---
def test_watchlist_has_analysis_fields(s):
    r = s.get(f"{API}/watchlist", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    row = data[0]
    for k in ["strengthScore", "stars", "tradeSetup", "riskLevel", "suggestedAction",
              "symbol", "name", "price", "rsi", "ema20", "vwap", "score", "trend", "changePct"]:
        assert k in row, f"missing {k}"
