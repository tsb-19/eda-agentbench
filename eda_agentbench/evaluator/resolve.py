"""Evaluator resolution.

A task's `metadata.json` names its evaluator as a string. Two forms are accepted:

    "workflow_handoff.WorkflowHandoffEvaluator"        -> eda_agentbench.evaluator.workflow_handoff
    "tests.support.qa_stub_evaluator:AnswerMatchStub"  -> any importable module (test support)

Before this branch the resolution was a ~60-line `if/elif` chain, duplicated in `cli.py` and
`agentic/runner.py`, naming every track evaluator explicitly and silently falling back to the
RTL-debug evaluator for anything unrecognised. Both properties became liabilities once the
benchmark tracks that are not part of the paper were removed: the chain listed modules that no
longer exist, and the silent fallback would have scored a task with the wrong evaluator instead
of failing. Resolution is now dynamic and unknown specs raise.
"""

from __future__ import annotations

import importlib
from pathlib import Path

PACKAGE = "eda_agentbench.evaluator"


def resolve_evaluator(evaluator_spec: str, task_path: Path, meta: dict):
    """Instantiate the evaluator named by `evaluator_spec`.

    Raises ValueError with the offending spec if the module or class cannot be resolved --
    never falls back to a different evaluator, because scoring a task with the wrong grader
    is worse than failing to score it.
    """
    if not evaluator_spec or not isinstance(evaluator_spec, str):
        raise ValueError(f"task declares no evaluator: {evaluator_spec!r}")

    if ":" in evaluator_spec:
        module_name, _, class_name = evaluator_spec.partition(":")
    else:
        module_stem, _, class_name = evaluator_spec.rpartition(".")
        if not module_stem:
            raise ValueError(f"malformed evaluator spec {evaluator_spec!r} "
                             f"(expected 'module.Class' or 'package.module:Class')")
        module_name = f"{PACKAGE}.{module_stem}"

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise ValueError(
            f"evaluator module {module_name!r} not found for spec {evaluator_spec!r}. "
            f"This branch keeps only the evaluators the paper uses; see docs/REMOVED.md."
        ) from exc

    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise ValueError(
            f"evaluator class {class_name!r} not found in {module_name!r}"
        ) from exc

    return cls(task_path, meta)
