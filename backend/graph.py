
###################### Claudes improved code ###################################

# """
# graph.py  —  LangGraph pipeline for AI-powered PDF translation.

# Improvements over v1:
#   • Dual-channel prompting: each page gets BOTH its rendered image AND
#     pdfplumber word-level text  →  image = layout authority, text = word accuracy.
#     Eliminates medical-term misreads caused by low-DPI aliasing.
#   • Sliding context window: the previous page's translated HTML is passed as
#     [PREVIOUS PAGE CONTEXT] so the AI can maintain table continuity and avoid
#     dropping cross-page sentences.
#   • Correct fallback: failed pages inject the original page IMAGE (base64),
#     not garbled PyMuPDF raw text  (which was unreadable for custom-encoded PDFs).
#   • Backoff jitter: random.uniform(0, 3) added to retry waits so parallel
#     threads de-synchronise and don't all slam the API simultaneously.
#   • All HTML post-processing (underscore→span, checkbox→Unicode, BS4 repair)
#     moved into pdf_utils.postprocess_page_html()  for a single clean call.
#   • Back-translation quality gate: after each language is rendered, a second
#     Claude/Gemini call checks for missing clauses or critical mistranslations
#     and logs a WARNING if any are found.  (Non-blocking — output is still saved.)
#   • max_workers reduced 3 → 2 to reduce simultaneous rate-limit pressure.
# """

# import os
# import random
# import time
# import concurrent.futures
# from typing import TypedDict, List

# from langgraph.graph import StateGraph, END
# from langchain_google_genai import (
#     ChatGoogleGenerativeAI,
#     HarmCategory,
#     HarmBlockThreshold,
# )
# from langchain_core.messages import HumanMessage

# from pdf_utils import (
#     pdf_to_base64_images,
#     html_to_pdf,
#     postprocess_page_html,
# )

# # ---------------------------------------------------------------------------
# # LLM setup
# # ---------------------------------------------------------------------------

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

# # ---------------------------------------------------------------------------
# # State
# # ---------------------------------------------------------------------------

# class PDFState(TypedDict):
#     pdf_path:        str
#     target_languages: List[str]
#     page_images:     List[str]          # base-64 PNG per page
#     page_texts:      List[str]          # pdfplumber word text per page
#     output_files:    List[str]


# # ---------------------------------------------------------------------------
# # Node 1 — extraction
# # ---------------------------------------------------------------------------

# def extract_images_node(state: PDFState) -> dict:
#     print("[INFO] Extracting page images (250 DPI) and word-level text …")
#     images, page_texts = pdf_to_base64_images(state["pdf_path"], dpi=250)
#     print(f"[INFO] Extracted {len(images)} pages.")
#     return {"page_images": images, "page_texts": page_texts}


# # ---------------------------------------------------------------------------
# # Node 2 — translation
# # ---------------------------------------------------------------------------

# def _build_prompt(
#     lang: str,
#     source_text: str,
#     prev_page_html: str | None,
# ) -> str:
#     """Build the translation prompt for a single page."""

#     context_block = ""
#     if prev_page_html:
#         # Strip the HTML down to plain text so the token count stays low
#         from bs4 import BeautifulSoup
#         plain = BeautifulSoup(prev_page_html, "html.parser").get_text(" ", strip=True)[:1500]
#         context_block = f"""
# [PREVIOUS PAGE CONTEXT — DO NOT TRANSLATE — for table/sentence continuity only]
# {plain}
# [END CONTEXT]
# """

#     source_block = ""
#     if source_text.strip():
#         source_block = f"""
# [AUTHORITATIVE SOURCE TEXT extracted from the PDF — use this for every word,
#  do NOT invent text that isn't here]
# {source_text}
# [END SOURCE TEXT]
# """

