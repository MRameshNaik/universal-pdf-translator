



###################### Claudes improved code ###################################



# """
# pdf_utils.py  —  Utility helpers for the PDF translation pipeline.

# Improvements over v1:
#   • DPI raised 150 → 250 for sharper complex-script glyphs (Telugu, Kannada …)
#   • pdf_to_base64_images  now also returns pdfplumber word-level text per page
#     (dual-channel:  image  for layout,  text  for word accuracy)
#   • html_to_pdf  no longer adds page-break-after on the LAST page  →  no trailing blank
#   • html_to_pdf  runs a BeautifulSoup repair pass before rendering  →  safe from broken AI HTML
#   • Unicode checkbox post-processing:  [ ]→☐   [X]→☑
#   • Added img CSS guard  (display:block; max-width:100%)
#   • Font size reduced 10.5pt → 10pt body, 9pt inside table cells
#   • PDF metadata (Title, Language) injected via <meta> tags
#   • box-sizing: border-box on everything prevents edge bleed
# """

# import base64
# import os
# import re

# import fitz  # PyMuPDF
# import pdfplumber
# from bs4 import BeautifulSoup
# from weasyprint import HTML
# from weasyprint.text.fonts import FontConfiguration

# # ---------------------------------------------------------------------------
# # Font map
# # ---------------------------------------------------------------------------
# FONT_MAP = {
#     "English":   {"regular": "NotoSans-Regular.ttf",            "bold": "NotoSans-Bold.ttf"},
#     "Hindi":     {"regular": "NotoSansDevanagari-Regular.ttf",  "bold": "NotoSansDevanagari-Bold.ttf"},
#     "Telugu":    {"regular": "NotoSansTelugu-Regular.ttf",      "bold": "NotoSansTelugu-Bold.ttf"},
#     "Tamil":     {"regular": "NotoSansTamil-Regular.ttf",       "bold": "NotoSansTamil-Bold.ttf"},
#     "Kannada":   {"regular": "NotoSansKannada-Regular.ttf",     "bold": "NotoSansKannada-Bold.ttf"},
#     "Malayalam": {"regular": "NotoSansMalayalam-Regular.ttf",   "bold": "NotoSansMalayalam-Bold.ttf"},
#     "Bengali":   {"regular": "NotoSansBengali-Regular.ttf",     "bold": "NotoSansBengali-Bold.ttf"},
#     "Gujarati":  {"regular": "NotoSansGujarati-Regular.ttf",    "bold": "NotoSansGujarati-Bold.ttf"},
# }

# # ---------------------------------------------------------------------------
# # Extraction  —  dual-channel: base64 images  +  pdfplumber word text
# # ---------------------------------------------------------------------------

# def pdf_to_base64_images(pdf_path: str, dpi: int = 250):
#     """
#     Rasterise every page at *dpi* and also extract structured word-level text
#     via pdfplumber for the dual-channel prompt.

#     Returns
#     -------
#     images : list[str]
#         Base-64 encoded PNG strings, one per page.
#     page_texts : list[str]
#         Plain-text extraction per page  (empty string if extraction fails).
#         Each word is separated by a space; lines by newline.
#     """
#     # --- rasterise with PyMuPDF at higher DPI ---
#     doc = fitz.open(pdf_path)
#     images: list[str] = []
#     for page in doc:
#         pix = page.get_pixmap(dpi=dpi)
#         img_bytes = pix.tobytes("png")
#         images.append(base64.b64encode(img_bytes).decode("utf-8"))
#     doc.close()

#     # --- word-level text extraction with pdfplumber ---
#     page_texts: list[str] = []
#     try:
#         with pdfplumber.open(pdf_path) as plumb:
#             for page in plumb.pages:
#                 words = page.extract_words(
#                     x_tolerance=3,
#                     y_tolerance=3,
#                     keep_blank_chars=False,
#                     use_text_flow=True,
#                 )
#                 if words:
#                     # Reconstruct reading-order lines by grouping close y values
#                     lines: dict[int, list[str]] = {}
#                     for w in words:
#                         y_key = round(w["top"] / 5) * 5        # bucket to 5-pt rows
#                         lines.setdefault(y_key, []).append(w["text"])
#                     text = "\n".join(
#                         " ".join(line_words)
#                         for _, line_words in sorted(lines.items())
#                     )
#                 else:
#                     text = ""
#                 page_texts.append(text)
#     except Exception as exc:
#         print(f"[WARNING] pdfplumber extraction failed: {exc}")
#         page_texts = [""] * len(images)

#     return images, page_texts


