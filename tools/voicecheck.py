# 声のそろい具合を調べる・直すための小さな道具
# Gemini は原稿を約3分ずつに分けて読み上げるため、区切りごとに声の高さが変わることがある。
# ここでは各区切りの「声の高さ（基本周波数の中央値）」を測り、ずれを見つけて補正する。
import subprocess

try:
    import numpy as np
except ImportError:  # numpy が無い環境では何もしない
    np = None

SR = 24000


def pitch(pcm):
    """16bit/24kHz モノラル PCM の声の高さ（Hz の中央値）。測れなければ None。"""
    if np is None or not pcm:
        return None
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
    x = x[::2]  # 12kHz に間引いて速くする
    sr = SR // 2
    W, H = int(sr * 0.04), int(sr * 0.02)
    lo, hi = int(sr / 400), int(sr / 100)
    n = (len(x) - W) // H
    if n < 50:
        return None
    fr = np.lib.stride_tricks.sliding_window_view(x, W)[::H][:n].copy()
    fr -= fr.mean(1, keepdims=True)
    loud = np.sqrt((fr ** 2).mean(1)) > 0.02
    fr = fr[loud]
    if len(fr) < 50:
        return None
    spec = np.fft.rfft(fr * np.hanning(W), n=2 * W)
    ac = np.fft.irfft(np.abs(spec) ** 2)[:, :W]
    k = lo + np.argmax(ac[:, lo:hi], axis=1)
    strength = ac[np.arange(len(ac)), k] / (ac[:, 0] + 1e-9)
    f0 = sr / k[strength > 0.5]
    return float(np.median(f0)) if len(f0) >= 30 else None


def shift(pcm, ratio):
    """長さを変えずに声の高さだけ ratio 倍にする（ratio は 0.9〜1.1 程度を想定）。"""
    p = subprocess.run(
        ['ffmpeg', '-loglevel', 'error', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-',
         '-af', f'asetrate={SR * ratio:.1f},aresample={SR},atempo={1 / ratio:.5f}',
         '-f', 's16le', '-ar', str(SR), '-ac', '1', '-'],
        input=pcm, capture_output=True, check=True)
    return p.stdout
