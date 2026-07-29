"""Tests for the Level-2 full-path check standard (scripts/fullpath_check.py).

Covers: (1) score-independence -- the check takes no candidate/score argument and never inspects a
candidate result; (2) healthy path; (3) signoff-RED corruption -> unhealthy; (4) broken digest chain
-> unhealthy; (5) truncated/missing report -> unhealthy. regen_evidence + artifacts are mocked."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fullpath_check as L2  # noqa: E402

REPORT_OK_HDR = "# acc_stage stage-1 evidence\n# consumed_netlist=netlist_v2.v clock=clk_main scenario=slow corner=func signoff=OK paths=1 slack=0.130000\n"
REPORT_BAD_HDR = "# acc_stage stage-1 evidence\n# consumed_netlist=netlist_v2.v clock=clk_main scenario=slow corner=func signoff=FAIL paths=1 slack=-0.500000\n"
BODY = "=== REPORT_TIMING BEGIN ===\nslack (MET) 0.13\n=== REPORT_TIMING END ===\n"


def _seed_workspace(work, hdr, signoff="OK", digest_match=True, complete=True):
    (work / "timing_report.rpt").write_text(hdr + BODY)
    rd = "389cdd5f065ccc886343a4cda3b00a51c0fe9072589d5994983257c1f42aa64a"
    upstream = rd if digest_match else "deadbeef" * 8
    (work / "evidence_manifest.json").write_text(__import__("json").dumps(
        {"tool_exit": 0, "signoff": signoff, "report_digest": rd}))
    (work / "stage2_summary.json").write_text(__import__("json").dumps(
        {"signoff": signoff, "upstream_evidence_digest": upstream}))
    if not complete:
        (work / "timing_report.rpt").write_text(hdr)  # no REPORT_TIMING body


def test_check_is_score_independent_signature():
    # the check function must take NO candidate/score parameter -- only env (+ optional timeout)
    sig = inspect.signature(L2.check)
    params = set(sig.parameters)
    assert "env" in params
    for forbidden in ("candidate", "score", "expected", "task_id", "tid", "result"):
        assert forbidden not in params, f"check() must not take a candidate/score arg: {forbidden}"


def test_check_source_does_not_inspect_scores():
    # the check() FUNCTION BODY (excluding docstring) must not reference candidate scores / expected
    # fairness results. (The module docstring legitimately says it does NOT inspect candidates.)
    import ast, inspect
    src = inspect.getsource(L2.check)
    tree = ast.parse(src)
    # drop docstrings (string literals that are the first statement)
    body = [n for n in tree.body[0].body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
    code = ast.unparse(ast.Module(body=body, type_ignores=[]))
    for forbidden in ("total_score", "expected", "wrong_axis", "golden_score"):
        assert forbidden not in code, f"check() body must not reference '{forbidden}' (score-dependent)"


def test_healthy_path(monkeypatch, tmp_path):
    work_holder = {}

    def fake_regen(work, env, timeout):
        work_holder["w"] = work
        _seed_workspace(work, REPORT_OK_HDR)

    def fake_copytree(src, dst, **kw):
        # minimal staging so flow_config + solution exist
        Path(dst).mkdir(parents=True, exist_ok=True)
        return None
    monkeypatch.setattr(L2, "REFERENCE_FC_HASH", None, raising=False)  # bypass fingerprint for unit test
    monkeypatch.setattr(L2.shutil, "copytree", fake_copytree)
    monkeypatch.setattr(L2.G, "regen_evidence", fake_regen)
    # make the fingerprint check pass: patch sha256 of the solution flow_config
    monkeypatch.setattr(L2, "REFERENCE_FC_HASH", "x")
    (L2.G.TRACK / L2.REFERENCE_TASK / "solution").mkdir(parents=True, exist_ok=True)
    (L2.G.TRACK / L2.REFERENCE_TASK / "solution" / "flow_config.json").write_text("{}")
    monkeypatch.setattr(L2.hashlib, "sha256", lambda b: type("H", (), {"hexdigest": lambda self: "x"})())
    rec = L2.check({})
    assert rec["healthy"] is True
    assert rec["signoff_ok"] and rec["slack_ok"] and rec["freshness_ok"]


def test_signoff_red_corruption_is_unhealthy(monkeypatch):
    def fake_regen(work, env, timeout):
        _seed_workspace(work, REPORT_BAD_HDR, signoff="FAIL")
    monkeypatch.setattr(L2.G, "regen_evidence", fake_regen)
    monkeypatch.setattr(L2.shutil, "copytree", lambda *a, **k: None)
    (L2.G.TRACK / L2.REFERENCE_TASK / "solution").mkdir(parents=True, exist_ok=True)
    (L2.G.TRACK / L2.REFERENCE_TASK / "solution" / "flow_config.json").write_text("{}")
    monkeypatch.setattr(L2, "REFERENCE_FC_HASH", "x")
    monkeypatch.setattr(L2.hashlib, "sha256", lambda b: type("H", (), {"hexdigest": lambda self: "x"})())
    rec = L2.check({})
    assert rec["healthy"] is False
    assert rec["signoff_ok"] is False


def test_broken_digest_chain_is_unhealthy(monkeypatch):
    def fake_regen(work, env, timeout):
        _seed_workspace(work, REPORT_OK_HDR, digest_match=False)
    monkeypatch.setattr(L2.G, "regen_evidence", fake_regen)
    monkeypatch.setattr(L2.shutil, "copytree", lambda *a, **k: None)
    (L2.G.TRACK / L2.REFERENCE_TASK / "solution").mkdir(parents=True, exist_ok=True)
    (L2.G.TRACK / L2.REFERENCE_TASK / "solution" / "flow_config.json").write_text("{}")
    monkeypatch.setattr(L2, "REFERENCE_FC_HASH", "x")
    monkeypatch.setattr(L2.hashlib, "sha256", lambda b: type("H", (), {"hexdigest": lambda self: "x"})())
    rec = L2.check({})
    assert rec["healthy"] is False
    assert rec["freshness_ok"] is False


def test_truncated_report_is_unhealthy(monkeypatch):
    def fake_regen(work, env, timeout):
        _seed_workspace(work, REPORT_OK_HDR, complete=False)
    monkeypatch.setattr(L2.G, "regen_evidence", fake_regen)
    monkeypatch.setattr(L2.shutil, "copytree", lambda *a, **k: None)
    (L2.G.TRACK / L2.REFERENCE_TASK / "solution").mkdir(parents=True, exist_ok=True)
    (L2.G.TRACK / L2.REFERENCE_TASK / "solution" / "flow_config.json").write_text("{}")
    monkeypatch.setattr(L2, "REFERENCE_FC_HASH", "x")
    monkeypatch.setattr(L2.hashlib, "sha256", lambda b: type("H", (), {"hexdigest": lambda self: "x"})())
    rec = L2.check({})
    assert rec["healthy"] is False
    assert rec["report_complete"] is False