# # ---------------------------------------------------------------------------
# # Post-processing helpers
# # ---------------------------------------------------------------------------

# def _fix_underscores(html: str) -> str:
#     """
#     Replace 3+ consecutive underscores with a CSS blank-line span.
#     Guard: only fire if real underscores are present (not inside attribute
#     values like  style="text-decoration:underline").
#     """
#     if re.search(r'(?<!["\'])_{3,}(?!["\'])', html):
#         html = re.sub(r'_{3,}', '<span class="blank-line"></span>', html)
#     return html


# def _fix_checkboxes(html: str) -> str:
#     """Replace ASCII checkbox notation with proper Unicode glyphs."""
#     html = re.sub(r'\[X\]', '☑', html, flags=re.IGNORECASE)
#     html = re.sub(r'\[ \]', '☐', html)
#     return html


# def _repair_html(html: str) -> str:
#     """
#     Run a BeautifulSoup parse-and-repair pass so that unclosed or malformed
#     tags from the AI don't corrupt WeasyPrint's layout.
#     """
#     try:
#         soup = BeautifulSoup(html, "html.parser")
#         return str(soup)
#     except Exception as exc:
#         print(f"[WARNING] HTML repair failed, using raw output: {exc}")
#         return html


# def postprocess_page_html(raw_html: str) -> str:
#     """Apply all post-processing steps to a single translated page."""
#     html = raw_html.replace("```html", "").replace("```", "").strip()
#     html = _fix_underscores(html)
#     html = _fix_checkboxes(html)
#     html = _repair_html(html)
#     return html


# # ---------------------------------------------------------------------------
# # Rendering  —  html_to_pdf
# # ---------------------------------------------------------------------------

# def html_to_pdf(
#     html_pages: list[str],
#     output_path: str,
#     target_lang: str,
#     study_title: str = "Informed Consent Document",
# ):
#     """
#     Combine translated HTML pages into a single A4 PDF.

#     Changes vs v1
#     -------------
#     • No page-break-after on the LAST page  →  eliminates trailing blank page.
#     • img { display:block; max-width:100% } guard.
#     • Font size 10.5pt → 10pt body; 9pt inside table cells.
#     • PDF metadata injected via <meta> tags.
#     • box-sizing: border-box on all elements.
#     """
#     font_info = FONT_MAP.get(target_lang, FONT_MAP["English"])
#     base_dir  = os.path.abspath(os.path.dirname(__file__))
#     reg_font  = os.path.join(base_dir, "fonts", font_info["regular"]).replace("\\", "/")
#     bold_font = os.path.join(base_dir, "fonts", font_info["bold"]).replace("\\", "/")

#     # Language code for <html lang="…"> (best-effort map)
#     lang_code_map = {
#         "Hindi": "hi", "Telugu": "te", "Tamil": "ta", "Kannada": "kn",
#         "Malayalam": "ml", "Bengali": "bn", "Gujarati": "gu", "English": "en",
#     }
#     lang_code = lang_code_map.get(target_lang, "en")

#     css = f"""
#         @font-face {{
#             font-family: 'TargetFont';
#             src: url('file:///{reg_font}');
#             font-weight: normal;
#         }}
#         @font-face {{
#             font-family: 'TargetFont';
#             src: url('file:///{bold_font}');
#             font-weight: bold;
#         }}

#         /* --- Box model -------------------------------------------------- */
#         *, *::before, *::after {{
#             box-sizing: border-box;
#         }}

#         /* --- Page setup -------------------------------------------------- */
#         @page {{
#             size: A4;
#             margin: 0.75in;
#         }}

#         /* --- Body -------------------------------------------------------- */
#         body {{
#             font-family: 'TargetFont', sans-serif;
#             font-size: 10pt;          /* was 10.5pt — denser scripts need room */
#             line-height: 1.5;
#             color: #000;
#             margin: 0;
#             padding: 0;
#             max-width: 100%;
#         }}

#         /* --- Prevent WeasyPrint infinite-page bug ----------------------- */
#         html, body, .page-container, div, table, tr, td, th {{
#             height: auto !important;
#             max-height: none !important;
#         }}

#         /* --- Tables ------------------------------------------------------ */
#         table {{
#             border-collapse: collapse;
#             width: 100% !important;
#             margin-bottom: 12px;
#             table-layout: auto !important;
#         }}

#         td, th {{
#             padding: 6px 8px;
#             font-size: 9pt;           /* tighter in cells to avoid overflow */
#             vertical-align: top;
#             text-align: left;
#             word-wrap: break-word;
#             overflow-wrap: break-word;
#         }}

