"""One voice request to the Gemini API (TTS) and its WAV.

Usage (the key comes only from the environment; it never goes on the command line):
    export GEMINI_API_KEY first, for example from an env file kept outside the repository:
    set -a; source <your env file>; set +a
    venv/bin/python -I tts.py <model> <voice> <text_file> <out.wav>

- The key is read from GEMINI_API_KEY and travels only in the x-goog-api-key header.
- It is never printed or stored: error messages are scrubbed in case they contain it.
- Every request is logged in requests.json next to this script (time, model, voice, status, duration), without the key.
- No retries: a 429 or any other error is reported and the script stops.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
REQUEST_LOG = os.path.join(HERE, "requests.json")


def log_request(entry):
    data = json.load(open(REQUEST_LOG)) if os.path.exists(REQUEST_LOG) else []
    data.append(entry)
    json.dump(data, open(REQUEST_LOG, "w"), indent=1, ensure_ascii=False)


def scrub(text, key):
    return text.replace(key, "[key]") if key else text


def main():
    model, voice, text_path, out = sys.argv[1:5]
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("GEMINI_API_KEY is missing from the environment")
        sys.exit(2)
    text = open(text_path, encoding="utf-8").read()
    body = {
        "contents": [{"role": "user", "parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    t0 = time.time()
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "model": model, "voice": voice, "text": os.path.basename(text_path)}
    try:
        with urllib.request.urlopen(request, timeout=300) as r:
            data = json.loads(r.read().decode("utf-8"))
            entry["status"] = r.status
    except urllib.error.HTTPError as e:
        error_body = scrub(e.read().decode("utf-8", "replace"), key)
        entry.update({"status": e.code, "error": error_body[:2000], "seconds": round(time.time() - t0, 1)})
        log_request(entry)
        print(f"HTTP ERROR {e.code}")
        print(error_body[:2000])
        sys.exit(1)
    except Exception as e:  # network, timeout, etc.
        msg = scrub(f"{type(e).__name__}: {e}", key)
        entry.update({"status": "no response", "error": msg, "seconds": round(time.time() - t0, 1)})
        log_request(entry)
        print("ERROR", msg)
        sys.exit(1)
    entry["seconds"] = round(time.time() - t0, 1)
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    audio = next((p["inlineData"] for p in parts if "inlineData" in p), None)
    if audio is None:
        entry["error"] = "the response carries no audio: " + scrub(json.dumps(data)[:1500], key)
        log_request(entry)
        print(entry["error"])
        sys.exit(1)
    mime = audio.get("mimeType", "")
    rate = 24000
    for chunk in mime.split(";"):
        if chunk.strip().startswith("rate="):
            rate = int(chunk.strip()[5:])
    pcm = base64.b64decode(audio["data"])
    if pcm[:4] == b"RIFF":  # the model already returns a complete WAV ("audio/wav"): saved as is
        open(out, "wb").write(pcm)
        with wave.open(out, "rb") as w:
            rate, samples = w.getframerate(), w.getnframes()
        duration = samples / rate
    else:  # raw 16 bit PCM ("audio/L16;rate=...")
        with wave.open(out, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm)
        duration = len(pcm) / 2 / rate
    entry.update({"mime": mime, "rate": rate, "duration_s": round(duration, 2), "out": os.path.basename(out),
                  "usage": data.get("usageMetadata", {}), "model_version": data.get("modelVersion", "")})
    log_request(entry)
    print(f"ok: {entry['duration_s']} s of audio ({mime}), {entry['seconds']} s of waiting, model {entry['model_version'] or model}")


if __name__ == "__main__":
    main()
