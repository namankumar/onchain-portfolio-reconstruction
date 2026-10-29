"""Source-authentic EVM preview bytecode builder; it does not make an RPC call."""


def push(n, size=None):
    size = size or max(1, (n.bit_length() + 7) // 8)
    return bytes([0x5F + size]) + n.to_bytes(size, "big")


def build_runtime(owner, calls):
    """Build the original temporary-code sequential CALL dispatcher for `owner`.

    This is the `SRC-EVM-DISPATCH-001` runtime logic with only the private global
    owner replaced by an argument. Call validation and RPC submission belong to
    an outer integration layer; this source unit intentionally only emits code.
    """
    code = bytearray(b"\x33" + push(int(owner, 16), 20) + b"\x14")
    main_patch = len(code) + 1
    code += push(0, 2) + b"\x57\x00"
    main = len(code)
    code += b"\x5b"
    code[main_patch:main_patch + 2] = main.to_bytes(2, "big")
    max_calldata = max((len(bytes.fromhex(x["data"][2:])) for x in calls), default=0)
    output_base = max(4096, ((max_calldata + 31) // 32) * 32 + 256)
    patches, revert_patches, payloads = [], [], []
    for i, item in enumerate(calls):
        data = bytes.fromhex(item["data"][2:])
        code += push(len(data))
        patches.append(len(code) + 1)
        code += push(0, 2) + push(0) + b"\x39"
        code += push(128) + push(output_base + i * 128) + push(len(data)) + push(0)
        code += push(item.get("value", 0)) + push(int(item["to"], 16), 20) + b"\x5a\xf1\x15"
        revert_patches.append(len(code) + 1)
        code += push(0, 2) + b"\x57"
        payloads.append(data)
    code += b"\x47" + push(output_base + len(calls) * 128) + b"\x52"
    code += push(len(calls) * 128 + 32) + push(output_base) + b"\xf3"
    revert_at = len(code)
    code += b"\x5b\x3d\x80" + push(0) + push(0) + b"\x3e" + push(0) + b"\xfd"
    for patch in revert_patches:
        code[patch:patch + 2] = revert_at.to_bytes(2, "big")
    for patch, payload in zip(patches, payloads):
        code[patch:patch + 2] = len(code).to_bytes(2, "big")
        code += payload
    return "0x" + code.hex()
