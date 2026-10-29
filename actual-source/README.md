# Original Reconstruction Components

These are original algorithms extracted from the reconstruction project, alongside the separately packaged CLI in the repository root. Private wallet records, addresses, transactions, balances, labels, raw responses, caches and research narratives are excluded.

It contains three narrow, source-traceable components:

| Candidate | Authenticity | Source component | Why it is safe to evaluate |
| --- | --- | --- | --- |
| `src/solana_idl_decode.py` | **Byte-identical extraction** | `SRC-SOL-IDL-001` | Self-contained, offline decoder; no addresses, transactions, balances, caches, signer material or network code |
| `src/evm_dispatcher.py` | **Minimal-redaction extraction** | `SRC-EVM-DISPATCH-001`, `push` and `runtime` | The actual sequential `eth_call` override bytecode builder; the private owner global becomes an explicit `owner` argument. It does not make an RPC call. |
| `src/nonce_recovery.py` | **Source-derived parameterization** | `SRC-EVM-NONCE-001`, `SRC-EVM-NONCE-002` | The actual bounded concurrent nonce-bisection recovery algorithm, with private account, endpoint, fixed block bounds, and cache-writing removed in favor of explicit inputs and an injected read-only RPC callable. |

The opaque source IDs, hashes and exact transformations are recorded in `provenance.json` and [AUTHENTICITY.md](AUTHENTICITY.md). A private ignored filename map exists for internal review; public exports must exclude `private-review/`.


## What is deliberately excluded

- Every wallet address, transaction hash, balance, token quantity, label, timestamp, report result, screenshot, raw response, cache path and local filesystem path.
- Seed-phrase/derivation modules and all authenticated or signing code.
- Hard-coded RPC endpoints, calls at import time, report orchestration and personal cache I/O.
- Any claim that these modules have been live-run since extraction. Offline synthetic contracts are exercised by tools/verify_offline.py in the repository root; no live-provider or recovery result is claimed.

## Review checks

```sh
python3.12 -m py_compile src/*.py
python3.12 -m unittest discover -s tests -v
python3.12 - <<'PY'
from pathlib import Path
import hashlib
path = Path('src/solana_idl_decode.py')
print(hashlib.sha256(path.read_bytes()).hexdigest())
PY
```

The second command should emit the byte-identical original hash recorded in `provenance.json`. No network, wallet, signing or transaction operation is involved.

## Promotion rule

Promote a candidate only after an independent public-source/privacy review confirms that the code and metadata contain no personal facts and the public package documents its provenance truthfully. The original investigation remains private.
