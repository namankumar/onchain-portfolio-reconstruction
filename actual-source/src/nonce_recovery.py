"""Source-authentic bounded concurrent historical EVM nonce recovery.

This is parameterized from the original EVM recovery scripts. The
caller supplies a read-only `rpc(method, params)` function; this module has no
endpoint, cache, account, provider, or network behavior of its own.
"""
import queue
import threading
import time


def recover_sender_transactions(rpc, owner, first_block, last_block, first_nonce,
                                last_nonce, request_limit, deadline_seconds,
                                workers=4):
    """Recover a contiguous outbound nonce interval by historical bisection.

    The original queue/worker algorithm is retained. Return errors instead of
    writing a private cache packet so the caller can preserve its own evidence.
    """
    pending = queue.Queue()
    pending.put((first_block, last_block, first_nonce, last_nonce))
    lock = threading.Lock()
    counts = {"reads": 0, "blocks": 0, "failed": 0}
    found, errors, nonce_samples = [], [], {}
    started = time.time()

    def worker():
        while True:
            try:
                lo, hi, nlo, nhi = pending.get(timeout=2)
            except queue.Empty:
                if pending.unfinished_tasks == 0:
                    return
                continue
            try:
                with lock:
                    counts["reads"] += 1
                    number = counts["reads"]
                if number > request_limit or time.time() - started > deadline_seconds:
                    raise RuntimeError("bounded scan limit reached")
                if hi - lo == 1:
                    response = rpc("eth_getBlockByNumber", [hex(hi), True])
                    transactions = [tx for tx in response.get("result", {}).get("transactions", [])
                                    if tx.get("from", "").lower() == owner.lower()]
                    with lock:
                        found.extend(transactions)
                        counts["blocks"] += 1
                else:
                    mid = (lo + hi) // 2
                    response = rpc("eth_getTransactionCount", [owner, hex(mid)])
                    if "result" not in response:
                        raise RuntimeError(str(response))
                    nonce = int(response["result"], 16)
                    if not nlo <= nonce <= nhi:
                        raise RuntimeError("non-monotonic nonce")
                    with lock:
                        nonce_samples[str(mid)] = nonce
                    if nonce > nlo:
                        pending.put((lo, mid, nlo, nonce))
                    if nonce < nhi:
                        pending.put((mid, hi, nonce, nhi))
            except Exception as error:
                with lock:
                    counts["failed"] += 1
                    errors.append({"range": [lo, hi, nlo, nhi], "error": str(error)})
            finally:
                pending.task_done()

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for thread in threads:
        thread.start()
    pending.join()
    for thread in threads:
        thread.join()
    return {
        "bounds": [first_block, last_block],
        "expected_nonce": last_nonce,
        "counts": counts,
        "transactions": sorted(found, key=lambda tx: int(tx["nonce"], 16)),
        "errors": errors,
        "nonce_samples": nonce_samples,
    }
