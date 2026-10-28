# Capability coverage

This table describes engineering patterns represented in the private source base, not a promise of universal CLI support. The portable package extracts only components with explicit inputs, evidence boundaries and synthetic tests. The complete high-level inventory is the [opaque scope manifest](source-catalog.md).

| System family | Engineering patterns represented | Portable status |
| --- | --- | --- |
| EVM networks | Receipts, traces, nonce intervals, native and token transfers, gas, contract calls and state-aware previews | Generic sender-history, receipt decoding, exact accounting and preview-bytecode primitives |
| Non-EVM account and UTXO-style networks | Account/state reads, serialized transaction decoding, token/mint identity and network-specific simulation research | Catalogued only; no portable adapter command |
| Protocol state | Contract reads, positions, rewards, pools, migrations, raw-storage fallbacks and data-quality checks | Investigation patterns documented; no generic protocol adapter |
| Cross-domain movement | Bridge and destination matching, state transitions, settlement checks and failure classification | Evidence model documented; no universal bridge adapter |
| Digital assets | Fungible-token events, non-fungible asset identity and duplicate-accounting guards | ERC20 event decoding in the portable core; no asset indexer |
| Provider behavior | Archive-state reads, pagination, rate limits, retries, reorg boundaries and request budgets | HTTPS RPC allowlist, integrity-checked cache and bounded nonce search |
| Data normalization | CSV imports, raw-unit validation, timestamps, source links and discrepancy reporting | Normalized CSV importer and exact-integer ledger |
| Unsigned evaluation | Sequential-call encoding, calldata/memory isolation and no-execution boundaries | Pure EVM preview-bytecode builder; no simulation service or broadcast |

## Coverage principles

- Supplied evidence, provider observations and execution previews are distinct states.
- Native, token, receipt and trace data are accounted for separately to prevent duplicate counting.
- Missing data, provider failures and unresolved intervals stop a completeness claim rather than becoming zero.
- Public chain reads and signed transaction execution are separate authority boundaries.
- Adapters require explicit chain, contract, token and interval validation before they can make a result claim.

## Outside the portable package

The release excludes real addresses, account sessions, seed derivation, credentials, exports, screenshots, response caches, signing, broadcast, tax calculation, a universal indexer and protocol-specific adapters. The opaque manifest preserves source-base scale and categories without exposing private filenames, source hashes or import dependencies.
