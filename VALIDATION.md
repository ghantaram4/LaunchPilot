# LaunchPilot verification — 8 November 2026 (Asia/Kolkata)

> **Historical implementation verification: Aster campaign.** This document preserves the original test/run report, including its then-current handoff and approval state. It is not the final Northstar submission result. See [SUBMISSION.md](SUBMISSION.md#actual-results-for-this-campaign-only) and [CAMPAIGN_RESULTS.json](submission/CAMPAIGN_RESULTS.json) for the separate Northstar version-5 result. Current installation instructions are in [README.md](README.md#run-locally). These historical tests were not rerun for the repository documentation update.

The application is implemented in `D:\LaunchPilot`. All writes, dependencies, source copies and campaign state remain in this workspace. The other project was used only for read-only discovery of its existing Nebius destination and the single credential line; no file in `D:\ReviewPilot_VSCode_Backend` was modified.

Launch from PowerShell in `D:\LaunchPilot`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

The server was started and its health endpoint returned `200 ok`. The fictional live campaign can be opened at:

http://127.0.0.1:8501/?campaign=d7a98647-c402-41a1-a244-ed8b0ec6665c

## Offline checks

Before the live workflow, 28 offline tests passed. After additional inspection handling and malformed-tool-argument recovery checks, the final suite passed **31 tests in 20.07 seconds**. `ruff check .` also passed. Tests ran with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` after preparing the public model cache. Offline generation used scripted responses or HTTP MockTransport, never paid provider calls.

| Requirement | Observed check |
|---|---|
| Complete input produces four consistent formats | Separate research, retrieval, planning, drafting and review stages; four formats and three ad variants; exact confirmed logistics blocks |
| Missing/conflicting essentials | Both cases paused in persisted LangGraph interrupts; fresh store reopened the questions; answers resumed without repeating research/planning; invalid answers remained pending |
| Retrieval/provider failures | Injected failures disclosed their cause class and persisted a retry handoff; retry continued only the failed stage |
| Malformed output/tool arguments | Schema-invalid JSON and invalid retrieval arguments stopped explicitly, then recovered through an explicit stage retry |
| Bounded retries/provider settings | Transient retry at most once; nontransient error no automatic retry; hard timeout killed worker; attempt/time exhaustion blocked requests; actual outgoing JSON inspected offline |
| Restart and ambiguous completion | A separate Python interpreter reopened checkpoint and approval state; completed workflows did not generate again; an in-flight uncertain request did not silently repeat |
| Approval/export | Content approval and separate export approval required; unapproved exports blocked; draft edits invalidated both; critical-fact changes blocked approval |
| Review is fallible | One automated revision maximum; unresolved issues persisted; additional inspection findings could be saved for human resolution |
| Local embeddings and Chroma | Real MiniLM tokenizer and embeddings; chunks strictly below 256 tokens including special tokens, with overlap; persistent Chroma reopening and campaign isolation |
| Seven-day cleanup | Expired campaign source copies, vector directory and checkpoints removed; active campaign and user-owned export left intact; real Chroma handles released on Windows |
| Streamlit flow | Consent gating, fictional demo generation, four tabs, reload without regeneration and approval/export gating passed AppTest |

No external sending, publishing, dashboard or additional evaluation framework was added.

## The one authorized live workflow

Only the bundled `demo/FICTIONAL_event_brief.txt` and `demo/FICTIONAL_event_calendar.csv` were used. The college and event are invented, the example.org registration link is a placeholder, and no real audience results are claimed. The fixed existing Nebius destination was used with `openai/gpt-oss-120b`, `reasoning_effort=low`, `temperature=1`, exact `max_tokens` wire settings, named retrieval-tool choice and JSON-object response mode. All four provider requests succeeded; the live run therefore verifies these settings against this destination.

| Item | Actual outcome |
|---|---|
| Campaign | `d7a98647-c402-41a1-a244-ed8b0ec6665c` |
| Final workflow status | `awaiting_human_review` |
| Output | LinkedIn post, promotional email, short blog, three ad variations |
| Provider attempts | **4 of 8**: research, plan, draft, review |
| Generation workflow active time | **27.859 seconds** |
| Active time including no-generation restart check | **27.875 seconds of 180** |
| Provider worker time | **17.983 seconds** including process/SDK overhead |
| Input tokens reported | **6,808** |
| Output tokens reported | **1,444** |
| Total tokens reported | **8,252** |
| Attempts without usage data | **0** |
| Automatic revisions | **0**; the model reviewer reported no issues |
| Deterministic critical-fact issues | **0** |
| Content approval | **Not granted** |
| Export approval / export | **Not granted / not performed** |

The returned usage metadata is recorded rather than estimating a bill from token counts. A monetary charge was not reported by the API and was not independently verified. Usage may include provider caching/reasoning accounting as supplied by Nebius; no hidden reasoning text was retained.

A fresh Python process reopened the actual live campaign, invoked ordinary resume, and observed **4 attempts before and after**. Approval stayed false and attempting to prepare an export was blocked. A separate Streamlit AppTest opened the actual saved campaign: zero exceptions, four draft tabs, both approval actions disabled before user acknowledgement, and the additional inspection findings visible. These checks made no further generation calls.

## Remaining human handoff and limits

All four outputs share the confirmed date, start/end time, timezone, venue, price and registration link. However, implementation inspection found two wording issues that the model review missed, and saved them in the campaign's checkpointed review history:

- **Blocking, blog:** its opening attributes an institutional belief to Aster College that the source does not establish. Remove or replace that sentence, or provide explicit confirmation.
- **Warning, LinkedIn:** “open to all undergraduates” can imply broader eligibility than the stated Aster College undergraduate audience. Keep the scope explicit or confirm broader eligibility.

The drafts remain unedited and unapproved so the actual provider outcome is reviewable. Human editing/review and a written disposition are required before content approval; export then requires its separate approval. No further provider workflow was started. The source-free live-run marker prevents a second CLI run under the task's authorization.

There are no dependency or provider blockers in the verified environment. Retention runs at startup, before operations and every five minutes while Streamlit runs. If the entire server is stopped beyond expiry, deletion occurs at next startup unless the documented cleanup command is scheduled externally. No Windows scheduled task was installed. Source/data retention is logical deletion, not secure erasure of OS backups. The app is local and single-user; a model review or numeric guard cannot establish every free-text claim as true.

Detailed provider ledger and the machine-readable live result are retained inside the campaign directory (`data/campaigns/<campaign-id>/live_result.json`) and expire with its seven-day data. User exports, when explicitly approved later, remain user controlled.
