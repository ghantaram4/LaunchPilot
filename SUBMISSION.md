# Project D submission: LaunchPilot

**Independent GTM agent for English college-event campaigns.** This is the source text for the required Google Doc. Repository, Google Doc and recording links remain pending in [submission/CHECKLIST.md](submission/CHECKLIST.md). No upload, push or publication was performed while preparing this package.

**Submission sample:** campaign `e71f3548-b1c2-4969-9841-396ef719c46d`, approved working version **5**, Northstar College Portfolio Lab. All event data is fictional; the example.org registration URL is a placeholder. No actual audience, engagement, registrations or campaign-performance results are claimed.

## Overview and one-liner

LaunchPilot turns a college-event brief and calendar into a LinkedIn post, promotional email, short blog and three ad variations. It retrieves local source evidence, identifies facts and audience, pauses for missing/conflicting essentials, drafts, reviews, and leaves approval and export to a human. It is independent of the other ReviewPilot workspace.

**Agreed one-liner:** LaunchPilot is an independent, human-approved GTM agent that turns English college-event briefs and calendars into evidence-backed LinkedIn posts, promotional emails, short blogs and ad variations.

The working interface has upload and local extraction preview, explicit generation consent, progress, clarification/failure handoffs, four editable draft tabs, evidence, review history, versioned approval and separately approved download. It has no external sending or publishing integration.

## Actual implementation and architecture

The stack is Python, Streamlit, LangChain, LangGraph, local persistent Chroma, sentence-transformers/all-MiniLM-L6-v2 and persistent SQLite LangGraph checkpoints. Application SQLite separately stores current working drafts, consent, approval audit and provider attempts/usage. This is an explicit graph with separate stages, rather than one generation prompt presented as several agents.

```text
Upload PDF/TXT brief + select one CSV event row
  -> local extraction/preview -> explicit consent -> persisted campaign
  -> research: model requests retrieve_sources
  -> retrieve: execute local Chroma tool; retain matches and full-source audit
  -> plan: facts, supporting quotes/IDs, audience, tone and approach
  -> gate: validate essentials and source conflicts
       -> clarification interrupt -> human answers -> gate
       -> content: four formats -> model + deterministic review
            -> if issues and no revision yet: one revision -> review again
            -> finish: human review
Any eligible stage failure -> persisted handoff -> explicit retry of that stage
Human draft edits -> new working version -> invalidate both approvals
Human content approval -> separate export approval -> local Markdown download
```

The graph finish status remains `awaiting_human_review` even after approval because approvals live in application state. The verified approval records and their draft digests, rather than that graph status alone, establish the approval of working version 5.

| Component | Implemented responsibility |
|---|---|
| `app.py` | Streamlit upload, preview, consent, progress, questions, four tabs, evidence and approval/export controls |
| `launchpilot/ingest.py` | Text-based PDF/TXT extraction, strict CSV parsing, selected-row metadata and labelled fact candidates |
| `launchpilot/retrieval.py` | Model tokenizer, overlapping source chunks, local embeddings, campaign-isolated persistent Chroma and `retrieve_sources` LangChain tool |
| `launchpilot/workflow.py` | Research, retrieval, planning, conditional clarification, content, review, at most one revision, and failure interrupts |
| `launchpilot/facts.py` | Quote/ID support checks, essential field validation, conflict detection, canonical logistics blocks and deterministic checks |
| `launchpilot/provider.py`, `worker.py` | Nebius requests, killable worker, bounded retry/budget ledger, response cache and JSON schema validation |
| `launchpilot/storage.py`, `service.py`, `retention.py` | SQLite application persistence, guarded edits, approval checks, audit and seven-day cleanup |
| `launchpilot/diagnostics.py` | Sanitized error chains and source-free connectivity check; no model invocation |

## Source data and provenance

The submitted campaign used the uploaded **FICTIONAL_event_brief.pdf**, page 1 (`brief:p1`), and **FICTIONAL_event_calendar.csv**, row 2 (`calendar:r2`; row 1 is the header). The original upload hashes were checked against the saved metadata during packaging.

| Source | SHA-256 of original upload |
|---|---|
| Brief PDF | `fc1400aa888bdbee8299b91016769e24fc68d97b10d45b8d9c60f9d65fc63e16` |
| Calendar CSV | `ac7fbd7e1e16e0c751679d52f593fc797b89b405dfa60c1674aa104537121df9` |

