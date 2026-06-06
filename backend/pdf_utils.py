

# import fitz  # PyMuPDF
# import os
# import html
# import re

# FONT_MAP = {
#     "English": {"regular": "NotoSans-Regular.ttf", "bold": "NotoSans-Bold.ttf"},
#     "Hindi": {"regular": "NotoSansDevanagari-Regular.ttf", "bold": "NotoSansDevanagari-Bold.ttf"},
#     "Telugu": {"regular": "NotoSansTelugu-Regular.ttf", "bold": "NotoSansTelugu-Bold.ttf"},
#     "Tamil": {"regular": "NotoSansTamil-Regular.ttf", "bold": "NotoSansTamil-Bold.ttf"},
#     "Kannada": {"regular": "NotoSansKannada-Regular.ttf", "bold": "NotoSansKannada-Bold.ttf"},
#     "Malayalam": {"regular": "NotoSansMalayalam-Regular.ttf", "bold": "NotoSansMalayalam-Bold.ttf"},
#     "Bengali": {"regular": "NotoSansBengali-Regular.ttf", "bold": "NotoSansBengali-Bold.ttf"},
#     "Gujarati": {"regular": "NotoSansGujarati-Regular.ttf", "bold": "NotoSansGujarati-Bold.ttf"}
# }

# def extract_text_and_bboxes(pdf_path):
#     doc = fitz.open(pdf_path)
#     pages_data = []
    
#     for page in doc:
#         page_width = page.rect.width
#         blocks = page.get_text("dict")["blocks"]
#         page_blocks = []
        
#         for b in blocks:
#             if b['type'] == 0: 
#                 text = ""
#                 sizes = []
#                 bold_char_count = 0
#                 total_char_count = 0
#                 span_bboxes = []
                
#                 for line in b['lines']:
#                     for span in line['spans']:
#                         span_text = span['text']
                        
#                         # Ignore underscores and signature lines
#                         if re.match(r'^[\s_.-]+$', span_text):
#                             continue
                            
#                         text += span_text + " "
#                         sizes.append(span['size'])
                        
#                         char_len = len(span_text.strip())
#                         total_char_count += char_len
                        
#                         if "Bold" in span['font'] or (span['flags'] & 16):
#                             bold_char_count += char_len
                            
#                         if span_text.strip():
#                             span_bboxes.append(span['bbox'])
                
#                 text = text.strip()
#                 if text:
#                     avg_size = sum(sizes) / len(sizes) if sizes else 10
#                     is_bold = (bold_char_count / total_char_count) > 0.5 if total_char_count > 0 else False
                    
#                     bbox = b['bbox']
#                     is_centered = False
#                     if bbox[0] > (page_width * 0.20) and bbox[2] < (page_width * 0.80):
#                         is_centered = True
                        
#                     content_type = "paragraph"
#                     if is_bold or is_centered:
#                         content_type = "heading"
#                     elif re.search(r'_{2,}|\[\s*\]', text): 
#                         content_type = "form_field"
#                     elif re.match(r'^[\d\s.,+()]+$', text): 
#                         content_type = "number_only"
                    
#                     page_blocks.append({
#                         "bbox": bbox,
#                         "text": text,
#                         "font_size": avg_size,
#                         "is_bold": is_bold,
#                         "is_centered": is_centered,
#                         "content_type": content_type,
#                         "spans": span_bboxes
#                     })
#         pages_data.append(page_blocks)
#     doc.close()
#     return pages_data

# def reconstruct_pdf(original_pdf_path, translated_pages, target_lang, output_path):
#     doc = fitz.open(original_pdf_path)
    
#     fonts = FONT_MAP.get(target_lang, FONT_MAP["English"])
#     reg_path = os.path.join("fonts", fonts["regular"])
#     bold_path = os.path.join("fonts", fonts["bold"])
    
#     archive = fitz.Archive()
#     if os.path.exists(reg_path):
#         with open(reg_path, "rb") as f:
#             archive.add(f.read(), "font_regular.ttf")
#     if os.path.exists(bold_path):
#         with open(bold_path, "rb") as f:
#             archive.add(f.read(), "font_bold.ttf")
    
#     for page_num, page in enumerate(doc):
#         original_blocks = translated_pages[page_num]['original']
#         translated_texts = translated_pages[page_num]['translated']
        
#         # 1. EXTRACT ALL PHYSICAL LINES (The Grid)
#         v_lines = [0, page.rect.width]
#         h_lines = [0, page.rect.height]
        