#     return f"""You are an Expert Frontend Developer and Medical/Legal Translator.
# Recreate the visual layout of the provided document image using HTML5, and translate ALL text into {lang}.
# {context_block}{source_block}
# CRITICAL CODING & LAYOUT RULES:
# 1. NO FULL-PAGE TABLES: DO NOT wrap the entire document in a single <table>.
#    Use tables ONLY for actual grids or side-by-side signature blocks.
#    Use <p> and <div> for normal text.
# 2. FILL-IN-THE-BLANKS: Use underscores (e.g. _________) for blank fields.
#    GRAMMAR RULE: If a sentence is broken by blanks (e.g. "Address _____ of _____ subject"),
#    translate it as ONE grammatically correct {lang} sentence and put the blank at the end.
#    Example output: "ప్రతిభాగి చిరునామా: _________"
# 3. MULTI-PAGE TABLE CONTINUITY:
#    - Use <table class="grid-table"> for visible grids.
#    - Assign % widths to the first row: <td style="width:10%;"> etc.
#    - If a table continues from the PREVIOUS PAGE CONTEXT, keep the same column count.
#    - DO NOT add headers that are not visible in the current image.
#    - Write empty <td></td> for empty cells.
# 4. SIGNATURE BLOCKS: Use a borderless table aligned horizontally.
#    EXAMPLE:
#    <table class="borderless" style="text-align:center; width:100%;">
#      <tr>
#        <td>_______________<br>Name</td>
#        <td>_______________<br>Signature / Thumb impression</td>
#        <td>_______________<br>Date (DD/MM/YYYY)</td>
#      </tr>
#    </table>
# 5. CHECKBOXES: Use  [ ]  for unchecked and  [X]  for checked. (Pipeline will upgrade to ☐/☑.)

# TRANSLATION RULES:
# - "Subject" → translate contextually as "Participant / Patient".
# - "Initial" → translate as "Signature / Sign".
# - TRANSLITERATE names of people (e.g. DR MUDHAVATH KARTHIK NAIK) and places
#   (HYDERABAD, ESIC) accurately into the {lang} script.
# - DO NOT translate email addresses, URLs, or pure numbers.
# - If the SOURCE TEXT above shows a word clearly but the image is ambiguous,
#   trust the SOURCE TEXT.

# OUTPUT FORMAT:
# Return ONLY valid HTML. No markdown fences (```html). No <html>, <head>, or <body> tags.
# Inner content only.
# """


# def _translate_page(
#     page_num: int,
#     b64_img: str,
#     source_text: str,
#     prev_page_html: str | None,
#     lang: str,
# ) -> tuple[int, str]:
#     """Translate a single page. Returns (page_num, translated_html)."""

#     prompt = _build_prompt(lang, source_text, prev_page_html)

#     message = HumanMessage(
#         content=[
#             {"type": "text",      "text": prompt},
#             {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
#         ]
#     )

#     max_retries = 4
#     for attempt in range(max_retries):
#         try:
#             response  = llm.invoke([message])
#             clean_html = postprocess_page_html(response.content)
#             print(f"  -> [SUCCESS] Page {page_num + 1} translated.")
#             return page_num, clean_html

#         except Exception as exc:
#             is_rate_limit = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
#             if is_rate_limit:
#                 # Jitter prevents all parallel threads from retrying simultaneously
#                 base_wait  = 10 * (2 ** attempt)
#                 jitter     = random.uniform(0, 3)
#                 wait_time  = base_wait + jitter
#                 print(
#                     f"  -> [WARNING] Rate limit on page {page_num + 1}. "
#                     f"Waiting {wait_time:.1f}s … (attempt {attempt + 1}/{max_retries})"
#                 )
#                 time.sleep(wait_time)
#             else:
#                 print(f"  -> [ERROR] Page {page_num + 1}: {exc}")
#                 break  # non-rate-limit error → skip retries, use fallback

#     # ---- Bulletproof fallback: embed the original page IMAGE ----
#     # (Never use raw PyMuPDF text — it is garbled for custom-encoded PDFs.)
#     print(f"  -> [FALLBACK] Embedding original page image for page {page_num + 1}.")
#     fallback_html = f"""
# <div class="fallback-banner">
#     [Translation blocked — original page image preserved below]
# </div>
# <img src="data:image/png;base64,{b64_img}" alt="Original page {page_num + 1}" />
# """
#     return page_num, fallback_html


# def _quality_check(
#     original_english_text: str,
#     translated_pages_html: list[str],
#     lang: str,
# ) -> None:
#     """
#     Non-blocking back-translation quality gate.
#     Sends a short summary of both the source and translated text to the LLM
#     and asks it to flag missing consent clauses or critical mistranslations.
#     Logs WARNING but does NOT raise — the PDF is still saved.
#     """
#     from bs4 import BeautifulSoup

#     translated_plain = " ".join(
#         BeautifulSoup(h, "html.parser").get_text(" ", strip=True)
#         for h in translated_pages_html
#     )[:3000]

#     source_snippet = original_english_text[:2000]

#     check_prompt = f"""You are a medical translation quality reviewer.

