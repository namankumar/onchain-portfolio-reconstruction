"""Copy only reviewed portable sources into a new standalone directory."""
import argparse
import shutil
from pathlib import Path

FILES = {"README.md", "pyproject.toml", ".gitignore"}
DIRECTORIES = {"onchain_reconstruction", "examples", "tests", "docs", "tools"}
EVALUATION_FILES = {
    "__init__.py", "build_fixtures.py", "runtime.py", "grader.py", "compare.py", "serve.py", "grade_episode.py",
    "README.md", "FINDINGS.md", "versions.json", "fixtures/cases.json", "oracles/expectations.json",
    "prompts/investigator-v1.md", "results/scorecard.json", "results/comparison.md", "examples/investigation-requests.jsonl",
    "versions/d084374/evm.py", "versions/d084374/ledger.py", "versions/a81ed25/evm.py", "versions/a81ed25/ledger.py",
}
ORIGINAL_FILES = {"src/solana_idl_decode.py", "src/nonce_recovery.py", "src/evm_dispatcher.py", "tests/test_actual_components.py", "provenance.json", "AUTHENTICITY.md"}


def export(destination):
    source = Path(__file__).resolve().parents[1]
    destination = Path(destination).resolve()
    if destination.exists() or source == destination or source in destination.parents:
        raise ValueError("Choose a new directory outside the source package")
    selected = []
    for name in FILES:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("Missing or symlinked release file")
        selected.append(path)
    for name in DIRECTORIES:
        for path in (source / name).rglob("*"):
            if path.is_symlink():
                raise ValueError("Release does not follow symlinks")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix in {".py", ".md", ".json", ".csv"}:
                selected.append(path)
    for name in EVALUATION_FILES:
        path = source / "evals" / name
        if not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents if p == source or source in p.parents):
            raise ValueError("Missing or symlinked evaluation source")
        selected.append(path)
    originals = source / "actual-source"
    if not originals.exists():
        originals = source / "actual-source-candidate"
    for name in ORIGINAL_FILES | {"README.md"}:
        path = originals / name
        if not path.is_file() or path.is_symlink() or any(p.is_symlink() for p in path.parents if p == originals or originals in p.parents):
            raise ValueError("Missing or symlinked original component")
    destination.mkdir(parents=True)
    for path in selected:
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    for name in ORIGINAL_FILES:
        path = originals / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("Missing or symlinked original component")
        target = destination / "actual-source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    readme = (originals / "README.md").read_text()
    # The public copy keeps source provenance while excluding private planning links.
    readme = "\n".join(line for line in readme.splitlines() if "FULL_SCOPE_EXTRACTION_PLAN" not in line)
    readme = readme.replace("# Source-authentic expansion candidate", "# Original Reconstruction Components")
    readme = readme.replace("This is a publication-ready source candidate for real algorithms extracted from a private reconstruction project. It is not a replacement for the current portable package.", "These are original algorithms extracted from the reconstruction project, alongside the separately packaged CLI in the repository root.")
    readme = readme.replace("They were source-reviewed and syntax-checked only.", "Offline synthetic contracts are exercised by tools/verify_offline.py in the repository root; no live-provider or recovery result is claimed.")
    (destination / "actual-source/README.md").write_text(readme + "\n")
    return len(selected) + len(ORIGINAL_FILES) + 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(f"Exported {export(args.out)} reviewed files; no original investigation data included.")
    except ValueError as error:
        parser.error(str(error))
