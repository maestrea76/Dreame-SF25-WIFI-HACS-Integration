"""DataUpdateCoordinator para el Dreame SF25.

Estrategia hibrida:
  - MQTT (push): el dispositivo empuja los cambios al instante.
  - Sondeo: red de seguridad. Lento cuando el push esta vivo; rapido si se cae.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DreameApiError, DreameAuthError, DreameSF25Client
from .const import POLL_PROPERTIES, SCAN_INTERVAL_POLL, SCAN_INTERVAL_PUSH
from .mqtt import DreameSF25Mqtt

_LOGGER = logging.getLogger(__name__)


class DreameSF25Coordinator(DataUpdateCoordinator[dict[tuple[int, int], Any]]):
    """Mantiene el estado del SF25 (push MQTT + sondeo de respaldo)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: DreameSF25Client) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Dreame SF25",
            update_interval=timedelta(seconds=SCAN_INTERVAL_POLL),
        )
        self.entry = entry
        self.client = client
        self.mqtt = DreameSF25Mqtt(client, self._handle_push)

    # ------------------------------------------------------------------- push
    async def async_start_push(self) -> None:
        """Arranca el cliente MQTT. Si falla, seguimos con sondeo rapido."""
        try:
            await self.hass.async_add_executor_job(self.mqtt.start)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "No se pudo iniciar el push MQTT (%s); se usara solo sondeo cada %ss",
                err,
                SCAN_INTERVAL_POLL,
            )

    async def async_stop_push(self) -> None:
        await self.hass.async_add_executor_job(self.mqtt.stop)

    def _handle_push(self, updates: dict[tuple[int, int], Any]) -> None:
        """Llamado desde el hilo de paho: lo pasamos al loop de HA."""
        self.hass.loop.call_soon_threadsafe(self._apply_push, updates)

    @callback
    def _apply_push(self, updates: dict[tuple[int, int], Any]) -> None:
        data = dict(self.data or {})
        data.update(updates)
        self._sync_interval()
        self.async_set_updated_data(data)

    # ----------------------------------------------------------------- sondeo
    @callback
    def _sync_interval(self) -> None:
        """Sondeo lento mientras el push este vivo; rapido si se cae."""
        wanted = timedelta(
            seconds=SCAN_INTERVAL_PUSH if self.mqtt.connected else SCAN_INTERVAL_POLL
        )
        if self.update_interval != wanted:
            self.update_interval = wanted

    async def _async_update_data(self) -> dict[tuple[int, int], Any]:
        try:
            data = await self.hass.async_add_executor_job(
                self.client.get_properties, POLL_PROPERTIES
            )
        except DreameAuthError as err:
            raise UpdateFailed(f"Autenticacion rechazada: {err}") from err
        except DreameApiError as err:
            raise UpdateFailed(f"Error de la nube Dreame: {err}") from err

        self._sync_interval()
        # el sondeo confirma el estado completo; el push solo trae lo que cambia
        merged = dict(self.data or {})
        merged.update(data)
        return merged