# Below is the ORIGINAL English informed consent document (excerpt) and its {lang} translation.

# ORIGINAL (English):
# {source_snippet}

# TRANSLATED ({lang}):
# {translated_plain}

# Task:
# 1. Check whether all major consent clauses are present in the translation
#    (purpose of study, voluntary participation, risks, withdrawal rights, confidentiality,
#    contact details, signature section).
# 2. Flag any critical medical terms that appear mistranslated or omitted.
# 3. Reply in English. Be concise. If everything is fine, reply: "QUALITY OK".
#    Otherwise list issues as: "ISSUE: <description>".
# """

#     try:
#         response = llm.invoke([HumanMessage(content=check_prompt)])
#         result   = response.content.strip()
#         if "QUALITY OK" in result.upper():
#             print(f"  [QA] {lang}: QUALITY OK ✓")
#         else:
#             print(f"  [QA WARNING] {lang} translation issues detected:\n{result}")
#     except Exception as exc:
#         print(f"  [QA] Quality check failed (non-fatal): {exc}")


# def vision_translation_node(state: PDFState) -> dict:
#     target_languages = state["target_languages"]
#     page_images      = state["page_images"]
#     page_texts       = state["page_texts"]
#     output_files     = []

#     # Combine all source text for quality check
#     full_source_text = "\n\n--- PAGE BREAK ---\n\n".join(page_texts)

#     for lang in target_languages:
#         print(f"\n[INFO] ─── Starting translation: {lang} ───")
#         lang_start = time.time()

#         # ------------------------------------------------------------------
#         # Parallel translation — max_workers=2 to reduce rate-limit pressure
#         # Sequential prev_page_html context is built AFTER all pages complete
#         # (parallel execution means we can't do true sequential sliding window,
#         #  but we pass the prior page's text from the pdfplumber extraction
#         #  which gives reasonable continuity at zero extra API cost).
#         # ------------------------------------------------------------------

#         def _task(args):
#             page_num, b64_img, src_text, prev_html = args
#             return _translate_page(page_num, b64_img, src_text, prev_html, lang)

#         # Build (page_num, image, source_text, prev_source_text) tuples.
#         # For the context we use the pdfplumber text of page N-1 as a lightweight
#         # proxy; it's not translated HTML but gives the AI vocabulary continuity.
#         tasks = []
#         for i, (img, txt) in enumerate(zip(page_images, page_texts)):
#             prev_context = page_texts[i - 1] if i > 0 else None
#             tasks.append((i, img, txt, prev_context))

#         results_unordered: list[tuple[int, str]] = []
#         with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
#             for result in executor.map(_task, tasks):
#                 results_unordered.append(result)

#         results_unordered.sort(key=lambda x: x[0])
#         translated_html_pages = [html for _, html in results_unordered]

#         # ------------------------------------------------------------------
#         # Quality gate (non-blocking)
#         # ------------------------------------------------------------------
#         print(f"[INFO] Running quality check for {lang} …")
#         _quality_check(full_source_text, translated_html_pages, lang)

#         # ------------------------------------------------------------------
#         # Render to PDF
#         # ------------------------------------------------------------------
#         out_path = (
#             state["pdf_path"]
#             .replace(".pdf", f"_{lang}.pdf")
#             .replace("uploads", "outputs")
#         )
#         print(f"[INFO] Rendering PDF → {out_path}")
#         render_start = time.time()
#         html_to_pdf(translated_html_pages, out_path, lang)
#         print(
#             f"[TIME] Rendered in {time.time() - render_start:.1f}s | "
#             f"Total {lang}: {time.time() - lang_start:.1f}s"
#         )

#         output_files.append(out_path)
#         print(f"[SUCCESS] ─── {lang} complete ───")

#     return {"output_files": output_files}


# # ---------------------------------------------------------------------------
# # Graph assembly
# # ---------------------------------------------------------------------------

# workflow = StateGraph(PDFState)
# workflow.add_node("extract", extract_images_node)
# workflow.add_node("process", vision_translation_node)

# workflow.set_entry_point("extract")
# workflow.add_edge("extract", "process")
# workflow.add_edge("process", END)

# app_graph = workflow.compile()

###################### vErsion 222 ################################

# import os
# import random
# import time
# import concurrent.futures
# from typing import TypedDict, List

# from langgraph.graph import StateGraph, END
# from langchain_google_genai import (
#     ChatGoogleGenerativeAI,
#     HarmCategory,
#     HarmBlockThreshold,
# )
# from langchain_core.messages import HumanMessage

