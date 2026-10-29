# Existing-version comparison

Layer: **deterministic software probes, not an LLM benchmark**. Both existing revisions use byte-identical receipt/ledger code. The fixed driver reads all evidence, decodes all bundles, then reconciles. It is not an autonomous investigator.

| Existing revision | Cases | Trials/case | Valid runs | Task-oracle success | Tool errors | Provider USD |
|---|---:|---:|---:|---:|---:|---:|
| d084374 | 20/20 | 3 | 100% | 70% | 21 | 0 |
| a81ed25 | 20/20 | 3 | 100% | 70% | 21 | 0 |

**No measured improvement.** These revisions have the same accounting source. Local per-run wall times are in the JSON, include grading/replay overhead, and are not model latency or a speedup claim. Hardware/energy cost was not measured.

## Retained failures

| Case | Baseline | Existing candidate | Errors | Evidence |
|---|---|---|---|---|
| RCP-06 | fail | fail | exact_raw_ledger, missing_or_unjustified_gap, status, unsupported_claim_value | [exact episode IDs](scorecard.json) `a81ed25-RCP-06-t1` |
| RCP-07 | fail | fail | exact_raw_ledger, missing_or_unjustified_gap, status, unsupported_claim_value | [exact episode IDs](scorecard.json) `a81ed25-RCP-07-t1` |
| RCP-08 | fail | fail | missing_or_unjustified_gap | [exact episode IDs](scorecard.json) `a81ed25-RCP-08-t1` |
| RCP-11 | fail | fail | exact_raw_ledger, missing_or_unjustified_gap, status, unsupported_claim_value | [exact episode IDs](scorecard.json) `a81ed25-RCP-11-t1` |
| RCP-19 | fail | fail | exact_raw_ledger, missing_or_unjustified_gap, status, unsupported_claim_value | [exact episode IDs](scorecard.json) `a81ed25-RCP-19-t1` |
| RCP-20 | fail | fail | exact_raw_ledger, missing_or_unjustified_gap, status, unsupported_claim_value | [exact episode IDs](scorecard.json) `a81ed25-RCP-20-t1` |

## Other layers

- **Model-task comparison: not-reached, zero trials.** No model/prompt/provider performance is claimed. The protocol and prompt are ready for a separately authorized runner; they do not call a provider.
- **Operational recovery impact: not-reached.** No asset recovery, cash proceeds, wallet-control or live-chain claims are measured here.
- Four cases are reserved from the runtime prompt as held-out tasks. They are public reproducibility fixtures, not a secret generalization test; no model tuning or generalization result is claimed.
- Failures are investigation findings, not authorization to change the product. See [proposed experiments](../FINDINGS.md).