#         for p in page.get_drawings():
#             for item in p["items"]:
#                 if item[0] == "l":
#                     p1, p2 = item[1], item[2]
#                     # Must be at least 20px long to be considered a table line (ignores checkboxes)
#                     if abs(p1.x - p2.x) < 2 and abs(p1.y - p2.y) > 20: v_lines.append(p1.x)
#                     if abs(p1.y - p2.y) < 2 and abs(p1.x - p2.x) > 20: h_lines.append(p1.y)
#                 elif item[0] == "re":
#                     r = item[1]
#                     v_lines.extend([r.x0, r.x1])
#                     h_lines.extend([r.y0, r.y1])
                    
#         try:
#             for tab in page.find_tables():
#                 for row in tab.cells:
#                     for cell in row:
#                         if cell:
#                             v_lines.extend([cell[0], cell[2]])
#                             h_lines.extend([cell[1], cell[3]])
#         except Exception:
#             pass

#         # Sort and clean the lines
#         v_lines = sorted(list(set([round(x, 1) for x in v_lines])))
#         h_lines = sorted(list(set([round(y, 1) for y in h_lines])))
        
#         # PASS 1: Erase original text
#         for block in original_blocks:
#             for span_bbox in block.get("spans", []):
#                 rect = fitz.Rect(span_bbox)
#                 rect.x0 -= 1; rect.y0 -= 1; rect.x1 += 1; rect.y1 += 1
#                 page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            
#         # PASS 2: Draw Translated Text inside Absolute Cages
#         for i, block in enumerate(original_blocks):
#             orig_rect = fitz.Rect(block["bbox"])
#             rect = fitz.Rect(orig_rect)
#             new_text = translated_texts[i]
            
#             safe_text = html.escape(new_text).replace('\n', '<br>')
#             if block.get("is_bold"):
#                 safe_text = f"<b>{safe_text}</b>"
            
#             # Reduce font size to 70% to ensure bulky scripts fit in table cells
#             f_size = block.get("font_size", 10) * 0.70
#             text_align = "center" if block.get("is_centered") else "left"
            
#             # CSS: Added hyphens and strict word-wrap to force breaks at borders
#             css = f"""
#             @font-face {{ font-family: 'CustomFont'; src: url('font_regular.ttf'); font-weight: normal; }}
#             @font-face {{ font-family: 'CustomFont'; src: url('font_bold.ttf'); font-weight: bold; }}
#             * {{ font-family: 'CustomFont'; font-size: {f_size}pt; line-height: 1.2; color: black; margin: 0; padding: 0; text-align: {text_align}; word-wrap: break-word; overflow-wrap: break-word; hyphens: auto; }}
#             """
            
#             # --- THE CENTER OF MASS LOGIC ---
#             # Find where the majority of the text actually lives
#             if block.get("spans"):
#                 avg_x = sum([(s[0] + s[2])/2 for s in block["spans"]]) / len(block["spans"])
#                 avg_y = sum([(s[1] + s[3])/2 for s in block["spans"]]) / len(block["spans"])
#             else:
#                 avg_x = (orig_rect.x0 + orig_rect.x1) / 2
#                 avg_y = (orig_rect.y0 + orig_rect.y1) / 2

#             # Find the physical walls enclosing this center point
#             left_walls = [x for x in v_lines if x < avg_x]
#             right_walls = [x for x in v_lines if x > avg_x]
#             bottom_walls = [y for y in h_lines if y > avg_y]
            
#             left_wall = max(left_walls) if left_walls else 0
#             right_wall = min(right_walls) if right_walls else page.rect.width
#             bottom_wall = min(bottom_walls) if bottom_walls else page.rect.height
            
#             # --- APPLY THE ABSOLUTE CAGE ---
#             # 1. Lock the Left Wall (Fixes bleeding into Column 1)
#             if left_wall > 10: # If it's an actual table line
#                 rect.x0 = max(orig_rect.x0, left_wall + 2)
            
#             # 2. Lock the Right Wall (Fixes bleeding into Column 3)
#             if right_wall < page.rect.width - 10: # If it's an actual table line
#                 rect.x1 = right_wall - 2
#             else:
#                 rect.x1 = orig_rect.x1 + 30 # Normal paragraph expansion
                
