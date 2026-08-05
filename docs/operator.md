# Operator qo'llanma — FJSTI ID

## O'rnatish (on-premise)

1. Docker Desktop / Docker Engine o'rnating
2. Repozitoriyni oching: `E:\FjstiID`
3. `backend/.env` dagi `SECRET_KEY` va `ENCRYPTION_KEY` ni prod uchun almashtiring
4. Ishga tushirish:

```bash
docker compose up --build -d
```

- UI: http://localhost:5173  
- API/Swagger: http://localhost:8000/docs  
- DB host port: **55432** (ichki 5432)

Admin: `admin@fjsti.uz` / `Admin123!` (darhol o'zgartiring)

## FaceID enroll

1. Admin → Foydalanuvchilar → yangi talaba/xodim
2. **Consent** tugmasi (biometrik rozilik)
3. **Enroll** — yuz rasmini yuklash
4. FaceID sahifasida kameradan tekshirish

Prod da: `FACE_PROVIDER=insightface` va `pip install -r requirements-face.txt`

## Yangi dastur ulash

1. Admin → Dasturlar → yaratish
2. `client_id`, `client_secret`, `api_key` ni bir marta saqlang
3. `allowed_fields` orqali maydonlarni cheklang
4. SDK:

```python
from fjsti_id import FjstiClient
c = FjstiClient("https://id.fjsti.uz", "fjsti_...")
c.verify_face("capture.jpg")
```

## Backup

```powershell
.\scripts\backup.ps1
```

Kunlik Task Scheduler orqali ishga tushiring.

## Pilot

1. Bitta fakultet/guruhni import qiling (`docs/sample_users.csv`)
2. Face enroll
3. Davomat demo: `sdk/python/examples/davomat_demo.py`
4. Audit jurnallarni kuzating