For repository review, [the extracted fictional brief](submission/source_data/FICTIONAL_NORTHSTAR_BRIEF_EXTRACTED.txt) preserves the stored PDF text; it is labelled as an extraction, not the original PDF. [The fictional calendar copy](submission/source_data/FICTIONAL_NORTHSTAR_CALENDAR.csv) is a byte-for-byte copy of the uploaded CSV. These are explicit public sample artifacts, not a copy of the runtime database or source-upload directory.

| Confirmed field | Value | Provenance |
|---|---|---|
| Event | Northstar College Portfolio Lab | Brief p1; calendar row 2 |
| Date | 2027-03-13 | Brief `date:`; calendar row 2 |
| Time | 10:00–12:30, Asia/Kolkata | Brief start/end/timezone fields; calendar row 2 |
| Venue | Seminar Hall B, Northstar College, Fictional City | Brief `venue:`; calendar row 2 |
| Price | Free | Brief `price:`; calendar row 2 |
| Registration | https://events.example.org/northstar-portfolio-demo | Brief and calendar; fictional placeholder |
| Audience | Northstar College final-year undergraduate students | Brief `audience:`; calendar row 2 |
| Eligibility | Registration is restricted to Northstar College final-year undergraduate students | Explicit narrative statement in brief p1; not inferred merely from target audience |
| Tone | Friendly, practical and clear; avoid hype and guarantees | Brief `tone:`; calendar row 2 |
| Activities/preparation | Portfolio-structure discussion, short project-description writing exercise, peer feedback; bring notes about one academic project; no prior portfolio-building experience required; laptop optional | Brief narrative, p1 |

The source excludes confirmed speakers, sponsors, certificates, prizes, food, capacity limits, registration deadlines, placements and guaranteed career outcomes. Uploaded documents are treated as data, not instructions. The current sources agree; the campaign contains no human fact-confirmation history or unanswered graph questions.

## Retrieval, agents and tools

Research uses a real model tool call, followed by actual local execution and a planning request containing the `ToolMessage`. The saved call is `retrieve_sources` with query **`event brief calendar row`**. It returned three chunks: `calendar:r2:c0`, `brief:p1:c0` and `brief:p1:c196`. Their recorded token counts, including special tokens, are **98, 222 and 91**, respectively. This demonstrates execution of the tool, not a claim about retrieval quality across other briefs.

MiniLM's own tokenizer creates up to 220 content-token chunks with 24-token overlap; every final chunk is checked to be strictly below its 256-token model input limit. Exact text spans and filename, source ID, page/CSV row, hash, token count and character offsets remain attached. Search uses normalized local embeddings and cosine distance, returning up to eight available matches. A full-source audit accompanies matches so a conflicting fact cannot be hidden solely by top-k selection. This also means a consenting user's full scoped source text, not just nearest chunks, can reach Nebius during planning.

The planning stage extracts supported facts and audience/tone. The deterministic gate compares labelled/CSV candidates and supported model facts; missing, invalid or conflicting essentials trigger clarification. Values use explicit date/time/timezone/currency/HTTPS formats. Clarification answers become human source references; source conflicts are never silently resolved by choosing one file.

The content stage produces all formats in one separate request. Code appends a common confirmed logistics block to each format and each ad. The review stage critiques support, consistency and tone, alongside deterministic checks. It can request one revision and one subsequent review. Remaining issues go to a human. This campaign had **zero automated revisions**: its model reviewer reported no issues, yet human review still led to corrections.

Tools are limited to extraction/parsing, local source retrieval, human clarification, fact validation, local persistence, guarded editing and approved local download. There is no web research tool, email sender, ad-platform tool or social publishing tool in the application.

## State, recovery and retention

Each campaign retains source copies/references, extracted facts and quotes, audience/tone, evidence, original generated drafts, review history, questions/answers, revision count, failure handoff, current working drafts, provider usage/timing and approval records. LangGraph uses `SqliteSaver` with synchronous checkpoints; it does not use memory-only checkpoints. Application edits use `Service.edit` with `expected_version`, increment the working version, append audit history and clear content/export approval.

