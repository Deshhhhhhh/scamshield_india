import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="scamshield-test-"))
os.environ.setdefault("SCAMSHIELD_DB_PATH", str(_TMP / "test.db"))
os.environ.setdefault("SCAMSHIELD_RATE_LIMIT", "10000")
os.environ.setdefault("SCAMSHIELD_LOG_LEVEL", "WARNING")
os.environ.setdefault("SCAMSHIELD_ENV", "test")
