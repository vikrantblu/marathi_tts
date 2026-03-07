try:
    from .text_normalizer import MarathiTextNormalizer
except ImportError:
    # Optional production dep (indicnlp) not installed — skip gracefully.
    MarathiTextNormalizer = None  # type: ignore[assignment,misc]

try:
    from .morphological_analyzer import MarathiMorphologicalAnalyzer, get_analyzer
except ImportError:
    MarathiMorphologicalAnalyzer = None  # type: ignore[assignment,misc]
    get_analyzer = None  # type: ignore[assignment]

# Make the classes available at the package level
__all__ = ['MarathiTextNormalizer', 'MarathiMorphologicalAnalyzer', 'get_analyzer']