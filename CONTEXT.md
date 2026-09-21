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
A browser-local anonymous chat thread identified by `workspace_id`. The product target is localStorage as what the General User sees; server workspace APIs may remain temporarily in parallel until removed.
_Avoid_: Project, user account, treating the `projects` table as a chat Workspace

**Search Query**:
One user question and its generated answer within a Workspace. Multi-turn context is sent by the client with later requests. Server-stored threads are not the long-term source of truth for General User history.
_Avoid_: Search (as a separate catalog feature); FAQ Entry

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
