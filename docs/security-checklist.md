# Xavfsizlik checklist (TT §7)

- [x] Biometrik rozilik (`consents`) enroll oldidan tekshiriladi
- [x] Xom rasm uzoq muddat saqlanmaydi — faqat embedding
- [x] Embedding qo'shimcha `embedding_encrypted` (Fernet)
- [x] HTTPS/TLS — prod da reverse proxy (nginx/caddy) orqali
- [x] RBAC: admin / moderator / student / staff
- [x] Client `allowed_fields` orqali maydon cheklovi
- [x] API key / client secret hash (SHA-256)
- [x] Access log + admin audit log
- [x] Soft-delete + face archive (`archived_at`)
- [x] Zaxira autentifikatsiya: parol + QR token
- [x] Kunlik backup skriptlari (`scripts/backup.*`)
- [ ] Yuridik rozilik shakli institut yuristi bilan tasdiqlash (operatsion)
- [ ] Prod `SECRET_KEY` / `ENCRYPTION_KEY` almashtirish
- [ ] Load test (Locust) pilot oldidan
