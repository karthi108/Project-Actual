"""Launch only a direct loopback synthetic development API."""

import logging

import uvicorn

from actual.persistence.errors import PersistenceError

from .app import create_app
from .config import ApiSettings, ConfigurationError
from .transport import REQUEST_LOG


def main() -> None:
    try:
        settings = ApiSettings.from_environment()
        app = create_app(settings)
    except (ConfigurationError, PersistenceError):
        raise SystemExit(
            "ACTUAL API requires explicit private synthetic development configuration."
        ) from None
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    REQUEST_LOG.handlers = [handler]
    REQUEST_LOG.setLevel(logging.INFO)
    REQUEST_LOG.propagate = False
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=settings.port,
        proxy_headers=False,
        server_header=False,
        access_log=False,
        log_config=None,
        log_level="critical",
        timeout_keep_alive=5,
    )


if __name__ == "__main__":
    main()
