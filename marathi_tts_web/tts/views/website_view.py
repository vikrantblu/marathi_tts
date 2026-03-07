


import re
import io
import logging
import os
import tempfile
from urllib.parse import urljoin

# Configure logger
logger = logging.getLogger(__name__)

from bs4 import BeautifulSoup
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_http_methods
from ..utils.text.text_processor import clean_text, clean_web_text, is_marathi_text, is_ocr_garbage


# ---------------------------------------------------------------------------
# Special site handlers — for JS-heavy sites that embed content in <script>
# ---------------------------------------------------------------------------

def _try_abhyaskosh(html: str, url: str) -> str:
    """Extract Jnaneshwari / Gita content from abhyaskosh.org.

    This site renders content via JavaScript from inline JSON variables
    (adhyayStr, shlokaStr, oviStr).  BeautifulSoup cannot see the rendered
    DOM, so we parse the JSON directly from the HTML source.
    """
    lines = []

    # Extract chapter metadata
    m = re.search(r'var\s+adhyayStr\s*=\s*(\{.*?\});', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            entries = data.get('data', [])
            if entries:
                e = entries[0]
                intro = e.get('introduction', '')
                subject = e.get('subject', '')
                if intro:
                    lines.append(intro)
                if subject:
                    lines.append(subject)
        except (ValueError, KeyError):
            pass

    # Extract Ovis (Jnaneshwari verses) — primary content
    m = re.search(r'var\s+oviStr\s*=\s*(\{.*?\})\s*;', html, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            for ovi in data.get('data', []):
                text = ovi.get('text', '').strip()
                if text:
                    lines.append(text)
        except (ValueError, KeyError):
            pass

    # Extract Shlokas (Gita verses embedded with chapter)
    m = re.search(r'var\s+shlokaStr\s*=\s*(\{.*?\})\s*;', html, re.DOTALL)
    if m:
        raw_json = m.group(1)
        raw_json = re.sub(r',\s*([}\]])', r'\1', raw_json)
        try:
            data = json.loads(raw_json)
            for shloka in data.get('data', []):
                text = shloka.get('text', '').strip()
                if text:
                    lines.append(text)
        except (ValueError, KeyError):
            pass

    # Extract chapter conclusion
    try:
        m2 = re.search(r'var\s+adhyayStr\s*=\s*(\{.*?\});', html, re.DOTALL)
        if m2:
            data = json.loads(m2.group(1))
            entries = data.get('data', [])
            if entries:
                conclusion = entries[0].get('conclusion', '')
                if conclusion:
                    lines.append(conclusion)
    except Exception:
        pass

    result = '\n'.join(lines)
    logger.info("[abhyaskosh] Extracted %d lines, %d chars", len(lines), len(result))
    return result


def _is_abhyaskosh_url(url: str) -> bool:
    """Check if URL belongs to abhyaskosh.org."""
    return 'abhyaskosh.org' in url.lower()


@csrf_protect
@require_http_methods(["POST"])
def fetch_website_content(request):
    try:
        data = json.loads(request.body)
        url = data.get('url')
        
        if not url:
            return JsonResponse({'success': False, 'error': 'URL is required'})
        
        try:
            # Use a realistic User-Agent — some sites block bare requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'mr,hi;q=0.9,en;q=0.8',
            }
            response = requests.get(url, headers=headers, verify=True, timeout=20)
            response.raise_for_status()

            # Handle encoding — respect HTTP header, then meta charset, then fallback
            if response.encoding and response.encoding.lower() != 'iso-8859-1':
                page_text = response.text
            else:
                response.encoding = response.apparent_encoding or 'utf-8'
                page_text = response.text

            # ── Special site handlers (JS-heavy sites) ────────────────
            if _is_abhyaskosh_url(url):
                special_text = _try_abhyaskosh(page_text, url)
                if special_text and len(special_text) > 50:
                    logger.info("[Special] abhyaskosh.org handler extracted %d chars", len(special_text))
                    soup = BeautifulSoup(page_text, 'html.parser')
                    title_tag = soup.find("title")
                    title = title_tag.get_text(strip=True) if title_tag else ""
                    cleaned_content = clean_web_text(special_text)
                    if title:
                        cleaned_content = f"{title}\n\n{cleaned_content}"
                    return JsonResponse({
                        'success': True,
                        'content': cleaned_content,
                        'image_count': 0,
                    })

            soup = BeautifulSoup(page_text, 'html.parser')
            
            # Get post metadata
            metadata = extract_post_metadata(soup)
            
            # Extract text content
            text_content = extract_main_content(soup)
            
            # Add metadata to the beginning if found
            if metadata.get('title'):
                text_content = f"{metadata.get('title')}\n\n{text_content}"
            
            # Process images if OCR is enabled
            process_images = data.get('process_images', True)
            ocr_results = []
            
            if process_images:
                logger.info(f"Fetching text from {url} for TTS Processing")
                # Find all images in the main content area
                images = find_content_images(soup, url)
                
                # Process up to 5 images (to limit processing time)
                for img_url in images[:5]:
                    try:
                        img_text = extract_text_from_image_url(img_url)
                        if img_text and len(img_text) > 20:  # Only keep substantial text
                            ocr_results.append(img_text)
                            logger.info(f"Successfully extracted text from image: {img_url[:50]}...")
                    except Exception as img_error:
                        logger.error(f"Error processing image URL {img_url}: {str(img_error)}")
            
            # Combine text content with OCR results
            combined_content = text_content
            
            if ocr_results:
                combined_content += "\n\n".join(ocr_results)
            
            # Light cleaning — preserve original text faithfully for display
            # (clean_text does TTS-specific transforms like abbreviation expansion)
            cleaned_content = clean_web_text(combined_content)
            
            return JsonResponse({
                'success': True,
                'content': cleaned_content,
                'image_count': len(ocr_results)
            })
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch content from {url}: {str(e)}")
            return JsonResponse({
                'success': False, 
                'error': 'वेबसाइट मधून मजकूर मिळवण्यात त्रुटी आली'
            })
            
    except Exception as e:
        logger.error(f"Unexpected error in fetch_website_content: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'अनपेक्षित त्रुटी आली'
        })

