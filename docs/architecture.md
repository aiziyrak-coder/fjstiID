# FJSTI ID — arxitektura

## Maqsad
Markazlashgan Identity Provider + FaceID: bitta hisob, barcha institut dasturlari.

## Komponentlar
- **API (FastAPI):** CRUD, Face enroll/verify, OAuth2/OIDC, webhooks
- **DB (PostgreSQL + pgvector):** foydalanuvchilar, rollar (M2M), biometrik vektorlar
- **Admin / User UI (React):** boshqaruv va shaxsiy kabinet
- **SDK:** Python / JavaScript ulanish

## FaceID oqimi
1. Rasm yuklanadi (xom rasm saqlanmaydi)
2. InsightFace `buffalo_l` embedding (512-d) hisoblanadi
3. Embedding shifrlangan nusxa bilan `face_biometrics` ga yoziladi
4. Verify: cosine distance (`<=>`) + `FACE_MATCH_THRESHOLD`

## Xavfsizlik
- Consent majburiy enroll oldidan
- Encryption at rest (Fernet) + TLS prod da
- Client `allowed_fields` / scopes
- Access + admin audit log
- Soft-delete + biometrik arxivlash

## OAuth2
- Authorization Code: `/oauth/authorize` → `/oauth/token`
- Client Credentials: server-to-server
- Discovery: `/.well-known/openid-configuration`
