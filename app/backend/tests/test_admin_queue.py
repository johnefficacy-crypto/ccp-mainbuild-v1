from app.api import admin_scrape
import pytest

class R:
    def __init__(self,data=None,count=None): self.data=data; self.count=count
class Q:
    def __init__(self,t,s):
        self.t=t; self.s=s; self.id=None; self.payload=None
        # status predicates so the claim-first compare-and-swap (P0-4) and the
        # state-machine guards (P0-2) behave like PostgREST: an update whose
        # status filter doesn't match the current row touches zero rows.
        self.status_eq=None; self.status_in=None
    def select(self,*a,**k): return self
    def eq(self,k,v):
        if k=='id': self.id=v
        if k=='status': self.status_eq=v
        return self
    def in_(self,k,v):
        if k=='status': self.status_in=set(v)
        return self
    def is_(self,k,v): return self
    def limit(self,*a,**k): return self
    def update(self,p): self.payload=p; return self
    def insert(self,p): self.payload=p; return self
    def _status_ok(self,row):
        st=row.get("status")
        if self.status_eq is not None and st!=self.status_eq: return False
        if self.status_in is not None and st not in self.status_in: return False
        return True
    def execute(self):
        if self.t=='admin_audit_logs': self.s['audits'].append(self.payload); return R([{}])
        if self.t=='scrape_queue':
            rows = [r for r in self.s['queue'] if self.id is None or r.get("id") == self.id]
            if not rows:
                return R([])
            row=rows[0]
            # Reads ignore the status predicate (PostgREST would filter, but the
            # promote path only ever selects a single id then branches in
            # Python). Writes honour it so CAS / guarded updates can miss.
            if self.payload is not None:
                if not self._status_ok(row):
                    return R([])
                row.update(self.payload)
            return R([row])
        return R([])
class SB:
    def __init__(self): self.state={'queue':[{'id':'q1','status':'approved','source_id':'src-1','notification_document_id':'doc-1','extracted_data':{'title':'t','organization_name':'Org','org_type':'central','year':2026,'official_notification_url':'https://x.gov/n','apply_end_date':'2026-06-30','posts':[{'post_name':'Clerk'}]}}],'audits':[]}
    def table(self,t): return Q(t,self.state)
    def rpc(self, fn, params):
        # `enqueue_eligibility_recompute` (PR #132) calls supabase.rpc first.
        # Raise PGRST202 so the helper falls back to the legacy Python path
        # (table/select/eq/is_/limit/insert), which this mock supports.
        raise RuntimeError(
            "PGRST202 Could not find the function "
            "public.enqueue_eligibility_recompute in the schema cache"
        )

def test_list_sources_uses_source_registry_only(monkeypatch):
    class SourceQ:
        def __init__(self, table, calls):
            self.table = table
            self.calls = calls
        def select(self, *a, **k): return self
        def order(self, *a, **k): return self
        def execute(self):
            self.calls.append(self.table)
            return R([])

    class SourceSB:
        def __init__(self):
            self.calls = []
        def table(self, table):
            return SourceQ(table, self.calls)

    sb = SourceSB()
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)

    assert admin_scrape._list_sources() == {"items": []}
    assert sb.calls == ["source_registry"]

def test_live_scrape_endpoint_exists_and_passes_safe_review_options(monkeypatch):
    captured = {}
    class SBSafe:
        pass

    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: SBSafe())

    def fake_run_scraping_pass(supabase, **kwargs):
        captured.update(kwargs)
        return {
            "run_id": "run-1",
            "status": "completed",
            "sources_checked": 1,
            "items_found": 1,
            "items_new": 1,
            "items_duplicate": 0,
            "errors": [],
        }

    monkeypatch.setattr(admin_scrape, "run_scraping_pass", fake_run_scraping_pass)
    monkeypatch.setattr(admin_scrape, "_audit", lambda *a, **k: None)

    routes = {getattr(route, "path", "") for route in admin_scrape.router.routes}
    assert "/admin/scrape/run" in routes

    out = admin_scrape.scrape_run(
        admin_scrape.ScrapeRunBody(source_ids=["src-1"], limit=7, force=False),
        {"id": "admin-1", "email": "a@example.com"},
    )

    assert out["run_id"] == "run-1"
    assert captured["source_ids"] == ["src-1"]
    assert captured["limit"] == 7
    assert captured["mock"] is False
    assert captured["triggered_by"] == "admin"

