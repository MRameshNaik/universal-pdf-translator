


# import os
# import time
# import random
# import concurrent.futures
# import re
# from bs4 import BeautifulSoup
# from typing import TypedDict, List
# from langgraph.graph import StateGraph, END
# from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
# from langchain_core.messages import HumanMessage
# from pdf_utils import pdf_to_base64_images, html_to_pdf
# from logger import send_log
# import fitz 

# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash",
#     temperature=0.1,
#     safety_settings={
#         HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
#         HarmCategory.HARM_CATEGORY_HATE_SPEECH:       HarmBlockThreshold.BLOCK_ONLY_HIGH,
#         HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_ONLY_HIGH,
#         HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
#     },
# )

# class PDFState(TypedDict):
#     pdf_path:        str
#     target_languages: List[str]
#     page_images:     List[str]          
#     page_texts:      List[str]          
#     output_files:    List[str]
#     client_id:       str

# def extract_images_node(state: PDFState) -> dict:
#     cid = state.get("client_id")
#     send_log(cid, "[INFO] Extracting page images and word-level text...")
    
#     images = pdf_to_base64_images(state["pdf_path"])
    
#     doc = fitz.open(state["pdf_path"])
#     page_texts = [page.get_text("text") for page in doc]
#     doc.close()
    
#     send_log(cid, f"[INFO] Extracted {len(images)} pages.")
#     return {"page_images": images, "page_texts": page_texts}

# def vision_translation_node(state: PDFState) -> dict:
#     target_languages = state["target_languages"]
#     page_images      = state["page_images"]
#     page_texts       = state["page_texts"]
#     cid              = state.get("client_id")
#     output_files     = []

#     for lang in target_languages:
#         send_log(cid, f"\n[INFO] ─── Starting translation: {lang} ───")
#         lang_start = time.time()

#         def _task(args):
#             page_num, b64_img, raw_text = args
            
#             raw_text_clean = re.sub(r'\s+', ' ', raw_text).strip()
            
#             prompt = f"""
#             <ROLE>You are an Expert Frontend Developer and Medical/Legal Translator.</ROLE>
#             <TASK>Recreate the visual layout of the provided document image using HTML5, and translate ALL text into {lang}.</TASK>
            
#             <RAW_TEXT_REFERENCE>
#             Use this text ONLY for translation spelling accuracy. 
#             {raw_text_clean}
#             </RAW_TEXT_REFERENCE>
            
#             <CRITICAL_INSTRUCTIONS>
#             1. THE [BLANK] TOKEN (CRITICAL): Wherever you see a physical line meant for handwriting (e.g., "Date: ______"), you MUST insert the exact text token `[BLANK]`. DO NOT type underscores. DO NOT skip them.
            
#             2. THE SIGNATURE TABLE RULE (CRITICAL): For side-by-side signature blocks (Name, Signature, Date) at the bottom of pages, you are FORBIDDEN from using normal paragraphs. You MUST use this exact HTML:
#                <table class="signature-table">
#                  <tr>
#                    <td>[BLANK]<br>Name</td>
#                    <td>[BLANK]<br>Signature</td>
#                    <td>[BLANK]<br>Date</td>
#                  </tr>
#                </table>
               
#             3. THE 3-COLUMN TABLE RULE: The main data table ALWAYS has exactly 3 columns. Even if it continues onto the next page and the 3rd column is empty, YOU MUST OUTPUT 3 COLUMNS FOR EVERY ROW. Example: `<tr><td>4.</td><td>Translated text...</td><td></td></tr>`. Use `<table class="grid-table">`.
            
#             4. CHECKBOXES & ABBREVIATIONS: 
#                - Wherever you see an empty square box `[ ]`, you MUST output the Unicode character `&#9744;`.
#                - "S/o, W/o., D/o:" MUST be translated into {lang} as the equivalent of "Son of, Wife of, Daughter of:".
            
#             5. GRAMMAR & FRAGMENTED SENTENCES: If a sentence is visually broken by blank spaces in the image (e.g., "Address [BLANK] of [BLANK] the [BLANK] subject"), DO NOT translate word-by-word. Combine it into ONE fluent, grammatically correct sentence in {lang} and place a single [BLANK] at the end.
            
#             6. VISUAL HIERARCHY (CRITICAL): 
#                - Use `<h1>` for the main document title at the very top.
#                - Use `<h2>` for section headers.
#                - Use `<p>` for normal body text.
            
#             7. GLOSSARY: 
#                - "Subject" MUST be translated INTO {lang} as the local word for the person participating in the study. ABSOLUTELY DO NOT output the English words "Participant/Patient" in the final HTML.
#                - "Initial" = "Signature/Sign" in {lang}.
#                - Do not translate emails or numbers.
#             </CRITICAL_INSTRUCTIONS>
            
#             OUTPUT FORMAT: Return ONLY valid HTML code. No markdown fences. Inner content only.
#             """
            
#             message = HumanMessage(
#                 content=[
#                     {"type": "text", "text": prompt},
#                     {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
#                 ]
#             )
            
