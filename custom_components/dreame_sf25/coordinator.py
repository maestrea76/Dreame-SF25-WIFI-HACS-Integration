"""DataUpdateCoordinator para el Dreame SF25."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DreameApiError, DreameAuthError, DreameSF25Client
from .const import DEFAULT_SCAN_INTERVAL, POLL_PROPERTIES

_LOGGER = logging.getLogger(__name__)


class DreameSF25Coordinator(DataUpdateCoordinator[dict[tuple[int, int], Any]]):
    """Sondea las propiedades del SF25 via la nube de Dreame."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: DreameSF25Client) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Dreame SF25",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> dict[tuple[int, int], Any]:
        try:
            return await self.hass.async_add_executor_job(
                self.client.get_properties, POLL_PROPERTIES
            )
        except DreameAuthError as err:
            raise UpdateFailed(f"Autenticacion rechazada: {err}") from err
        except DreameApiError as err:
            raise UpdateFailed(f"Error de la nube Dreame: {err}") from err
