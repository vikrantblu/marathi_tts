"""
Stotra Library API — serves the stotra catalog and individual stotra texts.
"""
import json
import os
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

# Resolve stotra data directory
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
_CATALOG_PATH = os.path.join(_DATA_DIR, 'stotra_catalog.json')
_STOTRAS_DIR = os.path.join(_DATA_DIR, 'stotras')

_catalog_cache = None


def _load_catalog():
    """Load and cache the stotra catalog."""
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache
    try:
        with open(_CATALOG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _catalog_cache = data.get('stotras', [])
    except Exception as e:
        logger.error(f"Failed to load stotra catalog: {e}")
        _catalog_cache = []
    return _catalog_cache


@require_http_methods(["GET"])
def stotra_list(request):
    """Return the stotra catalog as JSON, with optional deity/search filters."""
    stotras = _load_catalog()
    deity = request.GET.get('deity', '').strip()
    search = request.GET.get('q', '').strip().lower()

    results = []
    for idx, s in enumerate(stotras):
        # Filter by deity
        if deity and deity != 'all':
            s_deity = s.get('deity', '')
            if deity not in s_deity:
                continue
        # Filter by search
        if search:
            name = s.get('name', '').lower()
            source = s.get('source', '').lower()
            if search not in name and search not in source:
                continue
        results.append({
            'id': idx,
            'name': s.get('name', ''),
            'language': s.get('language', ''),
            'meter': s.get('meter', ''),
            'deity': s.get('deity', ''),
            'source': s.get('source', ''),
        })

    return JsonResponse({'success': True, 'stotras': results, 'count': len(results)})


@require_http_methods(["GET"])
def stotra_text(request, stotra_id):
    """Return the text content of a stotra by catalog index."""
    stotras = _load_catalog()
    if stotra_id < 0 or stotra_id >= len(stotras):
        return JsonResponse({'success': False, 'error': 'Invalid stotra ID'}, status=404)

    stotra = stotras[stotra_id]
    # Derive text filename from audio_file field (replace .mp3 with .txt)
    audio_file = stotra.get('audio_file', '')
    text_filename = audio_file.replace('.mp3', '.txt') if audio_file else ''

    # Try to find the text file
    text_content = ''
    text_path = os.path.join(_STOTRAS_DIR, text_filename) if text_filename else ''

    if text_path and os.path.isfile(text_path):
        with open(text_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
    else:
        # Try matching by name pattern
        for fname in os.listdir(_STOTRAS_DIR):
            if fname.endswith('.txt'):
                fpath = os.path.join(_STOTRAS_DIR, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Simple heuristic: if the stotra name appears in the file content
                stotra_name_part = stotra.get('name', '').split('(')[0].strip()
                if stotra_name_part and stotra_name_part in content[:200]:
                    text_content = content
                    break

    return JsonResponse({
        'success': True,
        'stotra': {
            'name': stotra.get('name', ''),
            'deity': stotra.get('deity', ''),
            'language': stotra.get('language', ''),
            'meter': stotra.get('meter', ''),
            'source': stotra.get('source', ''),
            'text': text_content,
        }
    })
