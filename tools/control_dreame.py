#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descubridor de CONTROLES del Dreame SF25 (dreame.fwd.u2527).

Prueba escrituras (set_properties) y acciones (action) via el RPC nube->dispositivo
para averiguar como se inician/pausan/paran los ciclos y programas.

SEGURIDAD:
- Es INTERACTIVO: pide confirmacion antes de cada escritura.
- Algunas ordenes pueden ARRANCAR fisicamente el aparato (ciclo de 6 h, motor,
  autolimpieza). Esas van marcadas con [!] y piden confirmacion escrita.
- Empieza por la opcion 1 (validar escritura con el modo silencio, inofensivo).

Uso:
  python tools/control_dreame.py
  (te pide email y contrasena de Dreamehome; region por defecto 'eu')

Requiere scan_dreame.py en la misma carpeta (reutiliza su cliente).
"""

import os
import sys
import getpass

import scan_dreame as S

REGION = os.environ.get("DREAME_REGION", "eu")

# Propiedades de control/estado que mostramos antes y despues de cada prueba.
WATCH = [
    (2, 1),   # estado: 1=trabajando, 2=espera, 3=suspension
    (2, 2),   # ?
    (2, 3),   # programa: -1=inactivo, 0=ciclo, 2=autolimpieza
    (2, 10),  # marcha: -1=apagado, 0=pausa, 1=marcha
    (2, 11),  # tiempo restante (min)
    (4, 6),   # ?
    (6, 10),  # bloqueo infantil
    (6, 17),  # modo silencio
    (6, 26),  # tapa
]

LABELS = {
    (2, 1): "estado",
    (2, 2): "?2.2",
    (2, 3): "programa",
    (2, 10): "marcha",
    (2, 11): "t.restante",
    (4, 6): "?4.6",
    (6, 10): "bloqueo_infantil",
    (6, 17): "modo_silencio",
    (6, 26): "tapa",
}


def connect():
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
    cloud.bind_host = target.get("bindDomain")
    return cloud, str(target.get("did"))


def snapshot(cloud, did, title="ESTADO ACTUAL"):
    keys = [{"did": f"{s}.{p}", "siid": s, "piid": p} for s, p in WATCH]
    res = cloud.send_rpc(did, "get_properties", keys, timeout=20) or []
    vals = {(e["siid"], e["piid"]): e.get("value") for e in res if e.get("code") == 0}
    print(f"\n--- {title} ---")
    for k in WATCH:
        if k in vals:
            print(f"  {k[0]}.{k[1]:<3} {LABELS.get(k,''):<16} = {vals[k]!r}")
    return vals


def set_property(cloud, did, siid, piid, value):
    params = [{"did": f"{siid}.{piid}", "siid": siid, "piid": piid, "value": value}]
    print(f"\n>>> set_properties {siid}.{piid} = {value!r}")
    resp = cloud.send_rpc_raw(did, "set_properties", params, timeout=20)
    print(f"    respuesta cruda: {resp}")
    return resp


def run_action(cloud, did, siid, aiid, args=None):
    params = {"did": str(did), "siid": siid, "aiid": aiid, "in": args or []}
    print(f"\n>>> action siid={siid} aiid={aiid} in={args or []}")
    resp = cloud.send_rpc_raw(did, "action", params, timeout=20)
    print(f"    respuesta cruda: {resp}")
    return resp


def confirm(msg, word="SI"):
    return input(f"{msg} (escribe {word} para continuar): ").strip() == word


def do_write(cloud, did, siid, piid, value, risky=False):
    snapshot(cloud, did, "ANTES")
    if risky:
        print("\n[!] Esta orden puede ACCIONAR el aparato fisicamente.")
        if not confirm("Confirmas la escritura?", "CONFIRMO"):
            print("Cancelado.")
            return
    else:
        if not confirm("Confirmas la escritura?"):
            print("Cancelado.")
            return
    set_property(cloud, did, siid, piid, value)
    import time
    time.sleep(2)
    snapshot(cloud, did, "DESPUES (2s)")


MENU = """
========================= MENU CONTROL SF25 =========================
  0) Releer estado actual
  1) VALIDAR escritura (segura): alternar modo silencio 6.17 y restaurar
  2) Escritura personalizada: set_property(siid, piid, valor)
  3) Probar accion MIoT: action(siid, aiid)
 --- experimentos de control (pueden accionar el aparato) [!] ---
  4) [!] PAUSAR  -> set 2.10 = 0
  5) [!] REANUDAR -> set 2.10 = 1
  6) [!] INICIAR CICLO normal -> set 2.3 = 0
  7) [!] INICIAR AUTOLIMPIEZA -> set 2.3 = 2
  8) [!] PARAR/CANCELar -> set 2.3 = -1
  q) Salir
