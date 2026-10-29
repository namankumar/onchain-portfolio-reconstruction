# Source-authenticity assessment

## Decision boundary

The question is whether the existing portable package demonstrates actual investigation engineering or newly authored, simplified packaging. This review uses source files and AST/text comparison only. No original module was imported or executed, and no network/provider/wallet action was taken.

## Observations

| Portable module | Assessment | Source component | Consequence |
| --- | --- | --- | --- |
| `onchain_reconstruction/dispatcher.py` | Close extraction, but not byte-identical | `SRC-EVM-DISPATCH-001` contains the same `push` and runtime bytecode layout, including the adaptive output-memory fix | It should be credited as an extracted algorithm, with owner parameterization and validation called out. |
| `onchain_reconstruction/rpc.py` | New safe wrapper + source-derived recovery algorithm | `SRC-EVM-NONCE-001` and `SRC-EVM-NONCE-002` contain the bounded threaded nonce-bisection search | Do not describe it as a direct copy or imply the existing cache/budget policy was present in the original. |
| `onchain_reconstruction/evm.py` | New generalized decoder | `SRC-EVM-TRACE-001`, `SRC-EVM-LEDGER-002`, and `SRC-EVM-LEDGER-003` contain the actual failed-trace, gas and ERC-20 accounting rules | The portable decoder is an honest reimplementation of real rules, not an extracted source module. |
| `onchain_reconstruction/ledger.py` | New package code | Original ledgers are case-specific scripts connected to private transaction/cache inputs | It is useful, but not evidence of a directly portable original subsystem. |
| `onchain_reconstruction/cli.py`, catalog/export/docs/examples/tests | New package work | No matching original command/package layer | Call this packaging/verification work, not original investigation code. |
| `src/solana_idl_decode.py` in this candidate | Byte-identical original code | `SRC-SOL-IDL-001` | This is direct, safe engineering evidence. |

## Frozen source model

The original system was an evidence-driven, case-specific investigation rather than a single generic application. Its genuine technical units include: bounded historical nonce recovery; raw receipt/internal-trace reconstruction; ERC-20/NFT distinction and conservation accounting; code-override sequential-call previews; Solana IDL account decoding; and protocol-specific position/state readers. Most scripts bind these units to private identity, history, responses, or outputs.

The public boundary therefore must preserve a technical unit only when its behavior can be separated from private inputs without inventing a different algorithm. Replacing the unit with fabricated balances, canned reports, or a generic demo would destroy the evidence value. Parameterizing an owner, bounds, endpoint, cache target, or injected RPC reader preserves the original control flow while removing private configuration.

## Candidate transformations

| Candidate | Transformation | Why it is minimal | Not claimed |
| --- | --- | --- | --- |
| `solana_idl_decode.py` | None; byte-identical from `SRC-SOL-IDL-001` | It is already standalone and contains no private values | That it decodes every Solana program or proves a position exists |
| `evm_dispatcher.py` | `A` global becomes `owner`; `runtime` becomes `build_runtime`; `operation`/`simulate` omitted because they depend on private RPC/cache helpers | All EVM opcodes, memory layout, result layout, error path and sequential-call semantics remain source-equivalent to `SRC-EVM-DISPATCH-001` | That a preview was executed, a route is executable, or a transaction is signed/broadcast |
| `nonce_recovery.py` | Global owner/endpoint/range/nonce/counters become function arguments; direct cache writes/printing and script-start side effects are removed; injected `rpc` replaces a private transport helper | The queue, worker, bisection, limit/deadline, monotonicity check, leaf transaction fetch, sorting and error capture remain the `SRC-EVM-NONCE-001` algorithm | That provider coverage is complete or that this candidate has contacted any provider |

## Known blockers to broader direct extraction

The source components behind `SRC-EVM-TRACE-001`, `SRC-EVM-LEDGER-002`, `SRC-EVM-LEDGER-003`, `SRC-EVM-POSITION-001` and `SRC-EVM-POSITION-002`, plus protocol recovery components, mix useful logic with actual wallet identifiers, transaction records, original exports, cache locations and result reports. Their public-safe extraction needs an explicit fixture/evidence contract and per-chain source review—not blind redaction. Seed/derivation modules are excluded entirely.

This candidate shows the real portable core first. It does not imply that every one of the 258 scripts is suitable for public release.
