"""Receipt/trace decoding extracted from the native and ERC20 ledger work."""
import re

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise ValueError("Expected a public EVM address")
    return value.lower()


def quantity(value):
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", value):
        raise ValueError("Expected an RPC hex quantity")
    return int(value, 16)


def decode(bundle):
    owner, tx, receipt = address(bundle["owner"]), bundle["transaction"], bundle["receipt"]
    txid, chain = tx["hash"], str(bundle["chain_id"])
    if receipt["transactionHash"].lower() != txid.lower():
        raise ValueError("Receipt does not match transaction")
    status = quantity(receipt["status"])
    if status not in (0, 1):
        raise ValueError("Invalid receipt status")
    source, observed = bundle["source"], bundle["observed_at"]
    events = []

    def add(identity, asset, amount, direction, kind="transfer"):
        if amount:
            events.append({"id": f"{chain}:{txid}:{identity}", "asset": asset,
                           "amount_raw": str(amount), "direction": direction, "kind": kind,
                           "status": "success" if status else "failed", "source": source, "observed_at": observed})

    native = f"{chain}:native"
    if address(tx["from"]) == owner:
        price = receipt.get("effectiveGasPrice", tx.get("gasPrice"))
        if price is None:
            raise ValueError("Missing actual gas price")
        if bundle.get("additional_fee_raw") is None:
            raise ValueError("Explicit additional_fee_raw required (zero only where justified)")
        fee = bundle["additional_fee_raw"]
        if not isinstance(fee, str) or not re.fullmatch(r"0|[1-9][0-9]*", fee):
            raise ValueError("Additional fee must be an integer string")
        add("gas", native, quantity(receipt["gasUsed"]) * quantity(price) + int(fee), "out", "gas")
    traces = bundle.get("traces")
    if traces is None:
        if tx.get("to") and address(tx["to"]) == owner and address(tx["from"]) != owner:
            add("external-in", native, quantity(tx["value"]), "in")
        if address(tx["from"]) == owner and (not tx.get("to") or address(tx["to"]) != owner):
            add("external-out", native, quantity(tx["value"]), "out")
    else:
        paths = [tuple(t["traceAddress"]) for t in traces]
        if len(paths) != len(set(paths)):
            raise ValueError("Duplicate trace paths")
        failed = [tuple(t["traceAddress"]) for t in traces if t.get("error")]
        for i, trace in enumerate(traces):
            path = tuple(trace["traceAddress"])
            if not status or any(path[:len(parent)] == parent for parent in failed):
                continue
            action = trace["action"]
            if trace["type"] == "call" and action.get("callType", "call") == "call":
                sender, recipient = address(action["from"]), address(action["to"])
                amount = quantity(action.get("value", "0x0"))
                if recipient == owner and sender != owner:
                    add(f"trace-{i}-in", native, amount, "in")
                if sender == owner and recipient != owner:
                    add(f"trace-{i}-out", native, amount, "out")
            elif trace["type"] == "suicide" and address(action["refundAddress"]) == owner:
                add(f"trace-{i}-refund", native, quantity(action["balance"]), "in")
            elif trace["type"] == "create":
                sender = address(action["from"])
                recipient = trace.get("result", {}).get("address")
                amount = quantity(action.get("value", "0x0"))
                if recipient and address(recipient) == owner and sender != owner:
                    add(f"trace-{i}-create-in", native, amount, "in")
                if sender == owner and (not recipient or address(recipient) != owner):
                    add(f"trace-{i}-create-out", native, amount, "out")
    seen_logs = set()
    for log in receipt.get("logs", []) if status else []:
        identity = quantity(log["logIndex"])
        if identity in seen_logs:
            raise ValueError("Duplicate log indices")
        seen_logs.add(identity)
        topics, data = log.get("topics", []), log.get("data", "")
        # ERC721 has four topics. Do not turn NFT IDs into fungible balances.
        if len(topics) != 3 or topics[0].lower() != TRANSFER or not re.fullmatch(r"0x[0-9a-fA-F]{64}", data):
            continue
        if not all(re.fullmatch(r"0x0{24}[0-9a-fA-F]{40}", topic) for topic in topics[1:]):
            raise ValueError("Invalid indexed transfer address")
        sender, recipient = (address("0x" + topic[-40:]) for topic in topics[1:])
        if sender == recipient:
            continue
        asset = f"{chain}:{address(log['address'])}"
        if recipient == owner:
            add(f"log-{identity}-in", asset, quantity(data), "in")
        if sender == owner:
            add(f"log-{identity}-out", asset, quantity(data), "out")
    return {"events": events, "internal_native_coverage": "supplied traces" if traces is not None else "not supplied",
            "limits": "Caller must establish complete receipts/traces, interval boundaries and chain-specific fees"}