=====================================================================
Elige opcion: """


def _read_one(cloud, did, siid, piid):
    res = cloud.send_rpc(did, "get_properties",
                         [{"did": f"{siid}.{piid}", "siid": siid, "piid": piid}], timeout=20) or []
    for e in res:
        if e.get("siid") == siid and e.get("piid") == piid and e.get("code") == 0:
            return e.get("value")
    return None


def _try_set(cloud, did, siid, piid, value, target):
    """Escribe value, sondea hasta 3 veces (6s) y dice si llego a target."""
    import time
    set_property(cloud, did, siid, piid, value)
    for i in range(3):
        time.sleep(2)
        got = _read_one(cloud, did, siid, piid)
        print(f"    lectura {i+1}: {siid}.{piid} = {got!r}")
        if got is not None and str(got) == str(target):
            return True
    return False


def validate_safe(cloud, did):
    """Alterna el modo silencio (6.17) probando int y booleano. Inofensivo."""
    vals = snapshot(cloud, did, "ANTES")
    cur = vals.get((6, 17))
    if cur is None:
        print("No pude leer 6.17; abortando validacion.")
        return
    if int(vals.get((2, 1), 0)) == 3:
        print("\n[!] AVISO: el aparato esta en SUSPENSION (2.1=3); puede ignorar escrituras.")
        print("    Despiertalo (abre la app en el dispositivo / abre-cierra la tapa) y reintenta.")
    curi = int(cur)
    newi = 0 if curi == 1 else 1
    print(f"\nModo silencio actual = {cur}. Probare ponerlo a {newi} (int y bool) y restaurar.")
    if not confirm("Continuar?"):
        return

    print("\n### Intento A: valor entero ###")
    ok_int = _try_set(cloud, did, 6, 17, newi, newi)

    ok_bool = False
    if not ok_int:
        print("\n### Intento B: valor booleano ###")
        ok_bool = _try_set(cloud, did, 6, 17, bool(newi), newi)

    if ok_int or ok_bool:
        print(f"\n[OK] La ESCRITURA FUNCIONA (via {'int' if ok_int else 'bool'}).")
    else:
        print("\n[REVISAR] La escritura NO se aplico (ni int ni bool). "
              "Probable: aparato dormido, propiedad no escribible, o requiere otra via.")

    # restaurar al valor original (probando ambos tipos por si acaso)
    set_property(cloud, did, 6, 17, curi)
    import time
    time.sleep(1)
    if _read_one(cloud, did, 6, 17) != curi:
        set_property(cloud, did, 6, 17, bool(curi))
    print(f"Intentado restaurar 6.17 a {cur}.")


def main():
    cloud, did = connect()
    snapshot(cloud, did)
    while True:
        choice = input(MENU).strip().lower()
        if choice == "q":
            break
        elif choice == "0":
            snapshot(cloud, did)
        elif choice == "1":
            validate_safe(cloud, did)
        elif choice == "2":
            try:
                siid = int(input("  siid: "))
                piid = int(input("  piid: "))
                raw = input("  valor (int, o texto): ")
                value = int(raw) if raw.lstrip("-").isdigit() else raw
            except ValueError:
                print("Entrada invalida.")
                continue
            do_write(cloud, did, siid, piid, value)
        elif choice == "3":
            try:
                siid = int(input("  siid: "))
                aiid = int(input("  aiid: "))
            except ValueError:
                print("Entrada invalida.")
                continue
            snapshot(cloud, did, "ANTES")
            if confirm("Ejecutar accion?", "CONFIRMO"):
                run_action(cloud, did, siid, aiid)
                import time
                time.sleep(2)
                snapshot(cloud, did, "DESPUES (2s)")
        elif choice == "4":
            do_write(cloud, did, 2, 10, 0, risky=True)
        elif choice == "5":
            do_write(cloud, did, 2, 10, 1, risky=True)
        elif choice == "6":
            do_write(cloud, did, 2, 3, 0, risky=True)
        elif choice == "7":
            do_write(cloud, did, 2, 3, 2, risky=True)
        elif choice == "8":
            do_write(cloud, did, 2, 3, -1, risky=True)
        else:
            print("Opcion no reconocida.")
    print("Fin.")


if __name__ == "__main__":
    main()