#             max_retries = 4
#             for attempt in range(max_retries):
#                 try:
#                     response = llm.invoke([message])
#                     clean_html = response.content.replace("```html", "").replace("```", "").strip()
                    
#                     # THE TOKEN SWAP
#                     clean_html = clean_html.replace("[BLANK]", '<span class="form-blank"></span>')
#                     clean_html = re.sub(r'([_—\-]\s*){3,}', '<span class="form-blank"></span>', clean_html)
                    
#                     soup = BeautifulSoup(clean_html, "html.parser")
#                     repaired_html = str(soup)
                    
#                     if len(repaired_html) < 200:
#                         raise ValueError("AI generated an empty or severely truncated page.")
                    
#                     send_log(cid, f"  -> [SUCCESS] Page {page_num + 1} translated.")
#                     return page_num, repaired_html
                    
#                 except Exception as e:
#                     if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
#                         jitter = random.uniform(1, 3)
#                         wait_time = (10 * (2 ** attempt)) + jitter
#                         send_log(cid, f"  -> [WARNING] Rate limit hit on page {page_num+1}. Waiting {wait_time:.1f}s...")
#                         time.sleep(wait_time)
#                     else:
#                         send_log(cid, f"  -> [ERROR] Error on page {page_num+1}: {e}. Retrying...")
#                         time.sleep(2)
            
#             send_log(cid, f"  -> [FALLBACK] Injecting original image for page {page_num+1}.")
#             safe_fallback_text = raw_text.replace('\n', '<br>')
#             fallback_html = f"""
#             <div style="color: red; border: 2px solid red; padding: 15px; margin-bottom: 20px; text-align: center;">
#                 <strong>[Translation Blocked or Failed - Original Text Preserved Below]</strong>
#             </div>
#             <div style="font-family: sans-serif;">{safe_fallback_text}</div>
#             """
#             return page_num, fallback_html

#         tasks = [(i, img, txt) for i, (img, txt) in enumerate(zip(page_images, page_texts))]
#         results_unordered = []
#         with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
#             for result in executor.map(_task, tasks):
#                 results_unordered.append(result)
                
#         results_unordered.sort(key=lambda x: x[0])
#         translated_html_pages = [html for _, html in results_unordered]
            
#         out_path = state["pdf_path"].replace(".pdf", f"_{lang}.pdf").replace("uploads", "outputs")
#         send_log(cid, f"[INFO] Rendering final continuous PDF for {lang}...")
        
#         html_to_pdf(translated_html_pages, out_path, lang)
        
#         send_log(cid, f"[SUCCESS] ─── {lang} complete ({time.time() - lang_start:.1f}s) ───")
#         output_files.append(out_path)

#     return {"output_files": output_files}

# workflow = StateGraph(PDFState)
# workflow.add_node("extract", extract_images_node)
# workflow.add_node("process", vision_translation_node)

# workflow.set_entry_point("extract")
# workflow.add_edge("extract", "process")
# workflow.add_edge("process", END)

# app_graph = workflow.compile()


import os
import time
import random
import concurrent.futures
import re
from bs4 import BeautifulSoup
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
from langchain_core.messages import HumanMessage
from pdf_utils import pdf_to_base64_images, html_to_pdf
from logger import send_log
import fitz 

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.1,
    safety_settings={
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH:       HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    },
)

class PDFState(TypedDict):
    pdf_path:        str
    target_languages: List[str]
    page_images:     List[str]          
    page_texts:      List[str]          
    output_files:    List[str]
    client_id:       str

def extract_images_node(state: PDFState) -> dict:
    cid = state.get("client_id")
    send_log(cid, "[INFO] Extracting page images and word-level text...")
    
    images = pdf_to_base64_images(state["pdf_path"])
    
    doc = fitz.open(state["pdf_path"])
    page_texts = [page.get_text("text") for page in doc]
    doc.close()
    
    send_log(cid, f"[INFO] Extracted {len(images)} pages.")
    return {"page_images": images, "page_texts": page_texts}

