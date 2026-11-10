# Project D remaining submission links

Final campaign: `e71f3548-b1c2-4969-9841-396ef719c46d`, approved working version **5**. All event/sample data is fictional.

| Required link | Status | Remaining action |
|---|---|---|
| GitHub repository | **PENDING — no repository URL supplied; workspace is not yet a Git repository** | Review/extract `LaunchPilot_GITHUB_READY.zip`, initialize a repository, inspect the staged file list, commit and push manually; add the real reviewer-accessible URL here |
| Google Doc | **PENDING — not created or uploaded** | Copy/import `../SUBMISSION.md`, check headings/tables, replace relative artifact links with real repository URLs, set required reviewer access, and add its actual URL here |
| Demo recording (<5 minutes) | **PENDING — script only** | Record using `DEMO.md`, verify duration and historical/fictional labels, upload manually, check access, and add the actual video URL here and in the Google Doc |

## Prepared locally

- [x] [Google Doc source text](../SUBMISSION.md): actual architecture, prompts/iterations, campaign-specific measurements, scenario matrix, limitations and learnings.
- [x] [4:40 recording script](DEMO.md): current saved UI and clearly labelled historical failure/correction/approval evidence; no replay or new generation required.
- [x] [Approved version-5 sample-output copy](SAMPLE_OUTPUT_FICTIONAL_APPROVED_v5.md): byte-identical to the existing download; fictional labels preserved.
- [x] [Campaign evidence/metrics](CAMPAIGN_RESULTS.json): read-only snapshot of approved version, saved usage/timestamps and sanitized checkpoint/audit summaries; no private database.
- [x] [Fictional brief extraction](source_data/FICTIONAL_NORTHSTAR_BRIEF_EXTRACTED.txt) and [calendar copy](source_data/FICTIONAL_NORTHSTAR_CALENDAR.csv): scoped to the submitted event and clearly identified.
- [x] Source archive `LaunchPilot_GITHUB_READY.zip` and manifest `GITHUB_FILES.sha256`: explicit allowlist; credentials, virtual environments, caches, private runtime uploads/databases/vectors/logs and local marker excluded. The archive itself is ignored by Git.
- [x] Current version-5 content/export digests checked against the saved drafts; no approval or campaign edit performed during packaging.

## Before the final hand-in

- [ ] Inspect `git diff --cached --name-only` and the staged diff before the manual push. Do not use an unreviewed `git add .`. Keep `.env*`, `.streamlit/secrets.toml`, `.venv/`, `.cache/`, `data/`, SQLite/Chroma files and logs out of the commit. Supply `NEBIUS_API_KEY` privately on another machine.
- [ ] Use this campaign's **41.485 active seconds / 8,494 reported tokens**, not the earlier Aster campaign's historical `VALIDATION.md` measurements. Failed-attempt usage is unknown.
- [ ] Confirm all three real links are present, reviewer-accessible and referenced in the Google Doc; do not leave placeholders in the submitted copy.
- [ ] Rehearse/record before the saved campaign expires on **15 November 2026, 13:15:15.786 IST**, or explicitly present the retained artifacts as historical. Do not regenerate merely to recreate footage.
- [ ] Submit the Google Doc/repository/recording links through the required Project D hand-in channel. Its destination/rubric was not supplied; verify it manually.

**Nothing has been pushed, uploaded, shared, recorded or published by this packaging task. No provider calls, regeneration, new campaign or application feature was added.**
