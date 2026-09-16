# Sprint 2 Scope — Full-Stack / Backend

Owner focus: Auth + Admin Document Management (P0), then chat history migration toward localStorage (P1).  
Vocabulary: see root `CONTEXT.md`.

## Out of scope this sprint

- FAQ Entry / FAQ Candidate pipeline and similarity
- Admin Dashboard / Usage Metric instrumentation
- AI Engineer login or AI Config UI
- Dropping or merging the `projects` table
- Advisor RAG “answer refine” details (awaiting separate feedback notes)
- Separate keyword/catalog search UI

## P0 — Admin auth and documents

### Goal

Administrators can sign in and manage the senior-project PDF archive; General Users keep using chat without login.

### Backend

1. **Auth**
   - `POST /api/v1/auth/login` → JWT (`access_token`, `token_type`, `role`, `username`)
   - `GET /api/v1/auth/me` → current Administrator profile
   - Sprint 2 seeds / supports **Administrator** only (AI Engineer later)
2. **Documents (JWT required for mutate/list)**
   - Protect per API Spec: upload, list, delete require Bearer JWT
   - Public PDF fetch by id may remain public (view/download) if already specified as Public
   - Keep `projects` + `documents` relationship as in current models (`project.py` / `document.py`)
3. **Chat**
   - Remains Public; no login gate for General User Q&A

### Frontend

1. Admin login flow and storing token for document admin calls
2. Document Management usable end-to-end with authenticated API (upload / list / download / delete as already planned)
3. General User chat stays usable without auth

### Acceptance (P0)

- [ ] Unauthenticated upload/list/delete are rejected (401/403)
- [ ] Administrator can login, call `/auth/me`, and complete document upload → list → delete
- [ ] Duplicate / corrupt / oversized PDF validation still behaves as current Sprint 2 QA expects
- [ ] General User can still stream chat answers without logging in
- [ ] Only Administrator role is required to demonstrate auth (no AI Engineer UI)

## P1 — Chat history toward localStorage

### Goal

Move what the General User **sees** as history toward browser localStorage, without yet deleting server workspace APIs.

### Behavior

1. Frontend persists Workspace threads in **localStorage** and restores them on load
2. Multi-turn: client sends prior turns (or equivalent history payload) with each query — server does not rely on DB thread as the UX source of truth
3. Existing `/api/v1/chat/workspaces*` may keep working **in parallel** (transitional); do not invent a second long-term source of truth in product copy/UI
4. No new Usage Metric / Dashboard work in this sprint

### Acceptance (P1)

- [ ] Refreshing the browser restores the user’s visible chat threads from localStorage
- [ ] A follow-up question in the same Workspace still gets conversational context via client-sent history
- [ ] Server workspace endpoints still respond (parallel), but UI primary history path is localStorage
- [ ] No FAQ or anonymous personal query-log feature is introduced under the guise of “history”

## Suggested order of work

1. JWT auth module + Admin seed user  
2. Wire document routes to auth dependency  
3. Frontend login + attach Bearer on document admin calls  
4. localStorage Workspace store + send history on query  
5. Keep workspace API parallel; document follow-up to deprecate later  

## Follow-ups (not Sprint 2 exit criteria)

- Deprecate/remove server workspace listing as General User history source (see ADR)
- Usage Metric events without message bodies (Sprint 4 dashboard)
- FAQ candidate source once localStorage-only history is settled
- Optional “สรุปไฟล์นี้” intent detection after advisor refine meeting
