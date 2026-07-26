"""Select (programa) del Dreame SF25.

Escribir la propiedad 2.3 arranca/para los programas:
  idle=-1 (parar) · cycle=0 (ciclo normal) · self_clean=2 (autolimpieza).
"""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DreameSF25ConfigEntry
from .const import (
    DOMAIN,
    PROGRAM_MAP,
    PROGRAM_OPTIONS,
    PROP_PROGRAM,
    TARGET_MODEL,
)
from .coordinator import DreameSF25Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameSF25ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea el select de programa."""
    async_add_entities([DreameSF25ProgramSelect(entry.runtime_data)])


class DreameSF25ProgramSelect(CoordinatorEntity[DreameSF25Coordinator], SelectEntity):
    """Selector de programa (iniciar ciclo / autolimpieza / parar)."""

    _attr_has_entity_name = True
    _attr_translation_key = "program"
    _attr_icon = "mdi:playlist-play"
    _attr_options = list(PROGRAM_OPTIONS.keys())

    def __init__(self, coordinator: DreameSF25Coordinator) -> None:
        super().__init__(coordinator)
        did = coordinator.client.did
        self._attr_unique_id = f"{did}_program"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(did))},
            manufacturer="Dreame",
            model=coordinator.client.model or TARGET_MODEL,
            name="Dreame SF25",
        )

    @property
    def current_option(self) -> str | None:
        raw = (self.coordinator.data or {}).get(PROP_PROGRAM)
        if raw is None:
            return None
        try:
            return PROGRAM_MAP.get(int(raw))
        except (ValueError, TypeError):
            return None

    async def async_select_option(self, option: str) -> None:
        value = PROGRAM_OPTIONS[option]
        siid, piid = PROP_PROGRAM
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_property, siid, piid, value
        )
        await self.coordinator.async_request_refresh()
