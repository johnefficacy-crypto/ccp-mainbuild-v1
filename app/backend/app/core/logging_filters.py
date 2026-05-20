"""Logging filters that scrub secrets from log records.

The SerpApi adapter sends ``api_key`` as a query-string parameter (their API
has no header auth). httpx's request logging prints the full URL at INFO,
which leaked the key once already. This filter strips ``api_key=<value>`` from
any formatted log message regardless of which logger emitted it, so a future
``logger.info("GET https://...?api_key=...")`` can never re-leak.
"""
import logging
import re

_SECRET_QUERY_RE = re.compile(r"(api_key=)[^&\s\"']+", re.IGNORECASE)

# Loggers that either emit request URLs (httpx/httpcore) or could log a SerpApi
# URL directly. A logging.Filter only runs for records emitted at the logger it
# is attached to (filters do not propagate to ancestors the way handlers do), so
# we attach to each known emitter plus root for any direct-to-root records.
_REDACTED_LOGGERS = ("", "httpx", "httpcore", "app.scraping.serpapi_discovery")


class RedactQuerySecretsFilter(logging.Filter):
    """Strips ``api_key=<value>`` from any logged message (URLs, exceptions, repr)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = _SECRET_QUERY_RE.sub(r"\1***REDACTED***", msg)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


def install_log_redaction() -> RedactQuerySecretsFilter:
    """Attach :class:`RedactQuerySecretsFilter` to the relevant loggers.

    Idempotent enough for repeated calls: a logger never accumulates a
    behaviourally-different filter, only an extra identical one (cheap).
    Returns the filter instance for tests / teardown.
    """
    log_filter = RedactQuerySecretsFilter()
    for name in _REDACTED_LOGGERS:
        logging.getLogger(name).addFilter(log_filter)
    return log_filter
