"""
Seed: tizim rollari, admin, sozlamalar va FJSTI rasmiy tuzilmasi.

Manba:
  https://fjsti.uz — Fakultetlar / Kafedralar
  https://moodle.fjsti.uz — Fakultet → kafedra bog'lanishi
  https://fjsti.uz/faculty/17/pediatriya-fakulteti — yo'nalishlar
  https://infoedu.uz — bakalavr mutaxassislik kodlari
"""

from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import (
    AcademicYear,
    Consent,
    Department,
    Faculty,
    IdentityDocument,
    Role,
    Specialty,
    StaffProfile,
    StudentProfile,
    StudyGroup,
    SystemSetting,
    User,
    UserRole,
)
from app.security import generate_token, hash_password
from app.services.users import compose_full_name

settings = get_settings()
STAFF_JSON = Path(__file__).resolve().parent / "data" / "fjsti_staff.json"
MART_STAFF_JSON = Path(__file__).resolve().parent / "data" / "fjsti_staff_mart2026.json"
STUDENTS_DATA_DIR = Path(__file__).resolve().parent / "data"
STUDENT_JSON_FILES = [
    ("fjsti_students_1kurs.json", "1-kurs.xlsx"),
    ("fjsti_students_2kurs.json", "2-kurs.xlsx"),
    ("fjsti_students_3kurs.json", "3-kurs.xlsx"),
    ("fjsti_students_4kurs.json", "4-kurs.xlsx"),
    ("fjsti_students_5kurs.json", "5-kurs.xlsx"),
    ("fjsti_students_6kurs.json", "6-kurs.xlsx"),
]
DEFAULT_STAFF_PASSWORD = "FjstiXodim123!"
DEFAULT_STUDENT_PASSWORD = "FjstiTalaba123!"