def test_approve_updates_status(monkeypatch):
    sb=SB(); monkeypatch.setattr(admin_scrape,'get_supabase_admin',lambda:sb)
    # Approve is now state-guarded (P0-2): it only acts on a non-terminal row.
    sb.state['queue'][0]['status']='pending'
    r=admin_scrape.approve_queue_item('q1', {'notes':'ok'}, {'id':'a','email':'e'})
    assert r['status']=='approved' and sb.state['queue'][0]['reviewer_id']=='a'

def test_reject_writes_audit(monkeypatch):
    sb=SB(); monkeypatch.setattr(admin_scrape,'get_supabase_admin',lambda:sb)
    admin_scrape.reject_queue_item('q1', {'notes':'bad'}, {'id':'a','email':'e'})
    assert any(a.get('action')=='scrape.queue.reject' for a in sb.state['audits'])


def test_reject_duplicate_mock_queue_rows_safely(monkeypatch):
    sb = SB()
    sb.state["queue"].append({"id": "q2", "status": "duplicate", "source_id": "src-1", "notification_document_id": "doc-2", "extracted_data": {}})
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)

    out = admin_scrape.reject_queue_item("q2", {"notes": "duplicate mock"}, {"id": "a", "email": "e"})

    assert out["status"] == "rejected"
    assert sb.state["queue"][1]["reviewer_notes"] == "duplicate mock"
    assert any(a.get("entity_id") == "q2" and a.get("action") == "scrape.queue.reject" for a in sb.state["audits"])

def test_promote_never_publishes(monkeypatch):
    sb=SB(); monkeypatch.setattr(admin_scrape,'get_supabase_admin',lambda:sb)
    import app.scraping.runner as runner
    import app.scraping.schemas as schemas
    monkeypatch.setattr(runner, 'promote_to_recruitments', lambda extracted, supabase, **kwargs: 'r1')
    # admin_scrape no longer imports alert_users_for_new_recruitment — the
    # promote endpoint never fans out alerts, so there is nothing to patch.
    # ensure pending accepted
    sb.state['queue'][0]['status']='pending'
    import pytest
    with pytest.raises(Exception):
        admin_scrape.promote_queue_item('q1', {'id':'a','email':'e'})

def test_field_verify_reject_correct_audit(monkeypatch):
    class SB2(SB):
        def __init__(self): super().__init__(); self.state['field']=[]
        def table(self,t):
            if t=='extracted_field_evidence':
                class FQ:
                    def __init__(self,s): self.s=s; self.p=None
                    def insert(self,p): self.p=p; return self
                    def update(self,p): self.p=p; return self
                    def execute(self):
                        if self.p is None: return R([])
                        self.s.state['field'].append(self.p); return R([self.p])
                    def select(self,*a,**k): return self
                    def eq(self,*a,**k): return self
                    def order(self,*a,**k): return self
                    def limit(self,*a,**k): return self
                return FQ(self)
            return super().table(t)
    sb=SB2(); monkeypatch.setattr(admin_scrape,'get_supabase_admin',lambda:sb)
    admin_scrape.verify_field('q1','apply_end_date',{'notes':'ok'},{'id':'a','email':'e'})
    admin_scrape.reject_field('q1','apply_end_date',{'notes':'bad'},{'id':'a','email':'e'})
    admin_scrape.correct_field('q1','apply_end_date',{'corrected_value':'2026-06-01'},{'id':'a','email':'e'})
    assert any(x.get('reviewer_status')=='corrected' for x in sb.state['field'])
    assert any(a.get('action')=='scrape.field.verify' for a in sb.state['audits'])


