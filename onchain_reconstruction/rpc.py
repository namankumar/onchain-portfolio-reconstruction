"""Bounded public RPC reads with locally retained, integrity-checked evidence."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request

from .evm import address, quantity

ALLOWED = {"eth_chainId", "eth_getTransactionCount", "eth_getBlockByNumber", "eth_getBalance", "eth_getTransactionReceipt", "eth_call"}


class RPC:
    def __init__(self, url, cache, budget=1000):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Use an HTTPS RPC URL without userinfo or fragments")
        if budget < 1 or budget > 10000:
            raise ValueError("RPC budget must be between 1 and 10000")
        self.url, self.cache, self.budget = url, Path(cache), budget
        self.requests, self.last = 0, 0.0
        self.cache.mkdir(parents=True, exist_ok=True)

    def call(self, method, params, refresh=False):
        if method not in ALLOWED:
            raise ValueError("RPC method is outside the read-only allowlist")
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        # URL may contain a provider key: only an opaque digest is retained.
        identity = hashlib.sha256((self.url + json.dumps(body, sort_keys=True)).encode()).hexdigest()
        path = self.cache / (identity + ".json")
        if path.exists() and not refresh:
            saved = json.loads(path.read_text())
            if saved["request"] != body or saved["endpoint_id"] != hashlib.sha256(self.url.encode()).hexdigest():
                raise ValueError("Cached request identity mismatch")
            response = saved["response"]
            if hashlib.sha256(json.dumps(response, sort_keys=True).encode()).hexdigest() != saved["response_sha256"]:
                raise ValueError("Cached response integrity failure")
            return self._result(response)
        for attempt in range(3):
            if self.requests >= self.budget:
                raise ValueError("RPC request budget exhausted; scan is incomplete")
            time.sleep(max(0, self.last + 0.2 - time.monotonic()))
            self.requests += 1
            self.last = time.monotonic()
            request = Request(self.url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            try:
                # Disable automatic redirects so a keyed URL cannot be forwarded.
                from urllib.request import HTTPRedirectHandler, build_opener
                class NoRedirect(HTTPRedirectHandler):
                    def redirect_request(self, *args, **kwargs):
                        return None
                with build_opener(NoRedirect).open(request, timeout=30) as reply:
                    response = json.load(reply)
            except HTTPError as error:
                if error.code == 429 and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise ValueError(f"RPC HTTP failure ({error.code}); no zero balance inferred") from None
            except (OSError, ValueError):
                raise ValueError("RPC transport/JSON failure; no zero balance inferred") from None
            result = self._result(response)
            path.write_text(json.dumps({"request": body, "endpoint_id": hashlib.sha256(self.url.encode()).hexdigest(),
                                       "observed_at": datetime.now(timezone.utc).isoformat(), "response": response,
                                       "response_sha256": hashlib.sha256(json.dumps(response, sort_keys=True).encode()).hexdigest()}, indent=2) + "\n")
            return result
        raise ValueError("RPC rate limit remained unresolved")

    @staticmethod
    def _result(response):
        if not isinstance(response, dict) or response.get("id") != 1 or response.get("jsonrpc") != "2.0" or "error" in response or response.get("result") is None:
            raise ValueError("Missing or invalid RPC result; absence is not zero")
        return response["result"]


def scan_nonces(call, owner, chain_id, start, end, verify_call=None):
    """Find sender transactions by binary search of historical account nonces.

    Coverage is outgoing transactions in an inclusive fixed block interval.
    Incoming transfers, internal activity and account-abstraction user operations
    require other evidence. A provider must retain historical state.
    """
    owner = address(owner)
    if start < 1 or end < start:
        raise ValueError("Use 1 <= start <= end")
    if quantity(call("eth_chainId", [])) != chain_id:
        raise ValueError("RPC chain identity mismatch")
    first = call("eth_getBlockByNumber", [hex(start - 1), False])
    last = call("eth_getBlockByNumber", [hex(end), False])
    low = quantity(call("eth_getTransactionCount", [owner, hex(start - 1)]))
    high = quantity(call("eth_getTransactionCount", [owner, hex(end)]))
    if high < low:
        raise ValueError("Non-monotonic nonce boundaries")
    found, pending = [], [(start - 1, end, low, high)]
    while pending:
        lo, hi, nlo, nhi = pending.pop()
        if nlo == nhi:
            continue
        if hi - lo == 1:
            block = call("eth_getBlockByNumber", [hex(hi), True])
            if quantity(block["number"]) != hi:
                raise ValueError("Provider returned wrong block")
            found.extend(t for t in block["transactions"] if address(t["from"]) == owner)
            continue
        mid = (lo + hi) // 2
        nonce = quantity(call("eth_getTransactionCount", [owner, hex(mid)]))
        if not nlo <= nonce <= nhi:
            raise ValueError("Non-monotonic historical nonce")
        pending.extend([(lo, mid, nlo, nonce), (mid, hi, nonce, nhi)])
    found.sort(key=lambda t: quantity(t["nonce"]))
    if [quantity(t["nonce"]) for t in found] != list(range(low, high)):
        raise ValueError("Transaction coverage mismatch; no complete scan claimed")
    # CLI supplies fresh reads here; replaying cached hashes cannot detect a reorg.
    verify = verify_call or call
    if first["hash"] != verify("eth_getBlockByNumber", [hex(start - 1), False])["hash"] or last["hash"] != verify("eth_getBlockByNumber", [hex(end), False])["hash"]:
        raise ValueError("Block boundaries changed during scan")
    return {"chain_id": chain_id, "start_block": start, "end_block": end,
            "start_hash": first["hash"], "end_hash": last["hash"],
            "expected_outgoing": high-low, "transactions": found, "complete": True,
            "scope": "Sender transactions only; no incoming/internal/AA coverage implied"}

