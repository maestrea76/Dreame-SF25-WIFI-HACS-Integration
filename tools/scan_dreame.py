#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sonda de descubrimiento para el Dreame SF25 WiFi (dreame.fwd.u2527).

Ingenieria inversa de la nube de Dreame (Dreamehome) para un modulo de Home
Assistant. Solo usa la libreria estandar de Python: no hay que instalar nada.

Que hace:
  1. Inicia sesion en la nube de Dreame con tus credenciales de Dreamehome.
  2. Lista tus dispositivos y localiza el SF25 (dreame.fwd.u2527).
  3. Escanea el espacio de propiedades MIoT (siid x piid) del aparato.
  4. Imprime una tabla "siid.piid = valor" y guarda el volcado en un .json.

Uso:
  1. Rellena EMAIL, PASSWORD y REGION mas abajo (o pasalos por variables de
     entorno: DREAME_EMAIL, DREAME_PASSWORD, DREAME_REGION).
  2. Ejecuta:  python tools/scan_dreame.py
  3. Pega aqui la salida (o el fichero dump_*.json) para continuar el mapeo.

NOTA DE PRIVACIDAD: tus credenciales se usan solo en tu PC para hablar con la
nube de Dreame. No se envian a ningun otro sitio. Puedes usar variables de
entorno para no dejarlas escritas en el fichero.
"""

import os
import ssl
import json
import time
import getpass
import hashlib
import urllib.request
import urllib.error
import urllib.parse

# ------------------------- CONFIGURACION -------------------------------------
EMAIL = os.environ.get("DREAME_EMAIL", "TU_EMAIL_DREAMEHOME")
PASSWORD = os.environ.get("DREAME_PASSWORD", "TU_PASSWORD_DREAMEHOME")
# Region de tu cuenta: "eu" (Europa), "cn" (China), "us", "ru", "sg", "de"...
REGION = os.environ.get("DREAME_REGION", "eu")

# Rango de escaneo. Amplia si crees que faltan propiedades.
SIID_MAX = 16      # servicios 1..16
PIID_MAX = 60      # propiedades 1..60 por servicio
BATCH = 15         # la API acepta ~15 claves por peticion

TARGET_MODEL = "dreame.fwd.u2527"
# -----------------------------------------------------------------------------

# Constantes derivadas del protocolo de la app Dreamehome (para tu dispositivo).
PORT = "13267"
PWD_SALT = "RAylYC%fmSKp7%Tq"
UA = "Dreame_Smarthome/2.1.9 (iPhone; iOS 18.4.1; Scale/3.00)"
BASIC_AUTH = "Basic ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg="
DEFAULT_TENANT = "000000"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def base_url() -> str:
    return f"https://{REGION}.iot.dreame.tech:{PORT}"


def _post(path: str, headers: dict, data: bytes) -> dict:
    url = f"{base_url()}{path}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        print(f"[HTTP {e.code}] {path}: {raw[:400]}")
        try:
            return json.loads(raw)
        except Exception:
            return {}
    except Exception as e:
        print(f"[ERROR] {path}: {e}")
        return {}
    try:
        return json.loads(raw)
    except Exception:
        print(f"[WARN] respuesta no-JSON en {path}: {raw[:300]}")
        return {}


class DreameCloud:
    def __init__(self, email: str, password: str, region: str):
        self.email = email
        self.password = password
        self.region = region
        self.access_token = None
        self.tenant_id = DEFAULT_TENANT
        self.uid = None
        self.bind_host = None      # ej: "10000.mt.eu.iot.dreame.tech:19973"
        self._rpc_id = 1

    def login(self) -> bool:
        pwd_hash = hashlib.md5((self.password + PWD_SALT).encode("utf-8")).hexdigest()
        body = (
            "platform=IOS&scope=all&grant_type=password"
            f"&username={urllib.parse.quote(self.email)}"
            f"&password={pwd_hash}&type=account"
        )
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Language": "en-US;q=0.8",
            "User-Agent": UA,
            "Authorization": BASIC_AUTH,
            "Tenant-Id": DEFAULT_TENANT,
        }
        data = self._post_raw("/dreame-auth/oauth/token", headers, body.encode("utf-8"))
        if "access_token" in data:
            self.access_token = data["access_token"]
            self.tenant_id = data.get("tenant_id", DEFAULT_TENANT)
            self.uid = data.get("uid")
            print(f"[OK] Login correcto. uid={self.uid} tenant={self.tenant_id}")
            return True
        print(f"[FALLO] Login: {json.dumps(data)[:400]}")
        return False

    def _post_raw(self, path: str, headers: dict, data: bytes) -> dict:
        return _post(path, headers, data)

    def _auth_headers(self) -> dict:
        return {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "User-Agent": UA,
            "Authorization": BASIC_AUTH,
            "Tenant-Id": self.tenant_id or DEFAULT_TENANT,
            "Dreame-Auth": self.access_token,
        }

    def _api(self, path: str, params=None) -> dict:
        data = json.dumps(params, separators=(",", ":")).encode("utf-8") if params is not None else b""
        return _post(path, self._auth_headers(), data)

    def list_devices(self) -> list:
        resp = self._api("/dreame-user-iot/iotuserbind/device/listV2")
        if resp.get("code") == 0 and "data" in resp:
            return list(resp["data"].get("page", {}).get("records", []))
        print(f"[WARN] listV2: {json.dumps(resp)[:400]}")
        return []

    def get_props(self, did: str, keys: list) -> list:
        resp = self._api("/dreame-user-iot/iotstatus/props", {"did": str(did), "keys": keys})
        if "data" in resp:
            return resp["data"]
        return []

    # --- endpoints extra para diagnostico ---
    def raw(self, path: str, params) -> dict:
        return self._api(path, params)

    def device_info(self, did: str) -> dict:
        return self._api("/dreame-user-iot/iotuserbind/device/info", {"did": str(did)})

    def dev_otc_info(self, did: str) -> dict:
        return self._api("/dreame-user-iot/iotstatus/devOTCInfo", {"did": str(did)})

    def get_device_data(self, did: str, props) -> dict:
        # ojo: la clave del body es "model" (asi lo usa la app), el valor es la lista de props
        return self._api("/dreame-user-iot/iotuserdata/getDeviceData", {"did": str(did), "model": props})

    def _rpc_path(self) -> str:
        host = ""
        if self.bind_host:
            host = f"-{self.bind_host.split('.')[0]}"   # bindDomain empieza por "10000"
        return f"/dreame-iot-com{host}/device/sendCommand"

    def send_rpc_raw(self, did: str, method: str, params, timeout: int = 15) -> dict:
        """RPC MIoT nube->dispositivo. Devuelve la respuesta cruda completa."""
        self._rpc_id += 1
        body = {
            "did": str(did),
            "id": self._rpc_id,
            "data": {"did": str(did), "id": self._rpc_id, "method": method, "params": params},
        }
        return self._api(self._rpc_path(), body)

    def send_rpc(self, did: str, method: str, params, timeout: int = 15):
        """Como send_rpc_raw pero devuelve solo data.result (o None)."""
        resp = self.send_rpc_raw(did, method, params, timeout)
        if resp and isinstance(resp.get("data"), dict) and "result" in resp["data"]:
            return resp["data"]["result"]
        return None


def _show(title: str, obj) -> None:
    s = json.dumps(obj, ensure_ascii=False, indent=2)
    if len(s) > 2500:
        s = s[:2500] + "\n... (truncado)"
    print(f"\n----- {title} -----\n{s}")


def diagnose(cloud: DreameCloud, did: str) -> dict:
    """Vuelca respuestas crudas de varios endpoints/formatos para ver donde
    esta el estado y con que formato de 'keys' responde este MCU."""
    print("\n########## DIAGNOSTICO (respuestas crudas) ##########")
    diag = {}

    # 1) device/info y devOTCInfo suelen traer el estado actual embebido
    diag["device_info"] = cloud.device_info(did)
    _show("device/info", diag["device_info"])
    diag["devOTCInfo"] = cloud.dev_otc_info(did)
    _show("iotstatus/devOTCInfo", diag["devOTCInfo"])

    # 2) props con distintos formatos de keys (siid 2, piid 1..6)
    sample = [(2, p) for p in range(1, 7)] + [(3, p) for p in range(1, 4)]
    fmt_a = [{"did": f"{s}.{p}", "siid": s, "piid": p} for s, p in sample]
    fmt_b = [f"{s}.{p}" for s, p in sample]
    fmt_c = [{"siid": s, "piid": p} for s, p in sample]
    diag["props_fmtA_dict"] = cloud.raw("/dreame-user-iot/iotstatus/props", {"did": str(did), "keys": fmt_a})
    _show("props (fmt A: [{did,siid,piid}])", diag["props_fmtA_dict"])
    diag["props_fmtB_str"] = cloud.raw("/dreame-user-iot/iotstatus/props", {"did": str(did), "keys": fmt_b})
    _show("props (fmt B: ['siid.piid'])", diag["props_fmtB_str"])
    diag["props_fmtC_nodid"] = cloud.raw("/dreame-user-iot/iotstatus/props", {"did": str(did), "keys": fmt_c})
    _show("props (fmt C: [{siid,piid}])", diag["props_fmtC_nodid"])

    # 3) getDeviceData (iotuserdata)
    diag["getDeviceData"] = cloud.get_device_data(did, fmt_a)
    _show("iotuserdata/getDeviceData", diag["getDeviceData"])

    # 4) RPC MIoT via sendCommand (la via prometedora para dispositivos MCU online)
    rpc_params = [{"did": f"{s}.{p}", "siid": s, "piid": p} for s, p in sample]
    diag["rpc_get_properties"] = cloud.send_rpc_raw(did, "get_properties", rpc_params, timeout=20)
    _show("sendCommand get_properties (RPC nube->dispositivo)", diag["rpc_get_properties"])

    print("\n########## FIN DIAGNOSTICO ##########")
    return diag


def scan_properties(cloud: DreameCloud, did: str) -> list:
    """Escanea siid x piid via RPC get_properties (nube->dispositivo)."""
    all_keys = [
        {"did": f"{s}.{p}", "siid": s, "piid": p}
        for s in range(1, SIID_MAX + 1)
        for p in range(1, PIID_MAX + 1)
    ]
    found = []
    total = len(all_keys)
    for i in range(0, total, BATCH):
        chunk = all_keys[i:i + BATCH]
        result = cloud.send_rpc(did, "get_properties", chunk, timeout=20)
        for entry in result or []:
            # code 0 = ok; guardamos las que devuelven valor
            if entry.get("code") == 0 and "value" in entry:
                found.append(entry)
        print(f"  escaneadas {min(i + BATCH, total)}/{total} claves...", end="\r")
        time.sleep(0.1)
    print()
    return found


def main():
    email = EMAIL
    password = PASSWORD
    # Pedir por teclado si no vienen (o vienen con el placeholder). Asi evitamos
    # el escapado de PowerShell: $ , & , etc. se envian tal cual se teclean.
    if "TU_EMAIL" in email:
        entered = input("Email de Dreamehome: ").strip()
        if entered:
            email = entered
    if "TU_PASSWORD" in password:
        password = getpass.getpass("Contrasena de Dreamehome (no se vera): ")

    # --- Verificacion previa SIN contactar al servidor (no gasta intentos) ---
    last = password[-1] if password else ""
    print("\n--- Comprobacion de la contrasena (local, no se envia nada) ---")
    print(f"  Longitud: {len(password)} caracteres")
    print(f"  Primer caracter: {password[:1]!r}   Ultimo caracter: {last!r}")
    print("  (Debe ser 15 caracteres y terminar en '3'.)")
    ans = input("Escribe SI (mayusculas) para lanzar el login, cualquier otra cosa cancela: ").strip()
    if ans != "SI":
        print("Cancelado. No se ha gastado ningun intento.")
        return

    print(f"\n== Nube Dreame: {base_url()} (region {REGION}) ==")
    cloud = DreameCloud(email, password, REGION)
    if not cloud.login():
        print("Revisa credenciales y region. Regiones tipicas: eu, cn, us, ru, sg, de.")
        return

    devices = cloud.list_devices()
    print(f"[OK] {len(devices)} dispositivo(s) en la cuenta:")
    target = None
    for d in devices:
        model = d.get("model")
        name = d.get("customName") or d.get("deviceInfo", {}).get("displayName") or "?"
        print(f"   - {model:24s} did={d.get('did')} mac={d.get('mac')} nombre={name}")
        if model == TARGET_MODEL or (model and "u2527" in model):
            target = d

    if not target:
        print(f"[FALLO] No encuentro {TARGET_MODEL}. Revisa la region de la cuenta.")
        return

    did = str(target.get("did"))
    cloud.bind_host = target.get("bindDomain")  # necesario para el RPC sendCommand
    print(f"\n== Escaneando {TARGET_MODEL} (did={did}) ==")
    print(f"   host/bindDomain: {cloud.bind_host}")

    diag = diagnose(cloud, did)

    props = scan_properties(cloud, did)
    props.sort(key=lambda e: (e.get("siid", 0), e.get("piid", 0)))

    print(f"\n== {len(props)} propiedades encontradas ==")
    print(f"{'siid.piid':>10}  {'tipo':<8}  valor")
    print("-" * 60)
    for e in props:
        v = e.get("value")
        t = type(v).__name__
        vs = json.dumps(v, ensure_ascii=False)
        if len(vs) > 60:
            vs = vs[:57] + "..."
        print(f"{e['siid']:>4}.{e['piid']:<4}  {t:<8}  {vs}")

    out = {
        "model": TARGET_MODEL,
        "did": did,
        "mac": target.get("mac"),
        "bindDomain": target.get("bindDomain"),
        "firmware": target.get("deviceInfo", {}).get("firmwareVersion"),
        "device_record": target,
        "properties": props,
        "diagnostico": diag,
    }
    fname = f"dump_{TARGET_MODEL.replace('.', '_')}_{int(time.time())}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Volcado guardado en: {fname}")
    print("Pega la tabla de arriba (o el .json) para continuar el mapeo semantico.")


if __name__ == "__main__":
    main()
