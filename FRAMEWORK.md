# LaunchPilot — Project D GTM agent

This is the original agreed scope and acceptance framework. Historical references to one task-authorized live workflow describe the initial implementation task, not a measured success-rate claim. For the current setup and workflow diagram, see [README.md](README.md#architecture). For the later supervised Northstar result, manual corrections and live/offline distinctions, see [SUBMISSION.md](SUBMISSION.md).

## Agreed one-liner
LaunchPilot is an independent, human-approved GTM agent that turns English college-event briefs and calendars into evidence-backed LinkedIn posts, promotional emails, short blogs and ad variations.

## Architecture
- Python + Streamlit UI; LangChain model/tool messages; LangGraph research, clarification, content, review and optional single-revision nodes.
- Research makes a real model tool call to local retrieval; source documents are untrusted data. Retrieve before planning; persist essential facts, audience and tone. Missing/conflicting essentials interrupt for a human answer.
- Local persistent Chroma with sentence-transformers/all-MiniLM-L6-v2. Chunk using the model tokenizer, including special tokens, below the model input limit, with modest overlap and source/page/row metadata.
- SQLite LangGraph checkpoints and an application SQLite store under this workspace. Persist every completed generation stage and recoverable handoff; resume the same thread after restart without replaying completed generation.
- Nebius OpenAI-compatible API, model openai/gpt-oss-120b, reasoning_effort=low. Use private credentials in place, without logging/copying secrets or unrelated configuration. Document settings after compatibility verification.

## State and retention policy
Campaign state contains consent, input/source references, confirmed facts, audience/tone, evidence, drafts, model and deterministic review history, revision count, pending questions, failure handoffs, usage/timing and approval versions. Model review is fallible; critical facts also receive programmatic validation. Any content edit invalidates approvals. All campaign data, source copies, embeddings and checkpoints expire seven days after creation; cleanup runs at startup and before operations. User-downloaded exports remain under user control. No source, prompt or credential logging outside retained campaign state.

## Tools and trust
PDF/TXT text extraction; CSV calendar parsing; campaign-scoped Chroma retrieval exposed as a LangChain tool; human clarification; critical-fact validation; bounded provider adapter; SQLite persistence; approval-gated local download. Uploaded text and human-provided source text never override system instructions. No external sending/publishing integration.

## Approval boundaries
- Explicit consent is required before transmitting source text, spending on generation or writing internal campaign checkpoints. Local extraction/preview precedes consent.
- Draft generation and one revision are permitted after consent. Missing/conflicting facts require clarification, never guessing. Failure handoffs and unresolved review issues persist for human handling.
- Human content approval and separate explicit export approval are required before an export is prepared. No automatic approval or export. Editing approved content invalidates both approvals.
- This implementation task separately authorizes one live workflow using only clearly labelled fictional demo documents and the existing Nebius destination: at most eight provider attempts and 180 active seconds total, including retries and revision. Stop at human approval. Record usage/timing without secrets.

## Acceptance criteria
1. A complete fictional brief/calendar produces four English formats with consistent supported critical facts and source evidence.
2. Missing or conflicting date, time/timezone, venue, price or registration link (and essential event identity/audience) produces persisted clarification; answers resume processing.
3. Research uses real tool-calling retrieval and a conditional clarification path; content and review are separate stages, with at most one revision.
4. Extraction, retrieval, provider and schema failures are explicitly disclosed. Eligible transient failures have bounded retries; other failures persist recoverable handoffs.
5. Restart preserves progress, questions, review history, budget ledger and versioned approvals; completed generation does not repeat on ordinary resume.
6. Seven-day cleanup removes application data, uploads, embeddings and checkpoints; export files are not removed.
7. UI includes upload, consent, progress, clarification, four draft tabs, supporting evidence, review issues, content approval and separate export approval.
8. Run meaningful offline checks first, then the one authorized live fictional workflow within limits. Report actual outcome, usage, timing and blockers. Do not claim real events or audience results.
9. Keep D:\ReviewPilot_VSCode_Backend unchanged. No dashboards, sending/publishing integrations or additional evaluation framework.
