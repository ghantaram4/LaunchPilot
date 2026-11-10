# LaunchPilot

Independent Project D GTM agent for English college-event campaigns. See [FRAMEWORK.md](FRAMEWORK.md) for the agreed scope and boundaries. The application has no sending or publishing integrations.

From PowerShell in `D:\LaunchPilot`, launch with:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open http://127.0.0.1:8501. The virtual environment and all application data are local to this workspace. `D:\ReviewPilot_VSCode_Backend` is only a read-only credential source; its code, data, environment and configuration are unchanged.

For a fresh installation:

```powershell
$env:UV_CACHE_DIR='D:\LaunchPilot\.cache\uv'
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -e '.[dev]'
.\.venv\Scripts\python.exe -m launchpilot prepare-model
```

`requirements-lock.txt` records the versions actually verified here. To reproduce them, install with `uv pip install --python .venv\Scripts\python.exe -r requirements-lock.txt` instead. The first model preparation downloads public MiniLM weights; source documents are never sent to Hugging Face. Once cached, embeddings run locally on CPU. A missing model produces a recoverable retrieval handoff; the app never silently substitutes another embedding model.

## Using a campaign

Upload a UTF-8 TXT or text-based PDF brief and a UTF-8 CSV calendar. Select the event row if the calendar has several events. This MVP handles one event per campaign; supply a brief scoped to that event. PDFs must be readable on every page, unencrypted, at most 30 pages, with at most 65,000 extracted characters; each upload is limited to 5 MB. Scans require an external text extraction/replacement. Extraction errors stay in the local upload preview before consent; no failed upload is persisted without consent.

Recommended CSV columns:

```text
event_id,event_name,date,start_time,end_time,timezone,venue,price,registration_url,audience,tone
```

For reliably auditable facts, use matching `field: value` lines in the brief. Dates use `YYYY-MM-DD`, times `HH:MM` (24-hour, same-day events), timezone an IANA name such as `Asia/Kolkata`, prices include a currency or `Free`, and registration links use HTTPS. Natural-language briefs are also supported through the planning agent's verbatim source quotes. Ambiguous representations, missing fields and conflicting values ask for human confirmation. The app deliberately prefers clarification to interpreting ambiguous date/time/currency formats. Case-sensitive URL paths remain distinct. Audience and tone are essential too.

The consent checkbox authorizes source transmission to the fixed Nebius destination, paid generation and internal checkpoints. It does not approve content or export. Choose the fictional-demo toggle to use the bundled invented college/event. Its example.org link is a placeholder, not a real registration service. The demonstration makes no real-event or audience-result claims.

Research first issues a genuine LangChain tool call. The app executes campaign-scoped Chroma retrieval, then supplies the tool result to the planning agent. A full-source audit accompanies the nearest matches so top-k retrieval cannot silently hide conflicting logistics. The essential-facts gate checks source quotes, labelled/CSV candidates, field validity and human confirmations before content generation. Clarification resumes from its SQLite interrupt without repeating research or planning.

Content creates all four narratives in one separate stage. The app appends an identical confirmed logistics block to each format and each of the three ad variations. The independent review stage checks support, consistency and tone, alongside deterministic critical-fact checks. Any review issues permit one automated revision and a second review. Unresolved issues then go to a human. The reviewer can miss semantic claims, and deterministic checks cannot prove every free-text assertion; inspect source evidence yourself.

Use the four draft tabs to edit, then save. Saving increments the version and invalidates both approvals. The fact block must stay exact; alternate numeric, date or link details in narrative block approval. Every current version requires explicit human content approval. Outstanding model issues or edits require a written human disposition. A second, separate export checkbox and action enable the Markdown download. No export bytes are prepared before both approvals. User downloads are outside application cleanup.

## Persistence, recovery and retention

`data/campaigns/<UUID>/` contains source copies, source metadata, persistent Chroma, application SQLite, provider response/usage records and **SQLite LangGraph checkpoints**. State includes confirmed facts, evidence references, drafts, review history, pending questions, human answers, versioned approval records and an audit trail. A workspace-wide file lock prevents simultaneous generation, editing, export and retention operations. Bind the app to localhost; this MVP is a trusted, single-user application without authentication.

Each completed graph stage checkpoints synchronously. Successful provider responses are also cached by stage and input hash, closing the normal gap between provider completion and graph checkpoint commit. Opening a saved campaign or resuming completed work does not regenerate it. A process crash during an in-flight request produces an explicit uncertain-completion handoff; another charge requires acknowledgement before retry. A crash after the provider returned but before its response could be saved cannot guarantee exactly-once execution; the app does not silently repeat that request.

Retrieval, provider, malformed-output and internal failures become persistent handoffs. Retry resumes the failed stage. Eligible connection/timeouts, HTTP 429 and 5xx errors receive at most one automatic retry with short backoff. Authentication/request/schema errors do not automatically retry. Raw provider exceptions, headers, credentials and hidden reasoning are excluded from reports. Failed/timeout requests may still be billable; usage is marked unknown if the provider supplies none.

