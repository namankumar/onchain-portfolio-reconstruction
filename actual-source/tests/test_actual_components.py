"""Offline contracts for the source-authentic extraction candidate."""
import base64
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evm_dispatcher import build_runtime
from nonce_recovery import recover_sender_transactions
from solana_idl_decode import decode_account


class ActualComponentTests(unittest.TestCase):
    def test_idl_decoder_verifies_owner_discriminator_and_byte_count(self):
        idl = {"accounts": [{"name": "counter", "type": {"kind": "struct", "fields": [{"name": "value", "type": "u64"}]}}]}
        discriminator = hashlib.sha256(b"account:Counter").digest()[:8]
        value = {"owner": "ProgramOwner", "data": [base64.b64encode(discriminator + (42).to_bytes(8, "little")).decode(), "base64"]}
        decoded = decode_account(idl, value, "counter", "ProgramOwner")
        self.assertEqual(decoded["state"], {"value": 42})
        self.assertEqual(decoded["decodedBytes"], 16)
        self.assertTrue(decoded["discriminatorVerified"])
        with self.assertRaises(AssertionError):
            decode_account(idl, value, "counter", "WrongOwner")

    def test_dispatcher_retains_large_calldata_after_generated_program(self):
        owner = "0x" + "11" * 20
        target = "0x" + "22" * 20
        payload = "ab" * 5000
        runtime = bytes.fromhex(build_runtime(owner, [{"to": target, "data": "0x" + payload}])[2:])
        self.assertTrue(runtime.endswith(bytes.fromhex(payload)))
        self.assertGreater(len(runtime), 5000)
        self.assertIn(bytes.fromhex(owner[2:]), runtime)
        self.assertIn(bytes.fromhex(target[2:]), runtime)

    def test_nonce_recovery_bisects_history_and_sorts_sender_transactions(self):
        owner = "0x" + "11" * 20
        nonce_at_block = {0: 0, 1: 0, 2: 1, 3: 1, 4: 2, 6: 2, 7: 2, 8: 3}
        transactions = {
            2: [{"from": owner, "nonce": "0x0"}],
            4: [{"from": owner, "nonce": "0x1"}],
            8: [{"from": owner, "nonce": "0x2"}],
        }

        def rpc(method, params):
            if method == "eth_getTransactionCount":
                return {"result": hex(nonce_at_block[int(params[1], 16)])}
            if method == "eth_getBlockByNumber":
                block = int(params[0], 16)
                return {"result": {"transactions": transactions.get(block, [])}}
            raise AssertionError(method)

        result = recover_sender_transactions(rpc, owner, 0, 8, 0, 3, 50, 5, workers=2)
        self.assertEqual([tx["nonce"] for tx in result["transactions"]], ["0x0", "0x1", "0x2"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["counts"]["blocks"], 3)


if __name__ == "__main__":
    unittest.main()
