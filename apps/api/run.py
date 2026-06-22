from __future__ import annotations

import uvicorn

from apps.api.app.config import ApiSettings


def main() -> None:
    settings = ApiSettings.from_env()
    uvicorn.run(
        "apps.api.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
