#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Escucha en tiempo real los eventos MQTT del Dreame SF25 (dreame.fwd.u2527).

Prueba de concepto para la v0.2.0: en vez de sondear cada 30 s, el dispositivo
EMPUJA los cambios de propiedad al instante (es el canal que usa la app).

Que hace:
  1. Login en la nube de Dreame (reutiliza scan_dreame.py).
  2. Localiza el SF25 y saca su bindDomain (broker MQTT) y masterUid.
  3. Se conecta al broker por TLS y se suscribe al topic de estado del aparato.
  4. Imprime cada cambio con hora: 'siid.piid = valor'.

Uso:
  python tools/mqtt_listen.py
  (te pide email y contrasena; region por defecto 'eu')

Mientras corre, ABRE Y CIERRA LA TAPA para comprobar la latencia real.
Ctrl+C para parar. Requiere: pip install paho-mqtt
"""

import json
import os
import random
import ssl
import sys
import time
import getpass

import scan_dreame as S

try:
    import paho.mqtt
    import paho.mqtt.client as mqtt
except ImportError:
    print("Falta paho-mqtt. Instalalo con:  python -m pip install paho-mqtt")
    sys.exit(1)

REGION = os.environ.get("DREAME_REGION", "eu")

# Etiquetas conocidas para leer la salida de un vistazo
LABELS = {
    (1, 4): "firmware", (1, 6): "modo_str",
    (2, 1): "estado", (2, 2): "?2.2", (2, 3): "programa",
    (2, 10): "marcha", (2, 11): "t.restante",
    (3, 2): "humedad", (3, 3): "temperatura", (3, 14): "energia_wh",
    (4, 3): "filtro_%", (4, 4): "filtro_dias", (4, 6): "?4.6",
    (6, 10): "bloqueo_infantil", (6, 17): "modo_silencio", (6, 26): "TAPA",
}


def connect_cloud():
    S.REGION = REGION
    email = os.environ.get("DREAME_EMAIL") or input("Email de Dreamehome: ").strip()
    password = os.environ.get("DREAME_PASSWORD") or getpass.getpass("Contrasena (no se vera): ")
    print(f"== Nube Dreame: {S.base_url()} (region {REGION}) ==")
    cloud = S.DreameCloud(email, password, REGION)
    if not cloud.login():
        print("Login fallido.")
        sys.exit(1)
    target = None
    for d in cloud.list_devices():
        model = d.get("model") or ""
        if model == S.TARGET_MODEL or "u2527" in model:
            target = d
            break
    if not target:
        print("No encuentro el SF25.")
        sys.exit(1)
    return cloud, target


def random_agent_id() -> str:
    return "".join(random.choice("ABCDEF") for _ in range(13))


def main():
    cloud, dev = connect_cloud()
    did = str(dev.get("did"))
    model = dev.get("model")
    master_uid = dev.get("masterUid")
    bind = dev.get("bindDomain")          # p.ej. 10000.mt.eu.iot.dreame.tech:19973
    host, port = bind.split(":")
    port = int(port)
    topic = f"/status/{did}/{master_uid}/{model}/{REGION}/"

    print(f"\n== MQTT ==\n  broker : {host}:{port}\n  topic  : {topic}")
    print(f"  user   : {cloud.uid}\n")

    client_id = f"p_{master_uid}_{random_agent_id()}_{host}"

    # paho 1.x y 2.x tienen APIs de callback distintas
    v2 = paho.mqtt.__version__[0] >= "2"
    if v2:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id, clean_session=True)
    else:
        client = mqtt.Client(client_id, clean_session=True)

    client.username_pw_set(cloud.uid, cloud.access_token)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)

    def on_connect(cl, userdata, flags, rc, *a):
        if rc == 0:
            print("[OK] Conectado al broker. Suscribiendo...")
            cl.subscribe(topic)
            print(">>> ABRE Y CIERRA LA TAPA para ver la latencia real. Ctrl+C para salir.\n")
        else:
            print(f"[FALLO] Conexion rechazada (rc={rc}). "
                  "rc=5 suele ser credenciales/token; rc=4 usuario o pass mal.")

    def on_disconnect(cl, userdata, rc, *a):
        print(f"[!] Desconectado (rc={rc})")

    def on_message(cl, userdata, msg):
        ts = time.strftime("%H:%M:%S")
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            print(f"[{ts}] (payload no-JSON) {msg.payload[:120]!r}")
            return

        data = payload.get("data", payload)
        method = data.get("method") if isinstance(data, dict) else None
        if method == "properties_changed":
            for p in data.get("params", []):
                k = (p.get("siid"), p.get("piid"))
                label = LABELS.get(k, "")
                print(f"[{ts}] PUSH {k[0]}.{k[1]:<3} {label:<16} = {p.get('value')!r}")
        else:
            print(f"[{ts}] mensaje ({method}): {json.dumps(data)[:300]}")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(host, port, keepalive=60)
    except Exception as e:
        print("[FALLO] No se pudo conectar al broker:", e)
        sys.exit(1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nParado por el usuario.")
        client.disconnect()


if __name__ == "__main__":
    main()