Future provider failures retain sanitized exception chains in the campaign's `provider_diagnostics.jsonl` and server output: exception types, numeric OS/TLS/status codes, interpreter/endpoint, credential-presence and connection-setting flags. Raw exception messages, request/response bodies, proxy credentials and headers are omitted. These files expire with the campaign. Historical failures recorded before this logging change contain only the wrapper error class; their underlying causes cannot be reconstructed. For a source-free check, run `.\.venv\Scripts\python.exe -m launchpilot.diagnostics` in the same terminal/context as the server. It sends only an unauthenticated HEAD to the fixed Nebius `/v1/models` path, without reading campaign state or invoking a model. An HTTP response such as 405 establishes network/TLS reachability, not credential validity or successful generation. A restricted Codex probe is not evidence that a server started in a normal terminal cannot connect.

Every campaign has a persisted maximum of eight provider attempts and 180 active workflow seconds. Human waiting is excluded. Each actual provider request is a killable child process with SDK retries disabled and a timeout capped by remaining budget. All workflow stages and retries share that budget. Attempt counts and usage survive restart. An unclean process exit conservatively charges elapsed wall time until recovery, potentially exhausting the budget rather than silently extending it. No automatic budget reset exists. Model loading/download setup can be done separately with `prepare-model` before generation.

Campaign data expires **seven days after creation**, without extending the deadline on reads or edits. Cleanup deletes the entire validated campaign directory, including uploads, vectors, checkpoints, approvals and usage. It runs on startup, before service operations and every five minutes while Streamlit is running. Expired campaigns cannot be opened. Windows file-handle failures are disclosed and retried; the Chroma 1.x close workaround is covered by the real retention integration check.

When the app is stopped, no application process can delete files. Run the following command from an existing Windows scheduled task if cleanup must continue while the server is off; otherwise overdue data is removed at next startup:

```powershell
D:\LaunchPilot\.venv\Scripts\python.exe -m launchpilot cleanup
```

Deletion is logical filesystem deletion; the app does not erase OS backups or promise forensic disk erasure. Model weights and installed dependencies contain no campaign data and are retained. User-exported files remain under user control.

## Nebius configuration and credential handling

The fixed destination is the existing `https://api.tokenfactory.nebius.com/v1/` with `openai/gpt-oss-120b`, Chat Completions, `reasoning_effort="low"`, `temperature=1`, and `max_tokens` budgets per stage. No OpenAI-hosted endpoint is used. Provider identity and GPT-OSS capabilities are described by [Nebius](https://nebius.com/services/token-factory/models/openai-gpt-oss). Its live compatibility is reported separately in `VALIDATION.md`.

The LangChain 1.x adapter renames its `max_tokens` field to `max_completion_tokens`; LaunchPilot sets that field to None and passes `extra_body={"max_tokens": limit}` so the wire request uses the Nebius-compatible spelling. JSON stages request `response_format={"type":"json_object"}` and validate against Pydantic schemas. Research requests exactly the `retrieve_sources` function, with parallel tool calls disabled. SDK retries and streaming usage are disabled; retries are controlled and counted by the application. The offline MockTransport check inspects these actual wire settings without contacting any provider.

Credentials come from `NEBIUS_API_KEY` or, if absent, only the `NEBIUS_API_KEY` line of the existing `D:\ReviewPilot_VSCode_Backend\.env`. Set `LAUNCHPILOT_CREDENTIAL_FILE` to override that read-only location. Secrets are not copied into this workspace, printed, persisted, included in argv or put into prompts. The child process receives its key over stdin. Unrelated configuration is not loaded. LangSmith and Chroma/Hugging Face telemetry are disabled.

Embeddings use the [all-MiniLM-L6-v2 model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), whose default input limit is 256 word pieces. The actual model tokenizer creates at most 220 content-token chunks with 24-token overlap, preserves exact source substrings and checks total tokens including special tokens are strictly below the model limit. Metadata includes filename, source ID, page/CSV row, SHA-256, token count and character offsets.

## Verification commands

After preparing the model, offline checks require no provider access:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

The tests cover complete campaigns, actual tool dispatch, missing/conflicting fact interruptions, invalid answers, retrieval/provider/schema handoffs, bounded retries, cached completion, provider wire settings, critical edits, process restart, approvals, Chroma isolation and seven-day cleanup. They use a scripted provider or MockTransport for offline checks, plus the real local tokenizer/embeddings/Chroma integration. No additional evaluation framework is included.

The task authorizes only **one** live fictional workflow. `python -m launchpilot live-demo` starts it; a permanent source-free marker prevents accidentally starting another via the CLI. `python -m launchpilot live-status` reads its retained outcome without generating. A saved handoff can be resumed in the UI within the original limits. The live command never approves or exports. See `VALIDATION.md` for the actual run rather than assuming success.