def extract_text_from_image_url(img_url):
    """Download image from URL and extract text using OCR"""
    try:
        # Lazy imports — only needed for OCR, avoids startup crash if Tesseract/cv2 not installed
        from PIL import Image
        try:
            import pytesseract
        except ImportError:
            logger.warning("pytesseract not available — image OCR skipped")
            return ""
        try:
            from ..utils.text.image_processor import preprocess_image_for_ocr
        except Exception:
            preprocess_image_for_ocr = None

        # Download image
        img_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        response = requests.get(img_url, headers=img_headers, stream=True, verify=True, timeout=10)
        response.raise_for_status()
        
        # Open image from response content
        img = Image.open(io.BytesIO(response.content))
        
        # Skip images that are too small for meaningful OCR
        if img.width < 200 or img.height < 100:
            logger.debug(f"Skipping small image: {img_url} ({img.width}x{img.height})")
            return ""
        
        # Skip images that are too wide/narrow (likely banners, buttons, decorative)
        aspect_ratio = img.width / max(img.height, 1)
        if aspect_ratio > 5 or aspect_ratio < 0.15:
            logger.debug(f"Skipping extreme aspect ratio image: {img_url} ({img.width}x{img.height})")
            return ""
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            try:
                img = img.convert('RGB')
            except Exception as e:
                logger.warning(f"Could not convert image mode {img.mode} to RGB: {e}")
                return ""
        
        # Preprocess for better OCR quality (if cv2-based preprocessor is available)
        if preprocess_image_for_ocr is not None:
            processed_image = preprocess_image_for_ocr(img)
        else:
            processed_image = img
        
        # Use pytesseract with Marathi + Hindi + Sanskrit for better Devanagari recognition
        # OEM 1 = LSTM neural net, PSM 6 = uniform block of text
        extracted_text = pytesseract.image_to_string(
            processed_image,
            config='--oem 1 --psm 6 -l mar+hin+san --dpi 300'
        )
        
        if not extracted_text or not extracted_text.strip():
            # Fallback: try with original unprocessed image
            extracted_text = pytesseract.image_to_string(
                img,
                config='--oem 1 --psm 3 -l mar+hin --dpi 300'
            )
        
        if not extracted_text or not extracted_text.strip():
            return ""
        
        # Validate OCR output quality before accepting
        if is_ocr_garbage(extracted_text):
            logger.info(f"Discarding OCR garbage from image: {img_url[:60]}...")
            return ""
        
        cleaned_text = clean_web_text(extracted_text)
        
        if not cleaned_text.strip():
            return ""
            
        return cleaned_text
    
    except Exception as e:
        logger.error(f"Error processing image URL {img_url}: {str(e)}")
        return ""
        
