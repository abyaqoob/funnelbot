"""Channel Adapter Base Interface."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.models.events import EngineAction, NormalizedEvent


class ChannelAdapter(ABC):
    """Abstract base class for external channel adapters (Telegram, Instagram, Simulator)."""

    @abstractmethod
    def normalize_inbound(
        self, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> Optional[NormalizedEvent]:
        """Convert raw channel webhook payload into standardized NormalizedEvent."""
        raise NotImplementedError

    @abstractmethod
    def send_action(self, action: EngineAction) -> bool:
        """Deliver EngineAction back to the channel's native API."""
        raise NotImplementedError
