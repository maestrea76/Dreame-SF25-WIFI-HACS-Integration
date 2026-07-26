<p align="center">
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/brands/dreame_sf25/icon.png" width="96" alt="Dreame SF25">
</p>

# Dreame SF25 Waste Disposer

Unofficial integration for the **Dreame SF25 WiFi Food Waste Disposer**
(food-waste composter/dehydrator, model `dreame.fwd.u2527`), by reverse-engineering
the Dreamehome cloud.

<p align="center">
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/docs/sensors.png" width="45%" alt="Sensors">
  &nbsp;
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/docs/controls.png" width="45%" alt="Controls">
</p>

## Entities

- **Sensors**: status, remaining time, energy (kWh), humidity, temperature,
  carbon filter life (% and days).
- **Binary**: running, lid.
- **Controls**: program (stopped / cycle / self-clean), pause / resume,
  child lock, silent mode.

## Installation

1. HACS → **Integrations** → ⋮ → **Custom repositories** → add this repo
   (category **Integration**) → **Add**.
2. Search **Dreame SF25 Waste Disposer**, click **Download** and **restart
   Home Assistant**.
3. **Settings → Devices & services → Add integration →** search **Dreame SF25**.

## Setup

Configured with the **email**, **password** and **region** (`eu`, `cn`, `us`,
`ru`, `sg`, `kr`) of your Dreamehome account. If you signed up with Google/Apple,
first set a password via *"Forgot password"* in the app.

> Writes only apply while the device is awake; in suspend mode they are ignored
> and the integration reports it with an error.

---

# Dreame SF25 Waste Disposer · Español

Integración no oficial para el **Dreame SF25 WiFi Food Waste Disposer**
(compostador/deshidratador de residuos, modelo `dreame.fwd.u2527`), mediante
ingeniería inversa de la nube de Dreamehome.

<p align="center">
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/docs/sensors.png" width="45%" alt="Sensores">
  &nbsp;
  <img src="https://raw.githubusercontent.com/maestrea76/Dreame-SF25-WIFI-HACS-Integration/main/docs/controls.png" width="45%" alt="Controles">
</p>

## Entidades

- **Sensores**: estado, tiempo restante, energía (kWh), humedad, temperatura,
  vida del filtro de carbón (% y días).
- **Binarios**: en marcha, tapa.
- **Controles**: programa (parado / ciclo / autolimpieza), pausar / reanudar,
  bloqueo infantil, modo silencio.

## Instalación

1. HACS → **Integraciones** → ⋮ → **Repositorios personalizados** → añade este
   repo (categoría **Integration**) → **Añadir**.
2. Busca **Dreame SF25 Waste Disposer**, pulsa **Descargar** y **reinicia
   Home Assistant**.
3. **Ajustes → Dispositivos y servicios → Añadir integración →** busca **Dreame SF25**.

## Configuración

Se configura con **email**, **contraseña** y **región** (`eu`, `cn`, `us`, `ru`,
`sg`, `kr`) de tu cuenta Dreamehome. Si te registraste con Google/Apple, crea
antes una contraseña con *"He olvidado mi contraseña"* en la app.

> Las escrituras solo se aplican con el aparato despierto; en suspensión se
> ignoran y la integración lo indica con un error.