# Mart 2026 bo'lim nomi → mavjud Department.code (yoki yangi yaratiladi)
MART_DEPT_MAP: dict[str, tuple[str, str, str]] = {
    # (dept_name, dept_code, faculty_code)
    "RAHBARIYAT": ("Rahbariyat", "ADM-RAHBAR", "ADM"),
    "Kadrlar bo‘limi": ("Kadrlar bo'limi", "ADM-KADR", "ADM"),
    "Xisobxona": ("Hisobxona", "ADM-HISOB", "ADM"),
    "DEVONXONA": ("Devonxona", "ADM-DEVON", "ADM"),
    "REJA MOLIYA BO‘LIMI": ("Reja-moliya bo'limi", "ADM-MOLIY", "ADM"),
    "TA‘LIM SIFATINI NAZORAT QILISH BO’LIMI": ("Ta'lim sifatini nazorat qilish bo'limi", "ADM-SIFAT", "ADM"),
    "MA’NAVIYAT MA’RIFAT BO’LIMI": ("Ma'naviyat va ma'rifat bo'limi", "ADM-MANAV", "ADM"),
    "O‘quv metodik ta’minot boshqarma": ("O'quv-metodik ta'minot boshqarmasi", "ADM-OQUV", "ADM"),
    "TEXNIKUM VA LITSEY": ("Texnikum va litsey", "ADM-TEXLIT", "ADM"),
    "Ta’lim jarayonini tashkil etish bo‘limi": ("Ta'lim jarayonini tashkil etish bo'limi", "ADM-TJTE", "ADM"),
    "Registrator offis": ("Registrator ofis", "ADM-REG", "ADM"),
    "XALQARO HAMKORLIK BO‘LIM": ("Xalqaro hamkorlik bo'limi", "ADM-XH", "ADM"),
    "KORRUPTSIYAGA QARSHI KURASHISH": ("Korrupsiyaga qarshi kurashish", "ADM-KORR", "ADM"),
    "ICHKI NAZORAT VA MONITORING BO’LIMI": ("Ichki nazorat va monitoring bo'limi", "ADM-INM", "ADM"),
    "ILMIY TADQIQOT BO’LIMI": ("Ilmiy tadqiqot bo'limi", "ADM-ILMIY", "ADM"),
    "O‘QITISHNING TEXNIK VOSITALARI BOLIMI": ("O'qitishning texnik vositalari bo'limi", "ADM-OTV", "ADM"),
    "MAGISTRATURA BO‘LIMI": ("Magistratura bo'limi", "ADM-MAG", "ADM"),
    "IQTIDORLI TALABALARNING ILMIY-TADKIKOT FAOLIYATINI TASHKIL ETISH BO‘LIMI": (
        "Iqtidorli talabalar ilmiy-tadqiqot faoliyatini tashkil etish bo'limi",
        "ADM-IQTD",
        "ADM",
    ),
    "MARKETING VA TALABALAR AMALIYOTI BO’LIMI": ("Marketing va talabalar amaliyoti bo'limi", "ADM-MARK", "ADM"),
    "AXBOROT RESURS MARKAZI": ("Axborot-resurs markazi", "ADM-ARM", "ADM"),
    "ATM": ("Axborot texnologiyalari markazi", "ADM-ATM", "ADM"),
    "OMBORXONA": ("Omborxona", "ADM-OMBOR", "ADM"),
    "FM VA MEHNAT MUXOFOZASI BO’LIMI": ("Fuqaro muhofazasi va mehnat muhofazasi bo'limi", "ADM-FM", "ADM"),
    "DAVOLASH ISHI DEKANATI": ("Davolash ishi dekanati", "DI-DEKAN", "DI"),
    "DAVOLASH ISHI TYUTORLARI": ("Davolash ishi tyutorlari", "DI-TYUTOR", "DI"),
    "FAKULTET va GOSPITAL XIRURGIYA": ("Fakultet va gospital jarrohlik kafedrasi", "DI-FAK-JAR", "DI"),
    "AKUSHERLIK VA GINEKOLOGIYA": ("Akusherlik va ginekologiya kafedrasi", "DI-AKUSH", "DI"),
    "UMUMIY XIRURGIYA": ("Umumiy jarrohlik kafedrasi", "DI-UMUM-JAR", "DI"),
    "GOSPITAL TERAPIYA": ("Gospital terapiya (laboratoriya) kafedrasi", "DI-GOSP-TER", "DI"),
    "ICHKI KASALLIKLAR PROPEDEVTIKASI": ("Ichki kasalliklar propedevtikasi kafedrasi", "DI-ICHKI-PROP", "DI"),
    "TERAPIYA YONALISHIDAGI FANLAR": ("Terapiya yo'nalishidagi fanlar kafedrasi", "DI-TERAPIYA", "DI"),
    "NORMAL ANATOMIYA": ("Normal anatomiya, operativ jarrohlik va topografik anatomiya kafedrasi", "DI-ANATOM", "DI"),
    "TRAVMATOLOGIYA VA ORTOPEDIYA": ("Travmatologiya va ortopediya kafedrasi", "DI-TRAVMA", "DI"),
    "PEDIATRIYA FAKULTETI": ("Pediatriya fakulteti dekanati", "PED-DEKAN", "PED"),
    "PEDIATRIYA FAKULTETI TYUTORLARI": ("Pediatriya fakulteti tyutorlari", "PED-TYUTOR", "PED"),
    "NEVROLOGIYA VA PSIXIATRIYA": ("Nevrologiya va psixiatriya kafedrasi", "PED-NEVRO", "PED"),
    "PEDIATRIYA": ("Pediatriya kafedrasi", "PED-1", "PED"),
    "PEDIATRIYA-2": ("Pediatriya kafedrasi-2", "PED-2", "PED"),
    "ENDOKRINOLOGIYA. GEMATOLOGIYA VA FTIZIATRIYA": (
        "Endokrinologiya, gematologiya va ftiziatriya kafedrasi",
        "PED-ENDO",
        "PED",
    ),
    "DERMATOVENEROLOGIYA VA ALLERGOLOGIYA": ("Dermatovenerologiya va allergologiya kafedrasi", "PED-DERMA", "PED"),
    "STOMATOLOGIYA VA OTORINOLARINGOLOGIYA": ("Stomatologiya va otorinolaringologiya kafedrasi", "PED-STOM", "PED"),
    "UROLOGIYA VA ONKOLOGIYA": ("Urologiya va onkologiya kafedrasi", "PED-URO", "PED"),
    "TIBBIY PROFILAKTIKA FAKULTETI": ("Tibbiy profilaktika fakulteti dekanati", "TP-DEKAN", "TPJS"),
    "TIBBIY PROFILAKTIKA FAKULTETI TYUTORLARI": ("Tibbiy profilaktika fakulteti tyutorlari", "TP-TYUTOR", "TPJS"),
    "BIOTIBBIYOT MUXANDISLIGI, BIOFIZIKA VA AXBOROT TEXNOLOGIYALARI": (
        "Biotibbiyot muhandisligi, biofizika va axborot texnologiyalari kafedrasi",
        "TP-BIOENG",
        "TPJS",
    ),
    "XALQ TABOBATI VA FARMOKOLOGIYA": ("Xalq tabobati va farmakologiya kafedrasi", "TP-FARMA", "TPJS"),
    "EPIDEMIOLOGIYA VA YUQUMLI KASALLIKLAR, XAMSHIRALIK ISHI": (
        "Epidemiologiya va yuqumli kasalliklar, hamshiralik ishi kafedrasi",
        "TP-EPIDEM",
        "TPJS",
    ),
    "OVQATLANISH, BOLALAR VA O‘SMIRLAR GIGIENASI": (
        "Ovqatlanish, bolalar va o'smirlar gigiyenasi kafedrasi",
        "TP-OVQAT",
        "TPJS",
    ),
    "PREVINTIV JAMOAT SALOMATLIGI, SOG’LIQNI SAQLASHNI TASHKIL ETISH, BOSHQARISH, BOSHQARISH VA SPORT": (
        "Preventiv tibbiyot asoslari, jamoat salomatligi, jismoniy tarbiya va sport kafedrasi",
        "TP-PREVENT",
        "TPJS",
    ),
    "MIKROBIOLOGIYA, VIRUSOLOGIYA VA IMMUNOLOGIYA": (
        "Mikrobiologiya, virusologiya va immunologiya kafedrasi",
        "TP-MIKRO",
        "TPJS",
    ),
    "KOMMUNAL VA MEHNAT GIGIENASI": ("Kommunal va mehnat gigiyenasi kafedrasi", "TP-KOMMUNAL", "TPJS"),
    "XALQARO HAMKORLIK FAKULTETI": ("Xalqaro fakultet dekanati", "XF-DEKAN", "XF"),
    "XALQARO HAMKORLIK FAKULTETI TYUTORLARI": ("Xalqaro fakultet tyutorlari", "XF-TYUTOR", "XF"),
    "GISTOLOGIYA VA BIOLOGIYA": ("Gistologiya va biologiya kafedrasi", "XF-GISTO", "XF"),
    "LOTIN TILI, PEDOGOGIKA VA PSIXOLOGIYA": ("Lotin tili, pedagogika va psixologiya kafedrasi", "XF-LOTIN", "XF"),
    "O‘ZBEK VA XORIJIY TILLAR": ("O'zbek va xorijiy tillar kafedrasi", "XF-TILLAR", "XF"),
    "TIBBIY VA BIOLOGIK KIMYO": ("Tibbiy va biologik kimyo kafedrasi", "XF-KIMYO", "XF"),
    "IJTIMOIY FANLAR": ("Ijtimoiy fanlar kafedrasi", "XF-IJTIMOIY", "XF"),
    "PATOLOGIK FIZIOLOGIYA VA PATOLOGIK ANATOMIYA": (
        "Patologik fiziologiya va patologik anatomiya kafedrasi",
        "XF-PATFIZ",
        "XF",
    ),
    "FIZIOLOGIYA": ("Fiziologiya kafedrasi", "XF-FIZIO", "XF"),
    "MALAKA OSHIRISH VA QAYTA TAYORLASH FAKULTETI": ("Malaka oshirish va qayta tayyorlash fakulteti", "ADM-MALAKA", "ADM"),
    "1-TTJ": ("1-TTJ", "ADM-TTJ1", "ADM"),
    "2-TTJ": ("2-TTJ", "ADM-TTJ2", "ADM"),
    "3-TTJ": ("3-TTJ", "ADM-TTJ3", "ADM"),
    "ASOSIY BINO XODIMLARI": ("Asosiy bino xodimlari", "ADM-BINO1", "ADM"),
    "2-BINO AXO XODIMLARI": ("2-bino AXO xodimlari", "ADM-BINO2", "ADM"),
    "VIVARIY": ("Vivariy", "ADM-VIVAR", "ADM"),
    "Mavsumiy o‘t yoquvchilar": ("Mavsumiy o't yoquvchilar", "ADM-MAVSUM", "ADM"),
}

