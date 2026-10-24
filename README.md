# Sarvam TTS Reader

A simple Text-to-Speech Content Reader built with the [Sarvam AI API](https://docs.sarvam.ai/). Convert articles, documents, or scripts into natural-sounding narrated audio using Bulbul TTS.

## Features

- **Multiple Input Sources**: Paste text directly, load from `.txt`/`.md` files, or fetch from URLs
- **Multilingual Support**: Support for Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, and more
- **Voice Customization**: Choose from 200+ voices with Bulbul v4 Flash and Bulbul v3
- **Content Presets**: Optimized settings for News, Fiction, and Education content
- **Pace Control**: Adjust speech speed from 0.5x to 2.0x
- **Long Content Handling**: Automatically chunks text at sentence/paragraph boundaries and stitches audio
- **Batch Processing**: Process entire folders of files at once
- **Translation Support**: Optional translation using Sarvam's translation API
- **Modern Web UI**: Clean, responsive interface for easy use

## Setup

### 1. Install Dependencies

```bash
pip install sarvamai requests beautifulsoup4 flask
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
SARVAM_API_KEY=your_api_key_here
```

Get your API key from the [Sarvam AI Dashboard](https://indus.sarvam.ai/).

### 3. Run the Application

#### Web Interface
```bash
python app.py
```
Open http://127.0.0.1:5000 in your browser.

#### CLI
```bash
# From text
python reader.py "Hello world" --lang en-IN --preset news --out output.wav

# From file
python reader.py --file article.txt --lang hi-IN --out hindi.wav

# From URL
python reader.py --url https://example.com/article --lang en-IN

# Batch mode
python reader.py --batch ./articles --lang en-IN --preset education
```

## CLI Options

| Option | Description | Default |
|---|---|---|
| `input` | Text, file path, or `-` for stdin | - |
| `--url` | URL to fetch article from | - |
| `--file` | Path to .txt or .md file | - |
| `--lang` / `--target-lang` | Target language code (e.g., hi-IN, en-IN) | en-IN |
| `--source-lang` | Source language code or `auto` | auto |
| `--speaker` | Voice speaker ID | - |
| `--model` | TTS model (bulbul:v4-flash or bulbul:v3) | bulbul:v4-flash |
| `--pace` | Speech pace (0.5-2.0) | - |
| `--preset` | news, fiction, or education | - |
| `--sample-rate` | Audio sample rate | - |
| `--translate-first` | Translate if source != target | false |
| `--out` | Output audio file | output.wav |
| `--batch` | Process all .txt/.md files in directory | - |

## Presets

- **News**: Clear, steady, neutral pace (0.95x)
- **Fiction**: Expressive, slightly slower, varied tone (0.9x)
- **Education**: Calm, slower pace, clear emphasis (0.85x)

## Project Structure

```
SarvamTTS/
├── app.py           # Flask web application
├── reader.py        # CLI tool
├── phase1_test.py   # Phase 1 verification script
├── templates/       # HTML templates
│   └── index.html
├── static/          # Static assets
│   ├── style.css
│   └── app.js
├── .env             # API key (not committed)
├── .gitignore       # Git ignore rules
└── README.md
```

## License

MIT License
