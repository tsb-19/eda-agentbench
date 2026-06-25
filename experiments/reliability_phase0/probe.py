"""Reliability/calibration Phase-0 probe (tool-free, gateway-only).

Runs k repeated trials per (model, task) at temperature>0 on a difficulty-stratified set of tool-free
P3 timing-report QA tasks, eliciting a calibrated CONFIDENCE/ABSTAIN with each answer. Grades each
trial with the existing match_answer, then reports per-model reliability (pass@1, pass@k, pass^k,
reliability gap, flip rate) + calibration (overconfident-wrong rate, cautious-fail, abstention, trust
score) + protocol-failure tally + cost. Scripted fairness baselines validate the metrics first.

GO if the reliability/calibration metrics DISCRIMINATE among the 5 models AND pass^k < pass@1 somewhere
(a real reliability gap). Usage:
  python experiments/reliability_phase0/probe.py baselines      # metrics self-test, no gateway
  python experiments/reliability_phase0/probe.py [tasks_per_type=1] [k=5]
"""
import concurrent.futures as cf
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "/data1/tongsb/eda-agentbench")
sys.path.insert(0, str(Path(__file__).parent))
from scripts.generate_model_submissions import load_model_specs
from eda_agentbench.evaluator.answer_match import match_answer
import metrics as M

ROOT = Path("/data1/tongsb/eda-agentbench")
GEN = ROOT / "tasks/p3_timing_report_qa/generated"
RELIABILITY_TEMP = 0.7          # fixed sampling temp so run-to-run variance is exposed fairly
MAX_WORKERS = 4                 # single-shot seat limit
SYS = "You are a precise STA/timing engineer. Answer from the report only and report your confidence honestly."

ANS_RE = re.compile(r"ANSWER\s*[:=]\s*(.+)", re.I)
CONF_RE = re.compile(r"CONFIDENCE\s*[:=]\s*\**\s*(HIGH|MEDIUM|MED|LOW|ABSTAIN)", re.I)


def select_tasks(per_type: int) -> list[Path]:
    """One-or-more task per (question_type) to stratify difficulty; deterministic order."""
    by_type: dict[str, list[Path]] = {}
    for md in sorted(GEN.glob("*/metadata.json")):
        try:
            d = json.loads(md.read_text())
        except Exception:
            continue
        qt = d.get("answer", {}).get("question_type", "?")
        by_type.setdefault(qt, []).append(md.parent)
    out = []
    for qt in sorted(by_type):
        out.extend(by_type[qt][:per_type])
    return out


def build_prompt(task_dir: Path) -> tuple[str, dict]:
    meta = json.loads((task_dir / "metadata.json").read_text())
    prompt_md = (task_dir / "prompt.md").read_text()
    report = (task_dir / "files" / "timing_report.rpt").read_text()
    p = (f"{prompt_md}\n\n# timing_report.rpt\n```\n{report}\n```\n\n"
         "Respond with EXACTLY two lines and nothing else:\n"
         "ANSWER: <a number, or the exact identifier/text — no units, no prose>\n"
         "CONFIDENCE: <HIGH | MEDIUM | LOW | ABSTAIN>\n"
         "Use ABSTAIN only if you genuinely cannot determine the answer from the report.")
    return p, meta["answer"]


_BARE_CONF = {"HIGH", "MEDIUM", "LOW", "ABSTAIN"}


def classify(text: str, ans_cfg: dict) -> tuple[str, str, bool]:
    """Return (outcome, confidence, format_ok). Lenient on FORM (so we measure capability/calibration,
    not label obedience); format_ok tracks exact-format compliance separately as a protocol signal."""
    if not text or not text.strip():
        return "empty", "", False
    labeled_ans = ANS_RE.findall(text)
    cm = CONF_RE.search(text)
    format_ok = bool(labeled_ans) and bool(cm)

    conf = (cm.group(1).lower() if cm else "")
    conf = "medium" if conf == "med" else conf
    if not conf:                                       # lenient: a bare confidence token on its own line
        for ln in text.splitlines():
            tok = ln.strip().strip("*`").upper()
            if tok in _BARE_CONF:
                conf = tok.lower()
                break

    if labeled_ans:
        answer = labeled_ans[-1].strip()
    else:                                              # lenient: last non-empty line that isn't confidence
        cand = [ln.strip() for ln in text.splitlines() if ln.strip()
                and ln.strip().strip("*`").upper() not in _BARE_CONF and not CONF_RE.search(ln)]
        answer = cand[-1] if cand else ""

    if conf == "abstain" and not answer:
        return "abstain", "abstain", format_ok
    if not answer:
        return "parse_fail", conf, format_ok
    if answer.upper() in ("ABSTAIN", "N/A", "UNKNOWN", "CANNOT DETERMINE"):
        return "abstain", "abstain", format_ok
    matched, _ = match_answer(ans_cfg.get("expected", ""), answer,
                              ans_cfg.get("type", "string"), ans_cfg.get("tolerance", 0.01))
    return ("pass" if matched else "fail"), (conf or ""), format_ok


