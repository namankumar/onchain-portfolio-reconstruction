# Development, provenance and Git history

## Source boundary

The private source base contains 258 Python scripts (17,599 lines). It was preserved in purpose-based local history without rewriting or fabricating authorship. The standalone package contains only a reviewed extraction with synthetic fixtures; it does not copy the private source, its inputs, response caches or its history.

## Source inventory

`docs/source-catalog.json` preserves the 258-script count, category, line count, import count and machine-local-path flag for every original script. Its opaque entry IDs intentionally do not expose original filenames, hashes or local paths. The manifest generator requires a private local source directory and is not a runtime dependency or a command that works in a standalone clone. It parses ASTs and never imports the scripts. Categories are navigation aids, not semantic proof of every file's behavior.

## Tests and verification

```sh
python3 -m unittest discover -s tests -v
```

Tests exercise exact-unit balances, failed gas/principal distinctions, unknown observations, duplicates, receipt identity, reverted trace ancestors, ERC721 versus ERC20, self-transfers, chain identity, sparse/multiple-per-block nonce searches, incomplete providers, boundary reorganization, blocked broadcast methods, request budget, invalid responses and large-calldata preview layout.

No original investigation module is imported, no user secrets are supplied and no live chain scan is required. Mocked RPC tests exercise local caching and failures without contacting a provider. Test success does not validate all 258 originals, live provider compatibility or asset recoverability.

## Release boundary

`tools/export.py` exports only a fixed set of reviewed project directories/files and refuses symlinks, an existing destination or a destination nested under the source. Runtime `cache/`, `output/`, `private/`, virtual environments and Git metadata are not copied.

Before publishing: choose a repository/license, review exported source and metadata, rerun the clean standalone quickstart, and confirm publication scope. The preparation here is local only. The original private repository's history is not the history to push into a public repository.
