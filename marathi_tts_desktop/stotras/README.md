# Stotra Audio Library
## Pre-recorded Chanting for Authentic Devotional Audio

### Why This Exists
Standard TTS (gTTS, VITS, etc.) is trained on conversational data and cannot produce
proper stotra chanting — it misses Chandas (metrical rhythm), Swaras (musical notes),
and devotional emotion entirely. **Pre-recorded audio from trained chanters is the only
way to get authentic results for established stotras.**

### Architecture
```
[User Text] → [Fingerprint Match] → [Pre-recorded Audio] ✓ Authentic
                    ↓ (no match)
             [G2P + gTTS fallback]  → [Generated Audio]   △ Best-effort
```

### How to Add a Stotra

1. **Obtain high-quality audio** — record at 44.1kHz/16-bit mono or better
2. **Save as MP3** in this directory (e.g., `ram_raksha_stotra.mp3`)
3. **Generate fingerprint** from the stotra text:
   ```python
   import re
   text = open("stotra.txt", "r", encoding="utf-8").read()
   print(re.sub(r'[^\u0900-\u097F]', '', text)[:60])
   ```
4. **Add entry** to `stotra_catalog.json` with the fingerprint
5. **Restart the app** — the TTS bridge will match and serve from library

### Catalog Fields
| Field | Description |
|-------|-------------|
| `name` | Display name (Devanagari + transliteration) |
| `audio_file` | Filename in this directory |
| `language` | `sa` (Sanskrit), `mr` (Marathi), `hi` (Hindi) |
| `meter` | Chandas/meter (अनुष्टुप्, ओवी, etc.) |
| `deity` | Primary deity |
| `source` | Author/scripture |
| `fingerprints` | Array of first-60-Devanagari-chars variants for matching |

### Audio Sources (Suggestions)
- **Self-recorded** by a trained pujari or music student
- **Public domain** recordings from temples or archival projects
- **Commissioned** from professional chanters (5-10 stotras covers most use cases)
- **Future: SVS/DiffSinger** model trained on chanting data for dynamic generation

### Stotras To Prioritize
1. ✅ रामरक्षास्तोत्र (Ram Raksha)
2. ✅ गणपती अथर्वशीर्ष
3. ✅ विष्णु सहस्रनाम
4. ✅ हनुमान चालीसा
5. ✅ मारुतिस्तोत्र (समर्थ)
6. ✅ नवग्रह स्तोत्र
7. ✅ श्रीमहालक्ष्मी अष्टक
8. ✅ भगवद्गीता अध्याय १२
9. ✅ मनाचे श्लोक
10. शिवमहिम्नस्तोत्र
11. ललिता सहस्रनाम
12. आदित्यहृदयस्तोत्र
