"""Upstox instrument-master loading and validation.

MD-03 wires the Upstox provider to a versioned, bundled ``NSE_EQ`` instrument
master instead of a hand-maintained environment mapping.  The JSON payload is
generated at release time by ``scripts/fetch_upstox_instruments.py`` and must
pass ``validate_instrument_master`` — schema, ``NSE_EQ`` scope, required fields,
uniqueness, record count, and source metadata — before it may be deployed.

The bundled file under ``backend/data/`` is the production release artifact;
validation refuses a missing, malformed, placeholder, or undersized file. The
test fixture under ``backend/tests/fixtures/`` is physically separate and is
the only sample the test-suite exercises.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Mapping

logger = logging.getLogger("tradelens.market_data.upstox.instruments")

_MASTER_PATH_ENV = "UPSTOX_INSTRUMENT_MASTER"
_DEFAULT_MASTER_NAME = "upstox_instruments.json"
#: Deployment safety threshold.  It is *not* the sole validity criterion: the
#: payload must also satisfy schema, scope, required-field, uniqueness, count
#: and source-metadata checks.
_MIN_NSE_EQ_COUNT = 1500

_REQUIRED_METADATA_FIELDS = (
    "scope",
    "count",
    "generated_at",
    "generated_by",
    "source_version",
)
_REQUIRED_RECORD_FIELDS = ("symbol", "name", "instrument_key")


class UpstoxInstrumentMasterError(RuntimeError):
    """Raised when an instrument master is missing or fails validation."""


def default_master_path() -> Path:
    """Return the bundled production master location (``backend/data/``)."""
    return Path(__file__).resolve().parents[2] / "data" / _DEFAULT_MASTER_NAME


def _resolve_master_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path)
    override = os.environ.get(_MASTER_PATH_ENV, "").strip()
    if override:
        return Path(override)
    return default_master_path()


def _read_payload(path: Path) -> Any:
    if not path.exists():
        raise UpstoxInstrumentMasterError(
            f"Upstox instrument master not found at {path}; run "
            f"scripts/fetch_upstox_instruments.py at release, or point "
            f"{_MASTER_PATH_ENV} at a validated file"
        )
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise UpstoxInstrumentMasterError(
            f"Upstox instrument master at {path} is not valid JSON: {exc}"
        ) from exc


def _normalized(symbol: object) -> str:
    return str(symbol).strip().upper()


def _require_metadata(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise UpstoxInstrumentMasterError(
            "instrument master must be a JSON object with 'metadata' and 'instruments'"
        )
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise UpstoxInstrumentMasterError("instrument master is missing the 'metadata' object")
    for field in _REQUIRED_METADATA_FIELDS:
        value = metadata.get(field)
        if value is None or str(value).strip() == "":
            raise UpstoxInstrumentMasterError(
                f"instrument master metadata is missing required field '{field}'"
            )
    if _normalized(metadata.get("scope")) != "NSE_EQ":
        raise UpstoxInstrumentMasterError(
            f"instrument master scope must be NSE_EQ, got {metadata.get('scope')!r}"
        )
    generated_at = str(metadata["generated_at"]).strip()
    try:
        parsed_generated_at = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UpstoxInstrumentMasterError(
            f"instrument master metadata 'generated_at' is not ISO-8601: {generated_at!r}"
        ) from exc
    if parsed_generated_at.tzinfo is None:
        raise UpstoxInstrumentMasterError(
            "instrument master metadata 'generated_at' must include a timezone"
        )
    source_version = str(metadata["source_version"]).strip().lower()
    if "placeholder" in source_version:
        raise UpstoxInstrumentMasterError(
            "instrument master metadata 'source_version' cannot identify a placeholder"
        )
    return metadata


def validate_instrument_master(
    payload: Any,
    *,
    min_count: int = _MIN_NSE_EQ_COUNT,
) -> dict[str, Any]:
    """Validate a master payload and return its metadata, or raise.

    Checks, in order: JSON object shape, metadata fields and ``NSE_EQ`` scope,
    required per-record fields, per-record scope prefix, symbol/key uniqueness,
    count/records consistency, and the deployment count threshold.
    """
    metadata = _require_metadata(payload)
    records = payload.get("instruments")
    if not isinstance(records, list):
        raise UpstoxInstrumentMasterError(
            "instrument master is missing the 'instruments' list"
        )

    seen_symbols: set[str] = set()
    seen_keys: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise UpstoxInstrumentMasterError(f"instruments[{index}] is not a JSON object")
        for field in _REQUIRED_RECORD_FIELDS:
            value = record.get(field)
            if value is None or str(value).strip() == "":
                raise UpstoxInstrumentMasterError(
                    f"instruments[{index}] is missing required field '{field}'"
                )
        symbol = _normalized(record["symbol"])
        instrument_key = str(record["instrument_key"]).strip()
        if not instrument_key.startswith("NSE_EQ|"):
            raise UpstoxInstrumentMasterError(
                f"instruments[{index}] instrument_key {instrument_key!r} is not an NSE_EQ key"
            )
        if symbol in seen_symbols:
            raise UpstoxInstrumentMasterError(f"instrument master has a duplicate symbol {symbol}")
        if instrument_key in seen_keys:
            raise UpstoxInstrumentMasterError(
                f"instrument master has a duplicate instrument_key {instrument_key}"
            )
        seen_symbols.add(symbol)
        seen_keys.add(instrument_key)

    try:
        declared_count = int(metadata["count"])
    except (TypeError, ValueError) as exc:
        raise UpstoxInstrumentMasterError(
            f"instrument master metadata 'count' is not an integer: {metadata['count']!r}"
        ) from exc
    if declared_count != len(records):
        raise UpstoxInstrumentMasterError(
            f"instrument master count mismatch: metadata says {declared_count}, "
            f"found {len(records)} records"
        )
    if len(records) < min_count:
        raise UpstoxInstrumentMasterError(
            f"instrument master has {len(records)} records, below the deployment "
            f"safety threshold of {min_count}; refusing to deploy a placeholder or sample"
        )
    logger.info(
        "upstox.instrument_master_validated count=%d scope=%s version=%s",
        len(records),
        metadata.get("scope"),
        metadata.get("source_version"),
    )
    return metadata


def load_instrument_master(path: str | Path | None = None) -> Mapping[str, str]:
    """Load a validated master and return a symbol -> instrument_key mapping.

    Raises :class:`UpstoxInstrumentMasterError` (fail-fast) when the master is
    missing, malformed, unscoped, or below the deployment threshold.
    """
    resolved = _resolve_master_path(path)
    payload = _read_payload(resolved)
    validate_instrument_master(payload)
    return {
        _normalized(record["symbol"]): str(record["instrument_key"]).strip()
        for record in payload["instruments"]
    }


def validate_instrument_master_file(
    path: str | Path | None = None,
    *,
    min_count: int = _MIN_NSE_EQ_COUNT,
) -> dict[str, Any]:
    """Validate the master file directly on disk (deploy-gate entry point)."""
    resolved = _resolve_master_path(path)
    payload = _read_payload(resolved)
    return validate_instrument_master(payload, min_count=min_count)


def build_master_payload(records: list[Mapping[str, Any]], *, version: str) -> dict[str, Any]:
    """Compose a normalized master payload from normalized records.

    Used by ``scripts/fetch_upstox_instruments.py`` to write the release
    artifact so the on-disk shape always matches the loader's expectations.
    """
    normalized_records = [
        {
            "symbol": _normalized(record["symbol"]),
            "name": str(record["name"]).strip(),
            "instrument_key": str(record["instrument_key"]).strip(),
        }
        for record in records
    ]
    return {
        "metadata": {
            "scope": "NSE_EQ",
            "count": len(normalized_records),
            "generated_by": "tradelens/scripts/fetch_upstox_instruments.py",
            "generated_at": _now_iso(),
            "source_version": str(version).strip(),
        },
        "instruments": normalized_records,
    }


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
