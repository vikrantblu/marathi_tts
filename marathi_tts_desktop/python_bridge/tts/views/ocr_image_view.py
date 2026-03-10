import os
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.conf import settings
from ..utils.text.text_processor import clean_text, is_marathi_text
from ..utils.text.image_processor import preprocess_image_for_ocr

logger = logging.getLogger(__name__)

def check_tesseract_installation():
    try:
        import pytesseract  # type: ignore
        pytesseract.get_tesseract_version()
    except ImportError:
        raise RuntimeError("pytesseract is not installed. Run: pip install pytesseract")
    except Exception as e:
        if "TesseractNotFoundError" in type(e).__name__ or "not installed" in str(e).lower():
            logger.error("Tesseract binary is not installed or not in PATH")
            raise RuntimeError(
                "Tesseract OCR binary is not installed. "
                "Download from: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        logger.error(f"Error checking Tesseract installation: {e}")
        raise

@csrf_protect
@require_http_methods(["POST"])
def extract_text_from_image(request):
    """Extract Marathi text from uploaded images using OCR"""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        check_tesseract_installation()
        image_data = request.FILES.get('image')
        if not image_data:
            return JsonResponse({'success': False, 'error': 'छायाचित्र आवश्यक आहे'}, status=400)

        # Validate image upload: magic bytes + size limit (10 MB)
        from ..utils.security import validate_image_upload
        is_valid, err_msg = validate_image_upload(image_data)
        if not is_valid:
            return JsonResponse({'success': False, 'error': err_msg}, status=400)
        
        # Open and preprocess the image for better Devanagari OCR
        image = Image.open(image_data)
        
        # Convert to RGB if needed (preprocess_image_for_ocr expects RGB)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        elif image.mode == 'L':
            image = image.convert('RGB')
        
        logger.info(f"Processing image: {filename}, size: {image.size}")
        
        # Use improved preprocessing pipeline
        processed_image = preprocess_image_for_ocr(image)
        
        # Extract text: OEM 1 (LSTM), PSM 6 (uniform text block), Marathi + Hindi + Sanskrit
        custom_config = r'--oem 1 --psm 6 -l mar+hin+san --dpi 300'
        extracted_text = pytesseract.image_to_string(processed_image, config=custom_config)
        
        # Fallback: try with different PSM if first attempt yields nothing
        if not extracted_text or not extracted_text.strip():
            custom_config_fallback = r'--oem 1 --psm 3 -l mar+hin --dpi 300'
            extracted_text = pytesseract.image_to_string(processed_image, config=custom_config_fallback)
        
        # Clean and validate the extracted text
        cleaned_text = clean_text(extracted_text) if extracted_text else ""
        
        # Check if any valid text was extracted
        if not cleaned_text.strip():
            return JsonResponse({
                'success': False, 
                'error': 'छायाचित्रातून वाचनयोग्य मराठी मजकूर मिळाला नाही'
            }, status=400)
        
        # Return the extracted text
        return JsonResponse({
            'success': True,
            'text': cleaned_text
        })
        
    except Exception as e:
        logger.error(f"OCR Error: {str(e)}")
        return JsonResponse({
            'success': False, 
            'error': f'मजकूर मिळवण्यात त्रुटी आली: {str(e)}'
        }, status=500)