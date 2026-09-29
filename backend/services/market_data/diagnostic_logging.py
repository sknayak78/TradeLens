"""Durable provider-diagnostic logging for market-data provider events.

Observability only.  This module changes no provider, fallback, retry, cache, or
screening behavior; it only makes the *existing* ``MarketDataService`` chain
events durably inspectable after the process exits.

Why this exists: the application configures logging through
``logging.basicConfig`` in ``server.py``, which writes only to the interactive
terminal's scrollback.  A completed ``/api/opportunities`` run therefore leaves
no durable record of which provider actually served each symbol, how many
attempts were made, or whether any attempt was rate limited - the Upstox-vs-
Yahoo split of a discovery run cannot be reconstructed afterwards.

Design constraints:
* File path is derived from the backend package location, never a hard-coded
  machine-specific absolute path.
* Handlers are attached to the existing provider loggers, so events already
  emitted by the service chain are captured without re-emitting or duplicating
  them, and console output is untouched.
* Configuration is idempotent: ``server.py`` reloads via uvicorn, and repeated
  imports must not stack duplicate handlers.
* Secrets never reach the file.  Every value passed through :func:`redact` is
  scrubbed of bearer tokens, ``Authorization`` headers, and token-like query
  parameters, and provider response payloads are never logged.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import re
import threading
from pathlib import Path
from typing import Any

#: Loggers whose records are persisted.  ``tradelens.market_data`` is a parent
#: of the Upstox and instrument-master loggers, so child records reach this
#: handler through normal propagation.
DIAGNOSTIC_LOGGERS = (
    "tradelens.market_data",
    "tradelens.market_scanner",
)

#: Log file name, relative to ``backend/logs``.
LOG_FILENAME = "market_data_provider.log"

#: Bounded rotation: 8 MiB per file, 3 backups (24 MiB worst case).
_MAX_BYTES = 8 * 1024 * 1024
_BACKUP_COUNT = 3

_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

#: Fields whose value may be arbitrarily large (an upstream error body echoed
#: into an exception message).  Only these are length-bounded, and only
#: *before* the record is serialized.
_BOUNDED_FIELDS = ("error_message",)

#: Maximum length of a bounded field.
_MAX_BOUNDED_FIELD = 500

_lock = threading.Lock()
_configured_paths: set[str] = set()


class _RedactingFormatter(logging.Formatter):
    """Formatter that scrubs credentials and omits tracebacks from the file.

    The provider chain logs failures with ``exc_info=True`` so the *console* keeps
    a traceback for interactive debugging.  Those tracebacks embed the original
    exception message verbatim, which can contain a bearer token or a
    token-bearing URL.  Redacting the already-formatted record is therefore not
    sufficient - the traceback has to be dropped as well, since the structured
    ``error_class`` / ``error_message`` fields on the event already carry the
    classified, redacted failure.

    Truncation is applied to the *individual* oversized field, never to the
    assembled line.  An earlier version redacted the whole rendered record,
    which length-limited the entire JSON payload and silently discarded the
    fields serialized after ``error_message`` (``http_status``,
    ``rate_limited``, ``provider``, ``operation``, ``symbol``), leaving
    unparseable JSON.  Every diagnostic record is now guaranteed to be valid
    JSON with all of its structured fields intact.

    Console output is unaffected: this formatter is installed only on the
    diagnostic file handler.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Suppress the traceback for the file only.  The event itself already
        # carries the redacted error summary.
        exc_info, exc_text = record.exc_info, record.exc_text
        record.exc_info = None
        record.exc_text = None
        try:
            return super().format(record)
        finally:
            record.exc_info, record.exc_text = exc_info, exc_text

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        """Sanitize the message, preserving the structure of JSON events."""
        return _sanitize_message(record.getMessage())


def diagnostic_log_path() -> Path:
    """Return ``backend/logs/market_data_provider.log``.

    Derived from this module's location so it is correct regardless of the
    current working directory and contains no machine-specific literal.
    """
    backend_root = Path(__file__).resolve().parent.parent.parent
    return backend_root / "logs" / LOG_FILENAME


def configure_diagnostic_logging(*, log_path: Path | None = None) -> Path:
    """Attach a rotating file handler to the provider loggers (idempotent).

    Returns the active log path.  Calling this more than once - including
    across a uvicorn reload - never installs a second handler for the same file.
    """
    target = Path(log_path) if log_path is not None else diagnostic_log_path()
    resolved = str(target.resolve())
    with _lock:
        if resolved in _configured_paths:
            return target
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            handler: logging.Handler = logging.handlers.RotatingFileHandler(
                target,
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
        except OSError:
            # A diagnostic log must never prevent the application from starting.
            return target
        handler.setFormatter(_RedactingFormatter(_FORMAT))
        for name in DIAGNOSTIC_LOGGERS:
            logger = logging.getLogger(name)
            # Provider success events are emitted at INFO.  ``basicConfig`` in
            # server.py already sets INFO on the root logger, so this is a
            # no-op in production; stating it explicitly keeps the file useful
            # when the root logger is configured at a higher level (e.g. under a
            # test runner) and the handler would otherwise receive nothing.
            if logger.level == logging.NOTSET or logger.level > logging.INFO:
                logger.setLevel(logging.INFO)
            if not any(
                isinstance(existing, logging.handlers.RotatingFileHandler)
                and str(getattr(existing, "baseFilename", "")) == resolved
                for existing in logger.handlers
            ):
                logger.addHandler(handler)
        # The provider events are emitted at INFO on these loggers; do not rely
        # on a global level change, and never propagate to the root handler
        # twice for the same record.
        _configured_paths.add(resolved)
    return target


# --- Secret redaction ---------------------------------------------------

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Bearer / Basic credentials in any message.
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._\-=]+"), r"\1 [REDACTED]"),
    # Authorization header assignment.
    (
        re.compile(r"(?i)(authorization\"?\s*[:=]\s*\"?)[^\",\s}]+"),
        r"\1[REDACTED]",
    ),
    # Token-like query parameters or JSON fields.
    (
        re.compile(
            r"(?i)\b(access_token|accessToken|api_key|apiKey|token|secret|"
            r"password|cookie|set-cookie)\b(\"?\s*[:=]\s*\"?)[^\",\s}&}]+"
        ),
        r"\1\2[REDACTED]",
    ),
)


