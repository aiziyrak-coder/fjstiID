"""Clean fjsti_staff.json — drop English course titles and other non-person rows."""

from __future__ import annotations

import json
import re
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "fjsti_staff.json"

UZ_END = re.compile(r"(vich|ovna|evna|yevna|qizi|ogli|ugli|zoda)$", re.I)
SURNAME = re.compile(r"(ov|ova|ev|eva|yev|yeva|iyev|iyeva|ovich)$", re.I)
CYR = re.compile(r"[А-Яа-яЁёЎўҚқҒғҲҳ]")


def is_person(name: str) -> bool:
    if CYR.search(name):
        return True
    parts = name.split()
    if len(parts) < 2:
        return False
    if UZ_END.search(parts[-1]) or SURNAME.search(parts[0]):
        # reject pure English medical titles even if somehow matched
        if re.fullmatch(r"[A-Za-z .]+", name) and not SURNAME.search(parts[0]) and not UZ_END.search(parts[-1]):
            return False
        return True
    # Latin Uzbek 3-part names
    if len(parts) == 3 and all(len(p) > 2 for p in parts) and SURNAME.search(parts[0]):
        return True
    return False


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    kept = []
    removed = []
    for dept in data:
        people = []
        for pe in dept["people"]:
            if is_person(pe["full_name"]):
                people.append(pe)
            else:
                removed.append(pe["full_name"])
        if people:
            kept.append({"dept_code": dept["dept_code"], "people": people})
    PATH.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
    print("kept", sum(len(x["people"]) for x in kept), "removed", len(removed))
    print("removed sample:", removed[:25])


if __name__ == "__main__":
    main()
