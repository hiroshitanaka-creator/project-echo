# run_sentinel.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from po_echo.sentinel import run_audit

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_sentinel.py <requirements.txt>")
        sys.exit(1)

    target = sys.argv[1]
    run_audit(target)