_MAP = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j",
        "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
        "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "ts",
        "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu",
        "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
        "А": "a", "Б": "b", "В": "v", "Г": "g", "Д": "d", "Е": "e", "Ё": "yo", "Ж": "j",
        "З": "z", "И": "i", "Й": "y", "К": "k", "Л": "l", "М": "m", "Н": "n", "О": "o",
        "П": "p", "Р": "r", "С": "s", "Т": "t", "У": "u", "Ф": "f", "Х": "x", "Ц": "ts",
        "Ч": "ch", "Ш": "sh", "Щ": "sh", "Ъ": "", "Ы": "i", "Ь": "", "Э": "e", "Ю": "yu",
        "Я": "ya", "Ў": "o", "Қ": "q", "Ғ": "g", "Ҳ": "h",
        "ʻ": "", "'": "", "`": "", "’": "", "‘": "",
    }
)


def slugify_email_part(text: str) -> str:
    t = text.translate(_MAP)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-zA-Z0-9]+", ".", t.lower()).strip(".")
    return t or "xodim"


def normalize_name_key(text: str) -> str:
    """Taqqoslash uchun F.I.Sh / bo'lim nomini soddalashtirish."""
    t = (text or "").translate(_MAP).lower()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-z0-9]+", "", t)
    return t


def parse_birth_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        y, m, d = value.split("-")
        return date(int(y), int(m), int(d))
    except (ValueError, AttributeError):
        return None

ROLES = [
    ("student", "Talaba", "Talaba"),
    ("staff", "Xodim", "Xodim / professor-o'qituvchi"),
    ("admin", "Administrator", "To'liq boshqaruv"),
    ("moderator", "Moderator", "Cheklangan admin"),
]