def _strip_date_prefix(text):
    """Remove leading date patterns from text (any language/format)."""
    # ISO dates, slash/dot dates, English month names
    text = re.sub(
        r'^(?:\d{1,4}[-/\.]\d{1,2}[-/\.]\d{2,4}|'
        r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'\s+\d{1,2},?\s+\d{4}|'
        r'\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'\s+\d{4})\s*',
        '', text, flags=re.IGNORECASE
    )
    return text.strip()


def extract_post_metadata(soup):
    """Extract post title and date from any website.
    Uses progressively broader selectors and falls back to <title> / og:title.
    """
    metadata = {}
    
    # --- Title extraction (ordered: most-specific → broadest) ---
    title_selectors = [
        'h1.post-title', 'h1.entry-title',
        'article h1', '.post-title', '.entry-title',
        'h1.title', 'h1.headline', '.headline',
        'h1',  # last resort among visible headings
    ]
    for selector in title_selectors:
        title_elem = soup.select_one(selector)
        if title_elem:
            raw = _strip_date_prefix(title_elem.get_text(' ', strip=True))
            if raw and len(raw) > 2:
                metadata['title'] = raw
                break
    
    # Fallback to OpenGraph / meta title / <title>
    if 'title' not in metadata:
        og = soup.find('meta', property='og:title')
        if og and og.get('content', '').strip():
            metadata['title'] = _strip_date_prefix(og['content'].strip())
    if 'title' not in metadata:
        t = soup.find('title')
        if t:
            # <title> often contains " – Site Name"; take only the first part
            raw = t.get_text(strip=True).split('|')[0].split('–')[0].split('—')[0].strip()
            raw = _strip_date_prefix(raw)
            if raw:
                metadata['title'] = raw
    
    # --- Date extraction ---
    date_selectors = [
        '.post-date', '.entry-date', '.date',
        'time[datetime]', 'time', '.post-meta time',
        '.published', '.dateline', '.byline time',
    ]
    for selector in date_selectors:
        date_elem = soup.select_one(selector)
        if date_elem:
            metadata['date'] = date_elem.get('datetime') or date_elem.get_text(strip=True)
            break
    
    # Fallback: article:published_time meta
    if 'date' not in metadata:
        pub = soup.find('meta', property='article:published_time')
        if pub and pub.get('content'):
            metadata['date'] = pub['content']
    
    return metadata

def extract_main_content(soup):
    """Extract main article content with fallback options"""
    try:
        # First try targeted content extraction
        content = traditional_content_extraction(soup)
        
        if not content or len(content.strip()) < 50:
            # Fallback to broader extraction
            content = basic_content_extraction(soup)
            
        return clean_text_content(content)
        
    except Exception as e:
        logger.error(f"Content extraction failed: {str(e)}")
        return ""