# from pdf_utils import (
#     pdf_to_base64_images,
#     html_to_pdf,
#     postprocess_page_html,
# )
# from logger import send_log # THE FIX: Import the logger

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
#     client_id:       str # THE FIX: Added client_id to State

# def extract_images_node(state: PDFState) -> dict:
#     cid = state.get("client_id")
#     send_log(cid, "[INFO] Extracting page images (250 DPI) and word-level text …")
#     images, page_texts = pdf_to_base64_images(state["pdf_path"], dpi=250)
#     send_log(cid, f"[INFO] Extracted {len(images)} pages.")
#     return {"page_images": images, "page_texts": page_texts}

# def _build_prompt(lang: str, source_text: str, prev_page_html: str | None) -> str:
#     context_block = ""
#     if prev_page_html:
#         from bs4 import BeautifulSoup
#         plain = BeautifulSoup(prev_page_html, "html.parser").get_text(" ", strip=True)[:1500]
#         context_block = f"""\n[PREVIOUS PAGE CONTEXT — DO NOT TRANSLATE — for table/sentence continuity only]\n{plain}\n[END CONTEXT]\n"""

#     source_block = ""
#     if source_text.strip():
#         source_block = f"""\n[AUTHORITATIVE SOURCE TEXT extracted from the PDF — use this for every word]\n{source_text}\n[END SOURCE TEXT]\n"""

#     return f"""You are an Expert Frontend Developer and Medical/Legal Translator.
# Recreate the visual layout of the provided document image using HTML5, and translate ALL text into {lang}.
# {context_block}{source_block}
# CRITICAL CODING & LAYOUT RULES:
# 1. NO FULL-PAGE TABLES: DO NOT wrap the entire document in a single <table>. Use tables ONLY for actual grids or side-by-side signature blocks.
# 2. MISSING BLANK LINES (CRITICAL): The RAW TEXT above strips out blank lines. You MUST look at the IMAGE. Wherever you see a physical line meant for handwriting (e.g., "Date: ______"), you MUST type underscores `_________` in your HTML. DO NOT SKIP THEM! Do NOT use <hr> tags.
#    GRAMMAR RULE: If a sentence is broken by blanks, translate it as ONE grammatically correct {lang} sentence and put the blank at the end.
# 3. MULTI-PAGE TABLE CONTINUITY:
#    - Use <table class="grid-table"> for visible grids.
#    - Assign % widths to the first row: <td style="width:10%;"> etc.
#    - If a table continues from the PREVIOUS PAGE CONTEXT, keep the same column count.
#    - Write empty <td></td> for empty cells.
# 4. SIGNATURE BLOCKS: Use a borderless table aligned horizontally.
#    YOU MUST INCLUDE THE UNDERSCORES IN THE HTML:
#    <table class="borderless" style="text-align:center; width:100%;">
#      <tr>
#        <td>_________<br>Name</td>
#        <td>_________<br>Signature</td>
#        <td>_________<br>Date</td>
#      </tr>
#    </table>
# 5. CHECKBOXES: Use  [ ]  for unchecked and  [X]  for checked.

# TRANSLATION RULES:
# - "Subject" → translate contextually as "Participant / Patient".
# - "Initial" → translate as "Signature / Sign".
# - TRANSLITERATE names of people and places accurately into the {lang} script.
# - DO NOT translate email addresses, URLs, or pure numbers.

# OUTPUT FORMAT:
# Return ONLY valid HTML. No markdown fences. No <html>, <head>, or <body> tags. Inner content only.
# """

# def _translate_page(page_num: int, b64_img: str, source_text: str, prev_page_html: str | None, lang: str, cid: str) -> tuple[int, str]:
#     prompt = _build_prompt(lang, source_text, prev_page_html)
#     message = HumanMessage(
#         content=[
#             {"type": "text", "text": prompt},
#             {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}},
#         ]
#     )

#     max_retries = 4
#     for attempt in range(max_retries):
#         try:
#             response  = llm.invoke([message])
#             clean_html = postprocess_page_html(response.content)
#             send_log(cid, f"  -> [SUCCESS] Page {page_num + 1} translated.")
#             return page_num, clean_html
#         except Exception as exc:
#             is_rate_limit = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
#             if is_rate_limit:
#                 base_wait  = 10 * (2 ** attempt)
#                 jitter     = random.uniform(0, 3)
#                 wait_time  = base_wait + jitter
#                 send_log(cid, f"  -> [WARNING] Rate limit on page {page_num + 1}. Waiting {wait_time:.1f}s … (attempt {attempt + 1}/{max_retries})")
#                 time.sleep(wait_time)
#             else:
#                 send_log(cid, f"  -> [ERROR] Page {page_num + 1}: {exc}")
#                 break