def test_promote_blocks_unverified_high_risk(monkeypatch):
    class SB3(SB):
        def table(self,t):
            if t=='extracted_field_evidence':
                class FQ:
                    def select(self,*a,**k): return self
                    def eq(self,*a,**k): return self
                    def execute(self): return R([{'field_name':'apply_end_date','reviewer_status':'unverified'}])
                return FQ(self)
            return super().table(t)
    sb=SB3(); monkeypatch.setattr(admin_scrape,'get_supabase_admin',lambda:sb)
    sb.state['queue'][0]['status']='pending'
    import pytest
    with pytest.raises(Exception):
        admin_scrape.promote_queue_item('q1', {'id':'a','email':'e'})


def test_field_evidence_fallback_document_created(monkeypatch):
    class SB4(SB):
        def __init__(self): super().__init__(); self.state["queue"][0]["notification_document_id"]=None; self.state["docs"]=[]; self.state["field"]=[]
        def table(self,t):
            if t=="extracted_field_evidence":
                class FQ:
                    def __init__(self,s): self.s=s; self.p=None
                    def select(self,*a,**k): return self
                    def eq(self,*a,**k): return self
                    def order(self,*a,**k): return self
                    def limit(self,*a,**k): return self
                    def execute(self): return R([])
                    def insert(self,p,*a,**k): self.s.state["field"].append(p); return self
                    def update(self,p,*a,**k): self.s.state["field"].append(p); return self
                return FQ(self)
            if t=="notification_documents":
                class DQ:
                    def __init__(self,s): self.s=s; self.payload=None
                    def insert(self,p): self.payload=p; return self
                    def select(self,*a,**k): return self
                    def eq(self,*a,**k): return self
                    def limit(self,*a,**k): return self
                    def execute(self):
                        if self.payload:
                            row={"id":"doc-fallback", **self.payload}; self.s.state["docs"]=[row]; return R([row])
                        return R(self.s.state["docs"])
                return DQ(self)
            return super().table(t)
    sb=SB4(); monkeypatch.setattr(admin_scrape,'get_supabase_admin',lambda:sb)
    out = admin_scrape.verify_field('q1','title',{'notes':'n'},{'id':'a','email':'e'})
    assert out["ok"] is True
    assert sb.state["queue"][0]["notification_document_id"] == "doc-fallback"
    assert sb.state["field"][0]["document_id"] == "doc-fallback"
    assert sb.state["docs"][0]["file_url"] == sb.state["docs"][0]["source_url"]


def test_field_evidence_continues_when_fallback_document_missing(monkeypatch):
    class SBMissingDoc(SB):
        def __init__(self):
            super().__init__()
            self.state["queue"][0]["notification_document_id"] = None
            self.state["field"] = []

        def table(self, t):
            if t == "extracted_field_evidence":
                class FQ:
                    def __init__(self, s): self.s = s; self.payload = None
                    def select(self, *a, **k): return self
                    def eq(self, *a, **k): return self
                    def order(self, *a, **k): return self
                    def limit(self, *a, **k): return self
                    def execute(self): return R([]) if self.payload is None else R([self.payload])
                    def insert(self, p, *a, **k):
                        self.payload = p
                        self.s.state["field"].append(p)
                        return self
                return FQ(self)
            if t == "notification_documents":
                class DQ:
                    def insert(self, p): return self
                    def select(self, *a, **k): return self
                    def eq(self, *a, **k): return self
                    def limit(self, *a, **k): return self
                    def execute(self): return R([])
                return DQ()
            return super().table(t)

    sb = SBMissingDoc()
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)

    out = admin_scrape.correct_field("q1", "title", {"corrected_value": "Fixed title"}, {"id": "a", "email": "e"})

    assert out["ok"] is True
    assert sb.state["field"][0]["document_id"] is None
    assert sb.state["field"][0]["corrected_value"] == "Fixed title"


