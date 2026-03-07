# Contributing to Marathi TTS

Thank you for your interest in contributing! This document outlines how to get involved effectively.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Submitting Changes](#submitting-changes)
- [Style Guide](#style-guide)
- [Adding Languages / Voices](#adding-languages--voices)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

Be respectful, inclusive, and constructive. Harassment of any kind will not be tolerated.

---

## Getting Started

1. **Fork** the repository and clone your fork:
   ```bash
   git clone https://github.com/your-username/marathi-tts.git
   cd marathi-tts
   ```

2. **Set up the environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

4. **Apply migrations and run the server:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

---

## Development Workflow

- Create a feature branch from `main`:
  ```bash
  git checkout -b feature/your-feature-name
  ```
- Keep commits small and focused on a single change.
- Write descriptive commit messages (e.g., `fix: handle empty Marathi text in normalizer`).

---

## Submitting Changes

1. Push your branch and open a **Pull Request** against `main`.
2. Fill in the PR template describing:
   - What the change does.
   - How to test it.
   - Any related issues.
3. At least one maintainer review is required before merging.

---

## Style Guide

- **Python**: Follow [PEP 8](https://pep8.org/). Use `black` for formatting.
- **Docstrings**: Use Google-style docstrings for all public functions.
- **Marathi text**: Always use Unicode Devanagari (UTF-8). Document any script-specific assumptions.
- **Imports**: Group as stdlib → third-party → local, separated by blank lines.

---

## Adding Languages / Voices

To add a new TTS voice or language:

1. Create a new service in `tts/utils/core/` following the pattern of `google_service.py`.
2. Register the voice in `TTSSettings.SUPPORTED_VOICES` in `tts/utils/core/tts_settings.py`.
3. Expose it in `tts_views.py` under `available_voices`.
4. Document the new voice in `README.md`.

---

## Reporting Issues

Use [GitHub Issues](../../issues). Please include:
- Steps to reproduce.
- Expected vs. actual behaviour.
- Your OS, Python version, and relevant package versions.
- Log snippets (without sensitive data).
