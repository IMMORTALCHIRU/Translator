# Gen Z Translator

Gen Z Translator is a small Flask-based web app that translates user text into Gen Z / slang variants and supports audio processing and translation history.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Locally](#running-locally)
- [Routes & Pages](#routes--pages)
- [How It Works (high level)](#how-it-works-high-level)
- [Development Notes](#development-notes)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project provides a simple translator web application that converts standard English input into Gen Z/slang variants. It is implemented with Flask for the backend, vanilla JS for client-side interactivity, and basic HTML/CSS templates for the UI.

The app also provides audio processing utilities that can accept or produce audio, and a simple history view to see previous translations.

## Features

- Text translation to Gen Z/slang
- Web UI for entering text and reviewing translations
- Audio processing utilities (input preprocessing / conversion)
- User auth scaffolding (login/register pages present)
- Translation history view

## Tech Stack

- Python 3.x
- Flask
- HTML/CSS/JavaScript
- Additional Python utilities in `utils/`

See `requirements.txt` for Python package dependencies.

## Repository Structure

Top-level files
- `app.py`: Application entrypoint.
- `config.py`: App configuration (flask config, secrets, etc.).
- `requirements.txt`: Python dependencies.

Major folders
- `routes/`: Flask route blueprints and view functions (`main.py`, `translation.py`, `auth.py`, `genz_translation.py`, `history.py`).
- `templates/`: HTML templates (`index.html`, `translate.html`, `genz_translate.html`, `history.html`, `login.html`, `register.html`, `base.html`).
- `static/`: Static assets: `css/`, `js/`, `audio/`.
- `utils/`: Helper modules — `genz_translator.py`, `translator.py`, `audio_processor.py`.
- `data/`: Data files (e.g., `slang_map.py`).
- `models/`: Data models (example: `user.py`).

## Installation

Recommended workflow on macOS (zsh):

1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. (Optional) If you plan to use audio features, ensure system audio utilities are available and any optional packages in `requirements.txt` are installed.

## Configuration

- Inspect `config.py` to see configuration options such as `SECRET_KEY`, database connection strings, and other app settings.
- If the app expects environment variables, set them in your shell before running. Example:

```bash
export FLASK_ENV=development
export SECRET_KEY='your-secret-key'
```

Note: This repo includes a basic `config.py`; if you need to store secrets, prefer using environment variables or a `.env` file (and add it to `.gitignore`).

## Running Locally

Start the Flask app (from the project root):

```bash
python app.py
```

By default the app will listen on `http://127.0.0.1:5000/` unless `app.py` or `config.py` overrides the host/port.

Open a browser and navigate to:
- `GET /` — home page
- `GET /translate` — translation UI
- `GET /genz_translate` — Gen Z-specific translation UI
- `GET /history` — view translation history

## Routes & Pages

The application includes the following main pages (see `routes/` for implementations):

- `/` — Home (`templates/index.html`)
- `/translate` — Page to enter text and receive translations (`templates/translate.html`)
- `/genz_translate` — Gen Z/slang-specific translator page (`templates/genz_translate.html`)
- `/history` — Translation history (`templates/history.html`)
- `/login` & `/register` — Authentication UI (`templates/login.html`, `templates/register.html`)

If you need the exact endpoint names (e.g. API endpoints used by AJAX calls), inspect `routes/translation.py`, `routes/genz_translation.py`, and the JavaScript files under `static/js/`.

## How It Works (high level)

- The frontend sends text to a Flask route (via form submit or Ajax).
- A translator utility in `utils/` (for example `genz_translator.py` or `translator.py`) performs the transformation using a mapping defined in `data/slang_map.py` or rule-based logic.
- Results are returned to the client, displayed, and optionally stored in a history store.
- Audio features use `utils/audio_processor.py` to preprocess or play audio content.

## Development Notes

- To modify translation logic, update `utils/genz_translator.py` or `utils/translator.py` and unit-test changes manually by running the server and trying sample inputs.
- The `data/slang_map.py` file is where slang mappings may be kept — editing or expanding it changes translation output.
- Static front-end behavior is in `static/js/` (`genz_translation.js`, `translation.js`, `history.js`, `main.js`).

# 