def test_promote_sets_status_promoted_when_high_risk_verified(monkeypatch):
    class SB5(SB):
        def table(self,t):
            if t=='extracted_field_evidence':
                class FQ:
                    def __init__(self, *a, **k): pass
                    def select(self,*a,**k): return self
                    def eq(self,*a,**k): return self
                    def order(self,*a,**k): return self
                    def limit(self,*a,**k): return self
                    def execute(self):
                        return R([
                            {'field_name':'apply_end_date','reviewer_status':'verified'},
                            {'field_name':'official_notification_url','reviewer_status':'verified'},
                            {'field_name':'official_apply_url','reviewer_status':'verified'},
                            {'field_name':'organization_name','reviewer_status':'verified'},
                            {'field_name':'total_vacancies','reviewer_status':'verified'},
                            # requires_domicile is a post-scoped HIGH_RISK
                            # field (PR #135). The shared SB queue item now
                            # carries one post ("Clerk"), so the gate's
                            # post-scoped check needs a verified row scoped
                            # to that post.
                            {'field_name':'requires_domicile','reviewer_status':'verified',
                             'entity_type':'post','entity_key':'clerk'},
                        ])
                return FQ(self)
            return super().table(t)
    sb=SB5(); monkeypatch.setattr(admin_scrape,'get_supabase_admin',lambda:sb)
    import app.scraping.runner as runner
    captured = {}
    def _promote(extracted, supabase, **kwargs):
        captured.update(kwargs)
        return 'r1'
    monkeypatch.setattr(runner, 'promote_to_recruitments', _promote)
    sb.state['queue'][0]['status']='approved'
    out=admin_scrape.promote_queue_item('q1', {'id':'a','email':'e'})
    assert out['publish_status']=='needs_review'
    assert sb.state['queue'][0]['status']=='approved'
    assert captured["source_id"] == "src-1"
    assert any(a.get('action')=='scrape.queue.promote' for a in sb.state['audits'])


def test_promote_failure_keeps_queue_item_pending(monkeypatch):
    class SB7(SB):
        def table(self,t):
            if t=='extracted_field_evidence':
                class FQ:
                    def __init__(self, *a, **k): pass
                    def select(self,*a,**k): return self
                    def eq(self,*a,**k): return self
                    def order(self,*a,**k): return self
                    def limit(self,*a,**k): return self
                    def execute(self):
                        return R([
                            {'field_name':'apply_end_date','reviewer_status':'verified'},
                            {'field_name':'official_notification_url','reviewer_status':'verified'},
                            {'field_name':'official_apply_url','reviewer_status':'verified'},
                            {'field_name':'organization_name','reviewer_status':'verified'},
                            {'field_name':'total_vacancies','reviewer_status':'verified'},
                        ])
                return FQ(self)
            return super().table(t)
    sb=SB7(); monkeypatch.setattr(admin_scrape,'get_supabase_admin',lambda:sb)
    import app.scraping.runner as runner
    def _boom(*_args, **_kwargs):
        raise RuntimeError("promotion write failed")
    monkeypatch.setattr(runner, 'promote_to_recruitments', _boom)
    sb.state['queue'][0]['status']='pending'
    import pytest
    with pytest.raises(Exception):
        admin_scrape.promote_queue_item('q1', {'id':'a','email':'e'})
    assert sb.state['queue'][0]['status']=='pending'


def test_verify_updates_existing_row_without_upsert(monkeypatch):
    class SB6(SB):
        def __init__(self): super().__init__(); self.state["updated"]=[]
        def table(self,t):
            if t=="extracted_field_evidence":
                class FQ:
                    def __init__(self,s): self.s=s; self.payload=None; self.sel=True
                    def select(self,*a,**k): return self
                    def eq(self,*a,**k): return self
                    def order(self,*a,**k): return self
                    def limit(self,*a,**k): return self
                    def update(self,p): self.payload=p; self.sel=False; return self
                    def execute(self):
                        if self.sel: return R([{"id":"efe-1","document_id":"doc-1"}])
                        self.s.state["updated"].append(self.payload); return R([self.payload])
                return FQ(self)
            return super().table(t)
    sb=SB6(); monkeypatch.setattr(admin_scrape,'get_supabase_admin',lambda:sb)
    out=admin_scrape.verify_field('q1','title',{'notes':'ok'},{'id':'a','email':'e'})
    assert out["ok"] is True
    assert sb.state["updated"]


def test_validate_queue_id_rejects_invalid():
    with pytest.raises(Exception):
        admin_scrape._validate_queue_id("")


def test_review_body_limits_notes():
    with pytest.raises(Exception):
        admin_scrape.ReviewBody(notes="x" * 2001)


