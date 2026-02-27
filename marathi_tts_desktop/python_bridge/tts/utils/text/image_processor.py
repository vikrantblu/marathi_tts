import cv2
import numpy as np
from PIL import Image, ImageEnhance

def preprocess_image_for_ocr(image):
    """
    Preprocess image for better Devanagari/Marathi OCR results.
    Args:
        image: PIL Image object
    Returns:
        PIL Image object optimized for Tesseract OCR
    """
    # Upscale small images first for better OCR accuracy
    min_dimension = 1000
    if min(image.size) < min_dimension:
        scale = min_dimension / min(image.size)
        new_size = tuple(int(dim * scale) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Convert PIL to OpenCV format
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter to remove noise while keeping edges sharp
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Use Otsu's thresholding for cleaner binarization
    # (better than adaptive threshold for printed Devanagari text)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Mild morphological opening to remove small noise spots
    # Avoid dilation — it merges Devanagari characters connected by shirorekha
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Convert back to PIL Image
    pil_image = Image.fromarray(cleaned)
    
    # Light contrast enhancement
    enhancer = ImageEnhance.Contrast(pil_image)
    enhanced = enhancer.enhance(1.5)
    
    # Cap maximum dimension to prevent memory issues
    max_dimension = 3000
    if max(enhanced.size) > max_dimension:
        ratio = max_dimension / max(enhanced.size)
        new_size = tuple(int(dim * ratio) for dim in enhanced.size)
        enhanced = enhanced.resize(new_size, Image.Resampling.LANCZOS)
    
    return enhanced