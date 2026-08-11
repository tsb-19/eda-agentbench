# Phase-7 Study C — Terminal-Bench 2.0→2.1 Static Audit (26 officially documented repairs)

**Framing:** *Retrospective application of a preregistered audit taxonomy to the 26 officially documented repairs between Terminal-Bench 2.0 and 2.1.*
This does NOT claim our protocol predicted/prevented the repairs, nor that Terminal-Bench validates our runtime implementation. No model calls.

## Frozen inputs (acquired + hashed before coding)
- **A. 2.0 snapshot:** `harbor-framework/terminal-bench-2` @main, 89 tasks (tasklist sha256 `5c7ed05c`).
- **B. 2.1 snapshot:** `harbor-framework/terminal-bench-2-1` @main, 89 tasks (same names; 26 content-modified).
- **C. Manifest:** PR #53 'Terminal-Bench 2.1' in `terminal-bench-2` (body sha256 `c7172fc6`; 57 files sha256 `fccf2d61`). Audit universe = the 26 enumerated tasks.
- **Provenance note:** an earlier PR #53 in the legacy `terminal-bench-1` repo ('Share envs across instances') is unrelated; recorded, not used.

## Coverage distribution
- **Direct:** 1  | **Partial:** 21  | **Not-covered/Other:** 4  (of 26)

## Validity-threat layer distribution (multi-layer allowed)
- L1_capability: 17
- L3_execution: 10
- L4_artifact_integrity: 1
- Other: 4

## Repair-mechanism distribution
- instruction_clarification: 10
- environment_dependency_repair: 10
- verifier_test_tightening: 5
- resource_increase: 5
- verifier_test_broadening: 4
- oracle_repair: 4
- timeout_change: 1
- external_dependency_removal: 1
- hidden_artifact_removal: 1

## Multi-layer cases (6)
caffe-cifar-10, filter-js-from-html, mteb-leaderboard, mteb-retrieve, torch-tensor-parallelism, train-fasttext

## Ambiguous / disagreement cases
- build-pov-ray
- financial-document-processor
- mcmc-sampling-stan
- overfull-hbox
- protein-assembly (L1 oracle-correctness vs L3 external-API dependency)
- train-fasttext (L3 verifier-reliability vs L1 capability)

## Primary descriptive result
Our protocol **directly** addresses only the action-surface/cheat repair (`fix-git`, L4). Most repairs **partially** overlap our layers: instruction/test misalignment and oracle-correctness map conceptually to capability validity (L1), and resource/timeout/dependency/oracle-execability map to execution validity (L3) — but our specific controls are EDA semantic-handoff / PT-HSPICE tool-health oriented, not generic verifier-over-specification or container-resource hygiene. Four package-pin removals are **not covered** (environment maintenance, outside the four layers). No repair mapped to sampling validity (L2). This is the honest external-taxonomy-application outcome: partial conceptual overlap, limited direct coverage — **not** a claim of prediction or prevention.

## Per-repair coding (26)
| task | validity_threat | repair_mechanism | coverage |
|---|---|---|---|
| adaptive-rejection-sampler | L1_capability | instruction_clarification | partial |
| build-pmars | L1_capability | instruction_clarification, verifier_test_tightening | partial |
| caffe-cifar-10 | L3_execution, L1_capability | timeout_change, verifier_test_broadening, instruction_clarification, environment_dependency_repair, resource_increase | partial |
| compile-compcert | L3_execution | environment_dependency_repair | partial |
| configure-git-webserver | L1_capability | oracle_repair, verifier_test_tightening | partial |
| extract-moves-from-video | L3_execution | external_dependency_removal | partial |
| filter-js-from-html | L1_capability, L3_execution | instruction_clarification, resource_increase | partial |
| fix-git | L4_artifact_integrity | hidden_artifact_removal, verifier_test_tightening | direct |
| hf-model-inference | L1_capability | verifier_test_broadening | partial |
| install-windows-3.11 | L1_capability | instruction_clarification, verifier_test_tightening | partial |
| make-doom-for-mips | L3_execution | oracle_repair, environment_dependency_repair | partial |
| mteb-leaderboard | L3_execution, L1_capability | environment_dependency_repair, instruction_clarification, resource_increase | partial |
| mteb-retrieve | L3_execution, L1_capability | environment_dependency_repair, instruction_clarification | partial |
| polyglot-c-py | L1_capability | verifier_test_broadening | partial |
| polyglot-rust-c | L1_capability | verifier_test_broadening | partial |
| protein-assembly | L1_capability | oracle_repair | partial |
| rstan-to-pystan | L1_capability | oracle_repair | partial |
| sam-cell-seg | L1_capability | instruction_clarification | partial |
| torch-tensor-parallelism | L1_capability, L3_execution | instruction_clarification, resource_increase | partial |
| torch-pipeline-parallelism | L3_execution | resource_increase | partial |
| query-optimize | L1_capability | instruction_clarification | partial |
| train-fasttext | L3_execution, L1_capability | verifier_test_tightening, environment_dependency_repair | partial |
| build-pov-ray | Other | environment_dependency_repair | not_covered |
| financial-document-processor | Other | environment_dependency_repair | not_covered |
| mcmc-sampling-stan | Other | environment_dependency_repair | not_covered |
| overfull-hbox | Other | environment_dependency_repair | not_covered |