# Fakultet → (code, specialties[(name, code)], departments[(name, code)])
# Kafedralar moodle.fjsti.uz kategoriya tuzilmasi bo'yicha
FJSTI_ORG: list[tuple[str, str, list[tuple[str, str]], list[tuple[str, str]]]] = [
    (
        "Davolash ishi fakulteti",
        "DI",
        [
            ("Davolash ishi", "60910200"),
        ],
        [
            ("Travmatologiya va ortopediya kafedrasi", "DI-TRAVMA"),
            ("Ichki kasalliklar propedevtikasi kafedrasi", "DI-ICHKI-PROP"),
            ("Normal anatomiya, operativ jarrohlik va topografik anatomiya kafedrasi", "DI-ANATOM"),
            ("Gospital terapiya (laboratoriya) kafedrasi", "DI-GOSP-TER"),
            ("Akusherlik va ginekologiya kafedrasi", "DI-AKUSH"),
            ("Umumiy jarrohlik kafedrasi", "DI-UMUM-JAR"),
            ("Fakultet va gospital jarrohlik kafedrasi", "DI-FAK-JAR"),
            ("Terapiya yo'nalishidagi fanlar kafedrasi", "DI-TERAPIYA"),
        ],
    ),
    (
        "Tibbiy profilaktika va jamoat salomatligi fakulteti",
        "TPJS",
        [
            ("Tibbiy profilaktika ishi", "60910400"),
            ("Biotibbiyot muhandisligi", "60711100"),
        ],
        [
            ("Kommunal va mehnat gigiyenasi kafedrasi", "TP-KOMMUNAL"),
            ("Ovqatlanish, bolalar va o'smirlar gigiyenasi kafedrasi", "TP-OVQAT"),
            ("Preventiv tibbiyot asoslari, jamoat salomatligi, jismoniy tarbiya va sport kafedrasi", "TP-PREVENT"),
            ("Epidemiologiya va yuqumli kasalliklar, hamshiralik ishi kafedrasi", "TP-EPIDEM"),
            ("Mikrobiologiya, virusologiya va immunologiya kafedrasi", "TP-MIKRO"),
            ("Biotibbiyot muhandisligi, biofizika va axborot texnologiyalari kafedrasi", "TP-BIOENG"),
            ("Xalq tabobati va farmakologiya kafedrasi", "TP-FARMA"),
        ],
    ),
    (
        "Xalqaro fakultet",
        "XF",
        [
            ("Davolash ishi (xalqaro)", "60910200-INT"),
        ],
        [
            ("Gistologiya va biologiya kafedrasi", "XF-GISTO"),
            ("O'zbek va xorijiy tillar kafedrasi", "XF-TILLAR"),
            ("Lotin tili, pedagogika va psixologiya kafedrasi", "XF-LOTIN"),
            ("Tibbiy va biologik kimyo kafedrasi", "XF-KIMYO"),
            ("Ijtimoiy fanlar kafedrasi", "XF-IJTIMOIY"),
            ("Fiziologiya kafedrasi", "XF-FIZIO"),
            ("Patologik fiziologiya va patologik anatomiya kafedrasi", "XF-PATFIZ"),
        ],
    ),
    (
        "Pediatriya fakulteti",
        "PED",
        [
            ("Pediatriya ishi", "60910300"),
            ("Stomatologiya", "60910100"),
            ("Farmatsiya", "60910700"),
        ],
        [
            ("Pediatriya kafedrasi", "PED-1"),
            ("Pediatriya kafedrasi-2", "PED-2"),
            ("Stomatologiya va otorinolaringologiya kafedrasi", "PED-STOM"),
            ("Nevrologiya va psixiatriya kafedrasi", "PED-NEVRO"),
            ("Urologiya va onkologiya kafedrasi", "PED-URO"),
            ("Dermatovenerologiya va allergologiya kafedrasi", "PED-DERMA"),
            ("Endokrinologiya, gematologiya va ftiziatriya kafedrasi", "PED-ENDO"),
        ],
    ),
]


async def ensure_admin_faculty(session: AsyncSession) -> Faculty:
    fac = await session.scalar(select(Faculty).where(Faculty.code == "ADM"))
    if not fac:
        fac = Faculty(name="Administratsiya va bo'limlar", code="ADM", is_active=True)
        session.add(fac)
        await session.flush()
    return fac


async def resolve_mart_department(session: AsyncSession, section: str) -> Department | None:
    """Mart 2026 bo'limini DB kafedra/bo'limiga bog'lash; yo'q bo'lsa yaratadi."""
    await ensure_admin_faculty(session)
    key_norm = normalize_name_key(section)
    mapped = None
    for raw, triple in MART_DEPT_MAP.items():
        if normalize_name_key(raw) == key_norm:
            mapped = triple
            break
    if not mapped:
        # qisman moslik
        for raw, triple in MART_DEPT_MAP.items():
            rn = normalize_name_key(raw)
            if rn and (rn in key_norm or key_norm in rn):
                mapped = triple
                break

    if mapped:
        dep_name, dep_code, fac_code = mapped
    else:
        dep_name = section.strip().title() if section.isupper() else section.strip()
        dep_code = "MART-" + (slugify_email_part(section).upper().replace(".", "-")[:40] or "X")
        fac_code = "ADM"

    fac = await session.scalar(select(Faculty).where(Faculty.code == fac_code))
    if not fac:
        fac = await ensure_admin_faculty(session)

    dept = await session.scalar(select(Department).where(Department.code == dep_code))
    if not dept:
        dept = Department(name=dep_name, code=dep_code, faculty_id=fac.id, is_active=True)
        session.add(dept)
        await session.flush()
    else:
        dept.name = dep_name
        dept.faculty_id = fac.id
        dept.is_active = True
    return dept


