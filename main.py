from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.cli import main as run_cli


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
