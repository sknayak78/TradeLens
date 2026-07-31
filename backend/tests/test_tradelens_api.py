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
    assert isinstance(data, list) and len(data) >= 10
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
    for k in ["symbol", "name", "score", "trend", "price", "changePct", "reason"]:
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
