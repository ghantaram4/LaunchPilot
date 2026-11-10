r"""Launch with: .\.venv\Scripts\python.exe -m streamlit run app.py"""
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from filelock import Timeout

from launchpilot.config import DATA, ENDPOINT, MODEL, ROOT
from launchpilot.ingest import calendar, extract
from launchpilot.models import FORMATS, Handoff
from launchpilot.service import Service
from launchpilot.retention import start_janitor

st.set_page_config(page_title="LaunchPilot · Project D", page_icon=":material/rocket_launch:", layout="wide")
st.markdown("""<style>
.block-container {max-width:1120px;padding-top:2.5rem;}
h1 {letter-spacing:-.04em;} [data-testid="stCaptionContainer"] {color:#465E5B;}
button:focus-visible,textarea:focus-visible {outline:3px solid #0F766E;outline-offset:3px;}
[data-testid="stTextArea"] textarea {line-height:1.65;}
@media (prefers-reduced-motion:reduce) {* {animation:none!important;transition:none!important;}}
</style>""", unsafe_allow_html=True)
st.caption("PROJECT D / INDEPENDENT GTM AGENT")
st.title("LaunchPilot")
st.write("Turn your college event brief into a grounded, human-reviewed campaign.")


def fail(exc):
    st.error(exc.message if isinstance(exc, Handoff) else "Another session is working. Wait for it to finish and reload.")


def advance(cid, response=None):
    try:
        with st.status("Running your campaign…", expanded=True) as progress:
            def update(stage):
                labels = {"research": "Research requested source retrieval", "retrieve": "Retrieved local evidence",
                          "plan": "Planned audience and tone", "gate": "Checked essential facts", "draft": "Drafted four formats",
                          "review": "Reviewed factual support and tone", "revise": "Completed the single revision",
                          "clarify": "Waiting for clarification", "handoff": "Saved a recoverable handoff",
                          "finish": "Ready for human review", "__interrupt__": "Progress saved; waiting for you"}
                st.write(labels.get(stage, stage))
            service.run(cid, response=response, callback=update)
            progress.update(label="Progress saved", state="complete", expanded=False)
    except (Handoff, Timeout) as exc:
        fail(exc)


service = Service()

@st.cache_resource
def retention_worker():
    return start_janitor(DATA)

_, retention_health = retention_worker()
for problem in retention_health["errors"]:
    st.error(problem)
try:
    cleaned = service.clean()
    if cleaned["removed"]:
        st.info(f"Removed {cleaned['removed']} expired campaign(s) under the seven-day policy.")
except (Handoff, Timeout) as exc:
    fail(exc)
    st.stop()

with st.sidebar:
    st.subheader("Campaign workspace")
    options = service.store.list()
    choices = ["New campaign"] + [r["id"] for r in options]
    requested = st.query_params.get("campaign")
    index = choices.index(requested) if requested in choices else 0
    selected = st.selectbox("Open saved campaign", choices, index=index,
                            format_func=lambda v: v if v == "New campaign" else f"Campaign {v[:8]}")
    st.caption("Campaigns and local embeddings expire seven days after creation. Downloads remain yours.")
    with st.expander("Provider and limits"):
        st.text(MODEL)
        st.text(ENDPOINT)
        st.write("Reasoning: low · Up to eight attempts and 180 active seconds per campaign.")
        st.caption("No sending or publishing integrations.")

cid = None if selected == "New campaign" else selected
if not cid:
    st.subheader("Start with your sources")
    st.caption("English briefs · one selected college event · local extraction before consent")
    demo = st.toggle("Use the clearly labelled fictional demonstration", value=False)
    if demo:
        st.warning("FICTIONAL DEMO. This is an invented event and college. The example.org link is a placeholder; no real event or audience results are represented.")
        name, cal_name = "FICTIONAL_event_brief.txt", "FICTIONAL_event_calendar.csv"
        brief = (ROOT / "demo" / name).read_bytes()
        cal = (ROOT / "demo" / cal_name).read_bytes()
    else:
        left, right = st.columns(2)
        with left:
            uploaded_brief = st.file_uploader("Event brief (text PDF or TXT)", type=["pdf", "txt"])
        with right:
            uploaded_cal = st.file_uploader("Event calendar (CSV)", type=["csv"])
        brief = uploaded_brief.getvalue() if uploaded_brief else None
        cal = uploaded_cal.getvalue() if uploaded_cal else None
        name = uploaded_brief.name if uploaded_brief else ""
        cal_name = uploaded_cal.name if uploaded_cal else ""
    st.caption("CSV columns: event_name, date, start_time, end_time, timezone, venue, price, registration_url, audience, tone. Missing values will be clarified. Dates use YYYY-MM-DD, time HH:MM, timezone IANA, price includes currency or Free.")
    docs = None
    if brief and cal:
        try:
            rows = calendar(cal)
            row_index = st.selectbox("Calendar event to promote", range(len(rows)), format_func=lambda i: f"Row {i + 2}: {rows[i]['event_name']}")
            docs = extract(name, brief, cal_name, cal, row_index)
            with st.expander("Preview extracted source text", expanded=False):
                for doc in docs:
                    st.caption(f"{doc['id']} · {doc['filename']}")
                    st.text(doc["text"])
        except Handoff as exc:
            fail(exc)
    consent = st.checkbox("I consent to sending these sources to Nebius, paid generation, and internal checkpoint writes. Campaign data is retained for seven days.")
    if st.button("Create campaign and generate", type="primary", disabled=not (docs and consent)):
        try:
            is_demo = demo or any("FICTIONAL DEMO" in d["text"].upper() for d in docs)
            cid = service.store.create(docs, consent=consent, demo=is_demo, raw_files=[(name, brief), (cal_name, cal)])
            st.query_params["campaign"] = cid
            advance(cid)
            st.rerun()
        except (Handoff, Timeout) as exc:
            fail(exc)
    st.stop()

