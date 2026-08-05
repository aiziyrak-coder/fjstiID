"""Scrape FJSTI department pages and extract staff F.I.Sh for seeding."""

from __future__ import annotations

import html as H
import json
import re
import time
import urllib.request
from pathlib import Path

BASE = "https://fjsti.uz/"
OUT = Path(__file__).resolve().parent / "data" / "fjsti_staff.json"

SLUGS = """
akusherlik-va-ginekologiya-kafedrasi
biotibbiyot-muhandisligi-biofizikia-va-axborot-texnologiyalar-kafedrasi
dermatovenerologiya-va-allergologiya-kafedrasi
endokrinologiya-gemotologiya-va-ftiziatriya-kafedrasi
epidemiologiya-va-yuqumli-kasalliklar-hamshiralik-ishi-kafedrasi
fakultet-va-gospital-jarrohlik-kafedrasi
fiziologiya-kafedrasi
gistologiya-va-biologiya-kafedrasi
gospital-terapiya-laboratoriya-kafedrasi
ichki-kasalliklar-propedevtikasi-kafedrasi
ijtimoiy-fanlar-kafedrasi
kommunal-va-mehnat-gigienasi-kafedrasi
lotin-tili-pedagogika-va-psixologiya
mikrobiologiya-virusologiya-va-immunologiya-kafedrasi
nevrologiya-va-psixiatriya-kafedrasi
normal-anatomiya-kafedrasi
ovqatlanish-bolalar-va-osmirlar-gigienasi-kafedrasi
ozbek-va-xorijiy-tillar-kafedrasi
patologik-fiziologiya-va-patologik-anatomiya-kafedrasi
pediatriya-kafedrasi
pediatriya-kafedrasi-2
preventiv-tibbiyot-asoslari-jamoat-salomatligi-jismoniy-tarbiya-va-sport-kafedrasi
stomatologiya-va-otorinolaringologiya-kafedrasi
terapiya-yonalishidagi-fanlar-kafedrasi
tibbiy-va-biologik-kimyo-kafedrasi
travmatologiya-va-ortopediya-kafedrasi
umumiy-jarrohlik-kafedrasi
urologiya-va-onkologiya-kafedrasi
xalq-tabobati-va-farmakologiya-kafedrasi
""".strip().split()

SLUG_TO_CODE = {
    "travmatologiya-va-ortopediya": "DI-TRAVMA",
    "ichki-kasalliklar-propedevtikasi": "DI-ICHKI-PROP",
    "normal-anatomiya": "DI-ANATOM",
    "gospital-terapiya": "DI-GOSP-TER",
    "akusherlik-va-ginekologiya": "DI-AKUSH",
    "umumiy-jarrohlik": "DI-UMUM-JAR",
    "fakultet-va-gospital-jarrohlik": "DI-FAK-JAR",
    "terapiya-yonalishidagi-fanlar": "DI-TERAPIYA",
    "kommunal-va-mehnat-gigienasi": "TP-KOMMUNAL",
    "ovqatlanish-bolalar": "TP-OVQAT",
    "preventiv-tibbiyot": "TP-PREVENT",
    "epidemiologiya-va-yuqumli": "TP-EPIDEM",
    "mikrobiologiya": "TP-MIKRO",
    "biotibbiyot-muhandisligi": "TP-BIOENG",
    "xalq-tabobati": "TP-FARMA",
    "gistologiya-va-biologiya": "XF-GISTO",
    "ozbek-va-xorijiy-tillar": "XF-TILLAR",
    "lotin-tili": "XF-LOTIN",
    "tibbiy-va-biologik-kimyo": "XF-KIMYO",
    "ijtimoiy-fanlar": "XF-IJTIMOIY",
    "fiziologiya-kafedrasi": "XF-FIZIO",
    "patologik-fiziologiya": "XF-PATFIZ",
    "pediatriya-kafedrasi-2": "PED-2",
    "pediatriya-kafedrasi": "PED-1",
    "stomatologiya-va-otorinolaringologiya": "PED-STOM",
    "nevrologiya-va-psixiatriya": "PED-NEVRO",
    "urologiya-va-onkologiya": "PED-URO",
    "dermatovenerologiya": "PED-DERMA",
    "endokrinologiya": "PED-ENDO",
}

NOISE = re.compile(
    r"(kafedra|fakultet|institut|faoliyat|buyruq|yilida|yildan|o‘quv|oqituv|"
    r"professor-o|talaba|fanlari|doktori|nomzodi|bo‘yicha|asosiy|prezident|"
    r"respublika|ilmiy|to‘garak|ma’naviy|manaviy|yo‘nalish|yonalish|"
    r"tibbiyot fanlari|pedagogika fanlari|falsafa|tarix fanlari|"
    r"bundan tashqari|asosiy ma)",
    re.I,
)