Successful provider results are also cached by stage and input hash. Normal restart/resume reuses completed stages. An ambiguous in-flight request after a crash requires acknowledgement before a potentially duplicate charge. Exactly-once execution cannot be guaranteed if the process dies after a provider response but before it can be saved. Older working versions are represented by original graph state, edit/approval audit and any retained user exports; the application does **not** store a full text snapshot for every manual edit.

Campaign-managed uploads, Chroma, application SQLite, checkpoints and diagnostics expire seven days after creation. This campaign expires **15 November 2026 at 13:15:15.786 IST**. Cleanup runs at startup, before service operations and every five minutes while the server runs. A stopped server cannot perform deletion; overdue data is removed on restart unless the documented cleanup command is scheduled separately. No Windows scheduled task was installed. User-requested sample files and downloads remain user controlled. Deletion does not promise forensic erasure of backups.

## Consent and approval boundaries

Explicit consent authorizes source transmission to the fixed Nebius destination, paid generation and internal checkpoint writes. Local extraction preview happens first. Credentials are read securely in place and never included in prompts, outputs or repository artifacts. Tracing and optional telemetry are disabled.

The provider is `openai/gpt-oss-120b` at `https://api.tokenfactory.nebius.com/v1/`, with `reasoning_effort=low`, `temperature=1`, explicit `max_tokens`, SDK retries disabled and bounded application retries. The adapter preserves Nebius's `max_tokens` spelling through `extra_body` because this LangChain version otherwise renames that field. Research forces the named tool, with parallel calls disabled; JSON stages use JSON-object mode and Pydantic validation.

Each campaign permits at most eight provider attempts and 180 active seconds across stages/retries. This campaign used all eight attempts. No further model request is necessary or authorized for submission preparation.

Human content approval and a separate explicit export approval are required for the current draft digest. Editing invalidates both. Version 4 had approvals; the version-5 edit cleared them; the human subsequently approved version 5 and separately approved export. Packaging verified those existing approvals read-only and copied an existing download. It did not approve content, regenerate it or call the exporter again.

## Coding prompts and iterations

These are excerpts or faithful summaries of the actual development requests, not a fabricated complete prompt transcript. The implementation prompts and agent instructions can be inspected in `workflow.py` and the Pydantic contracts in `models.py`.

| Step | Coding instruction or iteration | Result and evidence |
|---|---|---|
| Scope first | “First save FRAMEWORK.md … Then implement the working application; do not stop at a plan.” | Framework saved first, then Python/LangGraph/Streamlit implementation; independent workspace preserved |
| Workflow and safety | Real tool-calling retrieval, conditional clarification, persistent Chroma and SQLite checkpoints, one revision, consent, separate export approval | Implemented separate stages, guarded state and offline recovery tests |
| Provider compatibility | Nebius GPT-OSS low reasoning with compatible settings; bounded attempts and time | Offline transport inspection verified request fields; this campaign later completed four successful stages |
| Connection diagnosis | Diagnose repeated `OpenAIConnectionError`; inspect real process/context; no model requests during diagnosis | Four saved failures inspected; restricted process and source-free socket denial observed; server restarted outside the restricted context; future sanitized diagnostics added |
| Manual wording/eligibility corrections | Human edits revised LinkedIn/blog and made eligibility explicit; versions 2–4 are present in the audit | Review history retained; audit records edit timestamps and later version-4 approvals, but not every intermediate text body |
| Exact version-5 correction | Insert the restriction sentence before “Register today”; delete only old Ad variation 2 copy while keeping “Explore portfolio structure…” | `Service.edit` used current guard 4, saved version 5, invalidated approvals and verified both changes without provider calls |
| Final approval | Subsequent human actions approved version 5 and separately approved its export | Existing version-5 approval digests/timestamps verified; matching downloaded Markdown found |
| Submission | Prepare documentation, a short demo script and a labelled sample of the approved export; no regeneration or publishing | This package; source/runtime separation and read-only campaign verification |

The runtime system prompt explicitly treats source documents/tool results as data, prohibits invented claims and approval by the model, and requires supporting source IDs/quotes. Content instructions ask for narrative copy plus application-rendered logistics. These instructions improve boundaries but do not establish semantic correctness: the model planner even proposed a testimonial-style quote not present in the source; no such quote is in the submitted sample. Model review did not remove the need for human checking.

## Actual results for this campaign only

