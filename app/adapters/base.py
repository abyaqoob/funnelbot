"""Channel Adapter Base Interface."""
from abc import ABC, abstractmethod
from typing import Any

from app.models.events import EngineAction, NormalizedEvent


class ChannelAdapter(ABC):
    """Abstract base class for external channel adapters (Telegram, Instagram, Simulator)."""

    @abstractmethod
    def normalize_inbound(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> NormalizedEvent | None:
        """Convert raw channel webhook payload into standardized NormalizedEvent."""
        raise NotImplementedError

    @abstractmethod
    def send_action(self, action: EngineAction) -> bool:
        """Deliver EngineAction back to the channel's native API."""
        raise NotImplementedError
