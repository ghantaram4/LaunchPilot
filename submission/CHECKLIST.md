# Project D delivery checklist

Final sample: campaign `e71f3548-b1c2-4969-9841-396ef719c46d`, human-approved working **version 5**. All sample event data is fictional.

| Required item | Status | Next action |
|---|---|---|
| GitHub repository | **Uploaded:** [ghantaram4/LaunchPilot](https://github.com/ghantaram4/LaunchPilot) | Use this URL for submission; keep credentials and runtime data excluded |
| Google Doc | **Prepared:** [LaunchPilot submission](https://docs.google.com/document/d/1dGvFRPIv6yKrwUkn7iQa7BankwdDTo1sDW9yBwPG-DY) | Open Share and enable the required reviewer access; currently private |
| Demo recording, at most five minutes | **Pending — script prepared** | Follow [DEMO.md](DEMO.md), record/upload, verify duration and reviewer access |

Store the three delivery URLs in [DELIVERY_LINKS.json](DELIVERY_LINKS.json). The Google Doc link is recorded. The missing video link is deliberately `null`; no recording has been invented.

## Prepared

- [x] [README](../README.md): setup, credentials, input format, usage, architecture, limits and troubleshooting.
- [x] [Project write-up](../SUBMISSION.md): data, architecture, coding prompts/iterations, results, scenario matrix and learnings.
- [x] Native [Google Doc](https://docs.google.com/document/d/1dGvFRPIv6yKrwUkn7iQa7BankwdDTo1sDW9yBwPG-DY): structured headings, source facts, results and testing tables, repository links and visual formatting check.
- [x] [4:40 demo script](DEMO.md): saved UI plus explicitly labelled historical evidence; no new generation required.
- [x] [Approved version-5 sample](SAMPLE_OUTPUT_FICTIONAL_APPROVED_v5.md): existing download, fictional labels and review history preserved.
- [x] [Campaign metrics](CAMPAIGN_RESULTS.json): saved timings, usage, checkpoints and approval audit; no private database.
- [x] [Fictional brief extraction](source_data/FICTIONAL_NORTHSTAR_BRIEF_EXTRACTED.txt) and [calendar](source_data/FICTIONAL_NORTHSTAR_CALENDAR.csv).
- [x] GitHub repository uploaded; setup no longer depends on the developer's earlier project.
- [x] Placeholder-only [.env.example](../.env.example) with explicit credential-file instructions.
- [x] Current [repository-byte manifest](GITHUB_FILES.sha256); original local [packaging manifest](archive/GITHUB_FILES_PACKAGING_20261108.sha256) preserved separately.

## Finish before handing in

- [ ] Enable reviewer access to the prepared Google Doc. It is currently private; choose the course-required sharing setting and verify access.
- [ ] Rehearse, record and upload the demo; check actual duration is at most five minutes.
- [ ] Keep the distinction between active processing (**41.485 seconds**) and elapsed time through content approval (**48 minutes 59.449 seconds**).
- [ ] Describe **8,494 reported tokens** as known successful-call usage; four failed requests supplied no usage. No verified bill is available.
- [ ] Label the campaign fictional and saved. The model reviewer missed issues; human edits were part of the final result.
- [ ] If showing the saved UI, record before campaign expiry: **15 November 2026, 13:15:15.786 IST**. Otherwise present the retained sample as historical; a fresh clone does not contain the private campaign.
- [ ] Populate the pending video entry in [DELIVERY_LINKS.json](DELIVERY_LINKS.json); verify all three URLs work for the intended reviewer.
- [ ] Submit the required links through the course's hand-in channel and verify its current instructions.

The ZIP prepared locally is ignored and is not a current GitHub release. The current manifest hashes committed file bytes, excluding itself; Windows checkout line-ending conversion may change local hashes. The archived manifest describes the original packaging, not these updated documents.

This documentation update made no model requests, generation retries, campaign edits or approval changes.
