# Human Ground-Truth Labeling Guide: Verifier Benchmark

This guide documents the criteria and methodology used to author the 35 ground-truth claim verdicts in `eval/labeled_claims.json`.

---

## 1. Benchmark Purpose

To guarantee the Verifier is not circularly "grading its own homework," every claim-excerpt pair has been hand-labeled according to rigorous analytical standards.

The dataset is partitioned into:
- **25 Dev Claims**: Used for prompt development, tuning verification criteria, and analyzing failure modes.
- **10 Held-Out Claims**: Strictly isolated and evaluated out-of-sample to test prompt generalization and prevent overfitting.

---

## 2. Verdict Decision Criteria

### `SUPPORTED`
- The source excerpt directly and unambiguously states the assertion made in the claim.
- **Strict Quantitative Alignment**: Every number, price, currency sign, date, percentage, and unit in the claim matches the excerpt exactly.
- **No Scope Drift**: The entity, geographic region, and product tier correspond precisely to the excerpt.

### `PARTIAL`
- The source excerpt backs a meaningful portion of the claim, but the claim:
  - Omits a critical qualifying condition (e.g. stating general FDA approval while the excerpt specifies approval was restricted to age $\ge 12$).
  - Overgeneralizes or mildly exaggerates a metric (e.g. claiming "flawless accuracy" when the excerpt states "83% accuracy").
  - References a feature in general availability when the excerpt specifies it is in "public beta".

### `UNSUPPORTED`
- The source excerpt fails to back the assertion, specifically:
  - Direct contradiction (e.g. excerpt says 1.5% fee; claim says 0% fee).
  - Numeric corruption (e.g. $2.00 changed to $20, or $1.1B changed to $11B).
  - Negation inversion (e.g. excerpt says "did not approve"; claim says "approved").
  - Fabricated facts not mentioned in the source excerpt.

---

## 3. Key Failure Modes Scored

1. **False-SUPPORTED (High Severity)**: The verifier marks an unsupported or corrupted claim as `SUPPORTED`. This is the most dangerous failure in an analyst workflow.
2. **False-UNSUPPORTED (Medium Severity)**: The verifier marks a genuinely supported claim as `UNSUPPORTED` due to rigid syntactic differences.
3. **Partial Confusion (Low Severity)**: Disagreement between `PARTIAL` and `SUPPORTED` due to differing thresholds of qualifier importance.
