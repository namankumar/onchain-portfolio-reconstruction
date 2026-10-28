import copy
import json
import tempfile
import unittest
import io
from unittest.mock import patch
from pathlib import Path

from onchain_reconstruction.dispatcher import build_dispatcher
from onchain_reconstruction.evm import decode
from onchain_reconstruction.ledger import reconcile
from onchain_reconstruction.rpc import RPC, scan_nonces

ROOT = Path(__file__).resolve().parents[1]
OWNER = "0x" + "11" * 20


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.ledger = json.loads((ROOT / "examples/ledger.json").read_text())
        self.bundle = json.loads((ROOT / "examples/evm-bundle.json").read_text())

    def test_failed_transfer_ignored_but_failed_gas_charged(self):
        result = reconcile(self.ledger)
        self.assertTrue(result["reconciled"])
        self.assertEqual(result["ignored_failed_transfers"], ["failed-send"])
        self.assertEqual(result["balances"][0]["difference_raw"], "0")

    def test_missing_observation_is_not_zero(self):
        self.ledger["observed"]["31337:native"] = None
        self.assertFalse(reconcile(self.ledger)["complete"])

    def test_unknown_event_blocks_complete(self):
        self.ledger["events"][0]["status"] = "unknown"
        self.assertFalse(reconcile(self.ledger)["complete"])

    def test_discrepancy_is_reported(self):
        self.ledger["observed"]["31337:native"] = "0"
        self.assertFalse(reconcile(self.ledger)["reconciled"])

    def test_duplicate_event_rejected(self):
        self.ledger["events"].append(self.ledger["events"][0])
        with self.assertRaises(ValueError):
            reconcile(self.ledger)

    def test_float_and_negative_rejected(self):
        for value in [0.1, "1.1", "-1", True]:
            with self.subTest(value=value):
                self.ledger["events"][0]["amount_raw"] = value
                with self.assertRaises(ValueError):
                    reconcile(self.ledger)

    def test_unproven_source_rejected(self):
        del self.ledger["events"][0]["source"]
        with self.assertRaises(ValueError):
            reconcile(self.ledger)

    def test_trace_refund_and_erc20_decoded(self):
        result = decode(self.bundle)
        self.assertEqual(len(result["events"]), 4)
        self.assertEqual(sum(int(e["amount_raw"]) for e in result["events"] if e["direction"] == "in" and e["asset"].endswith("native")), 500000000000000000)

    def test_failed_parent_excludes_descendants(self):
        self.bundle["traces"][1]["error"] = "reverted"
        child = copy.deepcopy(self.bundle["traces"][1])
        child.pop("error")
        child["traceAddress"] = [0, 0]
        self.bundle["traces"].append(child)
        self.assertFalse(any(e["id"].endswith("-in") and e["asset"].endswith("native") for e in decode(self.bundle)["events"]))

    def test_erc721_is_not_fungible_transfer(self):
        self.bundle["receipt"]["logs"][0]["topics"].append("0x" + "00" * 32)
        self.assertEqual(len(decode(self.bundle)["events"]), 3)

    def test_self_transfer_does_not_change_inventory(self):
        self.bundle["receipt"]["logs"][0]["topics"][1] = self.bundle["receipt"]["logs"][0]["topics"][2]
        self.assertEqual(len(decode(self.bundle)["events"]), 3)

    def test_failed_transaction_only_charges_gas(self):
        self.bundle["receipt"]["status"] = "0x0"
        result = decode(self.bundle)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["kind"], "gas")

    def test_wrong_receipt_and_missing_extra_fees_rejected(self):
        for field in ["receipt", "fee"]:
            bundle = copy.deepcopy(self.bundle)
            if field == "receipt":
                bundle["receipt"]["transactionHash"] = "0xwrong"
            else:
                del bundle["additional_fee_raw"]
            with self.assertRaises(ValueError):
                decode(bundle)

    def test_duplicate_trace_and_log_rejected(self):
        for field in ["traces", "logs"]:
            bundle = copy.deepcopy(self.bundle)
            rows = bundle["traces"] if field == "traces" else bundle["receipt"]["logs"]
            rows.append(rows[0])
            with self.assertRaises(ValueError):
                decode(bundle)


