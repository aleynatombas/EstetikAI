"""Terminal entrypoint for one employee request."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.version_info < (3, 10) or sys.version_info >= (3, 14):
    print(
        "CrewAI 1.15, Python 3.10, 3.11, 3.12 veya 3.13 ister. "
        f"Şu an çalışan sürüm {sys.version.split()[0]}. "
        "Örnek kurulum: py -3.13 -m venv .venv",
        file=sys.stderr,
    )
    raise SystemExit(1)

from backend.config import ConfigError  # noqa: E402
from backend.crew import run_employee_request  # noqa: E402


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    print("Ziyaretçi talebini girin:")
    employee_request = sys.stdin.readline()
    if not employee_request or not employee_request.strip():
        print("Talep boş. Çalışan talebini yazıp Enter'a basın.", file=sys.stderr)
        raise SystemExit(1)

    try:
        result = run_employee_request(employee_request)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    except NotImplementedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
