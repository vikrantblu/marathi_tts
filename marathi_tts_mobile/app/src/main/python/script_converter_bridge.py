#!/usr/bin/env python3
"""
Script Converter Bridge - Ancient Script to Devanagari
=======================================================
Converts Modi, Brahmi, and IAST scripts to/from Devanagari.

Usage:
    python script_converter_bridge.py --text "..." --mode modi_to_devanagari
    python script_converter_bridge.py --text "..." --mode devanagari_to_iast
    python script_converter_bridge.py --text "..." --mode iast_to_devanagari
    python script_converter_bridge.py --text "..." --mode brahmi_to_devanagari

Returns: JSON { success, converted_text, mode, char_count }
"""

import sys, os, json, argparse, traceback, time

_BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BRIDGE_DIR)
try:
    from _bridge_logging import get_logger
except ImportError:
    import logging
    def get_logger(n, **kw):
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                            format="[%(asctime)s] [%(levelname)s] %(message)s")
        return logging.getLogger(n)

log = get_logger("script_converter_bridge")

_PROJECT_ROOT = os.environ.get(
    "MARATHI_TTS_PROJECT_ROOT",
    os.path.abspath(os.path.join(_BRIDGE_DIR, "..", "marathi_tts_web"))
)
if _PROJECT_ROOT not in sys.path and os.path.isdir(_PROJECT_ROOT):
    sys.path.insert(0, _PROJECT_ROOT)
os.environ.setdefault("MARATHI_TTS_STANDALONE", "1")

log.info("Script Converter Bridge initialised | bridge_dir=%s", _BRIDGE_DIR)

MODES = ["modi_to_devanagari", "devanagari_to_iast", "iast_to_devanagari", "brahmi_to_devanagari"]

# Embedded minimal Modi->Devanagari mapping (core characters)
_EMBEDDED_MODI_MAP = {
    "\U00011600": "\u0915",  # MODI LETTER KA -> क
    "\U00011601": "\u0916",  # KHA -> ख
    "\U00011602": "\u0917",  # GA  -> ग
    "\U00011603": "\u0918",  # GHA -> घ
    "\U00011604": "\u0919",  # NGA -> ङ
    "\U00011605": "\u091A",  # CA  -> च
    "\U00011606": "\u091B",  # CHA -> छ
    "\U00011607": "\u091C",  # JA  -> ज
    "\U00011608": "\u091D",  # JHA -> झ
    "\U00011609": "\u091E",  # NYA -> ञ
    "\U0001160A": "\u091F",  # TTA -> ट
    "\U0001160B": "\u0920",  # TTHA-> ठ
    "\U0001160C": "\u0921",  # DDA -> ड
    "\U0001160D": "\u0922",  # DDHA-> ढ
    "\U0001160E": "\u0923",  # NNA -> ण
    "\U0001160F": "\u0924",  # TA  -> त
    "\U00011610": "\u0925",  # THA -> थ
    "\U00011611": "\u0926",  # DA  -> द
    "\U00011612": "\u0927",  # DHA -> ध
    "\U00011613": "\u0928",  # NA  -> न
    "\U00011614": "\u092A",  # PA  -> प
    "\U00011615": "\u092B",  # PHA -> फ
    "\U00011616": "\u092C",  # BA  -> ब
    "\U00011617": "\u092D",  # BHA -> भ
    "\U00011618": "\u092E",  # MA  -> म
    "\U00011619": "\u092F",  # YA  -> य
    "\U0001161A": "\u0930",  # RA  -> र
    "\U0001161B": "\u0932",  # LA  -> ल
    "\U0001161C": "\u0935",  # VA  -> व
    "\U0001161D": "\u0936",  # SHA -> श
    "\U0001161E": "\u0937",  # SSA -> ष
    "\U0001161F": "\u0938",  # SA  -> स
    "\U00011620": "\u0939",  # HA  -> ह
}