class NonceTests(unittest.TestCase):
    def call(self, method, params):
        if method == "eth_chainId":
            return "0x7a69"
        block = int(params[-1] if method == "eth_getTransactionCount" else params[0], 16)
        if method == "eth_getTransactionCount":
            return hex(sum(n <= block for n in [2, 5, 5, 9]))
        txs = [{"from": OWNER, "hash": f"synthetic-{i}", "nonce": hex(i)} for i, n in enumerate([2, 5, 5, 9]) if n == block]
        return {"hash": f"block-{block}", "number": hex(block), "transactions": txs}

    def test_sparse_search_and_multiple_transactions_per_block(self):
        result = scan_nonces(self.call, OWNER, 31337, 1, 10)
        self.assertEqual(result["expected_outgoing"], 4)
        self.assertTrue(result["complete"])

    def test_interval_nonce_offset(self):
        result = scan_nonces(self.call, OWNER, 31337, 5, 8)
        self.assertEqual([t["nonce"] for t in result["transactions"]], ["0x1", "0x2"])

    def test_no_transactions(self):
        self.assertEqual(scan_nonces(self.call, OWNER, 31337, 6, 8)["expected_outgoing"], 0)

    def test_wrong_chain(self):
        with self.assertRaises(ValueError):
            scan_nonces(self.call, OWNER, 1, 1, 10)

    def test_provider_missing_transaction_not_complete(self):
        def broken(method, params):
            result = self.call(method, params)
            if method == "eth_getBlockByNumber" and params[1] is True:
                result["transactions"] = []
            return result
        with self.assertRaises(ValueError):
            scan_nonces(broken, OWNER, 31337, 1, 10)

    def test_reorg_boundary(self):
        with self.assertRaises(ValueError):
            scan_nonces(self.call, OWNER, 31337, 1, 10,
                        verify_call=lambda method, params: {"hash": "changed"})

    def test_missing_rpc_result_not_zero(self):
        for response in [{}, {"jsonrpc": "2.0", "id": 1, "result": None}, {"jsonrpc": "2.0", "id": 1, "error": {"code": -1}}]:
            with self.assertRaises(ValueError):
                RPC._result(response)

    def test_zero_is_valid(self):
        self.assertEqual(RPC._result({"jsonrpc": "2.0", "id": 1, "result": "0x0"}), "0x0")

    def test_broadcast_and_invalid_url_blocked_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpc = RPC("https://example.invalid", tmp)
            with self.assertRaises(ValueError):
                rpc.call("eth_sendRawTransaction", ["0x00"])
            self.assertEqual(rpc.requests, 0)
            for url in ["http://example.invalid", "file:///tmp/a", "https://u:p@example.invalid"]:
                with self.assertRaises(ValueError):
                    RPC(url, tmp)

    def test_budget_exhaustion_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            rpc = RPC("https://example.invalid", tmp, budget=1)
            rpc.requests = 1
            with self.assertRaises(ValueError):
                rpc.call("eth_getBalance", [OWNER, "0x1"])

    def test_cache_identity_replay_and_tamper_detection(self):
        class Opener:
            def open(self, request, timeout):
                return io.BytesIO(b'{"jsonrpc":"2.0","id":1,"result":"0x0"}')
        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.build_opener", return_value=Opener()) as transport:
            rpc = RPC("https://example.invalid/provider-key", tmp)
            self.assertEqual(rpc.call("eth_getBalance", [OWNER, "0x1"]), "0x0")
            self.assertEqual(rpc.call("eth_getBalance", [OWNER, "0x1"]), "0x0")
            self.assertEqual(transport.call_count, 1)
            saved_path = next(Path(tmp).glob("*.json"))
            self.assertNotIn("provider-key", saved_path.read_text())
            saved = json.loads(saved_path.read_text())
            saved["response"]["result"] = "0x1"
            saved_path.write_text(json.dumps(saved))
            with self.assertRaises(ValueError):
                rpc.call("eth_getBalance", [OWNER, "0x1"])

    def test_final_boundary_checks_can_bypass_cache(self):
        class Opener:
            def open(self, request, timeout):
                return io.BytesIO(b'{"jsonrpc":"2.0","id":1,"result":{"hash":"block"}}')
        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.build_opener", return_value=Opener()) as transport, patch("time.sleep"):
            rpc = RPC("https://example.invalid", tmp)
            rpc.call("eth_getBlockByNumber", ["0x1", False])
            rpc.call("eth_getBlockByNumber", ["0x1", False], refresh=True)
            self.assertEqual(transport.call_count, 2)

    def test_rate_limit_retries_are_budgeted(self):
        from urllib.error import HTTPError
        class Opener:
            def open(self, request, timeout):
                raise HTTPError("https://example.invalid", 429, "limit", {}, None)
        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.build_opener", return_value=Opener()), patch("time.sleep"):
            rpc = RPC("https://example.invalid", tmp, budget=2)
            with self.assertRaisesRegex(ValueError, "budget"):
                rpc.call("eth_getBalance", [OWNER, "0x1"])
            self.assertEqual(rpc.requests, 2)
            self.assertEqual(list(Path(tmp).glob("*.json")), [])


class DispatcherTests(unittest.TestCase):
    def test_long_calldata_uses_separate_output_region(self):
        # The original investigation found a >4096-byte calldata/output overlap.
        from onchain_reconstruction.dispatcher import push
        calls = [{"to": "0x" + "22" * 20, "data": "0x" + "ab" * 5000}]
        code = bytes.fromhex(build_dispatcher(OWNER, calls)[2:])
        expected_base = ((5000 + 31) // 32) * 32 + 256
        self.assertIn(push(128) + push(expected_base) + push(5000), code)
        self.assertTrue(code.endswith(bytes.fromhex("ab" * 5000)))

    def test_bad_calls_rejected(self):
        for call in [{"to": OWNER, "data": "0xz"}, {"to": OWNER, "data": "0x", "value": -1}]:
            with self.assertRaises(ValueError):
                build_dispatcher(OWNER, [call])


if __name__ == "__main__":
    unittest.main()

