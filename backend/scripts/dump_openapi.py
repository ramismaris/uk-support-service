import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.main import app

OUTPUT = Path(__file__).resolve().parent.parent / "openapi.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that openapi.json is up to date without writing it",
    )
    args = parser.parse_args()

    schema = app.openapi()
    content = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            print("openapi.json is out of date, run: uv run python scripts/dump_openapi.py")
            sys.exit(1)
        return

    OUTPUT.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
