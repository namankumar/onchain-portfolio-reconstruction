# Retained findings — no product changes authorized

These are task-contract gaps observed in the fixed software probe at both existing revisions. They are not measurements of an LLM's reasoning. A future model may resolve some by selecting and comparing evidence before using the tools. Existing CLI documentation already assigns some coverage/identity responsibility to the caller; the findings do not imply the CLI promised exhaustive investigation.

| ID / cases | Observed result | Proposed investigation or experiment | State |
|---|---|---|---|
| E-F01 / RCP-06 | Without traces the computed subtotal differs from the observed boundary; the probe does not identify missing internal coverage | Evaluate a model's ability to request traces and retain a justified unknown; propose coverage enforcement separately | reported; implementation held |
| E-F02 / RCP-07 | Existing decode accepts a transaction whose chainId contradicts the supplied bundle chain | Propose cross-source chain identity validation; no validator added to the product | reported; implementation held |
| E-F03 / RCP-08 | Conflicting status receipts reach duplicate-event rejection; the probe does not report the contradiction itself | Evaluate evidence comparison and justified refusal; do not choose a status arbitrarily | reported; implementation held |
| E-F04 / RCP-11 | Two copies of the same receipt trigger duplicate-event rejection | Evaluate identity-based deduplication before decoding; normalization changes require approval | reported; implementation held |
| E-F05 / RCP-19 | Existing decode accepts a child whose parent trace frame is absent | Propose trace-tree coverage validation; no behavior changed | reported; implementation held |
| E-F06 / RCP-20 | Existing decode accepts a token log's contradictory transactionHash | Propose per-log identity validation; no behavior changed | reported; implementation held |

Both versions score14/20 (70%) under this fixed probe and stronger oracle, repeated three times/case. No regressions, gains or optimization are claimed. Real failures and exact episodes remain in results/scorecard.json. Nothing here authorizes changes to product code, prompts, routing, tools, provider policy, model choice or production configuration.

Grader calibration detects false raw values, hidden/missing evidence, unsupported citations, forged transcripts, malformed fields and forbidden attempts. Replay establishes consistency with the supplied synthetic state, not historical authenticity of a model session. Free-prose entailment and undisclosed material claims remain human-review limitations. Public held-out fixtures are not secret generalization evidence.
