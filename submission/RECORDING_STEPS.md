# Record and finish the Project D submission

The Google Doc and GitHub repository are prepared. The recording must come from the actual application on your computer; no recording has been created for you.

## 1. Open the app

In **Windows Command Prompt**, from your existing installation:

```cmd
cd /d D:\LaunchPilot
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Keep the terminal open. Visit [the saved campaign](http://127.0.0.1:8501/?campaign=e71f3548-b1c2-4969-9841-396ef719c46d). If the command fails, resolve its terminal error before recording; a browser connection-refused screen does not demonstrate the app.

Use the saved version-5 result. Do not start a new campaign, retry generation, edit, approve again or regenerate for footage. The campaign expires on 15 November 2026 at 13:15:15.786 IST. After expiry, label retained artifacts historical; do not pretend a fresh clone contains private saved state.

## 2. Prepare one browser window

Open these in tabs in the same browser window:

- The local saved campaign: sources, draft tabs, approvals and usage.
- [The prepared Google Doc](https://docs.google.com/document/d/1dGvFRPIv6yKrwUkn7iQa7BankwdDTo1sDW9yBwPG-DY).
- [The graph implementation](https://github.com/ghantaram4/LaunchPilot/blob/main/launchpilot/workflow.py).
- [The campaign results](CAMPAIGN_RESULTS.json) and [approved sample](SAMPLE_OUTPUT_FICTIONAL_APPROVED_v5.md).
- [The 4:40 script](DEMO.md), read from another screen/device or rehearse first.

Do not show API keys, environment files or unrelated personal tabs. Show the existing result inside the running app; do not substitute screenshots for the whole application walkthrough.

## 3. Record with your voice

Windows Xbox Game Bar can record an app window. Press **Windows + G**, open Capture, and check the microphone is enabled. **Windows + Alt + R** starts/stops recording; **Windows + Alt + M** toggles the microphone. Stay in the browser window rather than relying on a single-app capture to record other applications.

Do a short microphone test first, play it back, then record the final take using [DEMO.md](DEMO.md). Target 4:40 and verify the actual file is **at most five minutes**. Explain what you built, how Codex was used, real retrieval/state/recovery, the four formats, human corrections, approvals and actual limitations. Label saved failure traces historical. This sample had no live clarification or automated revision.

Shortcut reference: [Microsoft's Xbox Game Bar recording guide](https://support.microsoft.com/en-us/accessibility/windows/use-a-screen-reader-to-record-your-screen-with-xbox-game-bar).

## 4. Make the links reviewer-accessible

- In the Google Doc, open **Share** and choose the course-required viewer access. The prepared Doc was created private. If the course accepts link sharing, use **Anyone with the link — Viewer** and copy the link.
- Upload the recording to your chosen video/Drive destination. Enable the required viewer access, check playback and confirm the duration.
- Verify the links in a signed-out/private window if using public link access; restricted course sharing instead requires an authorized reviewer account.

The Google Doc needs the actual recording URL in its opening delivery note. Record the URL in [DELIVERY_LINKS.json](DELIVERY_LINKS.json) too. You can provide the finished video URL for those final updates; do not put an invented link in the form.

## 5. Hand in

The supplied Week 3 handout lists [this submission form](https://forms.gle/waBYFkkf5xxmcouV9), with the final certification deadline of 11 November 2026. Check the form/course announcements for any changes before submitting.

Submit the GitHub URL, Google Doc and recording as requested. Review the populated form before sending and retain its confirmation. This preparation has not submitted the form or created a recording.
