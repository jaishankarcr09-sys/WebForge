from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.domain_disjoint_evaluation import main  # noqa: E402

if __name__ == "__main__":
    main()