#         table.grid-table,
#         table.grid-table td,
#         table.grid-table th {{
#             border: 1px solid #000;
#         }}

#         table.borderless,
#         table.borderless td,
#         table.borderless th {{
#             border: none !important;
#         }}

#         /* --- Page containers --------------------------------------------- */
#         /* NOTE: page-break-after is added inline per page;
#                  the LAST page gets none to avoid trailing blank. */
#         .page-container {{
#             width: 100%;
#         }}

#         /* --- Blank form-field line --------------------------------------- */
#         .blank-line {{
#             display: inline-block;
#             min-width: 120px;
#             border-bottom: 1px solid #000;
#             margin: 0 4px;
#         }}
#         .blank-line::after {{
#             content: "\\00A0";
#         }}

#         /* --- Images ------------------------------------------------------ */
#         img {{
#             display: block;
#             max-width: 100%;
#             height: auto;
#         }}

#         /* --- Fallback page (translation blocked) ------------------------- */
#         .fallback-banner {{
#             color: red;
#             border: 2px solid red;
#             padding: 12px 15px;
#             margin-bottom: 16px;
#             font-weight: bold;
#         }}
#     """

#     # Build the full HTML document
#     pages_html = ""
#     last_idx = len(html_pages) - 1
#     for i, page_html in enumerate(html_pages):
#         # Only add page-break BEFORE the last page, not after it
#         break_style = "page-break-after: always;" if i < last_idx else ""
#         pages_html += f"<div class='page-container' style='{break_style}'>{page_html}</div>\n"

#     combined_html = f"""<!DOCTYPE html>
# <html lang="{lang_code}">
# <head>
#     <meta charset="UTF-8">
#     <meta name="Title" content="{study_title} — {target_lang}">
#     <meta name="Language" content="{lang_code}">
#     <meta name="Author" content="Auto-translated by PDF Translation Pipeline">
#     <style>{css}</style>
# </head>
# <body>
# {pages_html}
# </body>
# </html>"""

#     os.makedirs(os.path.dirname(output_path), exist_ok=True)
#     font_config = FontConfiguration()
#     HTML(string=combined_html).write_pdf(output_path, font_config=font_config)
#     return output_path

######################### version 222#################
# import base64
# import os
# import re

# import fitz  # PyMuPDF
# import pdfplumber
# from bs4 import BeautifulSoup
# from weasyprint import HTML
# from weasyprint.text.fonts import FontConfiguration

# FONT_MAP = {
#     "English":   {"regular": "NotoSans-Regular.ttf",            "bold": "NotoSans-Bold.ttf"},
#     "Hindi":     {"regular": "NotoSansDevanagari-Regular.ttf",  "bold": "NotoSansDevanagari-Bold.ttf"},
#     "Telugu":    {"regular": "NotoSansTelugu-Regular.ttf",      "bold": "NotoSansTelugu-Bold.ttf"},
#     "Tamil":     {"regular": "NotoSansTamil-Regular.ttf",       "bold": "NotoSansTamil-Bold.ttf"},
#     "Kannada":   {"regular": "NotoSansKannada-Regular.ttf",     "bold": "NotoSansKannada-Bold.ttf"},
#     "Malayalam": {"regular": "NotoSansMalayalam-Regular.ttf",   "bold": "NotoSansMalayalam-Bold.ttf"},
#     "Bengali":   {"regular": "NotoSansBengali-Regular.ttf",     "bold": "NotoSansBengali-Bold.ttf"},
#     "Gujarati":  {"regular": "NotoSansGujarati-Regular.ttf",    "bold": "NotoSansGujarati-Bold.ttf"},
# }

# def pdf_to_base64_images(pdf_path: str, dpi: int = 250):
#     doc = fitz.open(pdf_path)
#     images: list[str] = []
#     for page in doc:
#         pix = page.get_pixmap(dpi=dpi)
#         img_bytes = pix.tobytes("png")
#         images.append(base64.b64encode(img_bytes).decode("utf-8"))
#     doc.close()

#     page_texts: list[str] = []
#     try:
#         with pdfplumber.open(pdf_path) as plumb:
#             for page in plumb.pages:
#                 words = page.extract_words(
#                     x_tolerance=3,
#                     y_tolerance=3,
#                     keep_blank_chars=False,
#                     use_text_flow=True,
#                 )
#                 if words:
#                     lines: dict[int, list[str]] = {}
#                     for w in words:
#                         y_key = round(w["top"] / 5) * 5
#                         lines.setdefault(y_key, []).append(w["text"])
#                     text = "\n".join(" ".join(line_words) for _, line_words in sorted(lines.items()))
#                 else:
#                     text = ""
#                 page_texts.append(text)
#     except Exception as exc:
#         print(f"[WARNING] pdfplumber extraction failed: {exc}")
#         page_texts = [""] * len(images)

