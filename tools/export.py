"""Copy only reviewed portable sources into a new standalone directory."""
import argparse
import shutil
from pathlib import Path

FILES = {"README.md", "pyproject.toml", ".gitignore"}
DIRECTORIES = {"onchain_reconstruction", "examples", "tests", "docs", "tools"}


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
    destination.mkdir(parents=True)
    for path in selected:
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return len(selected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(f"Exported {export(args.out)} reviewed files; no original investigation data included.")
    except ValueError as error:
        parser.error(str(error))
