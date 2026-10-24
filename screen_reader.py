#!/usr/bin/env python3
import os
import sys
import base64
import argparse
import re
import wave
import io
from pathlib import Path
import time

import pyautogui
import pyperclip
from mss import mss
from PIL import Image

from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError

MAX_CHARS = 2500

PRESETS = {
    "news": {"pace": 0.95},
    "fiction": {"pace": 0.9},
    "education": {"pace": 0.85},
}

def load_client():
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.strip().startswith("SARVAM_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key or api_key.strip() == "":
        raise SystemExit("Missing API key. Add SARVAM_API_KEY to .env or environment.")
    return SarvamAI(api_subscription_key=api_key)

def capture_screen(region=None):
    with mss() as sct:
        if region:
            monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
        else:
            monitor = sct.monitors[1]  # primary monitor
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img

def extract_text_from_screen(use_ocr=False):
    # Try clipboard first (user might have selected text)
    try:
        text = pyperclip.paste()
        if text and text.strip() and len(text.strip()) > 10:
            return text.strip()
    except:
        pass
    
    if use_ocr:
        try:
            import pytesseract
            img = capture_screen()
            text = pytesseract.image_to_string(img)
            if text and text.strip():
                return text.strip()
        except Exception as e:
            print(f"OCR failed: {e}", file=sys.stderr)
    
    # Fallback: take screenshot and ask user to copy
    print("No text in clipboard. Please select the text on screen and copy it (Ctrl+C), then press Enter here.", flush=True)
    input()
    try:
        text = pyperclip.paste()
        if text and text.strip():
            return text.strip()
    except:
        pass
    raise SystemExit("No text found. Please copy the text you want to read aloud.")

def chunk_text(text, max_chars=MAX_CHARS):
    if len(text) <= max_chars:
        return [text]
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current = []
    current_len = 0
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if current_len + len(p) + 2 <= max_chars:
            current.append(p)
            current_len += len(p) + 2
        else:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            if len(p) > max_chars:
                sentences = re.split(r'(?<=[.!?])\s+', p)
                s_cur = []
                s_len = 0
                for s in sentences:
                    s = s.strip()
                    if not s:
                        continue
                    if s_len + len(s) + 1 <= max_chars:
                        s_cur.append(s)
                        s_len += len(s) + 1
                    else:
                        if s_cur:
                            chunks.append(" ".join(s_cur))
                            s_cur = []
                            s_len = 0
                        if len(s) > max_chars:
                            for i in range(0, len(s), max_chars):
                                chunks.append(s[i:i+max_chars])
                        else:
                            s_cur = [s]
                            s_len = len(s)
                if s_cur:
                    chunks.append(" ".join(s_cur))
            else:
                current = [p]
                current_len = len(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks

def tts_convert(client, text, lang, speaker, model, pace, sample_rate=None):
    kwargs = {
        "text": text,
        "language_code": lang,
        "model": model,
    }
    if speaker:
        kwargs["speaker"] = speaker
    if pace is not None:
        kwargs["pace"] = pace
    if sample_rate is not None:
        kwargs["speech_sample_rate"] = sample_rate
    try:
        resp = client.text_to_speech.convert(**kwargs)
        return resp
    except ApiError as e:
        raise SystemExit(f"TTS API error: {e}")

def concatenate_wav_files(wav_bytes_list, output_path):
    if not wav_bytes_list:
        raise SystemExit("No audio generated")
    first = io.BytesIO(wav_bytes_list[0])
    with wave.open(first, 'rb') as w:
        params = w.getparams()
        frames = [w.readframes(w.getnframes())]
    for wb in wav_bytes_list[1:]:
        try:
            f = io.BytesIO(wb)
            with wave.open(f, 'rb') as w:
                frames.append(w.readframes(w.getnframes()))
        except Exception as e:
            print(f"Skipping segment: {e}", file=sys.stderr)
            continue
    with wave.open(output_path, 'wb') as out:
        out.setparams(params)
        for fr in frames:
            out.writeframes(fr)

def main():
    parser = argparse.ArgumentParser(description="Sarvam Screen Reader - Read text from current screen")
    parser.add_argument("--lang", "--target-lang", dest="target_lang", default="en-IN")
    parser.add_argument("--speaker", help="Voice speaker ID")
    parser.add_argument("--model", default="bulbul:v4-flash")
    parser.add_argument("--pace", type=float)
    parser.add_argument("--preset", choices=["news", "fiction", "education"])
    parser.add_argument("--sample-rate", type=int, dest="sample_rate")
    parser.add_argument("--ocr", action="store_true", help="Use OCR to extract text from screen")
    parser.add_argument("--out", default="screen_output.wav")
    parser.add_argument("--delay", type=int, default=3, help="Delay before capturing (seconds)")
    args = parser.parse_args()

    print(f"Screen reader starting in {args.delay} seconds...", flush=True)
    print("Switch to the window you want to read and select/copy text, or just wait.", flush=True)
    time.sleep(args.delay)

    client = load_client()
    text = extract_text_from_screen(use_ocr=args.ocr)
    if not text:
        raise SystemExit("Empty text")
    
    print(f"Extracted {len(text)} characters. Generating audio...", flush=True)
    
    pace = args.pace
    if args.preset and pace is None:
        pace = PRESETS[args.preset].get("pace")
    
    chunks = chunk_text(text)
    wav_segments = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...", flush=True)
        resp = tts_convert(client, chunk, args.target_lang, args.speaker, args.model, pace, args.sample_rate)
        for a in getattr(resp, "audios", []) or []:
            try:
                wav_segments.append(base64.b64decode(a))
            except Exception as e:
                print(f"Failed to decode: {e}", file=sys.stderr)
    
    if not wav_segments:
        raise SystemExit("No audio generated")
    
    concatenate_wav_files(wav_segments, args.out)
    print(f"Saved {args.out}", flush=True)
    
    # Try to play it
    try:
        import subprocess
        subprocess.Popen(["aplay", args.out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        try:
            subprocess.Popen(["paplay", args.out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            try:
                subprocess.Popen(["play", args.out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

if __name__ == "__main__":
    main()