def _indic_transliterate(text: str, src_scheme, dst_scheme) -> str:
    """Transliterate using indic-transliteration library."""
    from indic_transliteration import sanscript  # type: ignore
    from indic_transliteration.sanscript import transliterate  # type: ignore
    return transliterate(text, src_scheme, dst_scheme)


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def convert(text: str, mode: str = "modi_to_devanagari") -> dict:
    """Convert script text between supported modes.

    Returns: {success, converted_text, mode, char_count, original_char_count}
    """
    t0 = time.time()
    log.info("=== convert START | mode=%s text_len=%d ===", mode, len(text))
    log.debug("Input text preview: %.100s", text)

    if not text.strip():
        return {"success": False, "error": "Empty input text"}
    if mode not in MODES:
        return {"success": False, "error": f"Unsupported mode '{mode}'. Choose: {MODES}"}

    result = None

    # ── Modi -> Devanagari ─────────────────────────────────────────────────
    if mode == "modi_to_devanagari":
        # Try web-app ScriptConverter first
        try:
            from tts.utils.text.script_converter import ScriptConverter  # type: ignore
            result = ScriptConverter.modi_to_devanagari(text)
            log.info("modi_to_devanagari via ScriptConverter | %d -> %d chars",
                     len(text), len(result))
        except Exception as exc:
            log.warning("ScriptConverter unavailable (%s) - using embedded map", exc)

        # Embedded fallback
        if result is None:
            try:
                # Try constants map first
                from tts.constants.script_constants import MODI_TO_DEVANAGARI_MAP  # type: ignore
                result = "".join(MODI_TO_DEVANAGARI_MAP.get(c, c) for c in text)
                log.info("modi_to_devanagari via constants map")
            except Exception:
                result = "".join(_EMBEDDED_MODI_MAP.get(c, c) for c in text)
                log.info("modi_to_devanagari via embedded map")

    # ── Devanagari -> IAST ─────────────────────────────────────────────────
    elif mode == "devanagari_to_iast":
        try:
            from indic_transliteration import sanscript  # type: ignore
            result = _indic_transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
            log.info("devanagari_to_iast via indic-transliteration | %d -> %d chars",
                     len(text), len(result))
        except ImportError:
            log.error("indic-transliteration not installed. Run: pip install indic-transliteration")
            return {"success": False, "error": "Missing: pip install indic-transliteration"}
        except Exception as exc:
            log.error("devanagari_to_iast failed: %s", exc)
            return {"success": False, "error": str(exc)}

    # ── IAST -> Devanagari ─────────────────────────────────────────────────
    elif mode == "iast_to_devanagari":
        try:
            from indic_transliteration import sanscript  # type: ignore
            result = _indic_transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
            log.info("iast_to_devanagari via indic-transliteration | %d -> %d chars",
                     len(text), len(result))
        except ImportError:
            return {"success": False, "error": "Missing: pip install indic-transliteration"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ── Brahmi -> Devanagari ───────────────────────────────────────────────
    elif mode == "brahmi_to_devanagari":
        try:
            from indic_transliteration import sanscript  # type: ignore
            result = _indic_transliterate(text, sanscript.BRAHMI, sanscript.DEVANAGARI)
            log.info("brahmi_to_devanagari | %d -> %d chars", len(text), len(result))
        except ImportError:
            return {"success": False, "error": "Missing: pip install indic-transliteration"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if result is None:
        return {"success": False, "error": "Conversion produced no result"}

    log.info("=== convert DONE | mode=%s %d -> %d chars elapsed=%.2fs ===",
             mode, len(text), len(result), time.time() - t0)
    return {
        "success": True,
        "converted_text": result,
        "mode": mode,
        "char_count": len(result),
        "original_char_count": len(text),
        "elapsed_sec": round(time.time() - t0, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Marathi Script Converter Bridge")
    parser.add_argument("--text", required=True)
    parser.add_argument("--mode", default="modi_to_devanagari", choices=MODES)
    args = parser.parse_args()
    print(json.dumps(convert(args.text, args.mode), ensure_ascii=False))


if __name__ == "__main__":
    main()
