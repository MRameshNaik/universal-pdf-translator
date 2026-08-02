

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


################################ version 3 ########################

# import base64
# import os
# import re
# import fitz  # PyMuPDF
# import pdfplumber
# from bs4 import BeautifulSoup
# from weasyprint import HTML
# from weasyprint.text.fonts import FontConfiguration

# # SOTA: Script-specific settings to match English parity
# SCRIPT_SETTINGS = {
#     "English":   {"size": "10.5pt", "line_height": "1.4"},
#     "Hindi":     {"size": "9.5pt",  "line_height": "1.7"},
#     "Telugu":    {"size": "9.0pt",  "line_height": "1.8"},
#     "Kannada":   {"size": "9.0pt",  "line_height": "1.8"},
#     "Tamil":     {"size": "9.5pt",  "line_height": "1.7"},
#     "Malayalam": {"size": "9.0pt",  "line_height": "1.8"},
# }

# FONT_MAP = {
#     "English":   {"regular": "NotoSans-Regular.ttf",            "bold": "NotoSans-Bold.ttf"},
#     "Hindi":     {"regular": "NotoSansDevanagari-Regular.ttf",  "bold": "NotoSansDevanagari-Bold.ttf"},
#     "Telugu":    {"regular": "NotoSansTelugu-Regular.ttf",      "bold": "NotoSansTelugu-Bold.ttf"},
#     "Tamil":     {"regular": "NotoSansTamil-Regular.ttf",       "bold": "NotoSansTamil-Bold.ttf"},
#     "Kannada":   {"regular": "NotoSansKannada-Regular.ttf",     "bold": "NotoSansKannada-Bold.ttf"},
#     "Malayalam": {"regular": "NotoSansMalayalam-Regular.ttf",   "bold": "NotoSansMalayalam-Bold.ttf"},
# }

# def pdf_to_base64_images(pdf_path: str, dpi: int = 250):
#     """Dual-Channel Extraction: High-res images + Structured word-level text."""
#     doc = fitz.open(pdf_path)
#     images = []
#     for page in doc:
#         pix = page.get_pixmap(dpi=dpi)
#         img_bytes = pix.tobytes("png")
#         images.append(base64.b64encode(img_bytes).decode("utf-8"))
#     doc.close()

#     page_texts = []
#     try:
#         with pdfplumber.open(pdf_path) as plumb:
#             for page in plumb.pages:
#                 words = page.extract_words(x_tolerance=3, y_tolerance=3, use_text_flow=True)
#                 if words:
#                     lines = {}
#                     for w in words:
#                         y_key = round(w["top"] / 5) * 5
#                         lines.setdefault(y_key, []).append(w["text"])
#                     text = "\n".join(" ".join(line_words) for _, line_words in sorted(lines.items()))
#                 else:
#                     text = ""
#                 page_texts.append(text)
#     except Exception as exc:
#         print(f"[WARNING] pdfplumber failed: {exc}")
#         page_texts = [""] * len(images)
#     return images, page_texts

# def postprocess_page_html(raw_html: str) -> str:
#     """Cleans AI output, repairs tags, and injects SOTA form components."""
#     html = raw_html.replace("```html", "").replace("```", "").strip()
#     # Fix underscores
#     if re.search(r'(?<!["\'])_{3,}(?!["\'])', html):
#         html = re.sub(r'_{3,}', '<span class="blank-line"></span>', html)
#     # Fix checkboxes
#     html = re.sub(r'\[X\]', '☑', html, flags=re.IGNORECASE)
#     html = re.sub(r'\[ \]', '☐', html)
#     # Repair HTML
#     try:
#         soup = BeautifulSoup(html, "html.parser")
#         return str(soup)
#     except:
#         return html

# def html_to_pdf(html_pages, output_path, target_lang):
#     font_info = FONT_MAP.get(target_lang, FONT_MAP["English"])
#     settings = SCRIPT_SETTINGS.get(target_lang, SCRIPT_SETTINGS["English"])
#     base_dir = os.path.abspath(os.path.dirname(__file__))
    
#     reg_font = os.path.join(base_dir, "fonts", font_info["regular"]).replace('\\', '/')
#     bold_font = os.path.join(base_dir, "fonts", font_info["bold"]).replace('\\', '/')
    
#     css = f"""
#         @font-face {{ font-family: 'TargetFont'; src: url('file:///{reg_font}'); font-weight: normal; }}
#         @font-face {{ font-family: 'TargetFont'; src: url('file:///{bold_font}'); font-weight: bold; }}
        
#         @page {{ size: A4; margin: 0.6in 0.75in; }}
#         body {{
#             font-family: 'TargetFont', sans-serif;
#             font-size: {settings['size']};
#             line-height: {settings['line_height']};
#             color: #000;
#             margin: 0; padding: 0;
#         }}
#         table {{ 
#             width: 100% !important; border-collapse: collapse; 
#             margin-bottom: 12px; table-layout: auto !important; 
#         }}
#         td, th {{ padding: 6px 8px; vertical-align: top; text-align: left; word-wrap: break-word; }}
#         .grid-table td, .grid-table th {{ border: 1px solid #000; }}
#         .borderless td {{ border: none !important; }}

#         .blank-line {{
#             display: inline-block; min-width: 120px;
#             border-bottom: 1px solid #000; margin: 0 4px;
#             vertical-align: bottom;
#         }}
#         .blank-line::after {{ content: "\\00A0"; }}
        
#         .page-container {{ page-break-after: always; width: 100%; }}
#         h1, h2 {{ text-align: center; font-weight: bold; margin-bottom: 15px; }}
#     """
    
#     pages_html = ""
#     for i, page_html in enumerate(html_pages):
#         break_style = "page-break-after: always;" if i < len(html_pages)-1 else ""
#         pages_html += f"<div class='page-container' style='{break_style}'>{page_html}</div>"

#     full_html = f"<html><head><style>{css}</style></head><body>{pages_html}</body></html>"
#     HTML(string=full_html).write_pdf(output_path, font_config=FontConfiguration())
#     return output_path