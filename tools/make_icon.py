#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera el icono PNG del Dreame SF25 (sin dependencias externas).

Dibuja una representacion del aparato: cuerpo vertical blanco, tapa cuadrada
abierta e inclinada con ventana redonda, y la abertura circular superior.
Exporta PNG RGBA en 256 y 512 px (supersampling).

Salida:
  brands/dreame_sf25/icon.png     (256x256)
  brands/dreame_sf25/icon@2x.png  (512x512)
"""
from __future__ import annotations

import math
import os
import struct
import zlib

S = 1024  # resolucion de render (supersampling desde 256)
K = S / 256.0

# --- colores ---
BG_TOP = (0x3F, 0xA6, 0x6A)
BG_BOT = (0x2B, 0x7D, 0x4D)
WHITE = (0xFB, 0xFD, 0xFE)
BORDER = (0xD5, 0xDB, 0xDF)
RIM = (0xC9, 0xD0, 0xD5)
HOLE = (0x33, 0x38, 0x3D)
WINDOW = (0xEC, 0xF1, 0xF4)


def _lerp(a, b, t):
    return (round(a[0] + (b[0] - a[0]) * t),
            round(a[1] + (b[1] - a[1]) * t),
            round(a[2] + (b[2] - a[2]) * t))


def _rrect(px, py, cx, cy, hw, hh, r, ang=0.0):
    """Dentro de un rect redondeado centrado en (cx,cy) rotado ang grados."""
    dx = px - cx
    dy = py - cy
    if ang:
        a = math.radians(ang)
        c, s = math.cos(a), math.sin(a)
        dx, dy = dx * c + dy * s, -dx * s + dy * c
    dx, dy = abs(dx), abs(dy)
    if dx > hw or dy > hh:
        return False
    ox = dx - (hw - r)
    oy = dy - (hh - r)
    if ox <= 0 or oy <= 0:
        return True
    return ox * ox + oy * oy <= r * r


def _circle(px, py, cx, cy, r):
    return (px - cx) ** 2 + (py - cy) ** 2 <= r * r


def _ellipse(px, py, cx, cy, rx, ry):
    return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1.0


def _pixel(px, py):
    """Color RGBA (o None si transparente) del punto (px,py) en coords 0..256."""
    if not _rrect(px, py, 128, 128, 128, 128, 52):
        return None
    col = _lerp(BG_TOP, BG_BOT, py / 256.0)  # fondo

    # tapa abierta e inclinada (centro 142,66, girada -16 grados)
    lc = (142.0, 66.0)
    if _rrect(px, py, lc[0], lc[1], 40, 40, 13, -16):
        col = BORDER
    if _rrect(px, py, lc[0], lc[1], 38, 38, 12, -16):
        col = WHITE
        # ventana redonda de la tapa
        if _circle(px, py, lc[0], lc[1], 27):
            col = RIM
        if _circle(px, py, lc[0], lc[1], 19):
            col = WINDOW

    # bisagra
    if _rrect(px, py, 124, 108, 12, 10, 4):
        col = RIM

    # cuerpo del aparato (rect redondeado vertical)
    if _rrect(px, py, 128, 156, 44, 44, 16):
        col = WHITE

    # abertura circular superior (elipse en perspectiva)
    if _ellipse(px, py, 128, 112, 33, 14):
        col = RIM
    if _ellipse(px, py, 128, 112, 23, 10):
        col = HOLE

    return (col[0], col[1], col[2], 255)


def render_hi() -> bytearray:
    hi = bytearray(S * S * 4)
    for j in range(S):
        py = (j + 0.5) / K
        row = j * S * 4
        for i in range(S):
            c = _pixel((i + 0.5) / K, py)
            if c is None:
                continue
            o = row + i * 4
            hi[o] = c[0]; hi[o + 1] = c[1]; hi[o + 2] = c[2]; hi[o + 3] = c[3]
    return hi


def downsample(hi: bytearray, size: int) -> bytes:
    block = S // size
    n = block * block
    out = bytearray(size * size * 4)
    for oy in range(size):
        for ox in range(size):
            sr = sg = sb = sa = 0
            for by in range(block):
                base = ((oy * block + by) * S + ox * block) * 4
                for bx in range(block):
                    p = base + bx * 4
                    sr += hi[p]; sg += hi[p + 1]; sb += hi[p + 2]; sa += hi[p + 3]
            oo = (oy * size + ox) * 4
            out[oo] = sr // n; out[oo + 1] = sg // n
            out[oo + 2] = sb // n; out[oo + 3] = sa // n
    return _png(bytes(out), size, size)


def _png(rgba: bytes, w: int, h: int) -> bytes:
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    os.makedirs("brands/dreame_sf25", exist_ok=True)
    hi = render_hi()
    for size, name in [(256, "brands/dreame_sf25/icon.png"), (512, "brands/dreame_sf25/icon@2x.png")]:
        with open(name, "wb") as f:
            f.write(downsample(hi, size))
        print("OK", name, f"{size}x{size}")


if __name__ == "__main__":
    main()