# ───────────────────────────────────────────────────────────────────────────
# Post-scoped field evidence isolation (regression for G12)
# ───────────────────────────────────────────────────────────────────────────


def test_post_scoped_field_evidence_does_not_cross_contaminate(monkeypatch):
    """Verifying ``posts.0.min_age`` must not mark ``posts.1.min_age`` verified.

    The frontend writes a dotted path as the field_name; the backend stores
    that path verbatim so the unique-index ``uq_evidence_entity_scoped`` keeps
    each (queue, post, field) row separate. This test pins the contract: two
    sibling posts can have independent reviewer_status without one writing
    over the other.
    """

    class FieldSB(SB):
        def __init__(self):
            super().__init__()
            # Add a second post so posts.1.min_age has a target.
            self.state["queue"][0]["extracted_data"]["posts"] = [
                {"post_name": "Clerk", "min_age": 18},
                {"post_name": "Officer", "min_age": 22},
            ]
            self.state["evidence_rows"] = []

        def table(self, t):
            if t == "extracted_field_evidence":
                outer = self

                class FQ:
                    def __init__(self):
                        self._field_name = None
                        self._payload = None
                    def select(self, *a, **k): return self
                    def order(self, *a, **k): return self
                    def limit(self, *a, **k): return self
                    def eq(self, k, v):
                        if k == "field_name":
                            self._field_name = v
                        return self
                    def insert(self, p):
                        self._payload = p; return self
                    def update(self, p):
                        self._payload = p; return self
                    def execute(self):
                        if self._payload is not None:
                            outer.state["evidence_rows"].append(dict(self._payload))
                            return R([self._payload])
                        rows = outer.state["evidence_rows"]
                        if self._field_name is not None:
                            rows = [r for r in rows if r.get("field_name") == self._field_name]
                        return R(list(rows))
                return FQ()
            if t == "notification_documents":
                class NDQ:
                    def select(self, *a, **k): return self
                    def insert(self, p): self._p = p; return self
                    def eq(self, *a, **k): return self
                    def limit(self, *a, **k): return self
                    def execute(self): return R([{"id": "doc-fallback"}])
                return NDQ()
            return super().table(t)

    sb = FieldSB()
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)

    admin_scrape.verify_field(
        "q1", "posts.0.min_age",
        admin_scrape.ReviewBody(notes="post 0 ok"),
        {"id": "a", "email": "e"},
    )

    post0_rows = [r for r in sb.state["evidence_rows"] if r.get("field_name") == "posts.0.min_age"]
    post1_rows = [r for r in sb.state["evidence_rows"] if r.get("field_name") == "posts.1.min_age"]
    assert len(post0_rows) == 1
    assert post0_rows[0]["reviewer_status"] == "verified"
    assert post1_rows == []  # sibling post is untouched


# ───────────────────────────────────────────────────────────────────────────
# P0-1 / P0-2: merge-into trust gate + state machine
# ───────────────────────────────────────────────────────────────────────────


from fastapi import HTTPException


# Fully-verified evidence for the shared "Clerk" single-post queue row, so the
# promotion gate passes and merge can exercise the canonical-write path.
_ALL_VERIFIED_EVIDENCE = [
    {"field_name": "apply_end_date", "reviewer_status": "verified"},
    {"field_name": "official_notification_url", "reviewer_status": "verified"},
    {"field_name": "official_apply_url", "reviewer_status": "verified"},
    {"field_name": "organization_name", "reviewer_status": "verified"},
    {"field_name": "total_vacancies", "reviewer_status": "verified"},
    {"field_name": "requires_domicile", "reviewer_status": "verified",
     "entity_type": "post", "entity_key": "clerk"},
]


