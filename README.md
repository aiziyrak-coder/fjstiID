# FJSTI ID

Farg'ona Jamoat Salomatligi Tibbiyot Instituti — yagona identifikatsiya va FaceID platformasi.

## Stack
- Backend: Python FastAPI + SQLAlchemy + Alembic
- DB: PostgreSQL 16 + pgvector
- Face: InsightFace (`buffalo_l`), fallback mock embeddings
- Frontend: React + Vite + TypeScript (uz/ru/en)
- SSO: OAuth2 / OIDC

## Tezkor start (Docker)

```bash
docker compose up --build
```

- API: http://localhost:8000/docs
- UI: http://localhost:5173
- DB (host): `localhost:55432`
- Admin: `admin@fjsti.uz` / `.env` dagi `ADMIN_PASSWORD` (default: `Admin123!`)

Seed: tizim admini + FJSTI rasmiy fakultet/kafedra/yo‘nalishlar + fjsti.uz kafedra sahifalaridagi professor-o‘qituvchilar.

Xodim login: `familiya.ism@fjsti.uz` / `FjstiXodim123!`

Prod FaceID: `FACE_PROVIDER=insightface` + `requirements-face.txt`.

## Lokal (Docker faqat DB)

```bash
docker compose up -d db
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

## SDK

```python
from fjsti_id import FjstiClient
client = FjstiClient("http://localhost:8000", "fjsti_...")
print(client.verify_face("face.jpg"))
```

```js
import { FjstiClient } from "./sdk/js/fjsti-id.js";
const client = new FjstiClient("http://localhost:8000", "fjsti_...");
```

Davomat demo:
```bash
cd sdk/python
pip install -e .
set FJSTI_API_KEY=...
python examples/davomat_demo.py --image path\to\face.jpg
```

## Backup
```bash
# Linux/macOS
./scripts/backup.sh
# Windows
.\scripts\backup.ps1
```

## Load test
```bash
pip install locust pillow
locust -f scripts/locust_face.py --host http://localhost:8000
```

## Muhim env
| O'zgaruvchi | Maqsad |
|---|---|
| `SECRET_KEY` | JWT |
| `ENCRYPTION_KEY` | Biometrik shifrlash |
| `FACE_MATCH_THRESHOLD` | Cosine distance chegarasi (default 0.45) |
| `FACE_PROVIDER` | `insightface` yoki `mock` |

Batafsil: [docs/architecture.md](docs/architecture.md), [docs/data-model.md](docs/data-model.md), [docs/security-checklist.md](docs/security-checklist.md), [docs/operator.md](docs/operator.md)