#     return images, page_texts

# def _fix_underscores(html: str) -> str:
#     if re.search(r'(?<!["\'])_{3,}(?!["\'])', html):
#         html = re.sub(r'_{3,}', '<span class="blank-line"></span>', html)
#     return html

# def _fix_checkboxes(html: str) -> str:
#     html = re.sub(r'\[X\]', '☑', html, flags=re.IGNORECASE)
#     html = re.sub(r'\[ \]', '☐', html)
#     return html

# def _repair_html(html: str) -> str:
#     try:
#         soup = BeautifulSoup(html, "html.parser")
#         return str(soup)
#     except Exception as exc:
#         print(f"[WARNING] HTML repair failed, using raw output: {exc}")
#         return html

# def postprocess_page_html(raw_html: str) -> str:
#     html = raw_html.replace("```html", "").replace("```", "").strip()
#     html = _fix_underscores(html)
#     html = _fix_checkboxes(html)
#     html = _repair_html(html)
#     return html

# def html_to_pdf(html_pages: list[str], output_path: str, target_lang: str, study_title: str = "Informed Consent Document"):
#     font_info = FONT_MAP.get(target_lang, FONT_MAP["English"])
#     base_dir  = os.path.abspath(os.path.dirname(__file__))
#     reg_font  = os.path.join(base_dir, "fonts", font_info["regular"]).replace("\\", "/")
#     bold_font = os.path.join(base_dir, "fonts", font_info["bold"]).replace("\\", "/")

#     lang_code_map = {
#         "Hindi": "hi", "Telugu": "te", "Tamil": "ta", "Kannada": "kn",
#         "Malayalam": "ml", "Bengali": "bn", "Gujarati": "gu", "English": "en",
#     }
#     lang_code = lang_code_map.get(target_lang, "en")

#     css = f"""
#         @font-face {{
#             font-family: 'TargetFont';
#             src: url('file:///{reg_font}');
#             font-weight: normal;
#         }}
#         @font-face {{
#             font-family: 'TargetFont';
#             src: url('file:///{bold_font}');
#             font-weight: bold;
#         }}

#         *, *::before, *::after {{
#             box-sizing: border-box;
#         }}

#         @page {{
#             size: A4;
#             margin: 0.75in;
#         }}

#         body {{
#             font-family: 'TargetFont', sans-serif;
#             font-size: 10pt;
#             line-height: 1.5;
#             color: #000;
#             margin: 0;
#             padding: 0;
#             max-width: 100%;
#         }}

#         html, body, .page-container, div, table, tr, td, th {{
#             height: auto !important;
#             max-height: none !important;
#         }}

#         table {{
#             border-collapse: collapse;
#             width: 100% !important;
#             margin-bottom: 12px;
#             table-layout: auto !important;
#         }}

#         td, th {{
#             padding: 6px 8px;
#             font-size: 9pt;
#             vertical-align: top;
#             text-align: left;
#             word-wrap: break-word;
#             overflow-wrap: break-word;
#         }}

#         table.grid-table, table.grid-table td, table.grid-table th {{
#             border: 1px solid #000;
#         }}

#         table.borderless, table.borderless td, table.borderless th {{
#             border: none !important;
#         }}

#         .page-container {{
#             width: 100%;
#         }}

#         /* --- THE BLANK LINE FIX --- */
#         .blank-line {{
#             display: inline-block;
#             min-width: 120px;
#             border-bottom: 1px solid #000;
#             margin: 0 4px;
#             vertical-align: bottom; /* Forces the line to sit flush with the text baseline */
#         }}
#         .blank-line::after {{
#             content: "\\00A0";
#         }}

#         img {{
#             display: block;
#             max-width: 100%;
#             height: auto;
#         }}

#         .fallback-banner {{
#             color: red;
#             border: 2px solid red;
#             padding: 12px 15px;
#             margin-bottom: 16px;
#             font-weight: bold;
#         }}
#     """

#     pages_html = ""
#     last_idx = len(html_pages) - 1
#     for i, page_html in enumerate(html_pages):
#         break_style = "page-break-after: always;" if i < last_idx else ""
#         pages_html += f"<div class='page-container' style='{break_style}'>{page_html}</div>\n"

