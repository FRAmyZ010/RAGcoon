# RAGcoon

A web Q&A system over Computer Engineering senior project PDF archives, grounded by Retrieval-Augmented Generation so answers stay tied to retrieved sources.

## Language

### Actors

**General User**:
An anonymous visitor who asks natural-language questions and reads cited answers without signing in.
_Avoid_: Guest account, registered student (unless Admin/AI Engineer), client

**Administrator**:
An authenticated operator who manages the document archive, usage monitoring, feedback review, and future FAQ approval.
_Avoid_: Superuser, owner, “admin user” as a synonym for every staff role

**AI Engineer**:
An authenticated operator who selects LLM/RAG settings inside the product and evaluates retrieval quality.
_Avoid_: Treating AI Engineer as only a team job title with no login; merging this role into Administrator permanently

### Knowledge archive

**Project**:
A CE senior project’s durable metadata record (e.g. title, academic year, advisor, authors) stored in the `projects` table and associated with one or more Documents.
_Avoid_: Workspace, chat thread, using Project for browser conversation state

**Document**:
A PDF file in the archive that belongs to a Project (file path, ingestion status, and document-level fields such as keywords).
_Avoid_: Calling the PDF a Workspace; treating Document as the chat history store

**Citation**:
A pointer from an answer back to retrieved source material (document/chunk evidence) shown to the General User.
_Avoid_: Reference, link, source (as vague synonyms without the citation meaning)

### Conversation

**Workspace**:
A browser-local anonymous chat thread identified by `workspace_id`. Workspace history and thread messages are managed only in browser `localStorage`. The Frontend does not call `GET /workspaces*`. Server workspace APIs may still exist until a later removal, but they are not the history source for the UI.
_Avoid_: Project, user account, treating the `projects` table as a chat Workspace; loading Sidebar Recents from the server

**Search Query**:
One user question and its generated answer within a Workspace. Multi-turn context is sent by the client on `POST /api/v1/chat/query-stream` as `messages` (at most the latest 3 turns). The UI stores the assistant role as `'bot'` and maps it to `'assistant'` in that payload. `parent_query_id` stays on the request schema for database compatibility and is not sent by the Frontend. Completed or errored streams are logged to PostgreSQL `search_queries` via `BackgroundTasks`. Server-stored threads are not the long-term source of truth for General User history.
_Avoid_: Search (as a separate catalog feature); FAQ Entry; sending `parent_query_id` from the Frontend

### FAQ

**FAQ Entry**:
An Admin-approved question–answer pair published for reuse. Not in early sprint scope; similarity matching is undecided.
_Avoid_: Chat history, Search Query, undocumented “cached answer”

**FAQ Candidate**:
A proposed FAQ item pending Administrator approval. Collection mechanism is explicitly deferred while chat history remains browser-local.
_Avoid_: Calling an unapproved candidate an FAQ Entry

### Retrieval behavior

**Metadata Filter**:
Structured constraints (such as title, author, year, advisor) extracted from the question and applied inside retrieval — not a separate keyword-search product surface.
_Avoid_: Keyword search page, catalog search, “search feature” as distinct from Chat Q&A

### Usage signals

**Usage Metric**:
Anonymous operational signal for monitoring (e.g. visit counts, search counts, latency) without storing the General User’s message thread. Not a Sprint 2 focus.
_Avoid_: Chat history, Workspace transcript, personal query log

## Sprint 2 P1 Architecture Locks

### Client-side history (localStorage only)

- Workspace history and thread messages live only in browser `localStorage`.
- The Frontend does not call or implement `GET /workspaces*`.
- A draft "New Chat" thread is not added to Sidebar Recents until the first response stream is successfully saved.
- Sidebar Recents includes a manual thread deletion button.
- On refresh, the app loads the latest thread from `localStorage`. If that data is corrupted, it falls back to "New chat".

### API payload and role mapping (`POST /api/v1/chat/query-stream`)

`ChatRequest` accepts:

- `workspace_id` (str)
- `query_text` (str)
- `messages` (list of `ChatMessage`, capped at the latest 3 turns)

`parent_query_id` remains on the Pydantic schema for database backwards-compatibility. The Frontend does not send it.

The Frontend UI stores the assistant role as `'bot'` and maps `'bot'` to `'assistant'` when building the API request payload.

### Backend and RAG session wiring

Import `session_manager` as the instance, not the module:

`from app.rag.retrieval.session_manager import session_manager`

On each stream request: take at most 3 turns from `messages`, call `session_manager.clear_session()`, sync those client messages into `session_manager`, then run the RAG pipeline.

### Persistence and logging

Completed streams, and streams that error midway, log query, answer, sources, citations, and timing to PostgreSQL `search_queries` via `BackgroundTasks`.