class MergeSB(SB):
    """Adds ``recruitments`` + ``extracted_field_evidence`` so merge-into can run.

    ``evidence`` defaults to fully-verified so the gate PASSES; individual tests
    override it (or the queue row's ``is_dry_run`` / ``official_source_resolved``
    / ``status``) to drive the blocked paths.
    """

    def __init__(self, evidence=None):
        super().__init__()
        self.state["recruitments"] = [{"id": "rec-1", "source_id": None}]
        self.state["evidence"] = list(_ALL_VERIFIED_EVIDENCE if evidence is None else evidence)
        self.state["recruitment_updates"] = []
        # The shared queue row defaults to status='approved'; merge acts on
        # non-terminal rows, so seed it pending unless a test says otherwise.
        self.state["queue"][0]["status"] = "pending"
        self.state["queue"][0]["official_source_resolved"] = True

    def table(self, t):
        if t == "recruitments":
            outer = self

            class RQ:
                def __init__(self): self.id = None; self.payload = None
                def select(self, *a, **k): return self
                def eq(self, k, v):
                    if k == "id": self.id = v
                    return self
                def limit(self, *a, **k): return self
                def update(self, p): self.payload = p; return self
                def execute(self):
                    rows = [r for r in outer.state["recruitments"] if self.id is None or r.get("id") == self.id]
                    if self.payload is not None and rows:
                        rows[0].update(self.payload)
                        outer.state["recruitment_updates"].append(self.payload)
                    return R(rows)
            return RQ()
        if t == "extracted_field_evidence":
            outer = self

            class EQ:
                def select(self, *a, **k): return self
                def eq(self, *a, **k): return self
                def order(self, *a, **k): return self
                def limit(self, *a, **k): return self
                def execute(self): return R(list(outer.state["evidence"]))
            return EQ()
        return super().table(t)