async def seed_staff_from_mart2026(session: AsyncSession) -> tuple[int, int]:
    """Mart 2026.xlsx/docx ro'yxati — mavjud F.I.Sh o'tkaziladi, yangilari qo'shiladi."""
    if not MART_STAFF_JSON.exists():
        print("[seed] fjsti_staff_mart2026.json topilmadi — Mart 2026 o'tkazib yuborildi")
        return 0, 0

    data = json.loads(MART_STAFF_JSON.read_text(encoding="utf-8"))
    staff_role = await session.scalar(select(Role).where(Role.code == "staff"))
    if not staff_role:
        return 0, 0

    # mavjud ismlar (normalizatsiya)
    existing_rows = (await session.execute(select(User.full_name).where(User.is_deleted.is_(False)))).all()
    existing_keys = {normalize_name_key(r[0]) for r in existing_rows if r[0]}

    created = 0
    skipped = 0
    seq = 1
    # EMP-MART- prefiksi
    while await session.scalar(
        select(StaffProfile).where(StaffProfile.employee_number == f"EMP-MART-{seq:04d}")
    ):
        seq += 1

    for block in data:
        section = (block.get("department") or "").strip()
        dept = await resolve_mart_department(session, section) if section else None
        for person in block.get("people") or []:
            last_name = (person.get("last_name") or "").strip()
            first_name = (person.get("first_name") or "").strip()
            middle_name = (person.get("middle_name") or None)
            if middle_name:
                middle_name = middle_name.strip() or None
            if not last_name or not first_name or first_name == "-":
                continue
            full = compose_full_name(last_name, first_name, middle_name)
            key = normalize_name_key(full)
            raw_key = normalize_name_key(person.get("full_name_raw") or full)
            if key in existing_keys or raw_key in existing_keys:
                skipped += 1
                continue

            base = f"{slugify_email_part(last_name)}.{slugify_email_part(first_name)}"
            email = f"{base}@fjsti.uz"
            n = 2
            while await session.scalar(select(User).where(User.email == email)):
                email = f"{base}{n}@fjsti.uz"
                n += 1

            emp_no = f"EMP-MART-{seq:04d}"
            while await session.scalar(select(StaffProfile).where(StaffProfile.employee_number == emp_no)):
                seq += 1
                emp_no = f"EMP-MART-{seq:04d}"

            user = User(
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                full_name=full,
                email=email,
                birth_date=parse_birth_date(person.get("birth_date")),
                citizenship="O'zbekiston",
                password_hash=hash_password(DEFAULT_STAFF_PASSWORD),
                qr_token=generate_token(16),
                status="active",
                notes=f"Manba: Mart 2026 · {section}",
            )
            session.add(user)
            await session.flush()
            session.add(
                StaffProfile(
                    user_id=user.id,
                    employee_number=emp_no,
                    department_id=dept.id if dept else None,
                    position=person.get("position") or "Xodim",
                    employment_type="asosiy",
                    staff_status="active",
                )
            )
            session.add(Consent(user_id=user.id, consent_type="biometric", granted=True))
            session.add(UserRole(user_id=user.id, role_id=staff_role.id))
            existing_keys.add(key)
            existing_keys.add(raw_key)
            created += 1
            seq += 1

    await session.flush()
    return created, skipped


def infer_student_org(group_name: str) -> tuple[str, str | None, str]:
    """
    Guruh nomidan (faculty_code, specialty_code|None, education_level).
    """
    g = group_name or ""
    gl = g.lower()
    level = "bakalavr"
    if "magistr" in gl:
        level = "magistr"
    elif "ordinatura" in gl or "ordinat" in gl:
        level = "ordinatura"

    # kodli guruhlar
    if re.match(r"^(DI|ЛД|LD)[\s\-]?", g, re.I) or g.upper().startswith("DI-"):
        return "DI", "60910200", level
    if re.match(r"^MD[\s\-]?", g, re.I):
        return "XF", "60910200-INT", level
    if re.match(r"^TPI[\s\-]?", g, re.I):
        return "TPJS", "60910400", level
    if re.match(r"^BM[\s\-]?", g, re.I):
        return "TPJS", "60711100", level
    if re.match(r"^P[\s\-]?\d", g, re.I) or re.match(r"^P-\d", g, re.I):
        return "PED", "60910300", level
    if re.match(r"^S[\s\-]?\d", g, re.I) or re.match(r"^S-\d", g, re.I):
        return "PED", "60910100", level
    if re.match(r"^F[\s\-]?\d", g, re.I) or re.match(r"^F-\d", g, re.I):
        return "PED", "60910700", level
    if re.match(r"^FT[\s\-]?", g, re.I):
        return "TPJS", "60910400", level
    if re.match(r"^OHI[\s\-]?", g, re.I):
        return "TPJS", "60910400", level

    # mutaxassislik / klinika nomlari
    if any(k in gl for k in ("stomatolog", "ortodont", "jag'", "jag‘", "terapevtik stomat")):
        return "PED", "60910100", level
    if any(k in gl for k in ("pediatriya", "bolalar", "neonatolog")):
        return "PED", "60910300", level
    if any(k in gl for k in ("farmats", "farmak")):
        return "PED", "60910700", level
    if any(
        k in gl
        for k in (
            "gigiyena",
            "epidemiolog",
            "profilaktik",
            "kommunal",
            "mehnat gig",
            "ssbjss",
            "laboratoriya",
        )
    ):
        return "TPJS", "60910400", level
    if any(
        k in gl
        for k in (
            "akusher",
            "xirurg",
            "jarroh",
            "terapiya",
            "kardiolog",
            "nevrolog",
            "urolog",
            "onkolog",
            "travmatolog",
            "anestez",
            "oftalmolog",
            "otorinolaring",
            "dermatovener",
            "endokrin",
            "ftiziatr",
            "pulmonolog",
            "revmatolog",
            "nefrolog",
            "psixiatr",
            "narkolog",
            "reabilit",
            "radiolog",
            "yuqumli",
            "morfolog",
            "patologik",
            "allergolog",
        )
    ):
        return "DI", "60910200", level

    return "DI", "60910200", level