st.query_params["campaign"] = cid
try:
    state = service.state(cid)
    record = next(r for r in options if r["id"] == cid)
    st.caption(f"Campaign {cid[:8]} · expires {datetime.fromtimestamp(record['expires'], ZoneInfo('Asia/Kolkata')).isoformat(timespec='minutes')}")
    if service.store.get(cid, "demo"):
        st.warning("FICTIONAL DEMO — not a real event. No audience results are claimed.")
    labels = {"clarification": "Needs your clarification", "handoff": "Paused with a saved handoff",
              "awaiting_human_review": "Ready for your review"}
    status = state.get("status", "not_started")
    st.subheader(labels.get(status, "Progress saved · ready to continue"))
    if not state or status not in {"clarification", "handoff", "awaiting_human_review"}:
        if st.button("Resume saved progress", type="primary"):
            advance(cid)
            st.rerun()
    if state.get("questions") and status == "clarification":
        st.write("Confirm the authoritative values. Your answers are saved as human source references.")
        with st.form("clarifications"):
            answers = {}
            for question in state["questions"]:
                st.write(question["reason"])
                for candidate in question["candidates"]:
                    st.caption(f"{candidate['value']} · {', '.join(candidate['source_ids'])}")
                answers[question["key"]] = st.text_input(question["key"].replace("_", " ").title())
            if st.form_submit_button("Confirm facts and resume", type="primary"):
                advance(cid, answers)
                st.rerun()
    if state.get("failure"):
        st.error(state["failure"]["message"])
        uncertain = state["failure"]["kind"] == "uncertain_provider"
        duplicate_ok = st.checkbox("I acknowledge the previous request may have completed and retrying may incur another charge.") if uncertain else True
        if st.button("Retry failed stage", disabled=not state["failure"]["retryable"] or not duplicate_ok):
            if uncertain:
                with service.store.db(cid) as conn:
                    conn.execute("UPDATE calls SET status='abandoned',error='Human acknowledged uncertain completion' WHERE status='inflight'")
            advance(cid, "retry")
            st.rerun()
    work = service.working(cid)
    if work:
        st.caption(f"Draft version {work['version']} · {'Content approved' if work['approved'] else 'Human approval required'} · {'Export approved' if work['export_approved'] else 'Separate export approval required'}")
        tabs = st.tabs(["LinkedIn", "Email", "Blog", "Ad variations"])
        edited = {}
        for key, tab in zip(FORMATS, tabs):
            with tab:
                edited[key] = st.text_area(f"{key.title()} draft", work["drafts"][key], height=380, key=f"draft-{cid}-{key}-{work['version']}")
        unsaved = edited != work["drafts"]
        if st.button("Save draft edits", disabled=not unsaved):
            service.edit(cid, edited, work["version"])
            st.rerun()
        if unsaved:
            st.info("Save your edits before approval or export. Saving invalidates both approvals.")
        with st.expander("Review issues and history", expanded=True):
            st.caption("Model review is fallible. Check every claim, tone and critical fact yourself. One automated revision is allowed; remaining issues are yours to resolve.")
            for item in state.get("review_history", []):
                st.write(f"Review after revision {item['revision']}: {item['model']['summary']}")
                if item.get("additional_inspection"):
                    st.caption("Additional inspection found issues the model review missed; these are included below for human resolution.")
                for issue in item["issues"]:
                    st.write(f"{issue['severity'].upper()} · {issue['format']}: {issue['detail']}")
            current_issues = service.issues(cid, work)
            for issue in current_issues:
                st.error(f"{issue['format']}: {issue['detail']}")
            if work["edited"]:
                st.warning("Drafts were edited after model review. Human review of this version is required.")
        st.subheader("Human approval")
        reviewed = st.checkbox("I checked all four drafts against the sources, including dates, time, venue, price, registration link and unsupported claims.", key=f"reviewed-{cid}-{work['version']}")
        note = st.text_area("Human resolution of remaining issues / review note", key=f"note-{cid}-{work['version']}")
        if st.button("Approve this content version", disabled=unsaved or not reviewed or bool(current_issues) or status != "awaiting_human_review"):
            service.approve(cid, expected_version=work["version"], reviewed=reviewed, note=note)
            st.rerun()
        export_ok = st.checkbox("I separately approve exporting this content version to a local download.", disabled=not work["approved"] or unsaved, key=f"export-{cid}-{work['version']}")
        if st.button("Approve export", disabled=unsaved or not work["approved"] or not export_ok):
            service.approve_export(cid, expected_version=work["version"], explicit=export_ok)
            st.rerun()
        if work["export_approved"] and not unsaved:
            st.download_button("Download approved campaign (.md)", service.export_bytes(cid), file_name=f"launchpilot-{cid[:8]}-v{work['version']}.md", mime="text/markdown")
    with st.expander("Supporting evidence and confirmed facts"):
        for field, fact in state.get("facts", {}).items():
            st.write(f"**{field.replace('_', ' ').title()}:** {fact['value']}")
            st.caption("Sources: " + ", ".join(fact["source_ids"]))
            st.text(fact["quote"])
        for hit in state.get("evidence", []):
            st.caption(f"{hit['chunk_id']} · {hit['filename']} · page {hit['page']} / CSV row {hit['row']}")
            st.text(hit["text"])
    with st.expander("Usage and active timing"):
        calls = service.store.calls(cid)
        st.write(f"{len(calls)} / 8 attempts · {service.store.get(cid, 'active_spent'):.2f} / 180 active seconds")
        st.json(calls)
except (Handoff, Timeout) as exc:
    fail(exc)
