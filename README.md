<p align="center">
  <img src="brands/dreame_sf25/icon.png" width="120" alt="Dreame SF25">
</p>

# Dreame SF25 Waste Disposer — Home Assistant (HACS)

Integración no oficial para el **Dreame SF25 WiFi Food Waste Disposer**
(compostador/deshidratador de residuos de encimera, modelo `dreame.fwd.u2527`),
obtenida por **ingeniería inversa** de la nube de Dreame (app Dreamehome), ya que
el dispositivo no dispone de API abierta.

> ⚠️ Proyecto en desarrollo. Expone sensores y ya permite **iniciar/parar
> programas** (ciclo y autolimpieza) y ajustes (bloqueo infantil, modo silencio).

## Cómo funciona

El SF25 es un dispositivo `COMM_MCU` que **no cachea propiedades MIoT en la nube**.
Su estado se lee mediante un **RPC MIoT `sendCommand`** (nube → dispositivo) contra
la API de Dreame (`https://<región>.iot.dreame.tech:13267`), autenticando con las
credenciales de la cuenta Dreamehome (OAuth2, grant `password`).

## Instalación (HACS)

1. HACS → Integraciones → menú ⋮ → *Repositorios personalizados*.
2. Añade la URL de este repositorio, categoría **Integration**.
3. Instala "Dreame SF25 Waste Disposer" y reinicia Home Assistant.
4. Ajustes → Dispositivos y servicios → *Añadir integración* → "Dreame SF25".
5. Introduce **email**, **contraseña** y **región** de tu cuenta Dreamehome.

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

## Ingeniería inversa

Las herramientas en [`tools/`](tools/) sirven para el descubrimiento:

- `scan_dreame.py` — login + escaneo del espacio de propiedades MIoT vía RPC.
- `monitor_dreame.py` — monitor en vivo que imprime cambios de propiedades para
  mapear qué controla cada `siid.piid` operando el aparato.

## Créditos

El protocolo de la nube de Dreame se basa en el trabajo de
[Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum).

## Aviso

Proyecto independiente, sin relación con Dreame. Úsalo bajo tu responsabilidad.
