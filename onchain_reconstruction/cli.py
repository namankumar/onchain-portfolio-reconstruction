"""Explicit offline commands; network access requires scan-nonces."""
import argparse
import csv
import json
import os
from pathlib import Path

from .evm import decode
from .ledger import markdown, reconcile
from .rpc import RPC, scan_nonces
from .dispatcher import build_dispatcher


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("reconcile", help="Reconcile a normalized JSON ledger offline")
    report.add_argument("input", type=Path)
    report.add_argument("--format", choices=["json", "markdown"], default="json")
    decoder = sub.add_parser("decode-evm", help="Decode a saved EVM transaction/receipt/trace bundle offline")
    decoder.add_argument("input", type=Path)
    importer = sub.add_parser("import-csv", help="Import a normalized movement CSV offline")
    importer.add_argument("input", type=Path)
    dispatcher = sub.add_parser("build-dispatcher", help="Generate unsigned preview bytecode offline; no RPC submission")
    dispatcher.add_argument("input", type=Path)
    scan = sub.add_parser("scan-nonces", help="Explicit read-only live outgoing transaction discovery")
    scan.add_argument("--address", required=True)
    scan.add_argument("--chain-id", type=int, required=True)
    scan.add_argument("--start", type=int, required=True)
    scan.add_argument("--end", type=int, required=True)
    scan.add_argument("--budget", type=int, default=1000)
    scan.add_argument("--cache", type=Path, default=Path("cache/rpc"))
    scan.add_argument("--rpc-env", default="CRYPTO_RPC_URL", help="Environment variable containing the RPC URL")
    args = parser.parse_args(argv)
    try:
        if args.command == "reconcile":
            result = reconcile(json.loads(args.input.read_text()))
            print(markdown(result) if args.format == "markdown" else json.dumps(result, indent=2))
            return 0 if result["reconciled"] else 2
        if args.command == "decode-evm":
            result = decode(json.loads(args.input.read_text()))
        elif args.command == "build-dispatcher":
            document = json.loads(args.input.read_text())
            result = {"code": build_dispatcher(document["owner"], document["calls"]),
                      "scope": "Preview code only; not deployed or submitted; no balances/storage overridden"}
        elif args.command == "import-csv":
            with args.input.open(newline="") as source:
                reader = csv.DictReader(source)
                fields = {"id", "asset", "amount_raw", "direction", "kind", "status", "source", "observed_at"}
                if set(reader.fieldnames or []) != fields:
                    raise ValueError("CSV columns must exactly match the documented normalized schema")
                result = {"events": list(reader), "scope": "Add independently observed opening/end balances before reconciling"}
        else:
            url = os.environ.get(args.rpc_env)
            if not url:
                raise ValueError(f"Set {args.rpc_env} to an HTTPS public/archive RPC URL")
            rpc = RPC(url, args.cache, args.budget)
            result = scan_nonces(rpc.call, args.address, args.chain_id, args.start, args.end,
                                 verify_call=lambda method, params: rpc.call(method, params, refresh=True))
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        # Do not echo provider bodies, environment values or private input data.
        if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError):
            message = str(error)
        else:
            message = "Invalid or unavailable input; inspect schema and paths"
        parser.exit(2, "error: " + message + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
