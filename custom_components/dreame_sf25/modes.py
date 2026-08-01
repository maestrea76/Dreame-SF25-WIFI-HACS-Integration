"""Modos virtuales del SF25: Remover y Compactar.

El aparato solo conoce ciclo (2.3=0) y autolimpieza (2.3=2). Aqui se construyen
dos modos propios sobre la autolimpieza, acotandola en el tiempo:

  - Remover   : autolimpieza durante 10 min.
  - Compactar : autolimpieza durante 1 hora.

Disparos automaticos:
  - Remover  : al cerrar la tapa, si se han acumulado >= 2 aperturas.
  - Compactar: a la hora configurada (por defecto 15:00), con >= 2 aperturas.

Contador de aperturas: se reinicia SOLO cuando Triturar o Autolimpieza terminan
de forma natural. Si se cancelan a medias, o si lo que corrio fue Remover o
Compactar, el contador se conserva.

El estado (contador, modo virtual en curso y su vencimiento) se guarda en disco
para sobrevivir a un reinicio de Home Assistant.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_time_change
from homeassistant.helpers.storage import Store

from .const import (
    COMMAND_GRACE,
    DEFAULT_COMPACT_HOUR,
    DEFAULT_COMPACT_MINUTE,
    DOMAIN,
    LID_COUNT_THRESHOLD,
    NATURAL_END_REMAINING,
    PROGRAM_COMPACT,
    PROGRAM_OPTIONS,
    PROGRAM_STIR,
    PROP_LID,
    PROP_PROGRAM,
    PROP_REMAINING_TIME,
    STORAGE_VERSION,
    VIRTUAL_DURATIONS,
)

if TYPE_CHECKING:
    from .coordinator import DreameSF25Coordinator

_LOGGER = logging.getLogger(__name__)

_PROGRAM_IDLE: int = PROGRAM_OPTIONS["idle"]
_PROGRAM_CYCLE: int = PROGRAM_OPTIONS["cycle"]
_PROGRAM_SELF_CLEAN: int = PROGRAM_OPTIONS["self_clean"]


class DreameSF25Modes:
    """Contador de aperturas y modos virtuales (Remover / Compactar)."""

    def __init__(self, hass: HomeAssistant, coordinator: DreameSF25Coordinator, entry_id: str) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")

        self.lid_count: int = 0
        self.virtual_mode: str | None = None
        self._virtual_until: float = 0.0
        # hora del disparo diario de Compactar (editable desde HA)
        self.compact_hour: int = DEFAULT_COMPACT_HOUR
        self.compact_minute: int = DEFAULT_COMPACT_MINUTE

        # True mientras el programa que corre en el aparato lo lanzamos nosotros
        # (Remover/Compactar). Sirve para no confundir su final con el de un
        # programa real y, por tanto, no tocar el contador.
        self._owns_program: bool = False
        # instante de la ultima orden enviada: durante unos segundos las lecturas
        # pueden venir desfasadas (el aparato aun no ha arrancado/parado)
        self._command_at: float = 0.0

        self._last_lid: int | None = None
        self._last_program: int | None = None
        self._last_remaining: int | None = None

        self._unsub_timer = None
        self._unsub_daily = None

    # ------------------------------------------------------------ ciclo de vida
    async def async_load(self) -> None:
        """Restaura el estado guardado y reprograma lo pendiente."""
        data = await self._store.async_load() or {}
        self.lid_count = int(data.get("lid_count", 0))
        self.virtual_mode = data.get("virtual_mode")
        self._virtual_until = float(data.get("virtual_until", 0) or 0)
        self.compact_hour = int(data.get("compact_hour", DEFAULT_COMPACT_HOUR))
        self.compact_minute = int(data.get("compact_minute", DEFAULT_COMPACT_MINUTE))

        self._schedule_daily()

        if self.virtual_mode:
            remaining = self._virtual_until - time.time()
            if remaining > 0:
                _LOGGER.info(
                    "Reanudando modo %s tras reinicio (%.0f s restantes)",
                    self.virtual_mode,
                    remaining,
                )
                self._schedule_expiry(remaining)
            else:
                # venció mientras HA estaba parado: cerramos ya
                _LOGGER.info("El modo %s vencio durante el reinicio; parando", self.virtual_mode)
                await self._async_finish_virtual()

    async def async_unload(self) -> None:
        self._cancel_timer()
        if self._unsub_daily is not None:
            self._unsub_daily()
            self._unsub_daily = None
        await self._async_save()

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "lid_count": self.lid_count,
                "virtual_mode": self.virtual_mode,
                "virtual_until": self._virtual_until,
                "compact_hour": self.compact_hour,
                "compact_minute": self.compact_minute,
            }
        )

    @callback
    def _schedule_daily(self) -> None:
        """(Re)programa el disparo diario de Compactar a la hora configurada."""
        if self._unsub_daily is not None:
            self._unsub_daily()
        self._unsub_daily = async_track_time_change(
            self.hass,
            self._async_daily_compact,
            hour=self.compact_hour,
            minute=self.compact_minute,
            second=0,
        )
        _LOGGER.debug("Compactar programado a las %02d:%02d", self.compact_hour, self.compact_minute)

    async def async_set_compact_time(self, hour: int, minute: int) -> None:
        """Cambia la hora del disparo diario de Compactar."""
        self.compact_hour = int(hour)
        self.compact_minute = int(minute)
        self._schedule_daily()
        await self._async_save()

    async def async_set_lid_count(self, value: int) -> None:
        """Fija el contador de aperturas (editable desde HA)."""
        self.lid_count = max(0, int(value))
        await self._async_save()
        self.coordinator.async_update_listeners()

    # --------------------------------------------------------------- temporizador
    @callback
    def _cancel_timer(self) -> None:
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _schedule_expiry(self, delay: float) -> None:
        self._cancel_timer()
        self._unsub_timer = async_call_later(self.hass, delay, self._async_expired)

    async def _async_expired(self, _now) -> None:
        _LOGGER.info("Modo %s completado; parando el aparato", self.virtual_mode)
        await self._async_finish_virtual()

    async def _async_finish_virtual(self) -> None:
        """Detiene el aparato y cierra el modo virtual.

        Se conserva _owns_program para que el 'fin de programa' que provocara
        esta parada NO se confunda con el final de un programa real.
        """
        self._cancel_timer()
        self.virtual_mode = None
        self._virtual_until = 0.0
        await self._async_set_program(_PROGRAM_IDLE)
        await self._async_save()
        await self.coordinator.async_request_refresh()

    # -------------------------------------------------------------------- ordenes
    async def _async_set_program(self, value: int) -> None:
        siid, piid = PROP_PROGRAM
        self._command_at = time.time()
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_property, siid, piid, value
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("No se pudo escribir el programa %s: %s", value, err)

    async def async_start_virtual(self, mode: str) -> None:
        """Arranca Remover o Compactar (autolimpieza acotada)."""
        duration = VIRTUAL_DURATIONS[mode]
        self._owns_program = True
        await self._async_set_program(_PROGRAM_SELF_CLEAN)
        self.virtual_mode = mode
        self._virtual_until = time.time() + duration
        self._schedule_expiry(duration)
        await self._async_save()
        _LOGGER.info("Modo %s iniciado (%s min)", mode, duration // 60)
        await self.coordinator.async_request_refresh()

    async def async_clear_virtual(self) -> None:
        """Olvida el modo virtual sin tocar el aparato (cambio manual de modo)."""
        if self.virtual_mode is None:
            return
        self._cancel_timer()
        self.virtual_mode = None
        self._virtual_until = 0.0
        self._owns_program = False
        await self._async_save()

    async def async_reset_counter(self) -> None:
        self.lid_count = 0
        await self._async_save()
        self.coordinator.async_update_listeners()

    # ------------------------------------------------------------- observador
    @callback
    def handle_update(self, data: dict[tuple[int, int], Any]) -> None:
        """Analiza cada actualizacion para contar aperturas y detectar finales."""
        lid = _as_int(data.get(PROP_LID))
        program = _as_int(data.get(PROP_PROGRAM))
        remaining = _as_int(data.get(PROP_REMAINING_TIME))

        if program is not None and program != _PROGRAM_IDLE and remaining is not None:
            self._last_remaining = remaining

        # --- fin de programa: decidir si reiniciar el contador ---
        if (
            self._last_program is not None
            and program == _PROGRAM_IDLE
            and self._last_program in (_PROGRAM_CYCLE, _PROGRAM_SELF_CLEAN)
            # tras enviar una orden las lecturas pueden venir desfasadas: no
            # damos por terminado un programa que quiza ni siquiera ha arrancado
            and (time.time() - self._command_at) > COMMAND_GRACE
        ):
            self.hass.async_create_task(self._async_program_ended())

        # --- tapa: contar cierre tras apertura ---
        if lid is not None:
            if self._last_lid == 1 and lid == 0:
                self.hass.async_create_task(self._async_lid_closed(program))
            self._last_lid = lid

        if program is not None:
            self._last_program = program

    async def _async_program_ended(self) -> None:
        """Un programa del aparato acaba de terminar."""
        if self.virtual_mode is not None or self._owns_program:
            # Remover/Compactar: NUNCA reinician el contador. Si el aparato paro
            # por su cuenta antes de tiempo, cerramos tambien el modo virtual.
            self._owns_program = False
            if self.virtual_mode is not None:
                _LOGGER.info(
                    "%s terminado antes de tiempo por el aparato; contador intacto (%s)",
                    self.virtual_mode, self.lid_count,
                )
                self._cancel_timer()
                self.virtual_mode = None
                self._virtual_until = 0.0
            else:
                _LOGGER.debug("Fin de un modo virtual; contador intacto (%s)", self.lid_count)
            await self._async_save()
            return

        natural = (
            self._last_remaining is not None
            and self._last_remaining <= NATURAL_END_REMAINING
        )
        if natural:
            _LOGGER.debug("Programa completado; contador de aperturas a cero")
            await self.async_reset_counter()
        else:
            _LOGGER.debug(
                "Programa cancelado (quedaban %s min); se conserva el contador (%s)",
                self._last_remaining,
                self.lid_count,
            )
        self._last_remaining = None

    async def _async_lid_closed(self, program: int | None) -> None:
        """La tapa se acaba de cerrar."""
        self.lid_count += 1
        await self._async_save()
        self.coordinator.async_update_listeners()
        _LOGGER.debug("Tapa cerrada; aperturas acumuladas: %s", self.lid_count)

        if self.virtual_mode is not None:
            return  # ya estamos removiendo/compactando: no reiniciar ni cancelar
        if program is not None and program != _PROGRAM_IDLE:
            return  # hay un programa en marcha: no interrumpimos
        if self.lid_count >= LID_COUNT_THRESHOLD:
            _LOGGER.info(
                "Tapa cerrada con %s aperturas acumuladas: iniciando Remover",
                self.lid_count,
            )
            await self.async_start_virtual(PROGRAM_STIR)

    async def _async_daily_compact(self, _now) -> None:
        """Disparo diario de Compactar a la hora configurada."""
        if self.lid_count < LID_COUNT_THRESHOLD:
            return
        if self.virtual_mode is not None:
            return
        program = _as_int((self.coordinator.data or {}).get(PROP_PROGRAM))
        if program is not None and program != _PROGRAM_IDLE:
            _LOGGER.info(
                "%02d:%02d con %s aperturas, pero hay un programa en marcha: se omite Compactar",
                self.compact_hour,
                self.compact_minute,
                self.lid_count,
            )
            return
        _LOGGER.info("Disparo diario con %s aperturas acumuladas: iniciando Compactar", self.lid_count)
        await self.async_start_virtual(PROGRAM_COMPACT)


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