#             # 3. Lock the Bottom Wall (Prevents bleeding into the next row)
#             if bottom_wall < page.rect.height - 10:
#                 rect.y1 = bottom_wall - 2
#             else:
#                 rect.y1 = orig_rect.y1 + 40 # Normal paragraph expansion
            
#             # Failsafe: Ensure box has minimum size
#             if rect.x1 <= rect.x0 + 10: rect.x1 = rect.x0 + 50
#             if rect.y1 <= rect.y0 + 10: rect.y1 = rect.y0 + 20
            
#             page.insert_htmlbox(rect, f"<div>{safe_text}</div>", css=css, archive=archive)
            
#     doc.save(output_path)
#     doc.close()
#     return output_path

# version 2
# import fitz  # PyMuPDF
# import base64
# from weasyprint import HTML, CSS
# from weasyprint.text.fonts import FontConfiguration

# def pdf_to_base64_images(pdf_path):
#     """Converts each page of a PDF into a high-res base64 image for the Vision Model."""
#     doc = fitz.open(pdf_path)
#     base64_images = []
    
#     for page in doc:
#         # Render page to an image (dpi=200 for good vision quality)
#         pix = page.get_pixmap(dpi=200)
#         img_bytes = pix.tobytes("png")
#         b64_img = base64.b64encode(img_bytes).decode('utf-8')
#         base64_images.append(b64_img)
        
#     doc.close()
#     return base64_images

# def html_to_pdf(html_pages, output_path):
#     """Combines HTML strings into a single PDF using WeasyPrint."""
    
#     # Combine all pages with CSS page-breaks
#     combined_html = """
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <meta charset="UTF-8">
#         <style>
#             @import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;700&family=Noto+Sans+Devanagari:wght@400;700&family=Noto+Sans+Telugu:wght@400;700&family=Noto+Sans+Malayalam:wght@400;700&display=swap');
            
#             body {
#                 font-family: 'Noto Sans', 'Noto Sans Devanagari', 'Noto Sans Telugu', 'Noto Sans Malayalam', sans-serif;
#                 margin: 0;
#                 padding: 20px;
#             }
#             .page-break {
#                 page-break-before: always;
#             }
#             /* Reset table borders for clean rendering */
#             table { border-collapse: collapse; width: 100%; }
#             td, th { border: 1px solid black; padding: 8px; }
#         </style>
#     </head>
#     <body>
#     """
    
#     for i, page_html in enumerate(html_pages):
#         if i > 0:
#             combined_html += "<div class='page-break'></div>"
#         combined_html += page_html
        
#     combined_html += "</body></html>"
    
#     # Render PDF
#     font_config = FontConfiguration()
#     HTML(string=combined_html).write_pdf(output_path, font_config=font_config)
    
#     return output_path
# 

import fitz  # PyMuPDF
import base64
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def pdf_to_base64_images(pdf_path):
    """Converts each page of a PDF into a high-res base64 image for the Vision Model."""
    doc = fitz.open(pdf_path)
    base64_images = []
    
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        base64_images.append(b64_img)
        
    doc.close()
    return base64_images

def html_to_pdf(html_pages, output_path):
    """Combines HTML strings into a single PDF using WeasyPrint with strict layout rules."""
    
    combined_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;700&family=Noto+Sans+Devanagari:wght@400;700&family=Noto+Sans+Telugu:wght@400;700&family=Noto+Sans+Malayalam:wght@400;700&display=swap');
            
            @page {
                size: A4;
                margin: 0.75in;
            }
            body {
                font-family: 'Noto Sans', 'Noto Sans Devanagari', 'Noto Sans Telugu', 'Noto Sans Malayalam', sans-serif;
                font-size: 10pt; /* Slightly reduced to accommodate Indian script expansion */
                line-height: 1.4;
                color: #000;
                margin: 0;
                padding: 0;
            }
            
            /* DEFAULT TABLES: No borders (Used for aligning signatures and headers) */
            table { 
                border-collapse: collapse; 
                width: 100%; 
                margin-bottom: 15px;
                table-layout: fixed; 
                word-wrap: break-word;
                overflow-wrap: break-word;
            }
            td, th { 
                padding: 6px; 
                vertical-align: top;
                text-align: left;
            }
            
            /* GRID TABLES: Visible black borders (Used for actual data tables) */
            table.grid-table, table.grid-table td, table.grid-table th {
                border: 1px solid black;
            }
            
            .page-container {
                page-break-after: always;
            }
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