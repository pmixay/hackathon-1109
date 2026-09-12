import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kosmo import load_case  # noqa: E402
from kosmo.case import CHECKSUMS_FILE, SOURCE_FILES  # noqa: E402

COPIED_FILES = SOURCE_FILES + (CHECKSUMS_FILE, "config/portfolio.json", "config/alternatives.json", "config/weights.json")


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def case(root):
    return load_case(root)


@pytest.fixture
def case_root(root, tmp_path):
    for name in COPIED_FILES:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / name, destination)
    return tmp_path


V1 = (("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A"))
V3 = (("FIRE", "A"), ("FLOOD", "A"), ("TRANS", "A"), ("ENV", "A"))
V4 = (("AGRI", "A"), ("TRANS", "A"), ("ENV", "A"), ("SSA", "A"))
V5 = (("FIRE", "A"), ("AGRI", "B"), ("INFRA", "A"), ("TRANS", "B"))


@pytest.fixture
def v1():
    return V1


@pytest.fixture
def v3():
    return V3


@pytest.fixture
def v4():
    return V4


@pytest.fixture
def v5():
    return V5
