#!/usr/bin/env python3
import os
import sys
import base64
import argparse
import re
import wave
import io
from pathlib import Path

import requests
from bs4 import BeautifulSoup

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

def read_input(args):
    if args.url:
        try:
            resp = requests.get(args.url, headers={"User-Agent": "SarvamReader/1.0"}, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n")
            text = re.sub(r"\n\s*\n+", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)
            return text.strip()
        except Exception as e:
            raise SystemExit(f"Failed to fetch URL: {e}")
    if args.file:
        path = Path(args.file)
        if not path.exists():
            raise SystemExit(f"File not found: {path}")
        if path.suffix.lower() not in [".txt", ".md"]:
            raise SystemExit(f"Unsupported file type: {path.suffix}. Use .txt or .md")
        return path.read_text(encoding="utf-8").strip()
    if args.input and args.input != "-":
        p = Path(args.input)
        if p.exists() and p.is_file():
            if p.suffix.lower() not in [".txt", ".md"]:
                raise SystemExit(f"Unsupported file type: {p.suffix}. Use .txt or .md")
            return p.read_text(encoding="utf-8").strip()
        return args.input.strip()
    try:
        return sys.stdin.read().strip()
    except Exception:
        raise SystemExit("No input provided")

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

def maybe_translate(client, text, source_lang, target_lang):
    if source_lang == target_lang or source_lang == "auto":
        return text
    try:
        resp = client.text.translate(
            input=text,
            source_language_code=source_lang,
            target_language_code=target_lang,
            model="sarvam-translate:v1",
        )
        if hasattr(resp, "translated_text"):
            return resp.translated_text
        if isinstance(resp, dict):
            return resp.get("translated_text") or resp.get("translation") or text
        return text
    except Exception as e:
        print(f"Translation failed: {e}. Proceeding without translation.", file=sys.stderr)
        return text

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
    # Read first to get params
    first = io.BytesIO(wav_bytes_list[0])
    with wave.open(first, 'rb') as w:
        params = w.getparams()
        frames = [w.readframes(w.getnframes())]
    for wb in wav_bytes_list[1:]:
        try:
            f = io.BytesIO(wb)
            with wave.open(f, 'rb') as w:
                if w.getparams()[:4] != params[:4]:  # basic check
                    pass
                frames.append(w.readframes(w.getnframes()))
        except Exception as e:
            print(f"Skipping segment due to error: {e}", file=sys.stderr)
            continue
    with wave.open(output_path, 'wb') as out:
        out.setparams(params)
        for fr in frames:
            out.writeframes(fr)

def main():
    parser = argparse.ArgumentParser(description="Sarvam Text-to-Speech Content Reader")
    parser.add_argument("input", nargs="?", help="Text, .txt/.md file path, or '-' for stdin")
    parser.add_argument("--url", help="URL to article/blog")
    parser.add_argument("--file", help="Path to .txt/.md file")
    parser.add_argument("--lang", "--target-lang", dest="target_lang", default="en-IN", help="Target language code")
    parser.add_argument("--source-lang", dest="source_lang", default="auto", help="Source language code or auto")
    parser.add_argument("--speaker", help="Voice speaker ID")
    parser.add_argument("--model", default="bulbul:v4-flash", help="TTS model")
    parser.add_argument("--pace", type=float, help="Speech pace (0.5-2.0)")
    parser.add_argument("--preset", choices=["news", "fiction", "education"], help="Content preset")
    parser.add_argument("--sample-rate", type=int, dest="sample_rate", help="Speech sample rate")
    parser.add_argument("--translate-first", action="store_true", help="Translate if source != target")
    parser.add_argument("--out", default="output.wav", help="Output audio file (wav)")
    parser.add_argument("--batch", help="Process all .txt/.md files in directory")
    args = parser.parse_args()

    client = load_client()

    if args.batch:
        batch_dir = Path(args.batch)
        if not batch_dir.exists() or not batch_dir.is_dir():
            raise SystemExit(f"Batch directory not found: {batch_dir}")
        files = sorted([f for f in batch_dir.iterdir() if f.is_file() and f.suffix.lower() in [".txt", ".md"]])
        if not files:
            raise SystemExit("No .txt/.md files found in batch directory")
        for f in files:
            out_file = f.with_suffix(".wav")
            print(f"Processing {f} -> {out_file}")
            args.file = str(f)
            args.url = None
            args.input = None
            text = read_input(args)
            if not text:
                print(f"Empty input for {f}, skipping", file=sys.stderr)
                continue
            if args.translate_first and args.source_lang != args.target_lang:
                text = maybe_translate(client, text, args.source_lang, args.target_lang)
            pace = args.pace
            if args.preset and pace is None:
                pace = PRESETS[args.preset].get("pace")
            chunks = chunk_text(text)
            wav_segments = []
            for chunk in chunks:
                resp = tts_convert(client, chunk, args.target_lang, args.speaker, args.model, pace, args.sample_rate)
                for a in getattr(resp, "audios", []) or []:
                    try:
                        wav_segments.append(base64.b64decode(a))
                    except Exception as e:
                        print(f"Failed to decode audio segment: {e}", file=sys.stderr)
            if not wav_segments:
                raise SystemExit("No audio generated")
            concatenate_wav_files(wav_segments, str(out_file))
            print(f"Saved {out_file}")
        return

    text = read_input(args)
    if not text:
        raise SystemExit("Empty input")
    if args.translate_first and args.source_lang != args.target_lang:
        text = maybe_translate(client, text, args.source_lang, args.target_lang)
    pace = args.pace
    if args.preset and pace is None:
        pace = PRESETS[args.preset].get("pace")
    chunks = chunk_text(text)
    wav_segments = []
    for chunk in chunks:
        resp = tts_convert(client, chunk, args.target_lang, args.speaker, args.model, pace, args.sample_rate)
        for a in getattr(resp, "audios", []) or []:
            try:
                wav_segments.append(base64.b64decode(a))
            except Exception as e:
                print(f"Failed to decode audio segment: {e}", file=sys.stderr)
    if not wav_segments:
        raise SystemExit("No audio generated")
    concatenate_wav_files(wav_segments, args.out)
    print(f"Saved {args.out}")

if __name__ == "__main__":
    main()