async def get_or_create_group(
    session: AsyncSession,
    name: str,
    faculty: Faculty,
    specialty: Specialty | None,
) -> StudyGroup:
    group = await session.scalar(select(StudyGroup).where(StudyGroup.name == name))
    if group:
        if specialty and not group.specialty_id:
            group.specialty_id = specialty.id
        return group

    # fakultetning birinchi kafedrasiga bog'lash (guruh → kafedra modeli)
    dept = await session.scalar(
        select(Department).where(Department.faculty_id == faculty.id).order_by(Department.name)
    )
    group = StudyGroup(
        name=name,
        department_id=dept.id if dept else None,
        specialty_id=specialty.id if specialty else None,
        academic_year="2025/2026",
    )
    session.add(group)
    await session.flush()
    return group


async def seed_students_from_json(
    session: AsyncSession,
    path: Path,
    source_label: str,
    *,
    existing_stu: set[str] | None = None,
    existing_pin: set[str] | None = None,
    group_cache: dict[str, StudyGroup] | None = None,
) -> tuple[int, int]:
    """Kontingent JSON — Talaba ID / JSHSHIR bo'yicha dublikat o'tkaziladi."""
    if not path.exists():
        return 0, 0

    people = json.loads(path.read_text(encoding="utf-8"))
    student_role = await session.scalar(select(Role).where(Role.code == "student"))
    if not student_role:
        return 0, 0

    if existing_stu is None:
        existing_stu = {
            r[0]
            for r in (await session.execute(select(StudentProfile.student_number))).all()
            if r[0]
        }
    if existing_pin is None:
        existing_pin = {
            r[0]
            for r in (await session.execute(select(User.pinfl).where(User.pinfl.is_not(None)))).all()
            if r[0]
        }
    if group_cache is None:
        group_cache = {}

    created = 0
    skipped = 0
    course_hint = next((p.get("course") for p in people if p.get("course")), 1)

    for person in people:
        sn = (person.get("student_number") or "").strip()
        pinfl = (person.get("pinfl") or "").strip() or None
        if pinfl and len(pinfl) > 14:
            pinfl = pinfl[:14]
        if sn and sn in existing_stu:
            skipped += 1
            continue
        if pinfl and pinfl in existing_pin:
            skipped += 1
            continue

        last_name = (person.get("last_name") or "").strip()
        first_name = (person.get("first_name") or "").strip()
        middle_name = (person.get("middle_name") or None)
        if middle_name:
            middle_name = middle_name.strip() or None
        if not last_name or not first_name:
            skipped += 1
            continue

        group_name = (person.get("group_name") or "").strip()
        fac_code, sp_code, edu_level = infer_student_org(group_name)
        faculty = await session.scalar(select(Faculty).where(Faculty.code == fac_code))
        specialty = None
        if sp_code:
            specialty = await session.scalar(select(Specialty).where(Specialty.code == sp_code))
        if not faculty:
            faculty = await session.scalar(select(Faculty).where(Faculty.code == "DI"))

        group = None
        if group_name and faculty:
            if group_name not in group_cache:
                group_cache[group_name] = await get_or_create_group(
                    session, group_name, faculty, specialty
                )
            group = group_cache[group_name]

        course = int(person.get("course") or course_hint or 1)
        if not sn:
            sn = f"STU-{course}K-{created + skipped + 1:05d}"
            while sn in existing_stu:
                sn = f"STU-{course}K-{len(existing_stu) + 1:05d}"

        email = f"{sn}@student.fjsti.uz"
        n = 2
        while await session.scalar(select(User).where(User.email == email)):
            email = f"{sn}.{n}@student.fjsti.uz"
            n += 1

        # qabul yili: taxminan (joriy o'quv yili - kurs + 1)
        admission_year = 2025 - (course - 1)

        full = compose_full_name(last_name, first_name, middle_name)
        user = User(
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            full_name=full,
            gender=person.get("gender"),
            birth_date=parse_birth_date(person.get("birth_date")),
            pinfl=pinfl,
            email=email,
            citizenship="O'zbekiston",
            password_hash=hash_password(DEFAULT_STUDENT_PASSWORD),
            qr_token=generate_token(16),
            status="active",
            notes=f"Manba: {source_label} · {group_name}",
        )
        session.add(user)
        await session.flush()

        session.add(
            StudentProfile(
                user_id=user.id,
                student_number=sn,
                faculty_id=faculty.id if faculty else None,
                specialty_id=specialty.id if specialty else None,
                group_id=group.id if group else None,
                course=course,
                study_form="kunduzgi",
                funding="kontrakt",
                education_level=edu_level,
                admission_year=admission_year,
                academic_status="active",
            )
        )

        series = person.get("passport_series")
        number = person.get("passport_number")
        if series or number:
            session.add(
                IdentityDocument(
                    user_id=user.id,
                    doc_type="passport",
                    series=series,
                    number=number,
                )
            )

        session.add(Consent(user_id=user.id, consent_type="biometric", granted=True))
        session.add(UserRole(user_id=user.id, role_id=student_role.id))
        existing_stu.add(sn)
        if pinfl:
            existing_pin.add(pinfl)
        created += 1

        if created % 200 == 0:
            await session.flush()
            print(f"[seed] {source_label}: {created} qo'shildi...")

    await session.flush()
    return created, skipped


