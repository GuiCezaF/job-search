from pathlib import Path

import pytest

from src.types.exceptions import ConfigError
from src.utils.config_loader import ConfigLoader


def test_config_loader_raises_when_file_missing(tmp_path: Path) -> None:
    """ConfigLoader should raise ConfigError when the YAML path does not exist."""
    missing = tmp_path / "missing.yaml"
    with pytest.raises(ConfigError, match="not found"):
        ConfigLoader(config_path=missing)
