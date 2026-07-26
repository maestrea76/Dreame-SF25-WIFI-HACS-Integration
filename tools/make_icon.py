#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera el icono PNG del SF25 (sin dependencias externas).

Dibuja el mismo diseno que icon.svg (insignia verde + hoja de compost) con
supersampling y lo exporta a PNG RGBA transparente en 256 y 512 px.

Salida:
  brands/dreame_sf25/icon.png     (256x256)
  brands/dreame_sf25/icon@2x.png  (512x512)
"""
from __future__ import annotations

import math
import os
import struct
import zlib

S = 1024  # resolucion de render (supersampling)


def _lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _rounded_rect(x, y, w, h, r):
    # coverage 0/1 de un rectangulo redondeado [0,w]x[0,h] con radio r
    if x < 0 or y < 0 or x > w or y > h:
        return False
    rx = min(x, w - x)
    ry = min(y, h - y)
    if rx >= r or ry >= r:
        return True
    dx = r - rx
    dy = r - ry
    return dx * dx + dy * dy <= r * r


def render(size: int) -> bytes:
    scale = S / 256.0
    # colores
    top = (0x3F, 0xA6, 0x6A)
    bot = (0x2B, 0x7D, 0x4D)
    leaf_col = (0xEA, 0xFF, 0xF0)
    rib_col = (0x2B, 0x7D, 0x4D)

    # circulos de la hoja (en coords 0..256)
    c1 = (88.0, 168.0, 96.0)
    c2 = (168.0, 88.0, 96.0)
    # nervio central: segmento (73,73)-(183,183)
    rib_a = (73.0, 73.0)
    rib_b = (183.0, 183.0)

    def in_circle(px, py, c):
        return (px - c[0]) ** 2 + (py - c[1]) ** 2 <= c[2] ** 2

    def dist_seg(px, py, a, b):
        vx, vy = b[0] - a[0], b[1] - a[1]
        wx, wy = px - a[0], py - a[1]
        t = (wx * vx + wy * vy) / (vx * vx + vy * vy)
        t = max(0.0, min(1.0, t))
        cx, cy = a[0] + t * vx, a[1] + t * vy
        return math.hypot(px - cx, py - cy)

    # render supersampled -> RGBA
    hi = bytearray(S * S * 4)
    for j in range(S):
        py = (j + 0.5) / scale
        row = j * S * 4
        # gradiente vertical del fondo
        grad = _lerp(top, bot, py / 256.0)
        for i in range(S):
            px = (i + 0.5) / scale
            o = row + i * 4
            if not _rounded_rect(px, py, 256.0, 256.0, 52.0):
                continue  # transparente
            # fondo
            r, g, b = grad
            a = 255
            # hoja = interseccion de los dos circulos
            if in_circle(px, py, c1) and in_circle(px, py, c2):
                if dist_seg(px, py, rib_a, rib_b) <= 3.0:
                    r, g, b = rib_col
                else:
                    r, g, b = leaf_col
            hi[o] = r
            hi[o + 1] = g
            hi[o + 2] = b
            hi[o + 3] = a

    # downsample por bloques promediando (RGBA recto)
    block = S // size
    out = bytearray(size * size * 4)
    n = block * block
    for oy in range(size):
        for ox in range(size):
            sr = sg = sb = sa = 0
            for by in range(block):
                base = ((oy * block + by) * S + ox * block) * 4
                for bx in range(block):
                    p = base + bx * 4
                    sr += hi[p]; sg += hi[p + 1]; sb += hi[p + 2]; sa += hi[p + 3]
            oo = (oy * size + ox) * 4
            out[oo] = sr // n
            out[oo + 1] = sg // n
            out[oo + 2] = sb // n
            out[oo + 3] = sa // n
    return _png(bytes(out), size, size)


def _png(rgba: bytes, w: int, h: int) -> bytes:
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)  # filtro None
        raw += rgba[y * stride:(y + 1) * stride]
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")


def main():
    os.makedirs("brands/dreame_sf25", exist_ok=True)
    for size, name in [(256, "brands/dreame_sf25/icon.png"), (512, "brands/dreame_sf25/icon@2x.png")]:
        with open(name, "wb") as f:
            f.write(render(size))
        print("OK", name, f"{size}x{size}")


if __name__ == "__main__":
    main()
