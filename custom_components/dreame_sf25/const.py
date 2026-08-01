"""Constantes de la integracion Dreame SF25."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "dreame_sf25"

# Config entry
CONF_REGION: Final = "region"
CONF_DID: Final = "did"

DEFAULT_REGION: Final = "eu"
REGIONS: Final = ["eu", "cn", "us", "ru", "sg", "kr"]

# Modelo objetivo
TARGET_MODEL: Final = "dreame.fwd.u2527"

# Intervalos de sondeo (segundos):
#  - SCAN_INTERVAL_POLL: sin push MQTT (o si se cae) -> sondeo frecuente.
#  - SCAN_INTERVAL_PUSH: con push vivo -> el sondeo es solo red de seguridad.
SCAN_INTERVAL_POLL: Final = 30
SCAN_INTERVAL_PUSH: Final = 300

# --- Endpoints / secretos del protocolo de la app Dreamehome ---
PORT: Final = "13267"
PWD_SALT: Final = "RAylYC%fmSKp7%Tq"
USER_AGENT: Final = "Dreame_Smarthome/2.1.9 (iPhone; iOS 18.4.1; Scale/3.00)"
BASIC_AUTH: Final = "Basic ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg="
DEFAULT_TENANT: Final = "000000"

# --- Propiedades MIoT descubiertas (siid, piid) ---
# Confirmadas por observacion en vivo:
PROP_REMAINING_TIME: Final = (2, 11)   # minutos restantes de ciclo
PROP_ENERGY_WH: Final = (3, 14)        # energia acumulada en Wh (crudos)
PROP_HUMIDITY: Final = (3, 2)          # humedad relativa % (sube a ~100 al parar el secado)
PROP_TEMPERATURE: Final = (3, 3)       # temperatura de camara C (se enfria al parar)
PROP_CARBON_FILTER_PCT: Final = (4, 3)   # % de vida restante del filtro de carbon (82)
PROP_CARBON_FILTER_DAYS: Final = (4, 4)  # dias restantes para limpiar filtro de carbon (147)

# Estado del ciclo (2.1, enum) y flag marcha/pausa (2.10). Van unidos.
PROP_STATUS: Final = (2, 1)             # estado nativo (enum), ver STATUS_MAP
PROP_RUNNING: Final = (2, 10)           # tri-estado: -1=apagado, 0=pausa, 1=marcha
PROP_PROGRAM: Final = (2, 3)            # programa activo: -1=inactivo, 0=ciclo normal, 2=autolimpieza

# Estado nativo del aparato (PROP_STATUS = 2.1). Se ira completando.
STATUS_MAP: Final = {
    1: "working",     # triturando/limpiando activamente
    2: "standby",     # en espera (sin triturar ni limpiar)
    3: "suspended",   # modo suspension (sleep)
}

# Programa (PROP_PROGRAM = 2.3). Escribir este valor arranca/para el programa:
#   -1 = parar/inactivo, 0 = iniciar ciclo normal (360 min), 2 = iniciar autolimpieza (90 min).
# 1 = ¿tercer modo? (sin confirmar).
PROGRAM_MAP: Final = {          # valor -> opcion
    -1: "idle",
    0: "cycle",
    2: "self_clean",
}
PROGRAM_OPTIONS: Final = {      # opcion -> valor (para escribir desde el select)
    "idle": -1,
    "cycle": 0,
    "self_clean": 2,
}

# --- Modos virtuales -------------------------------------------------------
# El aparato solo conoce ciclo (0) y autolimpieza (2). "Remover" y "Compactar"
# son autolimpiezas acotadas en el tiempo por la integracion: se lanza 2.3=2 y
# se para al cumplirse la duracion. Al usuario se le muestran como modos propios.
PROGRAM_STIR: Final = "stir"           # Remover: autolimpieza corta
PROGRAM_COMPACT: Final = "compact"     # Compactar: autolimpieza larga

VIRTUAL_DURATIONS: Final = {
    PROGRAM_STIR: 10 * 60,             # 10 minutos
    PROGRAM_COMPACT: 60 * 60,          # 1 hora
}

# Opciones que ofrece el select (en orden de aparicion)
SELECT_OPTIONS: Final = ["idle", "cycle", "self_clean", PROGRAM_STIR, PROGRAM_COMPACT]

# Disparo automatico
LID_COUNT_THRESHOLD: Final = 2         # aperturas de tapa necesarias
# Hora por defecto de Compactar; editable desde HA (entidad "Hora de compactar")
DEFAULT_COMPACT_HOUR: Final = 15
DEFAULT_COMPACT_MINUTE: Final = 0
LID_COUNT_MAX: Final = 99              # tope de la entidad number

# Se considera que un programa termino de forma natural si al acabar le
# quedaba menos de esto (min). Si se cancela antes, el contador NO se reinicia.
NATURAL_END_REMAINING: Final = 1

# Segundos tras enviar una orden en los que ignoramos los 'fin de programa':
# la nube puede devolver todavia el estado anterior y provocar falsos finales.
COMMAND_GRACE: Final = 20

STORAGE_VERSION: Final = 1

# --- Parada de seguridad por temperatura ---
# Si la temperatura supera el limite del programa en curso, la integracion
# detiene el aparato (escribe 2.3 = -1) y dispara EVENT_SAFETY_STOP.
# Referencia: un ciclo normal no suele pasar de 140 C.
# NOTA: es una proteccion SECUNDARIA; depende de HA y de la nube. No sustituye
# al corte termico del propio aparato.
SAFETY_TEMP_LIMITS: Final = {
    0: 150,   # ciclo normal (PROGRAM 'cycle')
    2: 100,   # autolimpieza (PROGRAM 'self_clean')
}
EVENT_SAFETY_STOP: Final = "dreame_sf25_safety_stop"

PROP_LID: Final = (6, 26)              # tapa: abierta/cerrada (binary_sensor)

# Controles (escribibles):
PROP_CHILD_LOCK: Final = (6, 10)       # bloqueo infantil (0=off, 1=on)
PROP_SILENT_MODE: Final = (6, 17)      # modo silencio (0=off, 1=on)

# Accion MIoT para DESPERTAR de suspension (confirmada): siid 2, aiid 1.
# En suspension (2.1=3) las escrituras se ignoran (code 1); esta accion sí se honra.
ACTION_WAKE: Final = (2, 1)

# Sin mapear aun (candidatos a power/estado/modo/fallo):
PROP_FW_VERSION: Final = (1, 4)
PROP_SERIAL: Final = (1, 5)
PROP_HW_REV: Final = (1, 6)

# Conjunto de propiedades a sondear en cada ciclo del coordinator.
POLL_PROPERTIES: Final = [
    PROP_REMAINING_TIME,
    PROP_ENERGY_WH,
    PROP_HUMIDITY,
    PROP_TEMPERATURE,
    (2, 1), (2, 2), (2, 3), (2, 10),
    (4, 3), (4, 4), (4, 6),
    (6, 10), (6, 17), (6, 26),
]
