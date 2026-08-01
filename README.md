<p align="center">
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/brands/dreame_sf25/icon.png" width="120" alt="Dreame SF25">
</p>

<p align="center">
  <a href="https://github.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/actions/workflows/validate.yaml"><img src="https://github.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/actions/workflows/validate.yaml/badge.svg" alt="Validate"></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://github.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/releases"><img src="https://img.shields.io/github/v/release/maestrea76/Dreame-SF25-WIFI-HACS-Integration?display_name=tag" alt="Release"></a>
  <img src="https://img.shields.io/github/license/maestrea76/Dreame-SF25-WIFI-HACS-Integration" alt="License">
</p>

# Dreame SF25 Waste Disposer — Home Assistant (HACS)

**English** · [Español](#dreame-sf25-waste-disposer--home-assistant-hacs-español)

Unofficial integration for the **Dreame SF25 WiFi Food Waste Disposer**
(countertop food-waste composter/dehydrator, model `dreame.fwd.u2527`), obtained by
**reverse-engineering** the Dreame cloud (Dreamehome app), since the device has no
open API.

> ⚠️ Work in progress. Exposes sensors and already allows **starting/stopping
> programs** (cycle and self-clean) and settings (child lock, silent mode).

## Screenshots

<p align="center">
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/docs/sensors.png" width="45%" alt="Sensors">
  &nbsp;
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/docs/controls.png" width="45%" alt="Controls">
</p>

## How it works

The SF25 is a `COMM_MCU` device that **does not cache MIoT properties in the cloud**.
Its state is read through a **MIoT `sendCommand` RPC** (cloud → device) against the
Dreame API (`https://<region>.iot.dreame.tech:13267`), authenticating with your
Dreamehome account credentials (OAuth2, `password` grant).

Since v0.2.0 the integration also subscribes to Dreame's **MQTT broker** (the same
channel the app uses), so state changes arrive **instantly** instead of waiting for
a poll — a lid opened for a few seconds is no longer missed. Polling stays as a
safety net (every 5 min while push is alive, 30 s if it drops).

> The device is **cloud-only**: it has no open local ports and does not answer the
> miIO handshake, so local (LAN) control is not possible.

## Installation

### Via HACS (recommended)

