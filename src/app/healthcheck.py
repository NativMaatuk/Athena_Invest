import os
import time
from pathlib import Path


def main() -> int:
    heartbeat_path = Path(os.getenv("HEARTBEAT_FILE_PATH", "/tmp/athena_heartbeat"))
    max_age_seconds = int(os.getenv("HEALTHCHECK_MAX_AGE_SECONDS", "180"))

    if not heartbeat_path.exists():
        return 1

    try:
        last_seen = int(heartbeat_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return 1

    age = int(time.time()) - last_seen
    return 0 if age <= max_age_seconds else 1


if __name__ == "__main__":
    raise SystemExit(main())
