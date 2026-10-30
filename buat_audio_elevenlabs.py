#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buat_audio_elevenlabs.py  —  Pembuat suara (mp3) pakai ElevenLabs
untuk game "Petualangan Kata Rahasia"

Hasilnya sama dengan buat_audio.py:
    audio/en/<kata>.mp3     audio/id/<kalimat>.mp3
Jadi index.html tidak perlu diubah. Tidak perlu install apa-apa (hanya Python).

CARA PAKAI:
  1. Daftar di elevenlabs.io, lalu ambil API key
     (Profile -> API Keys -> Create).
  2. Taruh file ini SEJAJAR dengan index.html.
  3. Jalankan (ganti KUNCI_KAMU dengan API key):
       Windows (cmd):   set ELEVENLABS_API_KEY=KUNCI_KAMU
                        python buat_audio_elevenlabs.py
       Mac / Linux:     export ELEVENLABS_API_KEY=KUNCI_KAMU
                        python3 buat_audio_elevenlabs.py
  4. Upload folder "audio" bareng index.html.

Pilihan:
  --list                 lihat daftar + total karakter (tanpa API key, tanpa internet)
  --force                bikin ulang semua file
  --voice-en ID          ganti suara (ID dari Voice Library ElevenLabs) untuk Inggris
  --voice-id ID          ganti suara untuk Indonesia
  --model NAMA           default eleven_multilingual_v2 (kualitas terbaik)
                         eleven_flash_v2_5 = lebih hemat kredit (separuh harga)
"""
import argparse, json, os, pathlib, re, sys, time
import urllib.request, urllib.error

HERE = pathlib.Path(__file__).resolve().parent
HTML = HERE / "index.html"
OUT = HERE / "audio"

# Suara bawaan ElevenLabs ("Rachel"). Ganti dengan suara pilihanmu lewat --voice-en / --voice-id
DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"


def slug(s):
    """HARUS sama dengan slug() di index.html."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def kumpulkan_frasa(html):
    frasa = {}
    def tambah(lang, teks):
        frasa[(lang, slug(teks))] = (lang, teks)
    pola = r"""word\s*:\s*(["'])([^"']+)\1\s*,\s*meaning\s*:\s*(["'])([^"']+)\3"""
    for _, kata, _, arti in re.findall(pola, html):
        tambah("en", kata)
        tambah("id", "artinya " + arti)
    for _, petunjuk in re.findall(r"""clue\s*:\s*(["'])(.+?)\1""", html):
        tambah("id", petunjuk)
    for t in ("Cari", "Hebat!", "Bukan itu. Cari"):
        tambah("id", t)
    return sorted(frasa.values(), key=lambda x: (x[0], x[1].lower()))


def tts(teks, voice, model, key):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"
    body = json.dumps({
        "text": teks,
        "model_id": model,
        "voice_settings": {"stability": 0.55, "similarity_boost": 0.75, "speed": 0.9},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--voice-en", default=DEFAULT_VOICE)
    ap.add_argument("--voice-id", default=DEFAULT_VOICE)
    ap.add_argument("--model", default="eleven_multilingual_v2")
    a = ap.parse_args()

    if not HTML.exists():
        sys.exit("index.html tidak ketemu. Taruh script ini sejajar dengan index.html ya.")
    frasa = kumpulkan_frasa(HTML.read_text(encoding="utf-8"))
    total = sum(len(t) for _, t in frasa)
    print(f"Ditemukan {len(frasa)} suara, total {total} karakter (≈ {total} kredit ElevenLabs).")

    if a.list:
        for lang, teks in frasa:
            print(f"  [{lang}] {teks}  ->  audio/{lang}/{slug(teks)}.mp3")
        return

    key = os.environ.get("cc03e1dd00359fb4130c431f5b2511e57d2ca67ebcbbc9a0ebfbc5f560de808f", "").strip()
    if not key:
        sys.exit("API key belum diisi. Lihat cara pakai di bagian atas file ini (set ELEVENLABS_API_KEY=...).")

    ok = skip = 0
    gagal = []
    for i, (lang, teks) in enumerate(frasa, 1):
        path = OUT / lang / (slug(teks) + ".mp3")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not a.force:
            skip += 1
            continue
        voice = a.voice_en if lang == "en" else a.voice_id
        err = ""
        for percobaan in range(1, 4):
            try:
                data = tts(teks, voice, a.model, key)
                if len(data) > 500:
                    path.write_bytes(data)
                    ok += 1
                    print(f"[{i}/{len(frasa)}] ok  [{lang}] {teks}")
                    break
            except urllib.error.HTTPError as e:
                err = f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:120]}"
                if e.code in (401, 402, 403):   # key salah / kredit habis -> berhenti
                    sys.exit("Berhenti. " + err)
            except Exception as e:
                err = str(e)
            time.sleep(2 * percobaan)
        else:
            gagal.append((lang, teks, err))
        time.sleep(0.3)

    print(f"\nSelesai: {ok} dibuat, {skip} sudah ada, {len(gagal)} gagal.")
    for lang, teks, err in gagal:
        print(f"  gagal [{lang}] {teks}  ({err})")
    if not gagal:
        print("Mantap! Upload folder 'audio' bareng index.html.")


if __name__ == "__main__":
    main()
