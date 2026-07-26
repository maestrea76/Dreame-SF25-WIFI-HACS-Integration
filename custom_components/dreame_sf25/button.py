"""Botones (pausar / reanudar) del Dreame SF25.

Pausa y reanudar via la propiedad 2.10 (0=pausa, 1=reanudar). Confirmado en vivo.
Solo tienen efecto con un programa en marcha.
"""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DreameSF25ConfigEntry
from .const import DOMAIN, PROP_RUNNING, TARGET_MODEL
from .coordinator import DreameSF25Coordinator


@dataclass(frozen=True, kw_only=True)
class DreameSF25ButtonDescription(ButtonEntityDescription):
    """Descripcion de boton: escribe (siid,piid)=value al pulsarlo."""

    prop: tuple[int, int]
    value: int


BUTTONS: tuple[DreameSF25ButtonDescription, ...] = (
    DreameSF25ButtonDescription(
        key="pause",
        translation_key="pause",
        name="Pause",
        icon="mdi:pause",
        prop=PROP_RUNNING,
        value=0,
    ),
    DreameSF25ButtonDescription(
        key="resume",
        translation_key="resume",
        name="Resume",
        icon="mdi:play",
        prop=PROP_RUNNING,
        value=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DreameSF25ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea los botones."""
    coordinator = entry.runtime_data
    async_add_entities(DreameSF25Button(coordinator, desc) for desc in BUTTONS)


class DreameSF25Button(CoordinatorEntity[DreameSF25Coordinator], ButtonEntity):
    """Boton que escribe una propiedad MIoT al pulsarlo."""

    entity_description: DreameSF25ButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DreameSF25Coordinator,
        description: DreameSF25ButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        did = coordinator.client.did
        self._attr_unique_id = f"{did}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(did))},
            manufacturer="Dreame",
            model=coordinator.client.model or TARGET_MODEL,
            name="Dreame SF25",
        )

    async def async_press(self) -> None:
        siid, piid = self.entity_description.prop
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_property, siid, piid, self.entity_description.value
        )
        await self.coordinator.async_request_refresh()