def clean_text_content(text):
    """Clean and normalize extracted text"""
    # Remove empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Remove duplicate lines
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    
    # Join lines with proper spacing
    text = '\n\n'.join(unique_lines)
    
    # Fix extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Generic noise patterns (not tied to any specific website)
    noise_patterns = [
        r'Share\s+this:',
        r'Like\s+this:',
        r'Copyright\s*©.*',
        r'©\s*\d{4}.*',
        r'All\s+rights?\s+reserved\.?',
        r'Subscribe\s+to:.*',
        r'Blog\s+at.*',
        r'Powered\s+by.*',
        r'\d+\s+Comments?',
        r'Leave\s+a\s+comment',
        r'Posted\s+(?:in|on|by).*',
        r'Tagged\s+(?:with|in).*',
        r'Filed\s+under.*',
        r'Labels?:.*',
        r'Categor(?:y|ies):.*',
        r'No\s+comments?:?',
        r'Post\s+a\s+Comment',
        r'Newer\s+Post.*Older\s+Post',
        r'(?:Next|Previous)\s+(?:Post|Article)',
        r'Home\s*$',
        r'Read\s+more\.{0,3}$',
        r'Continue\s+reading\.{0,3}$',
        r'\b\d{10,}\b',  # Bare phone numbers (any language)
    ]
    
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()

def basic_content_extraction(soup):
    """Basic content extraction without AI"""
    # Remove unwanted elements
    for unwanted in soup.select('script, style, nav, header, footer, .sidebar, .comments'):
        unwanted.decompose()
        
    # Get all text blocks
    text_blocks = []
    for element in soup.find_all(['p', 'article', 'div']):
        text = element.get_text(strip=True)
        if len(text) > 100:  # Only consider substantial blocks
            text_blocks.append(text)
            
    # Return longest text block
    return max(text_blocks, key=len, default='') if text_blocks else ''

def traditional_content_extraction(soup):
    """Extract content using generic heuristics.
    Works across WordPress, Blogger, Medium, Ghost, Hugo, Jekyll, Wix,
    custom CMS, and plain HTML pages — no site-specific logic.
    """
    # Remove clearly non-content elements.  We keep .widget because many
    # platforms (Blogger, WordPress themes) wrap main content inside it.
    decompose_selectors = (
        'script, style, noscript, iframe, svg, '
        'nav, header, footer, '
        '.sidebar, .widget-area, #sidebar, aside, '
        '.menu, .navbar, .nav, .topbar, '
        '.comments, .comment-form, #comments, .respond, '
        '.pagination, .blog-pager, #blog-pager, .pager, '
        '.feed-links, .post-share-buttons, .sharedaddy, .share-buttons, '
        '.post-feeds, .blog-feeds, '
        '.archive-list, .tag-cloud, .categories-list, '
        '.related-posts, .recommended, '
        '.cookie-notice, .popup, .modal, '
        '.ad, .advertisement, .adsbygoogle'
    )
    for unwanted in soup.select(decompose_selectors):
        unwanted.decompose()

    # Content selectors — ordered from most specific to broadest.
    # Covers WordPress, Blogger, Medium, Ghost, Hugo, Jekyll, generic HTML.
    content_selectors = [
        'article .entry-content',
        'article .post-content',
        '.entry-content',
        '.post-content',
        '.post-body',
        '.article-body',
        '.story-body',
        '.td-post-content',        # Flavor theme (WordPress)
        '.single-post-content',
        '#post-body',               # Blogger
        '.post-entry',
        'article',
        '[role="article"]',
        '[role="main"]',
        'main',
        '#main-content',
        '#content',
        '.content',
    ]

    for selector in content_selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text('\n', strip=True)
            if len(text) > 50:
                return text

    # Ultimate fallback: find the densest text block on the page
    return _extract_by_text_density(soup)


