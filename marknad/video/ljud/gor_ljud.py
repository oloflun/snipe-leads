#!/usr/bin/env python3
"""Ljudspåret till reelen, syntetiserat från grunden: ingen annans musik.

Allt är låst till filmens bildrutor (30 fps) så att varje slag, klick, tick
och pling landar på sin händelse i bild. Tidslinjen speglar src/Film.tsx:

    krok     0–60     tre slag
    korning  60–270   puls börjar, klick vid 90/180/240, stigning mot 270
    pang     270–390  smäll, 50 tick i räknarens takt, punch vid 315
    utkast   390–540  bockar, skrivljud, klick vid 510 och svisch
    svar     540–690  30 plingar i accelererande rytm
    slut     690–795  slutslag, varmt ackord, tvärstopp

    python ljud/gor_ljud.py            # skriver public/ljud.wav
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

FPS = 30
SR = 48_000
LANGD_RUTOR = 795
UT = Path(__file__).resolve().parent.parent / "public" / "ljud.wav"

rng = np.random.default_rng(7)
N = int(LANGD_RUTOR / FPS * SR)
mix = np.zeros((N, 2), dtype=np.float64)


def s(frame: float) -> int:
    return int(frame / FPS * SR)


def lagg(start_frame: float, ljud: np.ndarray, niva: float = 1.0, pan: float = 0.0) -> None:
    i = s(start_frame)
    j = min(N, i + len(ljud))
    if i >= N:
        return
    del_ = ljud[: j - i] * niva
    v = math.sqrt(0.5 * (1 - pan))
    h = math.sqrt(0.5 * (1 + pan))
    mix[i:j, 0] += del_ * v * 1.414
    mix[i:j, 1] += del_ * h * 1.414


def env(n: int, attack: float, decay: float, kurva: float = 4.0) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.exp(-t / max(decay, 1e-4) * kurva)
    return a * d


def ton(frek: float, langd: float, attack: float = 0.004, decay: float = 0.3, overtoner=(1.0, 0.35, 0.12)) -> np.ndarray:
    n = int(langd * SR)
    t = np.arange(n) / SR
    v = sum(a * np.sin(2 * np.pi * frek * (k + 1) * t) for k, a in enumerate(overtoner))
    return v * env(n, attack, decay)


def brus(langd: float, attack: float, decay: float, lag: float = 0.0, hog: float = 1.0) -> np.ndarray:
    n = int(langd * SR)
    v = rng.standard_normal(n)
    # Enkelt bandpass genom två glidande medelvärden.
    if lag > 0:
        k = max(1, int(SR * lag))
        v = v - np.convolve(v, np.ones(k) / k, mode="same")
    if hog < 1.0:
        k = max(1, int(1 / (hog * 8000) * SR))
        v = np.convolve(v, np.ones(k) / k, mode="same")
    return v * env(n, attack, decay)


def kick(langd: float = 0.35) -> np.ndarray:
    n = int(langd * SR)
    t = np.arange(n) / SR
    frek = 42 + 120 * np.exp(-t * 28)
    fas = np.cumsum(2 * np.pi * frek / SR)
    return np.sin(fas) * env(n, 0.001, 0.22, 5)


def slag(langd: float = 0.6) -> np.ndarray:
    """Krokens slag: kick plus en kort brusexplosion."""
    k = kick(langd)
    b = brus(langd, 0.001, 0.08, lag=0.0004)[: len(k)] * 0.5
    return k * 1.0 + b


def hatt() -> np.ndarray:
    return brus(0.06, 0.001, 0.02, lag=0.0002) * 0.5


def klick() -> np.ndarray:
    return brus(0.04, 0.0005, 0.012, lag=0.0003) * 0.9 + ton(1800, 0.04, 0.001, 0.01) * 0.3


def tick(frek: float = 2600.0) -> np.ndarray:
    return ton(frek, 0.05, 0.001, 0.02, overtoner=(1.0, 0.2)) * 0.5


def tangent() -> np.ndarray:
    return brus(0.03, 0.0005, 0.01, lag=0.0004) * 0.35


def pling(frek: float) -> np.ndarray:
    return ton(frek, 0.5, 0.002, 0.18, overtoner=(1.0, 0.5, 0.0, 0.15)) * 0.5 + ton(frek * 2.0, 0.5, 0.002, 0.1, overtoner=(1.0,)) * 0.15


def stigning(langd: float) -> np.ndarray:
    n = int(langd * SR)
    t = np.arange(n) / SR
    v = rng.standard_normal(n)
    k = 400
    v = v - np.convolve(v, np.ones(k) / k, mode="same")
    stig = (t / langd) ** 2.2
    frek = 120 + 1400 * stig
    fas = np.cumsum(2 * np.pi * frek / SR)
    return (v * 0.35 + np.sin(fas) * 0.25) * stig


def smaell() -> np.ndarray:
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    frek = 30 + 200 * np.exp(-t * 18)
    fas = np.cumsum(2 * np.pi * frek / SR)
    sub = np.sin(fas) * env(n, 0.001, 0.6, 4)
    b = brus(1.4, 0.001, 0.25, lag=0.0006) * 0.6
    return sub * 1.2 + b


def svisch(langd: float = 0.6) -> np.ndarray:
    n = int(langd * SR)
    t = np.arange(n) / SR
    v = rng.standard_normal(n)
    k = 60
    v = v - np.convolve(v, np.ones(k) / k, mode="same")
    form = np.sin(np.pi * np.clip(t / langd, 0, 1)) ** 2
    return v * form * 0.4


def pluck(frek: float, langd: float = 0.35) -> np.ndarray:
    n = int(langd * SR)
    t = np.arange(n) / SR
    v = np.sin(2 * np.pi * frek * t) + 0.3 * np.sin(2 * np.pi * frek * 2 * t) + 0.08 * np.sin(2 * np.pi * frek * 3 * t)
    return v * env(n, 0.003, 0.16, 4)


def bas(frek: float, langd: float = 0.5) -> np.ndarray:
    n = int(langd * SR)
    t = np.arange(n) / SR
    v = np.sin(2 * np.pi * frek * t) + 0.25 * np.sin(2 * np.pi * frek * 2 * t)
    return v * env(n, 0.005, 0.5, 3)


def ackord(frekvenser, langd: float) -> np.ndarray:
    n = int(langd * SR)
    t = np.arange(n) / SR
    v = np.zeros(n)
    for f in frekvenser:
        v += np.sin(2 * np.pi * f * t) * 0.5 + np.sin(2 * np.pi * f * 2 * t + 0.3) * 0.12
    e = np.clip(t / 0.15, 0, 1) * np.exp(-t / langd * 2.4)
    return v * e / len(frekvenser)


# -- Kroken: tre slag -------------------------------------------------------
for f in (0, 15, 30):
    lagg(f, slag(), 0.9)
# Räknaren 0→50 i första raden: snabba tick.
for i in range(12):
    lagg(i, tick(2000 + i * 60), 0.12, pan=-0.3)

# -- Pulsen: 120 bpm från körningen till slutet ---------------------------------
A1, C2, F1, G1 = 55.0, 65.41, 43.65, 49.0
progression = [A1, A1, F1, F1, C2, C2, G1, G1]  # en ton per slag, två takter
for n_slag, f in enumerate(range(60, 690, 15)):
    styrka = 0.55 if f < 270 else 0.75
    lagg(f, kick(), styrka)
    lagg(f + 7.5, hatt(), 0.35 if f < 270 else 0.5, pan=0.25)
    lagg(f, bas(progression[(n_slag // 2) % 8]), 0.5 if f < 270 else 0.62)

# Pluckarpeggio efter smällen, åttondelar, A-moll.
arp = [220.0, 261.63, 329.63, 392.0, 329.63, 261.63]
k = 0
f = 270.0
while f < 690:
    lagg(f, pluck(arp[k % len(arp)]), 0.16, pan=0.35 if k % 2 else -0.35)
    k += 1
    f += 7.5

# -- Körningen: klick, tangenter, stigning ----------------------------------------
for f in (90, 180, 240):
    lagg(f, klick(), 0.9)
for f in range(120, 144, 3):  # Göteborg
    lagg(f, tangent(), 0.8, pan=-0.2)
for f in range(156, 168, 3):  # Bygg
    lagg(f, tangent(), 0.8, pan=-0.2)
lagg(170, klick(), 0.6)  # chip
for f in range(190, 210, 2):  # reglaget dras
    lagg(f, tick(900 + (f - 190) * 40), 0.15)
lagg(240, stigning(1.0), 0.9)

# -- PANG: smäll, 50 tick i räknarens takt, punch -------------------------------
lagg(270, smaell(), 1.0)


def antal_vid(fr: float) -> float:
    t = min(1.0, max(0.0, (fr - 4) / 41))
    return 50 * (1 - (1 - t) ** 3)


senast = -1
for fr in range(270, 320):
    n_nu = int(antal_vid(fr - 270))
    if n_nu > senast:
        for _ in range(n_nu - senast):
            lagg(fr, tick(1800 + n_nu * 24), 0.22, pan=((n_nu % 5) - 2) * 0.2)
        senast = n_nu
lagg(315, slag(0.5), 0.8)
for i in range(3):  # chips
    lagg(322 + i * 4, klick(), 0.35)

# -- Utkasten --------------------------------------------------------------------
for i in range(10):
    lagg(394 + i * 2.4, tick(2400 + i * 90), 0.3, pan=0.4)
lagg(420, svisch(0.35), 0.6)
for fr in range(430, 480, 2):
    lagg(fr, tangent(), 0.5, pan=0.1)
lagg(480, pling(1046.5), 0.35)
lagg(510, klick(), 1.0)
lagg(511, svisch(0.7), 1.0)
for i in range(14):
    lagg(511 + i * 1.4, tick(1400 + i * 60), 0.12, pan=0.5)

# -- Svaren: 30 plingar, stigande, allt tätare -------------------------------------
ankomster = [round(8 + 124 * (i / 29) ** 0.6) for i in range(30)]
skala = [659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.5]
for i, a in enumerate(ankomster):
    lagg(540 + a, pling(skala[i % len(skala)] * (1 + (i // 6) * 0.0)), 0.55 if i < 20 else 0.42, pan=((i % 3) - 1) * 0.45)
lagg(540 + ankomster[-1] + 2, slag(0.5), 0.7)

# -- Slutet: slag, varmt ackord, tvärstopp -----------------------------------------
lagg(690, slag(0.8), 1.0)
lagg(690, ackord([220.0, 277.18, 329.63, 440.0], 3.2), 0.6)
lagg(696, pling(1318.5), 0.3)

# -- Mastring: mjuk begränsning, normalisering, tvärstopp på sista rutan -----------
mix = np.tanh(mix * 0.9) / math.tanh(0.9)
mix /= max(1e-9, np.max(np.abs(mix)))
mix *= 10 ** (-5.5 / 20)
# Sista 3 bildrutorna: snabb nedtoning så att inget knäpper i klippet.
svans = int(3 / FPS * SR)
mix[-svans:] *= np.linspace(1, 0, svans)[:, None]

UT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(UT), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print(f"Skrev {UT} ({LANGD_RUTOR / FPS:.1f} s)")
