"""Demo davomat client — Face verify orqali davomat belgilash."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fjsti_id import FjstiClient

ATTENDANCE_FILE = Path(__file__).with_name("attendance.json")


def mark(user: dict) -> None:
    records = []
    if ATTENDANCE_FILE.exists():
        records = json.loads(ATTENDANCE_FILE.read_text(encoding="utf-8"))
    records.append(
        {
            "user_id": user.get("id"),
            "full_name": user.get("full_name"),
            "roles": [r.get("name") if isinstance(r, dict) else r for r in user.get("roles") or []],
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    ATTENDANCE_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Davomat: {user.get('full_name')} — {records[-1]['at']}")


def main() -> None:
    p = argparse.ArgumentParser(description="FJSTI davomat demo")
    p.add_argument("--base-url", default=os.getenv("FJSTI_URL", "http://localhost:8000"))
    p.add_argument("--api-key", default=os.getenv("FJSTI_API_KEY", ""))
    p.add_argument("--image", required=True, help="Yuz rasmi yo'li")
    args = p.parse_args()
    if not args.api_key:
        raise SystemExit("FJSTI_API_KEY yoki --api-key bering")

    client = FjstiClient(args.base_url, args.api_key)
    res = client.verify_face(args.image, device_info="davomat-demo")
    if not res.get("matched") or not res.get("user"):
        print("Yuz tanilmadi")
        raise SystemExit(1)
    mark(res["user"])


if __name__ == "__main__":
    main()
