#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor en vivo del Dreame SF25 (dreame.fwd.u2527) para MAPEO SEMANTICO.

Sondea via RPC (nube->dispositivo) las propiedades conocidas cada POLL segundos
e imprime SOLO los cambios, con marca de tiempo. Asi puedes correlacionar cada
propiedad con una accion fisica: enciende el triturador, cambia de modo, mete
carga, provoca un atasco... y ves que siid.piid cambia.

Uso:
  python tools/monitor_dreame.py
  (te pide email y contrasena de Dreamehome; region por defecto 'eu')

Mientras corre, OPERA el aparato. Guarda un log monitor_*.log que puedes pegar.
Ctrl+C para parar.

Requiere el fichero scan_dreame.py en la misma carpeta (reutiliza su cliente).
"""

import os
import sys
import time
import getpass

import scan_dreame as S

# --------------------------- CONFIGURACION -----------------------------------
REGION = os.environ.get("DREAME_REGION", "eu")
POLL = float(os.environ.get("DREAME_POLL", "2.0"))   # segundos entre sondeos

# Propiedades descubiertas por el escaneo (siid, piid). Amplia si aparecen mas.
KNOWN = [
    (1, 4), (1, 5), (1, 6),
    (2, 1), (2, 2), (2, 3), (2, 10), (2, 11),
    (3, 2), (3, 3), (3, 14),
    (4, 3), (4, 4), (4, 6),
    (6, 10), (6, 17), (6, 18), (6, 26),
]
# -----------------------------------------------------------------------------


def connect():
    S.REGION = REGION  # base_url() de scan_dreame usa este global
    email = os.environ.get("DREAME_EMAIL") or input("Email de Dreamehome: ").strip()
    password = os.environ.get("DREAME_PASSWORD") or getpass.getpass("Contrasena de Dreamehome (no se vera): ")
    print(f"== Nube Dreame: {S.base_url()} (region {REGION}) ==")
    cloud = S.DreameCloud(email, password, REGION)
    if not cloud.login():
        print("Login fallido. Revisa credenciales/region.")
        sys.exit(1)
    target = None
    for d in cloud.list_devices():
        model = d.get("model") or ""
        if model == S.TARGET_MODEL or "u2527" in model:
            target = d
            break
    if not target:
        print(f"No encuentro {S.TARGET_MODEL} en la cuenta.")
        sys.exit(1)
    cloud.bind_host = target.get("bindDomain")
    return cloud, str(target.get("did"))


def read_all(cloud, did) -> dict:
    keys = [{"did": f"{s}.{p}", "siid": s, "piid": p} for s, p in KNOWN]
    vals = {}
    for i in range(0, len(keys), 15):
        res = cloud.send_rpc(did, "get_properties", keys[i:i + 15], timeout=20)
        for e in res or []:
            if e.get("code") == 0:
                vals[(e["siid"], e["piid"])] = e.get("value")
    return vals


def main():
    cloud, did = connect()
    logname = f"monitor_{int(time.time())}.log"
    logf = open(logname, "w", encoding="utf-8")

    def log(line: str):
        print(line)
        logf.write(line + "\n")
        logf.flush()

    log(f"# Monitor SF25 did={did} region={REGION} poll={POLL}s")
    log(f"# Vigilando {len(KNOWN)} propiedades. Log: {logname}")
    log("# >>> OPERA EL TRITURADOR AHORA (encender, modos, carga, atasco). Ctrl+C para parar. <<<\n")

    prev = read_all(cloud, did)
    ts = time.strftime("%H:%M:%S")
    log(f"[{ts}] SNAPSHOT INICIAL:")
    for k in sorted(prev):
        log(f"    {k[0]}.{k[1]:<3} = {prev[k]!r}")
    log("")

    idle = 0
    try:
        while True:
            time.sleep(POLL)
            cur = read_all(cloud, did)
            if not cur:
                continue
            ts = time.strftime("%H:%M:%S")
            changes = [(k, prev.get(k), cur[k]) for k in cur if cur[k] != prev.get(k)]
            if changes:
                for k, o, n in sorted(changes):
                    log(f"[{ts}] CAMBIO {k[0]}.{k[1]:<3} : {o!r} -> {n!r}")
                idle = 0
            else:
                idle += 1
                if idle % 15 == 0:  # cada ~30s sin cambios, una senal de vida
                    print(f"[{ts}] (sin cambios; sigo vigilando...)", end="\r")
            prev = cur
    except KeyboardInterrupt:
        log("\n# Monitor detenido por el usuario.")
    finally:
        logf.close()
        print(f"\nLog guardado en: {logname}")


if __name__ == "__main__":
    main()
