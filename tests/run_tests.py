import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_core


if __name__ == "__main__":
    test_core.main()