def redact(value: Any, *, _depth: int = 0) -> Any:
    """Recursively scrub credential-like substrings from a value.

    Used on every free-text field that reaches the diagnostic log, so an
    exception message containing a URL with a token parameter cannot leak it.

    This scrubs *secrets only*; it deliberately does not impose a length limit,
    so applying it to a whole serialized record cannot destroy structure.  Length
    bounding is handled separately by :func:`_sanitize_message` for the specific
    fields that can grow arbitrarily large.
    """
    if _depth > 6:
        return "[TRUNCATED]"
    if isinstance(value, str):
        text = value
        for pattern, replacement in _REDACTIONS:
            text = pattern.sub(replacement, text)
        return text
    if isinstance(value, dict):
        return {
            redact(key, _depth=_depth + 1): redact(item, _depth=_depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item, _depth=_depth + 1) for item in value]
    return value


def _bound_text(text: str, limit: int = _MAX_BOUNDED_FIELD) -> str:
    if len(text) > limit:
        return text[:limit] + "...[TRUNCATED]"
    return text


def _sanitize_message(message: str) -> str:
    """Prepare a log message for the diagnostic file.

    For a structured (JSON) event: parse it, bound only the fields that can grow
    without limit, scrub secrets from every value, and re-serialize.  Every
    structured field is therefore guaranteed to survive intact and the output is
    always valid JSON.

    For a plain-text message: scrub secrets, then bound the whole line, since
    there is no structure to preserve.
    """
    try:
        payload = json.loads(message)
    except (json.JSONDecodeError, ValueError):
        return _bound_text(redact(message))
    if not isinstance(payload, dict):
        return _bound_text(redact(message))

    cleaned = redact(payload)
    for field in _BOUNDED_FIELDS:
        value = cleaned.get(field)
        if isinstance(value, str):
            cleaned[field] = _bound_text(value)
        elif isinstance(value, (dict, list)):
            cleaned[field] = _bound_text(json.dumps(value, sort_keys=True))
    return json.dumps(cleaned, sort_keys=True)


# --- Error classification ----------------------------------------------

_HTTP_ERROR_MARKERS = (
    "HTTPError",
    "Too Many Requests",
    "Client Error",
    "Server Error",
)


def _is_http_error(exc: BaseException | None) -> bool:
    """Whether the exception, or anything in its cause chain, is an HTTP error."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ in _HTTP_ERROR_MARKERS:
            return True
        if getattr(current, "response", None) is not None and (
            http_status_from_error(current) is not None
        ):
            return True
        current = current.__cause__ or current.__context__
    return False


def http_status_from_error(exc: BaseException | None) -> int | None:
    """Best-effort HTTP status for an exception, walking the ``__cause__`` chain.

    Providers wrap transport failures with ``raise ... from exc``, so the
    original ``requests.HTTPError`` (and its ``response.status_code``) is
    reachable without changing any provider code.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        response = getattr(current, "response", None)
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            return status
        match = re.search(r"\b([45]\d{2})\b", str(current))
        if match:
            return int(match.group(1))
        current = current.__cause__ or current.__context__
    return None


def classify_error(exc: BaseException | None) -> dict[str, Any]:
    """Summarize a provider failure for the diagnostic log.

    Produces an explicit ``http_status`` plus ``rate_limited`` so an HTTP 429 is
    unambiguous in the file rather than buried in an exception message.  Only
    the exception type and a redacted message are recorded; response bodies are
    never logged.
    """
    if exc is None:
        return {"error_class": None, "http_status": None, "rate_limited": False}
    status = http_status_from_error(exc)
    return {
        "error_class": type(exc).__name__,
        "error_message": redact(str(exc)),
        "http_status": status,
        "rate_limited": status == 429,
        "is_http_error": _is_http_error(exc),
    }


def subject_of(args: tuple[Any, ...]) -> dict[str, Any]:
    """Describe the record subject without ever logging a whole universe.

    A single symbol is recorded as-is.  A bulk key list is reduced to its
    length, because the discovery snapshot legitimately carries thousands of
    instrument keys.
    """
    if not args:
        return {"symbol": None, "subject_count": None}
    first = args[0]
    if isinstance(first, str):
        return {"symbol": first, "subject_count": None}
    if isinstance(first, (list, tuple, set, frozenset)):
        return {"symbol": None, "subject_count": len(first)}
    return {"symbol": None, "subject_count": None}
