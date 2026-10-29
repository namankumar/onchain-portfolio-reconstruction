"""Exact integer accounting; missing evidence is never a zero balance."""
import re


def raw(value):
    if not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise ValueError("Raw quantities must be nonnegative integer strings")
    return int(value)


def reconcile(document):
    opening, observed = document["opening"], document["observed"]
    totals = {asset: raw(amount) for asset, amount in opening.items()}
    seen, unknown, ignored = set(), [], []
    for event in document["events"]:
        identity = event["id"]
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError("Missing or duplicate event ID")
        seen.add(identity)
        if not event.get("source") or not event.get("observed_at"):
            raise ValueError("Each event needs a source and observation timestamp")
        asset, kind = event["asset"], event["kind"]
        if asset not in opening or asset not in observed:
            raise ValueError("Every asset needs explicit opening and observed entries")
        amount = raw(event["amount_raw"])
        if event["status"] not in {"success", "failed", "unknown"}:
            raise ValueError("Invalid event status")
        if kind not in {"transfer", "gas"} or event["direction"] not in {"in", "out"}:
            raise ValueError("Invalid movement kind/direction")
        if kind == "gas" and event["direction"] != "out":
            raise ValueError("Gas must be an outgoing movement")
        if event["status"] == "unknown":
            unknown.append(identity)
            continue
        if event["status"] == "failed" and kind != "gas":
            ignored.append(identity)
            continue
        totals[asset] += amount if event["direction"] == "in" else -amount
    if set(observed) != set(opening):
        raise ValueError("Opening/observed asset sets differ")
    rows = []
    for asset in sorted(totals):
        balance = None if observed[asset] is None else raw(observed[asset])
        difference = None if balance is None else totals[asset] - balance
        rows.append({"asset": asset, "computed_raw": str(totals[asset]),
                     "observed_raw": None if balance is None else str(balance),
                     "difference_raw": None if difference is None else str(difference)})
    complete = not unknown and all(r["observed_raw"] is not None for r in rows)
    return {"complete": complete, "reconciled": complete and all(r["difference_raw"] == "0" for r in rows),
            "balances": rows, "unknown_events": unknown, "ignored_failed_transfers": ignored,
            "scope": "Supplied events and balance boundaries only; not proof of exhaustive wallet discovery"}


def markdown(result):
    lines = ["# Balance reconciliation", "", f"Complete inputs: {result['complete']}",
             f"Reconciled: {result['reconciled']}", "",
             "| Asset | Computed raw | Observed raw | Difference raw |", "| --- | --- | --- | --- |"]
    for row in result["balances"]:
        # Asset names are untrusted input, not Markdown instructions.
        name = str(row["asset"]).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        lines.append(f"| {name} | {row['computed_raw']} | {row['observed_raw']} | {row['difference_raw']} |")
    lines.extend(["", result["scope"], ""])
    return "\n".join(lines)