1. Make sure [HACS](https://hacs.xyz) is installed.
2. In HACS open **Integrations** → ⋮ (top right) → **Custom repositories**.
3. Add the URL `https://github.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration`,
   category **Integration**, and click **Add**.
4. Search for **Dreame SF25 Waste Disposer**, open it and click **Download**.
5. **Restart Home Assistant.**

### Manual

1. Copy the `custom_components/dreame_sf25` folder into your Home Assistant
   `config/custom_components/` directory.
2. **Restart Home Assistant.**

## Configuration

1. Go to **Settings → Devices & services → Add integration** and search for
   **Dreame SF25**.
2. Enter the **email**, **password** and **region** (`eu`, `cn`, `us`, `ru`, `sg`,
   `kr`) of your Dreamehome account.

> If you signed up with **Google/Apple**, first set a password in the Dreamehome
> app via *"Forgot password"* (using your Google email).

## Entities

**Sensors**

| Entity | Prop | Notes |
|---|---|---|
| Status | 2.1 | working / standby / suspended |
| Remaining time | 2.11 | minutes of the program |
| Energy | 3.14 | Wh → kWh (÷1000), resets per cycle |
| Humidity | 3.2 | % (rises to ~100 when drying stops) |
| Temperature | 3.3 | °C |
| Carbon filter (life) | 4.3 | % remaining |
| Carbon filter (days) | 4.4 | days until cleaning |

**Binary:** Running (2.10) · Lid (6.26)

**Controls**

| Entity | Prop | Action |
|---|---|---|
| Program (select) | 2.3 | Stopped (-1) / Cycle (0) / Self-clean (2) — starts and stops |
| Pause / Resume (button) | 2.10 | Pauses (0) / resumes (1) the running program |
| Child lock (switch) | 6.10 | on/off (only effective while a cycle runs) |
| Silent mode (switch) | 6.17 | on/off |

> Note: writes only apply while the device is **awake**; in suspend mode
> (status = suspended) they are ignored and the integration raises an error.

## Modes

The appliance only knows two programs (grind and self-clean). The integration adds
two **virtual modes** built on top of self-clean, bounded in time:

| Mode | What it does | Duration |
|---|---|---|
| Grind | Normal grinding cycle | ~6 h |
| Self-clean | Full self-clean | ~90 min |
| **Stir** | Self-clean, stopped early | **10 min** |
| **Compact** | Self-clean, stopped early | **1 h** |

**Automatic triggers** (based on a lid-opening counter kept by the integration):

- **Stir** — when the lid closes and at least **2 openings** have accumulated.
- **Compact** — daily at **15:00**, if at least 2 openings have accumulated.

The counter resets **only when Grind or Self-clean finish naturally**; if you cancel
them early, or if Stir/Compact ran, it is kept. Opening the lid during Stir/Compact
does not cancel them. State survives a Home Assistant restart, and Stir/Compact
inherit the self-clean temperature limit (100 °C).

## Temperature safety stop

The integration watches the temperature on every update and **stops the device**
(program → stopped) if it exceeds the limit for the running program:

| Program | Limit |
|---|---|
| Cycle | **150 °C** (a normal cycle stays around 140 °C) |
| Self-clean | **100 °C** |

It retries the stop command up to 3 times and fires a
`dreame_sf25_safety_stop` event (with `temperature`, `limit`, `program`,
`stopped`) that you can use to send yourself a notification.

> ⚠️ This is a **secondary** safeguard: it depends on Home Assistant, your
> network and the Dreame cloud being up. It does **not** replace the appliance's
> own thermal cut-off. Limits live in `SAFETY_TEMP_LIMITS` (`const.py`).

## Reverse engineering

The tools in [`tools/`](tools/) are used for discovery:

- `scan_dreame.py` — login + scan of the MIoT property space via RPC.
- `monitor_dreame.py` — live monitor that prints property changes to map what each
  `siid.piid` controls while operating the device.
- `control_dreame.py` — interactive tester for writes (`set_property`) and actions.

## Credits

The Dreame cloud protocol is based on the work of
[Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum).

## Disclaimer

Independent project, not affiliated with Dreame. Use at your own risk.

---

<a name="dreame-sf25-waste-disposer--home-assistant-hacs-español"></a>

# Dreame SF25 Waste Disposer — Home Assistant (HACS) · Español

[English](#dreame-sf25-waste-disposer--home-assistant-hacs) · **Español**

Integración no oficial para el **Dreame SF25 WiFi Food Waste Disposer**
(compostador/deshidratador de residuos de encimera, modelo `dreame.fwd.u2527`),
obtenida por **ingeniería inversa** de la nube de Dreame (app Dreamehome), ya que
el dispositivo no dispone de API abierta.

> ⚠️ Proyecto en desarrollo. Expone sensores y ya permite **iniciar/parar
> programas** (ciclo y autolimpieza) y ajustes (bloqueo infantil, modo silencio).

## Capturas

<p align="center">
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/docs/sensors.png" width="45%" alt="Sensores">
  &nbsp;
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/docs/controls.png" width="45%" alt="Controles">
</p>

## Cómo funciona

El SF25 es un dispositivo `COMM_MCU` que **no cachea propiedades MIoT en la nube**.
Su estado se lee mediante un **RPC MIoT `sendCommand`** (nube → dispositivo) contra
la API de Dreame (`https://<región>.iot.dreame.tech:13267`), autenticando con las
credenciales de la cuenta Dreamehome (OAuth2, grant `password`).

Desde la v0.2.0 la integración además se suscribe al **broker MQTT** de Dreame (el
mismo canal que usa la app), así que los cambios llegan **al instante** en vez de
esperar al sondeo: una tapa abierta unos segundos ya no se pierde. El sondeo queda
como red de seguridad (cada 5 min con el push vivo, 30 s si se cae).

> El aparato es **solo nube**: no tiene puertos locales abiertos ni responde al
> handshake miIO, por lo que el control local (LAN) no es posible.

## Instalación

### Con HACS (recomendado)

1. Asegúrate de tener [HACS](https://hacs.xyz) instalado.
2. En HACS abre **Integraciones** → ⋮ (arriba a la derecha) → **Repositorios personalizados**.
3. Añade la URL `https://github.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration`,
   categoría **Integration**, y pulsa **Añadir**.
4. Busca **Dreame SF25 Waste Disposer**, ábrelo y pulsa **Descargar**.
5. **Reinicia Home Assistant.**

### Manual

1. Copia la carpeta `custom_components/dreame_sf25` en el directorio
   `config/custom_components/` de tu Home Assistant.
2. **Reinicia Home Assistant.**

## Configuración

1. Ve a **Ajustes → Dispositivos y servicios → Añadir integración** y busca
   **Dreame SF25**.
2. Introduce **email**, **contraseña** y **región** (`eu`, `cn`, `us`, `ru`, `sg`,
   `kr`) de tu cuenta Dreamehome.

> Si te registraste con **Google/Apple**, primero crea una contraseña en la app
> Dreamehome con *"He olvidado mi contraseña"* (usando tu email de Google).

## Entidades

**Sensores**

| Entidad | Prop | Notas |
|---|---|---|
| Estado | 2.1 | trabajando / en espera / suspensión |
| Tiempo restante | 2.11 | minutos del programa |
| Energía | 3.14 | Wh → kWh (÷1000), se resetea por ciclo |
| Humedad | 3.2 | % (sube a ~100 al parar el secado) |
| Temperatura | 3.3 | °C |
| Filtro de carbón (vida) | 4.3 | % restante |
| Filtro de carbón (días) | 4.4 | días hasta limpiar |

**Binarios:** En marcha (2.10) · Tapa (6.26)

**Controles**

| Entidad | Prop | Acción |
|---|---|---|
| Programa (select) | 2.3 | Parado (-1) / Ciclo (0) / Autolimpieza (2) — inicia y para |
| Pausar / Reanudar (button) | 2.10 | Pausa (0) / reanuda (1) el programa en marcha |
| Bloqueo infantil (switch) | 6.10 | on/off (solo efectivo con ciclo en marcha) |
| Modo silencio (switch) | 6.17 | on/off |

> Nota: las escrituras solo se aplican con el aparato **despierto**; en modo
> suspensión (estado = suspensión) se ignoran y la integración avisa con un error.

## Modos

El aparato solo conoce dos programas (triturar y autolimpieza). La integración añade
dos **modos virtuales** construidos sobre la autolimpieza, acotados en el tiempo:

| Modo | Qué hace | Duración |
|---|---|---|
| Triturar | Ciclo de triturado normal | ~6 h |
| Autolimpieza | Autolimpieza completa | ~90 min |
| **Remover** | Autolimpieza, parada antes | **10 min** |
| **Compactar** | Autolimpieza, parada antes | **1 h** |

**Disparos automáticos** (según un contador de aperturas de tapa que lleva la integración):

- **Remover** — al cerrarse la tapa habiendo acumulado **2 aperturas** o más.
- **Compactar** — a diario a las **15:00**, si hay 2 aperturas o más acumuladas.

El contador se reinicia **solo cuando Triturar o Autolimpieza terminan de forma
natural**; si los cancelas a medias, o si lo que corrió fue Remover/Compactar, se
conserva. Abrir la tapa durante Remover/Compactar no los cancela. El estado sobrevive
a un reinicio de Home Assistant, y Remover/Compactar heredan el límite de temperatura
de la autolimpieza (100 °C).

## Parada de seguridad por temperatura

La integración vigila la temperatura en cada actualización y **detiene el aparato**
(programa → parado) si supera el límite del programa en curso:

| Programa | Límite |
|---|---|
| Ciclo | **150 °C** (un ciclo normal se mueve sobre 140 °C) |
| Autolimpieza | **100 °C** |

Reintenta la orden de parada hasta 3 veces y dispara el evento
`dreame_sf25_safety_stop` (con `temperature`, `limit`, `program`, `stopped`),
que puedes usar para enviarte una notificación.

> ⚠️ Es una protección **secundaria**: depende de que Home Assistant, tu red y la
> nube de Dreame estén operativos. **No sustituye** al corte térmico del propio
> aparato. Los límites están en `SAFETY_TEMP_LIMITS` (`const.py`).

## Ingeniería inversa

Las herramientas en [`tools/`](tools/) sirven para el descubrimiento:

- `scan_dreame.py` — login + escaneo del espacio de propiedades MIoT vía RPC.
- `monitor_dreame.py` — monitor en vivo que imprime cambios de propiedades para
  mapear qué controla cada `siid.piid` operando el aparato.
- `control_dreame.py` — probador interactivo de escrituras (`set_property`) y acciones.

## Créditos

El protocolo de la nube de Dreame se basa en el trabajo de
[Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum).

## Aviso

Proyecto independiente, sin relación con Dreame. Úsalo bajo tu responsabilidad.
