#!/usr/bin/env python3
"""Deploy gate for the Upstox NSE_EQ instrument master.

MD-03 fails fast at startup when ``MARKET_DATA_PROVIDER=upstox`` is used with
an invalid master, but this script is the *release-time* gate: it is run against
the bundled/committed ``backend/data/upstox_instruments.json`` before deploy and
exits non-zero unless the payload is a validated full ``NSE_EQ`` artifact
(1500+ records).  The placeholder committed in the repo (count 0) intentionally
fails this gate so a sample can never ship.

Usage:
    scripts/validate_upstox_instruments.py [--path PATH] [--min-count N]

    --path        Master file to validate (default backend/data/upstox_instruments.json).
    --min-count   Deployment threshold (default 1500).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=None)
    parser.add_argument("--min-count", type=int, default=1500)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    sys.path.insert(0, str(ROOT_DIR / "backend"))

    from services.providers.upstox_instrument_source import (
        UpstoxInstrumentMasterError,
        validate_instrument_master_file,
    )

    path = args.path or (ROOT_DIR / "backend" / "data" / "upstox_instruments.json")
    try:
        metadata = validate_instrument_master_file(path, min_count=args.min_count)
    except UpstoxInstrumentMasterError as exc:
        print(f"FAIL: {path}: {exc}")
        return 1

    print(
        f"OK: {path} ({metadata['count']} NSE_EQ records, "
        f"source {metadata['source_version']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())