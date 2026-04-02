import pytest

from src.notifier.discord_client import DiscordNotifier


def test_discord_notifier_rejects_empty_webhook() -> None:
    """DiscordNotifier must reject blank webhook URLs at construction time."""
    with pytest.raises(ValueError, match="webhook"):
        DiscordNotifier("")
