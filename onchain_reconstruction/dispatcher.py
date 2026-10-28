"""Pure unsigned sequential-call preview bytecode from a private route-preview implementation.

This creates code only. It does not connect, sign, deploy, broadcast or submit
eth_call. Source uses a temporary code override at the owner and preserves real
balances/storage. Not a deployable production wallet or a withdrawal guarantee.
"""
import re
from .evm import address


def push(n, size=None):
    if type(n) is not int or not 0 <= n < 2**256:
        raise ValueError("Invalid EVM immediate")
    size = size or max(1, (n.bit_length() + 7) // 8)
    return bytes([0x5f + size]) + n.to_bytes(size, 'big')


def build_dispatcher(owner, calls):
    owner = address(owner)
    if len(calls) > 64:
        raise ValueError("At most 64 calls per preview")
    for call in calls:
        address(call["to"])
        if not isinstance(call["data"], str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", call["data"]):
            raise ValueError("Invalid call data")
        if type(call.get("value", 0)) is not int or not 0 <= call.get("value", 0) < 2**256:
            raise ValueError("Invalid native value")
    # Root CALLER must be owner. Native callbacks stop rather than reenter.
    code = bytearray(b'\x33' + push(int(owner, 16), 20) + b'\x14')
    main_patch = len(code) + 1
    code += push(0, 2) + b'\x57\x00'
    main = len(code)
    code += b'\x5b'
    code[main_patch:main_patch + 2] = main.to_bytes(2, 'big')
    # Keep prior CALL outputs beyond every calldata copy; aggregator calldata
    # may exceed 4096 bytes. The regions must never overlap.
    max_calldata = max((len(bytes.fromhex(x['data'][2:])) for x in calls), default=0)
    output_base = max(4096, ((max_calldata + 31) // 32) * 32 + 256)
    patches, revert_patches, payloads = [], [], []
    for i, item in enumerate(calls):
        data = bytes.fromhex(item['data'][2:])
        code += push(len(data))
        patches.append(len(code) + 1)
        code += push(0, 2) + push(0) + b'\x39'  # CODECOPY
        code += push(128) + push(output_base + i * 128) + push(len(data)) + push(0)
        code += push(item.get('value', 0)) + push(int(item['to'], 16), 20) + b'\x5a\xf1\x15'
        revert_patches.append(len(code) + 1)
        code += push(0, 2) + b'\x57'
        payloads.append(data)
    # Return every fixed-width output and final owner native balance.
    code += b'\x47' + push(output_base + len(calls) * 128) + b'\x52'
    code += push(len(calls) * 128 + 32) + push(output_base) + b'\xf3'
    revert_at = len(code)
    code += b'\x5b\x3d\x80' + push(0) + push(0) + b'\x3e' + push(0) + b'\xfd'
    for patch in revert_patches:
        code[patch:patch + 2] = revert_at.to_bytes(2, 'big')
    for patch, payload in zip(patches, payloads):
        code[patch:patch + 2] = len(code).to_bytes(2, 'big')
        code += payload
    return '0x' + code.hex()
