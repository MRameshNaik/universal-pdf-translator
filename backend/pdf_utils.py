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
            
            /* --- STRICT TABLE RULES (BORDERS BY DEFAULT) --- */
            table {{ 
                border-collapse: collapse; 
                width: 100% !important; 
                margin-bottom: 15px;
                table-layout: fixed !important; 
            }}
            tr {{ page-break-inside: avoid !important; }}
            
            /* THE FIX: All table cells get borders by default now! */
            td, th {{ 
                border: 1px solid black; 
                padding: 8px; 
                vertical-align: top;
                text-align: left;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }}
            
            /* --- THE FORM BLANK COMPONENT --- */
            .form-blank {{
                display: inline-block;
                min-width: 150px;
                max-width: 100%;
                border-bottom: 1px solid black;
                margin: 0 5px;
                vertical-align: bottom;
            }}
            .form-blank::after {{
                content: "\\00A0"; 
            }}
            
            /* --- THE SIGNATURE BLOCK COMPONENT (NO BORDERS) --- */
            table.signature-table, table.signature-table td, table.signature-table th {{
                border: none !important;
            }}
            table.signature-table {{
                margin-top: 30px;
                width: 100% !important;
                table-layout: fixed !important;
            }}
            table.signature-table td {{
                text-align: center;
                vertical-align: bottom;
                width: 33.33% !important; 
            }}
            
            .page-container {{
                page-break-after: always;
                width: 100%;
            }}
            .fallback-img {{
                max-width: 100%;
                height: auto;
                border: 2px dashed red;
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