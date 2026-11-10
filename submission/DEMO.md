# LaunchPilot Project D recording script

For opening the app, recording shortcuts, sharing and the final hand-in, use [RECORDING_STEPS.md](RECORDING_STEPS.md). The [Google Doc](https://docs.google.com/document/d/1dGvFRPIv6yKrwUkn7iQa7BankwdDTo1sDW9yBwPG-DY) is prepared; reviewer access still needs to be enabled. No video has been recorded by this preparation.

**Target duration: 4 minutes 40 seconds**, leaving 20 seconds below the five-minute limit. This is a script, not a claim that a recording has been made. Narration is deliberately short; rehearse transitions and use a visible timer.

**Only campaign:** `e71f3548-b1c2-4969-9841-396ef719c46d`, approved working version 5. Northstar College and its event are fictional; the registration URL is an example.org placeholder. No real audience or business result is claimed.

## Before recording

- Open the running app at http://127.0.0.1:8501/?campaign=e71f3548-b1c2-4969-9841-396ef719c46d. If it is already running, do not launch a second server.
- Have `SUBMISSION.md`, `submission/CAMPAIGN_RESULTS.json` and `submission/SAMPLE_OUTPUT_FICTIONAL_APPROVED_v5.md` ready in separate tabs. The sample is the already-downloaded approved export, not newly generated content.
- Use only existing saved state. Do not create a campaign, click Retry/Resume generation, edit/save, re-approve or call a provider. The campaign has already used all eight provider attempts.
- The recording uses current UI views plus **explicitly labelled historical records**. It does not replay a failure or a clarification. If there is no earlier video footage, use the timestamped table; do not imply it is a video of the original interaction.
- Hide credentials, environment files, private runtime folders and unrelated desktop tabs. Record before the campaign's 15 November 2026, 13:15:15.786 IST expiry if showing its live saved UI. After expiry, identify retained artifacts as historical; do not silently restore or regenerate a campaign.

## 0:00–0:25 — Show the saved application

**Screen:** LaunchPilot header, fictional-demo label, campaign identifier and version/approval caption. Leave the creation screen untouched.

**Say:** “LaunchPilot is an independent GTM agent that turns an English college-event brief and calendar into four evidence-backed formats. This is an existing, approved version-five campaign for a fictional Northstar College event. I am showing saved results; no generation is running and no real audience results are claimed.”

## 0:25–1:00 — Show evidence and the eligibility source

**Screen:** Expand Supporting evidence and confirmed facts. Show date, time/timezone, venue, Free price, placeholder registration link and source IDs. In the brief evidence, show the explicit registration restriction; the second brief chunk includes it. Point to PDF page 1 and CSV row 2.

**Say:** “The source is a text-based PDF and one CSV calendar row. Critical logistics agree. The brief explicitly restricts registration to Northstar College final-year undergraduate students; that is stronger evidence than inferring eligibility from audience alone. Source IDs, quotes and metadata stay attached to the evidence.”

## 1:00–1:35 — Explain the actual tool and agent flow

**Screen:** Briefly show `workflow.py` research/retrieve functions, then `CAMPAIGN_RESULTS.json` tool-call summary or the architecture section of `SUBMISSION.md`. Return to the four draft tabs.

**Say:** “I used Codex to build the scoped framework, implement the workflow and tests, diagnose failures, and save guarded edits. The research stage requested the real retrieve_sources tool. Chroma searched local MiniLM embeddings and returned three source chunks before planning. Planning checks facts and audience; missing or conflicting essentials can interrupt for clarification. Content drafts all four formats, and review can trigger one revision. This sample needed no fact clarification and used no automated revision.”

**Label:** “Implemented clarification path; tested offline. Not a live clarification demonstration.”

## 1:35–2:15 — Show saved failure and recovery history

**Screen:** `SUBMISSION.md` timestamp/results tables and the checkpoint timeline in `CAMPAIGN_RESULTS.json`. Overlay or visibly state **“HISTORICAL SAVED TRACE — not a live replay”**. The current UI does not expose an old failure viewer; do not claim it does.

**Say:** “This campaign first recorded four connection failures and persistent handoffs. The old worker discarded its underlying exception chain, so the exact historical cause is unknown. Separate source-free checks found socket denial in a restricted execution context and connectivity outside it. After a real server restart, an explicit retry completed research, planning, drafting and review in this same campaign. The saved counters were preserved.”

**Do not:** induce a failure, change checkpoints or click Retry. No mocked result is presented as a live provider result.

## 2:15–3:10 — Inspect four formats and manual corrections

**Screen:** LinkedIn and blog tabs briefly, then the email restriction before “Register today”, then Ad variation 2's “Explore portfolio structure…” sentence. Show that the obsolete duplicate passage is absent.

**Say:** “The formats share the confirmed logistics. Human review still mattered: it replaced overly broad experience wording, made eligibility explicit and removed duplicate ad copy. The version-five service edit inserted the restriction immediately before Register today in the email, and removed only the old Ad variation two passage while retaining the revised sentence. The model reviewer had returned no issues, so that result did not substitute for checking the copy.”

**Historical comparison:** Use the exact correction summary in `SUBMISSION.md`. Do not modify approved version 5 to recreate an earlier state. Intermediate versions 2–4 have audit entries, not a full built-in text history viewer.

## 3:10–3:45 — Show approval separation and approved export

**Screen:** Current content/export approval indicators and the available download control. Then open the existing `SAMPLE_OUTPUT_FICTIONAL_APPROVED_v5.md`, showing “Version: 5”, all formats, source references and fictional labels.

**Say:** “Each saved edit invalidates both approvals. The historical audit shows version-four approvals, a version-five edit and new human approvals for version five. Content approval and export approval are separate and tied to the current draft digest. This file is an exact copy of the already-downloaded approved export. I am not approving anything or exporting again in this demonstration.”

## 3:45–4:20 — Explain actual timing and tests honestly

**Screen:** Actual campaign metrics and scenario matrix in `SUBMISSION.md`.

**Say:** “This campaign used eight attempts: four failures and four successes. Saved active processing was forty-one point four eight five seconds. Reported successful usage was eight thousand four hundred ninety-four tokens; the failed requests supplied no usage. Creation to content approval took forty-eight minutes fifty-nine seconds including interruption, troubleshooting and human work. Missing/conflicting facts and injected retrieval or malformed-output failures were checked offline, not live in this sample.”

## 4:20–4:40 — Close with limits and deliverables

**Screen:** `submission/CHECKLIST.md`, the [GitHub repository](https://github.com/ghantaram4/LaunchPilot) and prepared Google Doc. Keep the recording link pending until the actual video is uploaded.

**Say:** “This demonstrates one fictional campaign, not general accuracy or business performance. Source support, persistence and human approval are central; model review remains fallible. The submission includes the implementation, documented results, fictional source data and approved sample output. There is no sending or publishing integration.”

Stop recording by **4:40**. Check actual runtime is below five minutes before uploading or linking it. No recording or upload is included in this preparation task.