def run_trial(name, prov, gk, task_dir, rep):
    prompt, ans_cfg = build_prompt(task_dir)
    t0 = time.time()
    try:
        resp = prov.generate(prompt, system=SYS, **gk)
        text = resp.text or ""
        toks = (resp.usage or {}).get("completion_tokens", 0)
    except Exception as e:
        return {"model": name, "task": task_dir.name, "rep": rep,
                "outcome": "http_429" if "429" in str(e) else "empty",
                "confidence": "", "format_ok": False, "tokens": 0,
                "latency": time.time() - t0, "raw": str(e)[:80]}
    outcome, conf, fmt_ok = classify(text, ans_cfg)
    return {"model": name, "task": task_dir.name, "rep": rep, "outcome": outcome,
            "confidence": conf, "format_ok": fmt_ok, "tokens": toks,
            "latency": time.time() - t0, "raw": text[:160]}


def fairness_baselines(tasks, k):
    """Scripted trials (no gateway) to validate the metrics behave before trusting models."""
    def synth(outcome, conf):
        return [{"model": "_", "task": t.name, "rep": r, "outcome": outcome,
                 "confidence": conf, "format_ok": True, "tokens": 0, "latency": 0.0}
                for t in tasks for r in range(k)]
    return {
        "always_correct(HIGH)": M.per_model(synth("pass", "high")),
        "always_wrong(HIGH)":   M.per_model(synth("fail", "high")),
        "always_abstain":       M.per_model(synth("abstain", "abstain")),
        "wrong_but_cautious(LOW)": M.per_model(synth("fail", "low")),
    }


def fmt(r):
    return (f"pass@1={r['pass1']:.2f} pass^k={r['passk_all']:.2f} gap={r['reliability_gap']:+.2f} "
            f"flip={r['flip_rate']:.2f} overconf={r['overconf_rate']:.2f}(n={r['n_overconf_wrong']}) "
            f"abst={r['abstain_rate']:.2f} fmt={r['format_compliance']:.2f} trust={r['trust']:+.2f}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "baselines":
        print("=== fairness baselines (metrics self-test, no gateway) ===")
        for nm, r in fairness_baselines(select_tasks(1), 5).items():
            print(f"  {nm:24} {fmt(r)}")
        return

    per_type = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    tasks = select_tasks(per_type)
    print("=== fairness baselines (metrics self-test) ===")
    for nm, r in fairness_baselines(tasks, k).items():
        print(f"  {nm:24} {fmt(r)}")

    specs = load_model_specs(ROOT / "configs/baseline_models.json", allow_mock=False)
    print(f"\n=== {len(tasks)} tasks x {len(specs)} models x k={k} trials @temp={RELIABILITY_TEMP} ===")
    print("    tasks:", ", ".join(t.name.replace("p3_timing_", "") for t in tasks))

    jobs = []
    for name, prov, gk in specs:
        gk = {**gk, "temperature": RELIABILITY_TEMP, "max_tokens": 1500}
        for td in tasks:
            for r in range(k):
                jobs.append((name, prov, gk, td, r))

    results = []
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(run_trial, *j) for j in jobs]
        done = 0
        for f in cf.as_completed(futs):
            results.append(f.result())
            done += 1
            if done % 25 == 0:
                print(f"    ... {done}/{len(jobs)} trials", flush=True)

    by_model: dict[str, list[dict]] = {}
    for t in results:
        by_model.setdefault(t["model"], []).append(t)
    rows = {name: M.per_model(ts) for name, ts in by_model.items()}

    print("\n=== per-model reliability + calibration ===")
    for name in sorted(rows):
        r = rows[name]
        print(f"  {name:16} {fmt(r)}")
        print(f"  {'':16} tokens~{r['mean_tokens']:.0f} lat~{r['mean_latency']:.1f}s protocol={r['protocol']}")

    gap_disc = M.discriminates(rows, "reliability_gap", 0.15)
    trust_disc = M.discriminates(rows, "trust", 0.15)
    overc_disc = M.discriminates(rows, "overconf_rate", 0.15)
    any_gap = any(r["reliability_gap"] > 0.05 for r in rows.values() if r["n_tasks"])
    print("\n=== GO/NO-GO ===")
    print(f"  discriminates on reliability_gap(>=0.15): {gap_disc}")
    print(f"  discriminates on trust(>=0.15):           {trust_disc}")
    print(f"  discriminates on overconf_rate(>=0.15):   {overc_disc}")
    print(f"  real reliability gap (pass^k<pass@1):     {any_gap}")
    go = (gap_disc or trust_disc or overc_disc) and any_gap
    print(f"  => {'GO — reliability signal is real and discriminates' if go else 'NO-GO / inconclusive — consider Phase-0b agentic'}")

    out = ROOT / "experiments/reliability_phase0/results.json"
    out.write_text(json.dumps({"rows": rows, "trials": results}, indent=2))
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