FIO3 = re.compile(
    r"^([A-ZА-ЯЁЎҚҒҲ][a-zа-яёўқғҳʼ'`\-]+)\s+"
    r"([A-ZА-ЯЁЎҚҒҲ][a-zа-яёўқғҳʼ'`\-]+)\s+"
    r"([A-ZА-ЯЁЎҚҒҲ][a-zа-яёўқғҳʼ'`\-]+)$"
)
FIO_INIT = re.compile(
    r"^([A-ZА-ЯЁЎҚҒҲ][a-zа-яёўқғҳʼ'`\-]+)\s+([A-ZА-ЯЁЎҚҒҲ])\.?\s*([A-ZА-ЯЁЎҚҒҲ])\.?$"
)


def code_for(slug: str) -> str | None:
    for k, v in SLUG_TO_CODE.items():
        if k in slug:
            return v
    return None


def is_person_name(s: str) -> bool:
    s = s.strip(" .,-–—")
    if len(s) < 8 or len(s) > 70:
        return False
    if NOISE.search(s):
        return False
    if any(ch.isdigit() for ch in s):
        return False
    words = s.split()
    if len(words) < 2 or len(words) > 4:
        return False
    # each word starts with capital letter (Latin or Cyrillic)
    for w in words:
        if not re.match(r"^[A-ZА-ЯЁЎҚҒҲ]", w):
            return False
    return bool(FIO3.match(s) or FIO_INIT.match(s) or (len(words) == 2 and all(len(w) > 2 for w in words)))


def parse_position(hint: str) -> str:
    h = hint.lower()
    if "mudiri" in h:
        return "Kafedra mudiri"
    if "professor" in h:
        return "Professor"
    if "dotsent" in h:
        return "Dotsent"
    if "katta o" in h:
        return "Katta o'qituvchi"
    if "assistent" in h:
        return "Assistent"
    if "phd" in h or "ph.d" in h:
        return "PhD, o'qituvchi"
    return "O'qituvchi"


def extract(raw: str) -> list[dict]:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    # prefer heading-like tags
    titled: list[tuple[str, str]] = []
    for m in re.finditer(
        r"<(?:h[1-6]|strong|b|p|div|span)[^>]*>\s*([^<]{6,90})\s*</",
        raw,
        flags=re.I,
    ):
        titled.append((H.unescape(m.group(1)).strip(), m.group(0)[:40]))

    text = re.sub(r"<[^>]+>", "\n", text)
    text = H.unescape(text)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    people: list[dict] = []
    for idx, ln in enumerate(lines):
        low = ln.lower()
        if "kafedra mudiri" in low or re.search(r"\b(phd|dsc|dotsent|professor)\b", low):
            for cand in (lines[idx - 1] if idx else "", ln.split(",")[0], ln.split("—")[0], ln.split("-")[0]):
                cand = cand.strip()
                if is_person_name(cand):
                    people.append({"full_name": cand, "position": parse_position(ln)})
                    break

    for ln in lines:
        if is_person_name(ln):
            people.append({"full_name": ln, "position": "O'qituvchi"})

    for name, _ in titled:
        name = re.sub(r"\s+", " ", name).strip()
        if is_person_name(name):
            people.append({"full_name": name, "position": "O'qituvchi"})

    # dedupe keep first (often mudir)
    seen: set[str] = set()
    out: list[dict] = []
    for p in people:
        key = p["full_name"].lower()
        if key in seen:
            # upgrade position if better
            for existing in out:
                if existing["full_name"].lower() == key:
                    if existing["position"] == "O'qituvchi" and p["position"] != "O'qituvchi":
                        existing["position"] = p["position"]
                    break
            continue
        seen.add(key)
        out.append(p)
    return out


def split_name(full: str) -> tuple[str, str, str | None]:
    m = FIO_INIT.match(full)
    if m:
        return m.group(1), m.group(2) + ".", m.group(3) + "."
    parts = full.split()
    if len(parts) >= 3:
        return parts[0], parts[1], " ".join(parts[2:])
    if len(parts) == 2:
        return parts[0], parts[1], None
    return full, "-", None


def main() -> None:
    result = []
    for slug in SLUGS:
        url = f"{BASE}departments/38/{slug}"
        print("fetch", slug)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 FJSTI-ID-seed"})
            raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001
            print(" FAIL", exc)
            continue
        people = extract(raw)
        for p in people:
            ln, fn, mn = split_name(p["full_name"])
            p["last_name"] = ln
            p["first_name"] = fn
            p["middle_name"] = mn
        code = code_for(slug)
        print(f"  -> {len(people)} staff, code={code}")
        result.append({"slug": slug, "dept_code": code, "people": people})
        time.sleep(0.3)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(x["people"]) for x in result)
    print("TOTAL", total, "->", OUT)


if __name__ == "__main__":
    main()
