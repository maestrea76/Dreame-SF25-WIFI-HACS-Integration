# Dreame SF25 Waste Disposer

Unofficial integration for the **Dreame SF25 WiFi Food Waste Disposer**
(food-waste composter/dehydrator, model `dreame.fwd.u2527`), by reverse-engineering
the Dreamehome cloud.

## Entities

- **Sensors**: status, remaining time, energy (kWh), humidity, temperature,
  carbon filter life (% and days).
- **Binary**: running, lid.
- **Controls**: program (stopped / cycle / self-clean), pause / resume,
  child lock, silent mode.

## Setup

Configured with the **email**, **password** and **region** of your Dreamehome
account. If you signed up with Google/Apple, first set a password via
*"Forgot password"* in the app.

> Writes only apply while the device is awake; in suspend mode they are ignored
> and the integration reports it with an error.

---

# Dreame SF25 Waste Disposer · Español

Integración no oficial para el **Dreame SF25 WiFi Food Waste Disposer**
(compostador/deshidratador de residuos, modelo `dreame.fwd.u2527`), mediante
ingeniería inversa de la nube de Dreamehome.

## Entidades

- **Sensores**: estado, tiempo restante, energía (kWh), humedad, temperatura,
  vida del filtro de carbón (% y días).
- **Binarios**: en marcha, tapa.
- **Controles**: programa (parado / ciclo / autolimpieza), pausar / reanudar,
  bloqueo infantil, modo silencio.

## Configuración

Se configura con **email**, **contraseña** y **región** de tu cuenta Dreamehome.
Si te registraste con Google/Apple, crea antes una contraseña con
*"He olvidado mi contraseña"* en la app.

> Las escrituras solo se aplican con el aparato despierto; en suspensión se
> ignoran y la integración lo indica con un error.