#     send_log(cid, f"  -> [FALLBACK] Embedding original page image for page {page_num + 1}.")
#     fallback_html = f"""
# <div class="fallback-banner">
#     [Translation blocked — original page image preserved below]
# </div>
# <img src="data:image/png;base64,{b64_img}" alt="Original page {page_num + 1}" />
# """
#     return page_num, fallback_html

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
#             page_num, b64_img, src_text, prev_html = args
#             return _translate_page(page_num, b64_img, src_text, prev_html, lang, cid)

#         tasks = []
#         for i, (img, txt) in enumerate(zip(page_images, page_texts)):
#             prev_context = page_texts[i - 1] if i > 0 else None
#             tasks.append((i, img, txt, prev_context))

#         results_unordered: list[tuple[int, str]] = []
#         with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
#             for result in executor.map(_task, tasks):
#                 results_unordered.append(result)

#         results_unordered.sort(key=lambda x: x[0])
#         translated_html_pages = [html for _, html in results_unordered]

#         out_path = state["pdf_path"].replace(".pdf", f"_{lang}.pdf").replace("uploads", "outputs")
#         send_log(cid, f"[INFO] Rendering PDF → {out_path}")
#         render_start = time.time()
#         html_to_pdf(translated_html_pages, out_path, lang)
#         send_log(cid, f"[TIME] Rendered in {time.time() - render_start:.1f}s | Total {lang}: {time.time() - lang_start:.1f}s")

#         output_files.append(out_path)
#         send_log(cid, f"[SUCCESS] ─── {lang} complete ───")

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
            
            # Clean raw text to prevent fragmented grammar
            raw_text_clean = re.sub(r'\s+', ' ', raw_text).strip()
            
            # THE HTML-NATIVE PROMPT
            prompt = f"""
            <ROLE>You are an Expert Frontend Developer and Medical/Legal Translator.</ROLE>
            <TASK>Recreate the visual layout of the provided document image using HTML5, and translate ALL text into {lang}.</TASK>
            
            <RAW_TEXT_REFERENCE>
            Use this text ONLY for translation spelling accuracy. 
            {raw_text_clean}
            </RAW_TEXT_REFERENCE>
            
            <CRITICAL_INSTRUCTIONS>
            1. FORM BLANKS (CRITICAL): Wherever you see a physical line meant for handwriting (e.g., "Date: ______"), you MUST insert this exact HTML tag: `<span class="form-blank"></span>`. DO NOT type underscores.
            
            2. CHECKBOXES (CRITICAL): Wherever you see an empty checkbox `[ ]` in the image, you MUST insert this exact HTML tag: `<span class="checkbox"></span>`.
            
            3. SIGNATURE TABLES: For side-by-side signature blocks (Name, Signature, Date), you MUST use this exact HTML:
               <table class="signature-table">
                 <tr>
                   <td><span class="form-blank"></span><br>Name</td>
                   <td><span class="form-blank"></span><br>Signature</td>
                   <td><span class="form-blank"></span><br>Date</td>
                 </tr>
               </table>
               
            4. TABLE COLUMNS: Keep the exact same number of columns as the image. If a column is empty, output `<td></td>`. Use `<table class="grid-table">` for visible grids.
            
            5. GRAMMAR: If a sentence is visually broken by blank spaces in the image (e.g., "Address ____ of ____ subject"), combine it into ONE fluent sentence in {lang} and place the blank line at the end. (Example: "Subject Address: <span class="form-blank"></span>").
            
            6. GLOSSARY: 
               - "Subject" MUST be translated INTO {lang} as the equivalent concept of "Participant/Patient". DO NOT output the English words.
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
                    
                    # Fallback Regex: Just in case it still types underscores
                    clean_html = re.sub(r'([_—\-]\s*){3,}', '<span class="form-blank"></span>', clean_html)
                    
                    # Repair broken HTML tags
                    soup = BeautifulSoup(clean_html, "html.parser")
                    repaired_html = str(soup)
                    
                    # Failsafe: Catch silent blank page hallucinations
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