All timestamps below are **8 November 2026, Asia/Kolkata (UTC+05:30)**. Values come from this campaign's application SQLite ledger, checkpoint timestamps and approval audit. They are not measurements from the earlier Aster demonstration recorded in `VALIDATION.md` or `REVIEW_PACKET.md`.

| Recorded milestone | IST timestamp |
|---|---|
| Campaign creation and consent | 13:15:15.786 |
| First persisted provider-failure handoff | 13:15:21.917 |
| Second persisted failure handoff after retry | 13:19:48.075 |
| Successful research attempt started | 13:32:13.020 |
| Generated drafts/review finished; graph awaits human review | 13:32:42.804 |
| Working version 2 saved | 13:39:26.422 |
| Working version 3 saved | 13:45:33.131 |
| Working version 4 saved | 13:49:37.581 |
| Version 4 first content/export approvals | 13:51:51.937 / 13:51:54.378 |
| Version 4 later content/export approvals | 13:54:17.406 / 13:54:19.243 |
| Working version 5 saved; both approvals invalidated | 13:59:05.361 |
| Version 5 content approval | **14:04:15.234** |
| Version 5 separate export approval | **14:04:17.129** |

### Processing and elapsed time

| Processing/elapsed measure | Actual value and interpretation |
|---|---|
| Provider attempts | **8 total: 4 failed research attempts, then 4 successful requests** |
| Successful requests | Research/tool request, plan, content bundle, review |
| Saved active workflow processing | **41.485 seconds**; across runs, including local work/retries; excludes time waiting for the user |
| Sum of provider worker durations | **26.890 seconds** including worker/SDK overhead; 10.562 failed + 16.328 successful |
| Final successful segment, start of attempt 5 to final checkpoint | **29.784 seconds** wall time; distinct from cumulative active processing |
| Creation to generation/review completion | **17 minutes 27.018 seconds** elapsed; includes interruption and troubleshooting |
| Creation to version-5 content approval | **48 minutes 59.449 seconds** elapsed |
| Creation to version-5 export approval | **49 minutes 1.343 seconds** elapsed |
| Reported successful-call input/output/total tokens | **6,922 / 1,572 / 8,494** |
| Failed attempts without usage data | **4**; usage/billing unknown, not counted as zero |
| Automated revision count | **0** |
| Outputs | Four formats, including three ad variations; human-edited approved working version 5 |

Elapsed time through approval includes interruptions, diagnosis, manual editing, review and idle time. It is not model latency, and it should not be described as all-human review time. No monetary bill was returned or verified. Known token totals exclude the four failed attempts with missing usage.

Read-only verification confirmed current working version 5, `human_reviewed=true`, and matching content/export approval digests:

```text
de725b4a83ecc2c476856199982753e84cef72ed5fd0b139bfd82f9a9777d835
```

The [labelled sample-output file](submission/SAMPLE_OUTPUT_FICTIONAL_APPROVED_v5.md) is a byte-for-byte copy of the existing downloaded version-5 export, **6,067 bytes**, SHA-256:

```text
56ce9f7b5e2bb22cd7e17f98855a8445b2452f390c66f911c0e4c2c969a8cd8c
```

All four formats contain the confirmed logistics block. The email now includes the explicit restriction immediately before “Register today”. Ad variation 2 retains the revised portfolio-structure sentence and no longer contains the duplicated “Build your academic showcase…” passage. The sample is an approved result from one fictional input pair, not a benchmark or evidence of general accuracy.

## What was tested live, offline or not tested

