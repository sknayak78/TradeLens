#!/usr/bin/env python3
"""Download the Upstox NSE_EQ instrument master and produce the release artifact.

MD-03 deployment gate: the bundled ``backend/data/upstox_instruments.json`` must
be a *validated* full ``NSE_EQ`` release artifact (1500+ records, correct shape,
no duplicates) before it can be committed/deployed.  This script generates the
artifact from the official Upstox master; the operator runs it at release time
and commits the result, then ``scripts/validate_upstox_instruments.py`` gates
any later deployment.

Usage:
    scripts/fetch_upstox_instruments.py [--output PATH] [--input LOCAL_MASTER_JSON]
                                         [--source-version VERSION]

    --input            Fetch from a local copy of the Upstox NSE_EQ master JSON
                       instead of the network; useful for CI sandboxes.
    --output           Destination file (default backend/data/upstox_instruments.json).
    --source-version   Version tag recorded in the artifact metadata
                       (default: timestamp + asset URL used).

Exit code is non-zero if the artifact cannot be produced or fails validation.
"""
from __future__ import annotations

import argparse
import gzip
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger("tradelens.tools.fetch_upstox_instruments")

_ASSET_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"


def _default_output() -> Path:
    return ROOT_DIR / "backend" / "data" / "upstox_instruments.json"


def _records_from_raw(payload: Any) -> list[dict[str, Any]]:
    """Normalize an Upstox NSE_EQ master payload (array or {"data": [...]})."""
    if isinstance(payload, dict):
        payload = payload.get("data", payload.get("instruments", []))
    if not isinstance(payload, list):
        raise ValueError("Upstox master payload is neither an array nor an object with 'data'")
    records: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        instrument_key = str(item.get("instrument_key") or "").strip()
        if not instrument_key.startswith("NSE_EQ|"):
            continue
        instrument_type = str(item.get("instrument_type") or "").strip().upper()
        if instrument_type and instrument_type != "EQ":
            continue
        symbol = str(item.get("trading_symbol") or item.get("symbol") or "").strip()
        name = str(item.get("name") or "").strip()
        if not symbol or not instrument_key:
            logger.warning("skipping master record without symbol/instrument_key: %r", item)
            continue
        records.append({"symbol": symbol, "name": name, "instrument_key": instrument_key})
    return records


def _fetch_remote() -> list[dict[str, Any]]:
    import requests

    try:
        logger.info("fetching %s", _ASSET_URL)
        response = requests.get(_ASSET_URL, timeout=60)
        response.raise_for_status()
        body = response.content
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        return _records_from_raw(json.loads(body))
    except Exception as exc:
        raise RuntimeError(f"official Upstox NSE instrument master fetch failed: {exc}") from exc


def _write_atomic(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(output.parent), prefix=".upstox_master.", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, output)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--source-version", default="")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    output = args.output or _default_output()
    version = args.source_version or (
        f"asset/{_ASSET_URL} filter=instrument_type=EQ "
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    if args.input is not None:
        logger.info("reading local master %s", args.input)
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        records = _records_from_raw(payload)
    else:
        records = _fetch_remote()

    if not records:
        raise SystemExit("no NSE_EQ instrument records were produced; aborting")

    sys.path.insert(0, str(ROOT_DIR / "backend"))

    from services.providers.upstox_instrument_source import (
        build_master_payload,
        validate_instrument_master,
    )

    artifact = build_master_payload(records, version=version)
    try:
        validate_instrument_master(artifact)
    except Exception as exc:
        logger.error("produced artifact failed validation: %s", exc)
        raise SystemExit(1) from exc
    _write_atomic(artifact, output)
    count = artifact["metadata"]["count"]
    logger.info("wrote validated NSE_EQ master (%d records) to %s", count, output)
    print(f"validated master written: {output} ({count} NSE_EQ records)")
    print("deploy gate: scripts/validate_upstox_instruments.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
