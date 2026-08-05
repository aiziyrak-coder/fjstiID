# FJSTI ID — ma'lumotlar modeli (ideal)

## Asosiy tamoyil
Shaxs **bitta** (`users`). Rol, o'qish va ish ma'lumotlari **alohida** jadvallarda.
Pasport va manzil ham alohida — chalkash "bitta katta jadval" emas.

```
users ──1:1── identity_documents   (pasport)
      ──1:1── addresses            (yashash manzili)
      ──1:1── emergency_contacts
      ──1:1── student_profiles     (Talaba ID + o'quv)
      ──1:1── staff_profiles       (Xodim ID + ish)
      ──M:N── roles                (student, staff, admin, ...)
      ──1:N── face_biometrics
      ──1:N── consents
```

## Tashkilot
```
faculties → specialties → study_groups
faculties → departments (ixtiyoriy bog'lanish)
```

## Unikal identifikatorlar
| Maydon | Jadval | Ma'nosi |
|---|---|---|
| `users.pinfl` | users | JSHSHIR (14 raqam) |
| `student_profiles.student_number` | student | Talaba ID |
| `staff_profiles.employee_number` | staff | Xodim / tabel ID |
| `identity_documents.series+number` | document | Pasport |

## API javob tuzilishi
```json
{
  "id": "...",
  "full_name": "Aliyev Sardor Olimovich",
  "pinfl": "...",
  "document": { "series": "AA", "number": "1234567" },
  "address": { "region": "...", "full_text": "..." },
  "emergency": { "full_name": "...", "phone": "..." },
  "student": { "student_number": "STU-2025-001", "faculty_name": "..." },
  "staff": null,
  "roles": [{ "code": "student", "name_uz": "Talaba" }]
}
```
