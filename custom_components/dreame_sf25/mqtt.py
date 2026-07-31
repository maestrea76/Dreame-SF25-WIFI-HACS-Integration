"""Cliente MQTT para recibir cambios de propiedad en tiempo real (push).

El SF25 publica sus cambios en el broker de Dreame (bindDomain del dispositivo),
que es el mismo canal que usa la app. Esto evita esperar al sondeo: la tapa, el
estado o el programa se reflejan al instante.

Formato del mensaje:
    {"data": {"method": "properties_changed",
              "params": [{"siid": 6, "piid": 26, "value": 1}, ...]}}

El cliente corre en su propio hilo (paho); los cambios se entregan mediante un
callback que el coordinator marshalea al loop de Home Assistant.
"""
from __future__ import annotations

import json
import logging
import random
import ssl
from collections.abc import Callable
from typing import Any

import paho.mqtt
import paho.mqtt.client as mqtt

from .api import DreameSF25Client

_LOGGER = logging.getLogger(__name__)

# rc=5 -> no autorizado (token caducado): reconectamos con credenciales frescas
_RC_NOT_AUTHORIZED = 5


def _random_agent_id() -> str:
    return "".join(random.choice("ABCDEF") for _ in range(13))


class DreameSF25Mqtt:
    """Suscripcion al topic de estado del dispositivo."""

    def __init__(
        self,
        client: DreameSF25Client,
        on_properties: Callable[[dict[tuple[int, int], Any]], None],
    ) -> None:
        self._api = client
        self._on_properties = on_properties
        self._client: mqtt.Client | None = None
        self.connected = False

    @property
    def _topic(self) -> str:
        return (
            f"/status/{self._api.did}/{self._api.master_uid}/"
            f"{self._api.model}/{self._api.region}/"
        )

    def start(self) -> None:
        """Conecta y arranca el bucle en segundo plano (llamar en executor)."""
        host, _, port = (self._api.bind_host or "").partition(":")
        if not host or not port:
            raise ValueError(f"bindDomain invalido: {self._api.bind_host!r}")

        username, password = self._api.mqtt_credentials()
        client_id = f"p_{self._api.master_uid}_{_random_agent_id()}_{host}"

        if paho.mqtt.__version__[0] >= "2":
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2, client_id, clean_session=True
            )
        else:  # paho 1.x
            client = mqtt.Client(client_id, clean_session=True)

        client.username_pw_set(username, password)
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        client.reconnect_delay_set(1, 60)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.connect(host, int(port), keepalive=60)
        client.loop_start()
        self._client = client

    def stop(self) -> None:
        """Cierra la conexion."""
        if self._client is not None:
            try:
                self._client.disconnect()
                self._client.loop_stop()
            except Exception:  # noqa: BLE001
                pass
            self._client = None
        self.connected = False

    # --------------------------------------------------------------- callbacks
    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        code = getattr(rc, "value", rc)
        if code == 0:
            self.connected = True
            client.subscribe(self._topic)
            _LOGGER.info("MQTT conectado; suscrito a %s", self._topic)
        else:
            self.connected = False
            _LOGGER.warning("MQTT rechazo la conexion (rc=%s)", code)

    def _on_disconnect(self, client, userdata, *args) -> None:
        # paho 1.x: (rc,) · paho 2.x: (disconnect_flags, reason_code, properties)
        self.connected = False
        rc = args[0] if len(args) == 1 else (args[1] if len(args) > 1 else 0)
        code = getattr(rc, "value", rc)
        _LOGGER.info("MQTT desconectado (rc=%s); paho reintentara", code)
        if code == _RC_NOT_AUTHORIZED:
            # token caducado: renovamos credenciales para el proximo intento
            try:
                username, password = self._api.mqtt_credentials()
                client.username_pw_set(username, password)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("No se pudieron renovar credenciales MQTT: %s", err)

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return

        data = payload.get("data", payload)
        if not isinstance(data, dict) or data.get("method") != "properties_changed":
            return

        updates: dict[tuple[int, int], Any] = {}
        for param in data.get("params") or []:
            if not isinstance(param, dict):
                continue
            siid, piid = param.get("siid"), param.get("piid")
            if siid is None or piid is None or "value" not in param:
                continue
            if param.get("code", 0) == 0:
                updates[(siid, piid)] = param["value"]

        if updates:
            self._on_properties(updates)
