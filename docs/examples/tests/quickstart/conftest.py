import sys
from pathlib import Path

_quickstart_src = Path(__file__).parent.parent.parent / "src" / "mersal_docs" / "quickstart"
sys.path.insert(0, str(_quickstart_src))
