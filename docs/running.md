# Run with your own inputs

## 1. Reconcile a normalized ledger offline

Use `examples/ledger.json` as the complete schema:

```json
{
  "opening": {"31337:native": "0"},
  "observed": {"31337:native": "100"},
  "events": [{
    "id": "unique-event-id",
    "asset": "31337:native",
    "amount_raw": "100",
    "direction": "in",
    "kind": "transfer",
    "status": "success",
    "source": "your-evidence-reference",
    "observed_at": "2026-01-01T00:00:00Z"
  }]
}
```

Use string integer quantities in the asset's smallest unit. Native assets use `CHAIN_ID:native`; tokens can use `CHAIN_ID:CONTRACT`. Every asset has explicit opening and ending entries. An unknown ending balance is JSON `null`, not `"0"`. Use unique IDs, preferably chain/transaction/log-or-trace identifiers. `kind` is `transfer` or `gas`; direction is `in` or `out`; status is `success`, `failed` or `unknown`. Unknown events prevent a complete result. Ending balances and events must describe the same interval; the CLI cannot independently prove that your opening balance or input set is exhaustive.

```sh
mkdir -p private output
python3 -m onchain_reconstruction.cli reconcile private/my-ledger.json > output/reconciliation.json
python3 -m onchain_reconstruction.cli reconcile private/my-ledger.json --format markdown > output/reconciliation.md
```

Create `private/my-ledger.json` yourself using the documented schema before running. `private/`, `output/` and `cache/` are ignored by Git. Shell redirection can leave an empty file on failure; check command exit status and JSON completeness before using a report.

## 2. Import CSV movements

The exact required header is:

```csv
id,asset,amount_raw,direction,kind,status,source,observed_at
```

```sh
python3 -m onchain_reconstruction.cli import-csv examples/movements.csv > output/imported-events.json
```

This is a normalized movement importer, **not** an automatic exchange, tax, or portfolio adapter. Validate columns, raw units and transaction meaning from your source first. Add independent opening and observed balance entries, then reconcile. The accounting CLI does not determine tax treatment or cost basis.

## 3. Decode saved EVM evidence

`examples/evm-bundle.json` supplies an owner, chain ID, observation timestamp, source reference, transaction, matching receipt, explicit additional fee and optional Parity-style traces.

```sh
python3 -m onchain_reconstruction.cli decode-evm examples/evm-bundle.json > output/decoded-events.json
```

Output is movement evidence, not an entire ledger. Combine transactions with nonoverlapping event IDs and independently measured opening/end balances. If traces are absent, internal native movements are explicitly uncovered. An empty supplied trace array is not proof that no internal movements occurred. Self-destruct/contract-creation value and reverted parent subtrees are handled, but trace completeness and provider correctness are the caller's responsibility.

## 4. Reconstruct outgoing EVM history

Supply your public address, verified chain ID, finalized start/end blocks and archive RPC URL. The inclusive search interval must satisfy `1 <= start <= end`. It compares account nonce at `start − 1` and `end`, recursively queries changing subranges, fetches relevant full blocks and verifies that returned sender nonces match the expected interval exactly.

Requirements:

- Historical `eth_getTransactionCount` at block numbers.
- `eth_chainId` and `eth_getBlockByNumber` with full transactions.
- Enough budget for the chosen account/range and two fresh boundary checks.
- A provider permitted for your use. This package does not provision accounts, enter keys or discover a free endpoint.

Use the live command in the README. Put keyed URLs in your own environment rather than a committed file or command argument. Cached requests contain your public address and may reveal a portfolio relationship, so keep `cache/` private. HTTP errors, pruning, wrong chain IDs, inconsistent nonces and budget exhaustion stop the scan. There is no resume-from-partial-transaction-list mode; rerun the same fixed range to reuse successful cached reads. Final boundary reads always use the provider.

## 5. Inspect unsigned preview code

```sh
python3 -m onchain_reconstruction.cli build-dispatcher examples/preview-calls.json
```

Input contains a public owner and a bounded list of `{to, data, value}` calls. Output is temporary preview bytecode only. It performs no RPC request, deployment, signing or transaction submission. Do not send it as a transaction. Provider state overrides and chain/protocol-specific simulations remain separate investigation tooling.

## Original investigation prerequisites

The full catalog's scripts are not all runnable from this package. Original report generation needs the private evidence tree, exact recorded filenames and schema versions, transaction exports and the established report dispatcher. Discovery/simulation scripts may perform network calls at import time; inspect them before execution. Some require optional third-party libraries such as `requests`, address-derivation/chain SDKs or plotting tools. No catch-all installation command is justified by the import catalog.

To port another adapter: isolate pure decoding from fetching/reporting; replace fixed owner/path/range with explicit inputs; retain chain/contract/token identity checks; add synthetic/cache fixtures and a failure test; document observed state versus simulation versus execution. Then add one explicit command. The existing 258 scripts remain preserved in local private Git history, not imported by the public-safe core.

## Troubleshooting

| Symptom | Meaning / action |
| --- | --- |
| `No module named onchain_reconstruction` | Run from the package root, or use the optional editable install |
| Nonzero reconciliation difference | Missing/duplicated movement, wrong interval, fee, unit or input; investigate it |
| `complete: false` | Missing balance or unknown event; obtain evidence rather than fill zero |
| HTTP 429 / budget exhausted | Narrow the range or deliberately choose a larger allowed budget; no result was proved |
| Historical state unavailable | Use a provider retaining state for those blocks |
| Coverage mismatch | Block data/nonces disagree, or nonce changes have another cause; do not claim completeness |
| Cached response integrity failure | Preserve the suspect cache for inspection; rerun with a separate clean cache directory |
| Preview bytecode built | Encoding succeeded, not evidence of recoverability or live execution |

