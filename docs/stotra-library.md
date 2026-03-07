# Stotra Library Specification

## Overview

Pre-packaged Marathi/Sanskrit stotra texts available across all three platforms.

## Catalog Format

`stotra_catalog.json`:
```json
[
  {
    "id": "vishnu_sahasranama",
    "name": "विष्णु सहस्रनाम",
    "nameEn": "Vishnu Sahasranama",
    "deity": "विष्णु",
    "filename": "vishnu_sahasranama.txt"
  }
]
```

## Asset Locations

| Platform | Location |
|----------|----------|
| Web | `marathi_tts_web/data/stotras/` |
| Desktop | `marathi_tts_desktop/stotras/` |
| Mobile | `marathi_tts_mobile/app/src/main/assets/stotras/` |

## Adding a new stotra

Use the `add-stotra` agent prompt, or manually:
1. Create `.txt` file (UTF-8, no BOM) with Devanagari text
2. Copy to all 3 locations
3. Add catalog entry to all 3 `stotra_catalog.json` files
4. Run tests

## Custom Voice Pipeline

For stotras with pre-recorded audio:
1. `preprocess_audio.py` — normalize + segment at verse boundaries
2. `align_transcript.py` — map verses to audio segments
3. `validate_dataset.py` — quality checks
4. `generate_piper_config.py` — Piper dataset format
5. `train_piper.py` — fine-tune Piper VITS model
