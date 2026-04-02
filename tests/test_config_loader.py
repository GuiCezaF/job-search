from pathlib import Path

import pytest

from src.types.exceptions import ConfigError
from src.utils.config_loader import ConfigLoader


def test_config_loader_raises_when_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nao_existe.yaml"
    with pytest.raises(ConfigError, match="não encontrado"):
        ConfigLoader(config_path=missing)