def vision_translation_node(state: PDFState) -> dict:
    target_languages = state["target_languages"]
    page_images      = state["page_images"]
    page_texts       = state["page_texts"]
    cid              = state.get("client_id")
    output_files     = []

    for lang in target_languages:
        send_log(cid, f"\n[INFO] ─── Starting translation: {lang} ───")
        lang_start = time.time()

        def _task(args):
            page_num, b64_img, raw_text = args
            
            raw_text_clean = re.sub(r'\s+', ' ', raw_text).strip()
            
            # THE SOTA NATURAL PROMPT
            prompt = f"""
            <ROLE>You are an Expert Frontend Developer and Medical/Legal Translator.</ROLE>
            <TASK>Recreate the visual layout of the provided document image using HTML5, and translate ALL text into {lang}.</TASK>
            
            <RAW_TEXT_REFERENCE>
            Use this text ONLY for translation spelling accuracy. 
            {raw_text_clean}
            </RAW_TEXT_REFERENCE>
            
            <CRITICAL_INSTRUCTIONS>
            1. MISSING BLANK LINES (CRITICAL): The RAW_TEXT_REFERENCE above strips out blank lines. You MUST look at the IMAGE. Wherever you see a physical line meant for handwriting (e.g., "Date: ______"), you MUST type underscores `_________` in your HTML. DO NOT skip them.
            
            2. SIGNATURE TABLES (CRITICAL): For side-by-side signature blocks (Name, Signature, Date) at the bottom of pages, you MUST use this exact HTML. DO NOT forget the underscores!
               <table class="signature-table">
                 <tr>
                   <td>_________<br>Name</td>
                   <td>_________<br>Signature</td>
                   <td>_________<br>Date</td>
                 </tr>
               </table>
               
            3. THE 3-COLUMN TABLE RULE (CRITICAL): The main data table (with items 1 through 6) ALWAYS has exactly 3 columns. 
               - If it continues onto the next page, YOU MUST KEEP 3 COLUMNS. 
               - The 3rd column is an empty box for initials. DO NOT put checkboxes `[ ]` in it. Output an empty `<td></td>` for the 3rd column in every row.
               - Use `<table class="grid-table">` for visible grids.
            
            4. CHECKBOXES: Use literal text `[ ]` for unchecked and `[X]` for checked.
            
            5. GRAMMAR: If a sentence is broken by blanks (e.g., "Address ____ of ____ subject"), combine it into ONE fluent sentence in {lang} and place the underscores at the end.
            
            6. GLOSSARY: 
               - "Subject" MUST be translated INTO {lang} as the local word for the person participating in the study. ABSOLUTELY DO NOT output the English words "Participant/Patient".
               - "Initial" = "Signature/Sign" in {lang}.
               - Do not translate emails or numbers.
            </CRITICAL_INSTRUCTIONS>
            
            OUTPUT FORMAT: Return ONLY valid HTML code. No markdown fences. Inner content only.
            """
            
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                ]
            )
            
            max_retries = 4
            for attempt in range(max_retries):
                try:
                    response = llm.invoke([message])
                    clean_html = response.content.replace("```html", "").replace("```", "").strip()
                    
                    # THE REGEX SWAP: Converts AI underscores into perfect CSS lines
                    clean_html = re.sub(r'([_—\-]\s*){3,}', '<span class="form-blank"></span>', clean_html)
                    # Convert AI text brackets to Unicode Checkboxes
                    clean_html = clean_html.replace('[ ]', '☐').replace('[X]', '☑').replace('[x]', '☑')
                    
                    # Repair broken HTML tags
                    soup = BeautifulSoup(clean_html, "html.parser")
                    repaired_html = str(soup)
                    
                    if len(repaired_html) < 200:
                        raise ValueError("AI generated an empty or severely truncated page.")
                    
                    send_log(cid, f"  -> [SUCCESS] Page {page_num + 1} translated.")
                    return page_num, repaired_html
                    
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        jitter = random.uniform(1, 3)
                        wait_time = (10 * (2 ** attempt)) + jitter
                        send_log(cid, f"  -> [WARNING] Rate limit hit on page {page_num+1}. Waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                    else:
                        send_log(cid, f"  -> [ERROR] Error on page {page_num+1}: {e}. Retrying...")
                        time.sleep(2)
            
            send_log(cid, f"  -> [FALLBACK] Injecting original image for page {page_num+1}.")
            safe_fallback_text = raw_text.replace('\n', '<br>')
            fallback_html = f"""
            <div style="color: red; border: 2px solid red; padding: 15px; margin-bottom: 20px; text-align: center;">
                <strong>[Translation Blocked or Failed - Original Text Preserved Below]</strong>
            </div>
            <div style="font-family: sans-serif;">{safe_fallback_text}</div>
            """
            return page_num, fallback_html

        # CLOUD OPTIMIZATION: max_workers=2
        tasks = [(i, img, txt) for i, (img, txt) in enumerate(zip(page_images, page_texts))]
        results_unordered = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for result in executor.map(_task, tasks):
                results_unordered.append(result)
                
        results_unordered.sort(key=lambda x: x[0])
        translated_html_pages = [html for _, html in results_unordered]
            
        out_path = state["pdf_path"].replace(".pdf", f"_{lang}.pdf").replace("uploads", "outputs")
        send_log(cid, f"[INFO] Rendering final continuous PDF for {lang}...")
        
        html_to_pdf(translated_html_pages, out_path, lang)
        
        send_log(cid, f"[SUCCESS] ─── {lang} complete ({time.time() - lang_start:.1f}s) ───")
        output_files.append(out_path)

    return {"output_files": output_files}

workflow = StateGraph(PDFState)
workflow.add_node("extract", extract_images_node)
workflow.add_node("process", vision_translation_node)

workflow.set_entry_point("extract")
workflow.add_edge("extract", "process")
workflow.add_edge("process", END)

app_graph = workflow.compile()