| Scenario | Evidence category | What can be claimed |
|---|---|---|
| PDF/CSV extraction, real model-requested retrieval, planning, four drafts and review | **Live, this campaign** | Original PDF/CSV hashes, actual tool call, three evidence chunks, four successful request/usage records and saved outputs |
| Repeated provider failure, persistent handoff and explicit recovery | **Live, this campaign** | Four connection failures, two checkpointed handoffs, successful later resume after a real server restart |
| Precise historical DNS/socket/TLS/proxy cause | **Unknown for historical model failures** | Old code discarded the chain. Source-free diagnosis separately observed restricted-token socket denial (`WinError 10013`) and normal-context HTTP 405 over TLS; it did not prove the old request's exact chain |
| Missing/conflicting essentials and invalid clarification answer | **Offline, scripted provider/local fixtures** | Both missing/conflicting inputs paused, persisted and resumed; invalid answers stayed pending. **No live clarification in this campaign:** history and pending questions are empty |
| Local retrieval failure and explicit retry | **Offline, injected failure** | Saved handoff and stage-specific retry; no live Chroma outage was induced |
| Malformed JSON or tool arguments | **Offline, scripted responses** | Validation and recoverable handoff; no live Nebius malformed-output test |
| Transient/nontransient retries, killable timeout, attempt/time exhaustion | **Offline, fake worker/MockTransport** | Control flow and limits exercised; no deliberately induced live 429/5xx/timeout or extra budget-exhaustion model call |
| DNS/TLS/proxy/timeout diagnostic classification and redaction | **Offline, synthetic exceptions** | Types/codes retained without raw secrets/source; source-free real probes are separate from model calls |
| Real MiniLM chunks, persistent Chroma, isolation and expiry cleanup | **Offline with real local libraries** | Token limits/overlap, reopening, isolation and simulated expired-time cleanup; no claim of a seven-day live soak |
| Completed-generation restart without regeneration, uncertain in-flight guard | **Offline scripted workflow + fresh Python process** | Persistence/control flow verified; a mid-provider crash was not induced live in this campaign |
| Manual edits invalidate approvals, followed by new human approval/export | **Live service/UI audit, this campaign** | Version-4 approvals, version-5 edit/invalidation, version-5 approvals; matching downloaded export exists |
| Adversarial prompt-injection resilience, load/concurrency, broad quality/accuracy | **Not tested as live evaluations** | Prompt boundaries and locks exist; no robustness, audience-performance or general-accuracy claim |

Recorded development checks were 31 offline application checks, followed later by 8 focused diagnostic checks. These were separate historical runs, not a newly executed combined 39-test suite. Packaging performs read-only state/export/hash verification and static source-package checks, not another evaluation campaign.

## Limitations and learnings

- A review model can miss issues even when it returns no findings. Eligibility, implied outcomes and duplicated copy required human correction here; approval is not delegated to the model.
- Clear target-audience wording and formal registration eligibility are different. In this sample the restriction is explicitly supplied in the brief, so the final copy can state it directly.
- Deterministic logistics blocks reduce opportunities for date/time/venue/price/link drift, but do not establish every narrative statement as true. Semantic drift can escape the numeric/link guard.
- The app targets one English college event per campaign, text-based documents, explicit field formats and same-day events. It has no OCR, web validation of registration links, localization, campaign analytics or multi-user authentication.
- Full-source planning audit is useful for conflicts but can be more expensive than sending only retrieval matches. The recorded retrieval query is broad; no relevance benchmark was performed.
- Execution context matters. A sandboxed network failure is not proof of a broken provider or a normal terminal's connectivity. Preserve sanitized exception chains early, while keeping secrets and source text out of diagnostics.
- Retention depends on a running cleanup process or the next startup, and manual-edit history does not contain every intermediate full draft. User-owned exports must be managed separately.
- The local CLI marker prevents another task-authorized demo workflow; it is not a global ban on a human creating a new campaign through the UI. This submission preparation created none and made no provider call.
- Human approval confirms a reviewed version, not guaranteed quality. The final approval note still says wording could improve; this package preserves the approved text rather than silently polishing it after approval.

## Repository and submission preparation

Run locally from `D:\LaunchPilot`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Use a normal terminal for provider connectivity. For a fresh machine, install the pinned dependencies, prepare MiniLM, and set `NEBIUS_API_KEY` privately; do not copy another project's environment file. No secrets are required to read the submitted sample or documents.

`submission/LaunchPilot_GITHUB_READY.zip` is prepared from an explicit source/artifact allowlist with a SHA-256 manifest. It excludes credentials, virtual environments, caches, private runtime databases/Chroma/uploads, logs, the local live-run marker and the stale Aster review packet. The fictional source extracts and approved sample are deliberate inclusions. `VALIDATION.md`, if consulted in the source archive, is historical Aster implementation verification; the Northstar results above and `submission/CAMPAIGN_RESULTS.json` are the current submission evidence.

There is no Git repository/remote configured in this workspace yet. No commit, push, Google Doc creation, sharing change, recording upload or publication was performed. Follow [the remaining-link checklist](submission/CHECKLIST.md), use the [under-five-minute recording script](submission/DEMO.md), and replace local Markdown links with repository URLs when preparing the final Google Doc.
