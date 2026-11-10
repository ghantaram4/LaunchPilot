from streamlit.testing.v1 import AppTest

from conftest import FakeProvider, FakeRetriever
from launchpilot.config import ROOT
from launchpilot.service import Service
from launchpilot.workflow import run


def test_streamlit_demo_consent_generation_approval_gates_and_reload(store, monkeypatch):
    service = Service(store)
    original_run = Service.run
    def offline_run(self, cid, **kwargs):
        self.clean()
        return run(self.store, cid, provider_factory=FakeProvider, retriever_factory=FakeRetriever, **kwargs)
    monkeypatch.setattr(Service, "run", offline_run)
    monkeypatch.setattr("launchpilot.service.Service", lambda: service)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    assert not app.exception
    assert app.button[0].label == "Create campaign and generate" and app.button[0].disabled
    app.toggle[0].set_value(True).run()
    assert not app.exception
    app.checkbox[0].check().run()
    assert not app.button[0].disabled
    app.button[0].click().run()
    assert not app.exception
    assert len(app.tabs) == 4
    assert app.tabs[0].label == "LinkedIn"
    assert any("Human approval required" in c.value for c in app.caption)
    approve = next(b for b in app.button if b.label == "Approve this content version")
    export = next(b for b in app.button if b.label == "Approve export")
    assert approve.disabled and export.disabled
    cid = service.store.list()[0]["id"]
    assert service.working(cid)["approved"] is None
    before = FakeProvider.calls.copy()
    app.run()
    assert not app.exception and len(app.tabs) == 4 and FakeProvider.calls == before
    # Approval actions are tested only against the offline campaign, never the task's live demo.
    review_checkbox = next(c for c in app.checkbox if c.label.startswith("I checked all four"))
    review_checkbox.check().run()
    next(b for b in app.button if b.label == "Approve this content version").click().run()
    assert not app.exception
    assert service.working(cid)["approved"] and not service.working(cid)["export_approved"]
    monkeypatch.setattr(Service, "run", original_run)