def test_merge_blocked_for_dry_run_row(monkeypatch):
    sb = MergeSB()
    sb.state["queue"][0]["is_dry_run"] = True
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        admin_scrape.merge_queue_item_into_recruitment("q1", "rec-1", {}, {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    assert exc.value.detail["reason"] == "dry_run_not_promotable"
    # No canonical recruitment field was mutated, and the queue row was NOT
    # flipped to merged.
    assert sb.state["recruitment_updates"] == []
    assert sb.state["queue"][0]["status"] == "pending"


def test_merge_blocked_when_gate_fails_on_unverified_fields(monkeypatch):
    # Only one high-risk field verified → gate returns high_risk_fields_unverified.
    sb = MergeSB(evidence=[{"field_name": "apply_end_date", "reviewer_status": "verified"}])
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        admin_scrape.merge_queue_item_into_recruitment("q1", "rec-1", {}, {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    assert "unverified_fields" in exc.value.detail
    assert sb.state["recruitment_updates"] == []
    assert sb.state["queue"][0]["status"] == "pending"


def test_merge_blocked_when_official_source_unresolved(monkeypatch):
    sb = MergeSB()
    sb.state["queue"][0]["official_source_resolved"] = False
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        admin_scrape.merge_queue_item_into_recruitment("q1", "rec-1", {}, {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    assert exc.value.detail["reason"] == "unverified_official_source"
    assert sb.state["recruitment_updates"] == []


def test_merge_rejected_from_terminal_state(monkeypatch):
    sb = MergeSB()
    sb.state["queue"][0]["status"] = "rejected"  # terminal
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        admin_scrape.merge_queue_item_into_recruitment("q1", "rec-1", {}, {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    # State guard fires before any canonical write.
    assert sb.state["recruitment_updates"] == []
    assert sb.state["queue"][0]["status"] == "rejected"


def test_merge_succeeds_when_gate_passes_and_state_actionable(monkeypatch):
    sb = MergeSB()  # pending + fully verified + official resolved
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    out = admin_scrape.merge_queue_item_into_recruitment(
        "q1", "rec-1", {}, {"id": "a", "email": "e"}
    )
    assert out["status"] == "merged"
    assert out["recruitment_id"] == "rec-1"
    # Canonical fields were patched from the (empty-on-existing) recruitment.
    assert sb.state["recruitment_updates"], "expected the recruitment to be patched"
    assert sb.state["queue"][0]["status"] == "merged"
    assert sb.state["queue"][0]["promoted_recruitment_id"] == "rec-1"
    assert any(a.get("action") == "scrape.queue.merge" for a in sb.state["audits"])


class _MergeConflictSB(MergeSB):
    """``MergeSB`` plus an open ``recruitment_verification_conflicts`` row so the
    merge open-conflict block (``_open_conflict_field_keys``) fires."""

    def table(self, t):
        if t == "recruitment_verification_conflicts":
            class CQ:
                def select(self, *a, **k): return self
                def eq(self, *a, **k): return self
                def execute(self):
                    return R([{"field_key": "apply_end_date", "status": "open"}])
            return CQ()
        return super().table(t)


def test_merge_blocked_when_open_consensus_conflicts(monkeypatch):
    # Gate passes (fully verified + official resolved + pending), but an OPEN
    # consensus conflict exists → merge must 409 before any canonical write.
    sb = _MergeConflictSB()
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        admin_scrape.merge_queue_item_into_recruitment("q1", "rec-1", {}, {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    assert exc.value.detail["reason"] == "open_conflicts_unresolved"
    assert exc.value.detail["field_keys"] == ["apply_end_date"]
    # The queue row is UNCHANGED (still actionable) and the recruitment was NOT
    # patched — the block fires before the claim and before the canonical write.
    assert sb.state["queue"][0]["status"] == "pending"
    assert sb.state["recruitment_updates"] == []


class _MergeWriteFailsSB(MergeSB):
    """``MergeSB`` whose ``recruitments.update`` raises, to exercise the
    claim → write → revert path (torn-write regression)."""

    def __init__(self, evidence=None):
        super().__init__(evidence=evidence)
        # Force a non-empty patch by seeding an empty existing recruitment and a
        # queue source_id that merge will copy over (so the update path runs).
        self.state["recruitments"] = [{"id": "rec-1", "source_id": None,
                                       "official_notification_url": None}]
        self.state["queue"][0]["extracted_data"]["official_notification_url"] = "https://x.gov/n"

    def table(self, t):
        if t == "recruitments":
            outer = self

            class RQ:
                def __init__(self): self.id = None; self.payload = None
                def select(self, *a, **k): return self
                def eq(self, k, v):
                    if k == "id": self.id = v
                    return self
                def limit(self, *a, **k): return self
                def update(self, p): self.payload = p; return self
                def execute(self):
                    if self.payload is not None:
                        raise RuntimeError("recruitments.update boom")
                    rows = [r for r in outer.state["recruitments"] if self.id is None or r.get("id") == self.id]
                    return R(rows)
            return RQ()
        return super().table(t)


def test_merge_reverts_queue_row_when_recruitment_update_raises(monkeypatch):
    sb = _MergeWriteFailsSB()
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        admin_scrape.merge_queue_item_into_recruitment("q1", "rec-1", {}, {"id": "a", "email": "e"})
    # Error surfaced as a clear 500 (claim succeeded, canonical write failed).
    assert exc.value.status_code == 500
    assert exc.value.detail["reason"] == "merge_write_failed"
    # The queue row was reverted to its original actionable status — NOT left in
    # the terminal ``merged`` state — and no rec id was stamped.
    assert sb.state["queue"][0]["status"] == "pending"
    assert sb.state["queue"][0].get("promoted_recruitment_id") is None
    # No audit row for a failed merge.
    assert not any(a.get("action") == "scrape.queue.merge" for a in sb.state["audits"])


# ───────────────────────────────────────────────────────────────────────────
# P0-2: mark-duplicate / approve state machine
# ───────────────────────────────────────────────────────────────────────────


def test_mark_duplicate_rejected_from_terminal_state(monkeypatch):
    sb = SB()
    sb.state["queue"][0]["status"] = "approved"  # terminal
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        admin_scrape.mark_queue_item_duplicate("q1", {"notes": "dup"}, {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    assert sb.state["queue"][0]["status"] == "approved"  # unchanged
    assert not any(a.get("action") == "scrape.queue.mark_duplicate" for a in sb.state["audits"])


def test_mark_duplicate_succeeds_from_pending(monkeypatch):
    sb = SB()
    sb.state["queue"][0]["status"] = "pending"
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    out = admin_scrape.mark_queue_item_duplicate("q1", {"notes": "dup"}, {"id": "a", "email": "e"})
    assert out["status"] == "duplicate"
    assert sb.state["queue"][0]["status"] == "duplicate"


def test_approve_rejected_from_terminal_state(monkeypatch):
    sb = SB()
    sb.state["queue"][0]["status"] = "merged"  # terminal
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        admin_scrape.approve_queue_item("q1", {"notes": "ok"}, {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    assert sb.state["queue"][0]["status"] == "merged"  # unchanged


def test_mark_duplicate_missing_row_is_404(monkeypatch):
    sb = SB()
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    with pytest.raises(HTTPException) as exc:
        admin_scrape.mark_queue_item_duplicate("does-not-exist", {"notes": "x"}, {"id": "a", "email": "e"})
    assert exc.value.status_code == 404


# ───────────────────────────────────────────────────────────────────────────
# P0-3 / P0-4: dry-run hard block + non-idempotent promote (claim-first CAS)
# ───────────────────────────────────────────────────────────────────────────


class _PromoteVerifiedSB(SB):
    """Shared queue row + fully-verified evidence so the gate passes on promote."""

    def table(self, t):
        if t == "extracted_field_evidence":
            class FQ:
                def select(self, *a, **k): return self
                def eq(self, *a, **k): return self
                def order(self, *a, **k): return self
                def limit(self, *a, **k): return self
                def execute(self): return R(list(_ALL_VERIFIED_EVIDENCE))
            return FQ()
        return super().table(t)


def test_promote_hard_blocks_dry_run_row(monkeypatch):
    """P0-3: even with every field verified, a dry-run row can never promote."""
    sb = _PromoteVerifiedSB()
    sb.state["queue"][0]["status"] = "pending"
    sb.state["queue"][0]["is_dry_run"] = True
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    import app.scraping.runner as runner
    created = []
    monkeypatch.setattr(runner, "promote_to_recruitments",
                        lambda *a, **k: created.append(1) or "r1")
    with pytest.raises(HTTPException) as exc:
        admin_scrape.promote_queue_item("q1", {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    assert exc.value.detail["reason"] == "dry_run_not_promotable"
    assert created == []  # no recruitment was created
    assert sb.state["queue"][0]["status"] == "pending"  # not flipped


def test_double_promote_returns_409_not_a_second_recruitment(monkeypatch):
    """P0-4: a concurrent/retried promote claims zero rows → 409, no 2nd create."""
    sb = _PromoteVerifiedSB()
    sb.state["queue"][0]["status"] = "pending"
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    import app.scraping.runner as runner
    create_count = {"n": 0}
    def _promote(*a, **k):
        create_count["n"] += 1
        return f"rec-{create_count['n']}"
    monkeypatch.setattr(runner, "promote_to_recruitments", _promote)

    # First promote succeeds and flips the row to approved (the claim).
    out1 = admin_scrape.promote_queue_item("q1", {"id": "a", "email": "e"})
    assert out1["recruitment_id"] == "rec-1"
    assert sb.state["queue"][0]["status"] == "approved"

    # Second promote sees an already-promoted row → 409 BEFORE the gate/claim,
    # so promote_to_recruitments is never invoked a second time.
    with pytest.raises(HTTPException) as exc:
        admin_scrape.promote_queue_item("q1", {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    assert exc.value.detail["reason"] == "already_promoted"
    assert create_count["n"] == 1  # promote_to_recruitments ran exactly once


def test_promote_blocked_while_another_call_is_mid_flight(monkeypatch):
    """P0-4 concurrent case: a row already claimed (transient 'promoting') by an
    in-flight promote is not re-promotable — the second call 409s and creates
    nothing."""
    sb = _PromoteVerifiedSB()
    sb.state["queue"][0]["status"] = "promoting"  # claimed, recruitment not yet stamped
    sb.state["queue"][0]["promoted_recruitment_id"] = None
    monkeypatch.setattr(admin_scrape, "get_supabase_admin", lambda: sb)
    import app.scraping.runner as runner
    created = []
    monkeypatch.setattr(runner, "promote_to_recruitments",
                        lambda *a, **k: created.append(1) or "r1")
    with pytest.raises(HTTPException) as exc:
        admin_scrape.promote_queue_item("q1", {"id": "a", "email": "e"})
    assert exc.value.status_code == 409
    assert created == []
    assert sb.state["queue"][0]["status"] == "promoting"  # untouched