async def seed_all_students(session: AsyncSession) -> list[tuple[str, int, int]]:
    existing_stu = {
        r[0]
        for r in (await session.execute(select(StudentProfile.student_number))).all()
        if r[0]
    }
    existing_pin = {
        r[0]
        for r in (await session.execute(select(User.pinfl).where(User.pinfl.is_not(None)))).all()
        if r[0]
    }
    group_cache: dict[str, StudyGroup] = {}
    results: list[tuple[str, int, int]] = []
    for filename, label in STUDENT_JSON_FILES:
        path = STUDENTS_DATA_DIR / filename
        if not path.exists():
            continue
        created, skipped = await seed_students_from_json(
            session,
            path,
            label,
            existing_stu=existing_stu,
            existing_pin=existing_pin,
            group_cache=group_cache,
        )
        results.append((label, created, skipped))
        print(f"[seed] {label}: +{created}, skip {skipped}")
    return results


async def seed_org(session: AsyncSession) -> None:
    """Idempotent: mavjud kod bo'lsa o'tkazib yuboradi."""
    await ensure_admin_faculty(session)
    for fac_name, fac_code, specialties, departments in FJSTI_ORG:
        fac = await session.scalar(select(Faculty).where(Faculty.code == fac_code))
        if not fac:
            fac = Faculty(name=fac_name, code=fac_code, is_active=True)
            session.add(fac)
            await session.flush()
        else:
            fac.name = fac_name
            fac.is_active = True

        for sp_name, sp_code in specialties:
            existing = await session.scalar(select(Specialty).where(Specialty.code == sp_code))
            if not existing:
                session.add(Specialty(name=sp_name, code=sp_code, faculty_id=fac.id))
            else:
                existing.name = sp_name
                existing.faculty_id = fac.id

        for dep_name, dep_code in departments:
            existing = await session.scalar(select(Department).where(Department.code == dep_code))
            if not existing:
                session.add(Department(name=dep_name, code=dep_code, faculty_id=fac.id, is_active=True))
            else:
                existing.name = dep_name
                existing.faculty_id = fac.id
                existing.is_active = True

    await session.flush()


async def seed_staff_from_fjsti(session: AsyncSession) -> int:
    """fjsti.uz kafedra sahifalaridan olingan professor-o'qituvchilar."""
    if not STAFF_JSON.exists():
        print("[seed] fjsti_staff.json topilmadi — xodimlar o'tkazib yuborildi")
        return 0

    data = json.loads(STAFF_JSON.read_text(encoding="utf-8"))
    staff_role = await session.scalar(select(Role).where(Role.code == "staff"))
    if not staff_role:
        return 0

    created = 0
    seq = 1
    for block in data:
        dept_code = block.get("dept_code")
        if not dept_code:
            continue
        dept = await session.scalar(select(Department).where(Department.code == dept_code))
        if not dept:
            continue
        for person in block.get("people") or []:
            last_name = (person.get("last_name") or "").strip()
            first_name = (person.get("first_name") or "").strip()
            middle_name = (person.get("middle_name") or None)
            if not last_name or not first_name or first_name == "-":
                continue
            full = compose_full_name(last_name, first_name, middle_name)
            # inglizcha fan nomlari / shovqin
            if re.fullmatch(r"[A-Za-z .]+", full) and not re.search(
                r"(ov|ova|ev|eva|yev|yeva|vich|ovna|qizi|ogli)$", full, re.I
            ):
                continue
            # mavjud bo'lsa o'tkaz
            if await session.scalar(select(User).where(User.full_name == full, User.is_deleted.is_(False))):
                continue

            base = f"{slugify_email_part(last_name)}.{slugify_email_part(first_name)}"
            email = f"{base}@fjsti.uz"
            n = 2
            while await session.scalar(select(User).where(User.email == email)):
                email = f"{base}{n}@fjsti.uz"
                n += 1

            emp_no = f"EMP-FJSTI-{seq:04d}"
            while await session.scalar(select(StaffProfile).where(StaffProfile.employee_number == emp_no)):
                seq += 1
                emp_no = f"EMP-FJSTI-{seq:04d}"

            user = User(
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                full_name=full,
                email=email,
                citizenship="O'zbekiston",
                password_hash=hash_password(DEFAULT_STAFF_PASSWORD),
                qr_token=generate_token(16),
                status="active",
                notes=f"Manba: fjsti.uz · {dept.name}",
            )
            session.add(user)
            await session.flush()
            session.add(
                StaffProfile(
                    user_id=user.id,
                    employee_number=emp_no,
                    department_id=dept.id,
                    position=person.get("position") or "O'qituvchi",
                    employment_type="asosiy",
                    staff_status="active",
                )
            )
            session.add(Consent(user_id=user.id, consent_type="biometric", granted=True))
            session.add(UserRole(user_id=user.id, role_id=staff_role.id))
            created += 1
            seq += 1
    await session.flush()
    return created