#     combined_html = f"""<!DOCTYPE html>
# <html lang="{lang_code}">
# <head>
#     <meta charset="UTF-8">
#     <meta name="Title" content="{study_title} — {target_lang}">
#     <meta name="Language" content="{lang_code}">
#     <style>{css}</style>
# </head>
# <body>
# {pages_html}
# </body>
# </html>"""

#     os.makedirs(os.path.dirname(output_path), exist_ok=True)
#     font_config = FontConfiguration()
#     HTML(string=combined_html).write_pdf(output_path, font_config=font_config)
#     return output_path


import fitz  # PyMuPDF
import base64
import os
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

FONT_MAP = {
    "English": {"regular": "NotoSans-Regular.ttf", "bold": "NotoSans-Bold.ttf"},
    "Hindi": {"regular": "NotoSansDevanagari-Regular.ttf", "bold": "NotoSansDevanagari-Bold.ttf"},
    "Telugu": {"regular": "NotoSansTelugu-Regular.ttf", "bold": "NotoSansTelugu-Bold.ttf"},
    "Tamil": {"regular": "NotoSansTamil-Regular.ttf", "bold": "NotoSansTamil-Bold.ttf"},
    "Kannada": {"regular": "NotoSansKannada-Regular.ttf", "bold": "NotoSansKannada-Bold.ttf"},
    "Malayalam": {"regular": "NotoSansMalayalam-Regular.ttf", "bold": "NotoSansMalayalam-Bold.ttf"},
    "Bengali": {"regular": "NotoSansBengali-Regular.ttf", "bold": "NotoSansBengali-Bold.ttf"},
    "Gujarati": {"regular": "NotoSansGujarati-Regular.ttf", "bold": "NotoSansGujarati-Bold.ttf"}
}

def pdf_to_base64_images(pdf_path):
    doc = fitz.open(pdf_path)
    base64_images = []
    for page in doc:
        # CLOUD OPTIMIZATION: 150 DPI reduces RAM usage by 60% on Render Free Tier
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        base64_images.append(b64_img)
    doc.close()
    return base64_images

def html_to_pdf(html_pages, output_path, target_lang):
    font_info = FONT_MAP.get(target_lang, FONT_MAP["English"])
    base_dir = os.path.abspath(os.path.dirname(__file__))
    reg_font_path = os.path.join(base_dir, "fonts", font_info["regular"]).replace('\\', '/')
    bold_font_path = os.path.join(base_dir, "fonts", font_info["bold"]).replace('\\', '/')
    
    combined_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @font-face {{
                font-family: 'TargetFont';
                src: url('file:///{reg_font_path}');
                font-weight: normal;
            }}
            @font-face {{
                font-family: 'TargetFont';
                src: url('file:///{bold_font_path}');
                font-weight: bold;
            }}
            
            @page {{
                size: A4;
                margin: 0.75in;
            }}
            
            body {{
                font-family: 'TargetFont', sans-serif;
                font-size: 10.5pt;
                line-height: 1.5;
                color: #000;
                margin: 0;
                padding: 0;
            }}
            
            table {{ 
                border-collapse: collapse; 
                width: 100% !important; 
                margin-bottom: 15px;
                table-layout: fixed !important; 
            }}
            tr {{ page-break-inside: avoid !important; }}
            td, th {{ 
                padding: 8px; 
                vertical-align: top;
                text-align: left;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }}
            table.grid-table, table.grid-table td, table.grid-table th {{
                border: 1px solid black;
            }}
            
            /* --- THE FORM BLANK COMPONENT --- */
            .form-blank {{
                display: inline-block;
                min-width: 150px;
                border-bottom: 1px solid black;
                margin: 0 5px;
                vertical-align: bottom;
            }}
            .form-blank::after {{
                content: "\\00A0"; 
            }}
            
            /* --- THE SIGNATURE BLOCK COMPONENT --- */
            table.signature-table {{
                border: none !important;
                margin-top: 30px;
                page-break-inside: avoid !important; /* FIX: Prevents splitting across pages */
            }}
            table.signature-table td {{
                border: none !important;
                text-align: center;
                vertical-align: bottom;
                width: 33.33% !important; 
            }}
            
            .page-container {{
                page-break-after: always;
                width: 100%;
            }}
        </style>
    </head>
    <body>
    """
    
    for page_html in html_pages:
        combined_html += f"<div class='page-container'>{page_html}</div>"
        
    combined_html += "</body></html>"
    
    font_config = FontConfiguration()
    HTML(string=combined_html).write_pdf(output_path, font_config=font_config)
    
    return output_path