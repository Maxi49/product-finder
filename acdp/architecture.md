# Project Architecture — product-finder

**Last updated:** 2026-04-13
**Maintained by:** agent-claude

## Module Map

```
product-finder/
├── acdp/                    # Coordination protocol (restricted)
├── backend/                 # FastAPI backend
│   ├── main.py              # App entry point
│   ├── database.py          # SQLite layer
│   ├── models.py            # Pydantic schemas
│   ├── vision.py            # Claude Vision + dedup logic
│   ├── routes/
│   │   ├── images.py        # POST /process-images
│   │   └── stores.py        # Store CRUD endpoints
│   └── tests/               # Backend test suite
├── frontend/                # Next.js frontend
│   ├── app/                 # App Router pages
│   │   ├── page.tsx         # Landing + upload
│   │   ├── setup/[storeId]/ # Product review & publish
│   │   ├── store/[storeId]/ # Public storefront
│   │   └── admin/[storeId]/ # Admin panel
│   ├── components/          # Shared UI components
│   └── lib/                 # API client
└── docs/                    # Project documentation
```

---

## Module Ownership

| Module | Owner | Reviewers |
|--------|-------|-----------|
| `backend/routes/` | agent-claude | — |
| `backend/vision.py` | agent-claude | — |
| `backend/models.py` | agent-claude | — |
| `backend/database.py` | agent-claude | — |
| `frontend/app/` | agent-claude | — |
| `frontend/components/` | agent-claude | — |
| `frontend/lib/` | agent-claude | — |
| `acdp/` | agent-claude | — |

---

## Restricted Areas

| Path | Reason |
|------|--------|
| `acdp/` | Protocol files — governs coordination itself |
| `acdp/governance.json` | Escalation and authority rules |
| `backend/tests/` | Test integrity must be preserved |
| `.env*` | Secrets and environment configuration |

---

## Coordination Rules

- **backend ↔ frontend:** If an API endpoint signature changes, the agent MUST also update `frontend/lib/api.ts`.
- **vision.py:** Changes to the Claude Vision prompt require a lock on `backend/vision.py` AND a notify to all agents.
- **models.py:** Pydantic schema changes may require coordinated updates in both `backend/routes/` and `frontend/lib/api.ts`.