async def seed(session: AsyncSession) -> None:
    for code, name_uz, desc in ROLES:
        if not await session.scalar(select(Role).where(Role.code == code)):
            session.add(Role(code=code, name_uz=name_uz, description=desc))
    await session.flush()

    if not await session.scalar(select(User).where(User.email == settings.admin_email)):
        admin = User(
            last_name="Tizim",
            first_name="Administrator",
            full_name=settings.admin_full_name or "Tizim Administrator",
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            qr_token=generate_token(16),
            citizenship="O'zbekiston",
            status="active",
        )
        session.add(admin)
        await session.flush()
        role = await session.scalar(select(Role).where(Role.code == "admin"))
        if role:
            session.add(UserRole(user_id=admin.id, role_id=role.id))

    await seed_org(session)
    staff_n = await seed_staff_from_fjsti(session)
    mart_n, mart_skip = await seed_staff_from_mart2026(session)
    student_results = await seed_all_students(session)
    stu_n = sum(c for _, c, _ in student_results)
    stu_skip = sum(s for _, _, s in student_results)

    if not await session.scalar(select(AcademicYear).where(AcademicYear.name == "2025/2026")):
        session.add(
            AcademicYear(
                name="2025/2026",
                is_current=True,
                starts_on=date(2025, 9, 2),
                ends_on=date(2026, 7, 15),
            )
        )
    if not await session.scalar(select(AcademicYear).where(AcademicYear.name == "2026/2027")):
        session.add(
            AcademicYear(
                name="2026/2027",
                is_current=False,
                starts_on=date(2026, 9, 1),
                ends_on=date(2027, 7, 15),
            )
        )

    defaults = [
        ("institute_name", "Farg'ona Jamoat Salomatligi Tibbiyot Instituti", "Institut nomi"),
        ("institute_short", "FJSTI", "Qisqa nom"),
        ("institute_address", "Farg'ona shahar, Yangi Turon, 2-a uy", "Manzil"),
        ("institute_phone", "+998 95 062-23-45", "Telefon"),
        ("institute_email", "info@fjsti.uz", "Email"),
        ("institute_website", "https://fjsti.uz", "Rasmiy sayt"),
        ("face_match_threshold", "0.45", "FaceID moslik chegarasi"),
        ("default_password", "ChangeMe123!", "Import uchun default parol"),
        ("id_card_footer", "FJSTI ID - rasmiy identifikatsiya", "ID karta pastki yozuvi"),
        ("support_email", "info@fjsti.uz", "Texnik yordam email"),
        ("allow_self_face_request", "true", "Foydalanuvchi Face yangilash so'rovi"),
    ]
    for key, value, label in defaults:
        row = await session.get(SystemSetting, key)
        if not row:
            session.add(SystemSetting(key=key, value=value, label=label))
        else:
            # real kontaktlarni yangilab turish
            if key in {
                "institute_name",
                "institute_address",
                "institute_phone",
                "institute_email",
                "institute_website",
                "support_email",
            }:
                row.value = value
                row.label = label

    await session.commit()
    n_fac = len((await session.execute(select(Faculty))).scalars().all())
    n_dep = len((await session.execute(select(Department))).scalars().all())
    n_sp = len((await session.execute(select(Specialty))).scalars().all())
    n_staff = len((await session.execute(select(StaffProfile))).scalars().all())
    n_stu = len((await session.execute(select(StudentProfile))).scalars().all())
    n_grp = len((await session.execute(select(StudyGroup))).scalars().all())
    print(
        f"[seed] OK — FJSTI: {n_fac} fakultet, {n_dep} kafedra, {n_sp} yo'nalish, {n_grp} guruh, "
        f"{n_staff} xodim (+{staff_n} fjsti.uz, +{mart_n} Mart2026, skip {mart_skip}), "
        f"{n_stu} talaba (+{stu_n} yangi, skip {stu_skip})"
    )


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
