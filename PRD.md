# MemoMate: Product Requirements Document

**Hackathon:** MongoDB Student Hackathon, Track 1 (Agentic Memory)
**One-liner:** A personal diary and planner that remembers what you like, uses it to plan your days, and updates itself when you change.

---

## 1. Problem

AI chatbots forget everything between sessions. Users repeat the same preferences ("I study at night", "I'm vegetarian", "gym on weekdays") every time, and plans ignore context the user already shared. Tools that do remember often keep stale or wrong information, because they never update or forget.

## 2. Target user

Students and young professionals who journal, plan their week, and want an assistant that adapts to them over time.

## 3. Goals

| Goal | Measured by |
|---|---|
| Memory changes behavior | A plan in session 2 uses a preference from session 1 without the user repeating it |
| Memory stays correct | A contradicting statement replaces the old memory, not duplicates it |
| Memory is transparent | Every reply shows which memories were used and why (similarity score) |
| Memory respects the user | Users can view, edit, and delete memories; sensitive data is never stored |

**Non-goals (out of scope):** mobile app, login/authentication, calendar sync, multi-user sharing, voice.

## 4. User stories

1. As a user, I write about my day and MemoMate quietly saves anything useful about me.
2. As a user, I ask "plan my week" and get a plan that fits my known preferences and upcoming events.
3. As a user, I say "actually I like mornings now" and MemoMate updates the old preference.
4. As a user, I see a list of everything MemoMate remembers and can delete any item.
5. As a user, I say "forget that I told you about X" and it's gone.
6. As a user, time-bound things (an exam on Friday) disappear automatically once they've passed.
7. As a user, I trust that passwords, phone numbers, and ID numbers are never saved.

## 5. Functional requirements

### FR1: Memory capture
- After each user message, an LLM extracts zero or more memories as JSON: `type`, `content`, `expires_on`.
- Memory types: `preference`, `fact`, `goal`, `mood`.
- Expiry rules: dated facts expire the day after the event; moods expire after 3 days; preferences and goals never expire.

### FR2: Semantic recall
- Each memory is embedded on save.
- Before replying, MongoDB Vector Search retrieves the top 5 memories relevant to the current message.
- Results are filtered to `user_id = current user` and `status = "active"`.
- Retrieved memories, with their similarity scores, are passed to the chat model and shown in the UI.

### FR3: Update and conflict handling (key hard case)
- When a new memory is saved, Vector Search finds the 3 most similar active memories of the same user.
- An LLM decides for each: `replaces`, `duplicate`, or `unrelated`.
  - `replaces`: old memory gets `status: "replaced"` and `replaced_by: <new id>`; the new one is saved.
  - `duplicate`: the new memory is not saved; the old one's `updated_at` is refreshed.
  - `unrelated`: the new memory is saved normally.
- Replaced memories are kept as history and visible in the inspector.

### FR4: Expiry
- A TTL index on `expires_at` auto-deletes expired memories.

### FR5: Forget
- A 🗑 button on each memory in the sidebar deletes it.
- A chat command ("forget …") finds the closest matching memory via Vector Search and deletes it after showing what will be removed.

### FR6: Privacy guard
- The extraction prompt forbids storing passwords, phone numbers, emails, addresses, bank or ID numbers.
- A regex check in code blocks any memory containing digit sequences of 6+, email patterns, or phone patterns, as a second safety layer.

### FR7: Memory inspector
- Sidebar lists active memories grouped by type, with expiry dates.
- A "History" toggle shows replaced memories and what replaced them.
- Each assistant reply has an expandable "Memories used" section with content and similarity score.

## 6. Data model (MongoDB, database `memomate`)

### `memories`
```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "type": "preference | fact | goal | mood",
  "content": "string",
  "embedding": [/* float array, dims match the embedding model */],
  "source": "original user message",
  "status": "active | replaced",
  "replaced_by": "ObjectId | null",
  "created_at": "Date",
  "updated_at": "Date",
  "expires_at": "Date | null"
}
```

### `messages`
```json
{
  "_id": "ObjectId",
  "user_id": "string",
  "role": "user | assistant",
  "content": "string",
  "memories_used": [{ "memory_id": "ObjectId", "score": 0.82 }],
  "created_at": "Date"
}
```

### Indexes
- **Vector Search index** `memory_vector_index` on `memories.embedding` (cosine), with filter fields `user_id`, `status`, `type`.
- **TTL index** on `memories.expires_at` (`expireAfterSeconds: 0`).
- **Regular index** on `messages` `{ user_id: 1, created_at: -1 }`.

## 7. Architecture

```
Streamlit UI (app.py)
   │
   ├── brain.py  → LLM: extract memories, judge conflicts, write replies
   ├── embeddings.py → embedding model (Voyage AI)
   └── db.py     → MongoDB Atlas: messages, memories, vector search, TTL
```

**Per-message flow:**
1. Save the user message.
2. Extract candidate memories → privacy filter → embed.
3. For each candidate: find similar memories → conflict check → save, replace, or skip.
4. Embed the user message → Vector Search for the top 5 relevant memories.
5. Generate the reply with those memories → save the reply with `memories_used`.
6. Show the reply, the "Memories used" panel, and any "Saved / Updated" notices.

## 8. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.10+ |
| UI | Streamlit |
| Database | MongoDB Atlas (free M0) with Vector Search |
| LLM | Anthropic Claude (Sonnet for chat, Haiku for extraction and conflict checks) |
| Embeddings | Voyage AI (dimension must match the vector index) |
| Config | `.env` via python-dotenv |

## 9. Demo script (3 minutes)

1. **Create memory:** "I study best at night and hate mornings. DBMS exam on Friday." → sidebar shows a preference and a fact with an expiry date.
2. **Memory changes the result:** Switch user and back (new session) → "Plan my day tomorrow." → plan puts study at night, and "Memories used" shows why.
3. **Inspect:** Open the memory in MongoDB Atlas or the inspector; explain its fields and similarity score.
4. **Hard case, correction:** "Actually I've started waking up early, mornings work now." → old preference marked `replaced`; ask for a plan again → study moves to morning.
5. **Hard case, forget and privacy:** "Forget my exam." → deleted. "My phone number is 98xxxxxx12." → not stored.

## 10. Milestones

| # | Milestone | Done when |
|---|---|---|
| M1 | Starter app (done) | Chat works, memories extracted and shown |
| M2 | Embeddings + Vector Search | Replies use only relevant memories, with scores shown |
| M3 | Conflict handling | Correction replaces the old memory, history visible |
| M4 | Forget + privacy guard | Chat "forget" works; sensitive data blocked |
| M5 | Inspector + polish | "Memories used" panel, history toggle, demo seed script |

## 11. Risks

| Risk | Mitigation |
|---|---|
| LLM returns bad JSON | Strip fences, try/except, fall back to no memories |
| Vector index not ready | Seed script + clear setup steps in README |
| Wrong conflict decisions | Only compare same-type memories; keep history so mistakes are recoverable |
| API costs | Haiku for background calls; short prompts |