def _extract_by_text_density(soup):
    """Fallback: pick the DOM subtree with the highest text density.
    This works on pages with no semantic class names at all.
    """
    candidates = []
    for tag in soup.find_all(['div', 'section', 'td', 'article']):
        text = tag.get_text(strip=True)
        if len(text) < 100:
            continue
        # Density = ratio of text length to total HTML length
        html_len = len(str(tag))
        density = len(text) / max(html_len, 1)
        # Prefer blocks that have <p> children (real prose)
        p_count = len(tag.find_all('p', recursive=False))
        score = len(text) * density * (1 + p_count * 0.3)
        candidates.append((score, text))
    
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    
    # Nothing found — return all body text as last resort
    return soup.get_text('\n', strip=True) if soup.body else ''


def find_content_images(soup, base_url):
    """Find relevant images in the page content"""
    image_urls = []
    processed_urls = set()  # Track processed URLs to avoid duplicates
    
    # Common content containers where meaningful images might be found
    content_selectors = [
        'article', '.post-content', '.entry-content', 
        '#content', '.content', '.post-body',
        'main', '[role="main"]'
    ]
    
    # If no content areas found, use the body
    content_areas = []
    for selector in content_selectors:
        areas = soup.select(selector)
        if areas:
            content_areas.extend(areas)
    
    if not content_areas:
        content_areas = [soup.body] if soup.body else []
    
    # Common icon patterns to skip
    icon_patterns = [
        'icon', 'logo', 'avatar', 'button', 'btn', 'widget', 'banner',
        'emoji', 'smiley', 'profile', 'favicon', 'badge', 'arrow',
        'separator', 'divider', 'spacer', 'pixel', 'tracker',
        'loading', 'spinner', 'thumb', 'thumbnail'
    ]
    
    # Find all images in content areas
    for area in content_areas:
        for img in area.find_all('img'):
            # Skip if no source
            src = img.get('src') or img.get('data-src')
            if not src:
                continue
                
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, src)
            
            # Skip if already processed
            if absolute_url in processed_urls:
                continue
                
            processed_urls.add(absolute_url)
                
            # Skip common icon patterns
            skip = False
            for pattern in icon_patterns:
                if pattern in absolute_url.lower() or (img.get('class') and pattern in ' '.join(img.get('class')).lower()):
                    skip = True
                    break
            
            if skip:
                continue
                
            # Check dimensions from attributes
            width = img.get('width')
            height = img.get('height')
            
            try:
                # Skip tiny images (likely icons)
                if width and height:
                    w, h = int(width), int(height)
                    if w < 200 or h < 100:
                        continue
                    # Skip extreme aspect ratios (banners, buttons)
                    if w > 0 and h > 0 and (w / h > 5 or h / w > 7):
                        continue
            except (ValueError, TypeError):
                pass
            
            # Check if this is a likely content image
            img_classes = img.get('class', [])
            img_id = img.get('id', '')
            
            if isinstance(img_classes, str):
                img_classes = [img_classes]
                
            # Skip social media icons and other common non-content images
            skip_classes = [
                'social', 'share', 'follow', 'subscribe', 'navbar',
                'comment', 'reply', 'reaction', 'emoji', 'decoration',
                'sidebar', 'ad', 'promo', 'related', 'recommended'
            ]
            all_attrs = ' '.join(img_classes).lower() + ' ' + img_id.lower()
            if any(cls in all_attrs for cls in skip_classes):
                continue
            
            # Skip common non-content image file patterns
            img_filename = absolute_url.lower().split('/')[-1].split('?')[0]
            skip_filenames = ['blank.', 'spacer.', 'pixel.', 'transparent.', 'clear.']
            if any(fn in img_filename for fn in skip_filenames):
                continue
                
            # Add the image URL for processing
            image_urls.append(absolute_url)
    
    return image_urls