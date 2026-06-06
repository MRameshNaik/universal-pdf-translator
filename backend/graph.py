

# import os
# import time
# from typing import TypedDict, List, Dict
# from langgraph.graph import StateGraph, END
# from langchain_google_genai import ChatGoogleGenerativeAI
# from pydantic import BaseModel, Field
# from pdf_utils import extract_text_and_bboxes, reconstruct_pdf

# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

# class TranslationItem(BaseModel):
#     id: int = Field(description="The exact ID of the original text block")
#     translated_text: str = Field(description="The translated text")

# class TranslatedBlocks(BaseModel):
#     translations: List[TranslationItem]

# structured_llm = llm.with_structured_output(TranslatedBlocks)

# class PDFState(TypedDict):
#     pdf_path: str
#     target_languages: List[str]
#     extracted_pages: List[List[Dict]]
#     output_files: List[str]

# def extract_node(state: PDFState):
#     extracted = extract_text_and_bboxes(state["pdf_path"])
#     return {"extracted_pages": extracted}

# def translate_and_reconstruct_node(state: PDFState):
#     extracted_pages = state["extracted_pages"]
#     target_languages = state["target_languages"]
#     output_files = []

#     for lang in target_languages:
#         translated_pages_data = []
        
#         for page_num, page_blocks in enumerate(extracted_pages):
#             if not page_blocks:
#                 translated_pages_data.append({"original": [], "translated": []})
#                 continue

#             input_data = [{"id": i, "text": b["text"], "type": b["content_type"]} for i, b in enumerate(page_blocks)]
            
#             prompt = f"""You are an Expert Medical, Legal, and Official Document Translator.
#             Translate the following JSON array of text blocks into {lang}. 
            
#             CRITICAL INSTRUCTIONS BASED ON 'type':
#             1. If type is "heading": Translate formally and concisely.
#             2. If type is "form_field": PRESERVE ALL underscores (___), checkboxes ([ ]), and brackets. Do not remove them.
#             3. If type is "number_only": DO NOT TRANSLATE. Return the exact same text.
#             4. If type is "paragraph": Translate naturally with proper grammar.
            
#             GLOSSARY & RULES (MUST FOLLOW):
#             - "Subject" MUST be translated as "Participant/Patient". NEVER translate it as "Topic" or "Matter".
#             - "Initial" MUST be translated as "Signature/Sign". NEVER translate it as "Start".
#             - TRANSLITERATE names of doctors, people, and places accurately into the {lang} script.
#             - DO NOT translate email addresses, URLs, or pure numbers.
#             - You MUST return the exact same 'id' for each block. Do not combine or skip any IDs.
            
#             Data to translate: {input_data}"""
            
#             final_translations = []
#             max_retries = 3
            
#             for attempt in range(max_retries):
#                 try:
#                     response = structured_llm.invoke(prompt)
#                     trans_dict = {item.id: item.translated_text for item in response.translations}
#                     for i, b in enumerate(page_blocks):
#                         final_translations.append(trans_dict.get(i, b["text"]))
#                     break 
                    
#                 except Exception as e:
#                     error_msg = str(e)
#                     if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
#                         print(f"Rate limit hit for {lang} (Page {page_num+1}). Waiting 15 seconds... (Attempt {attempt + 1}/{max_retries})")
#                         time.sleep(15) 
#                     else:
#                         print(f"LLM Error on page {page_num+1} for {lang}: {e}")
#                         final_translations = [b["text"] for b in page_blocks]
#                         break
#             else:
#                 print(f"Failed to translate Page {page_num+1} after {max_retries} attempts. Falling back to English.")
#                 final_translations = [b["text"] for b in page_blocks]

#             translated_pages_data.append({
#                 "original": page_blocks,
#                 "translated": final_translations
#             })
            
#             time.sleep(3) 
            
#         out_path = state["pdf_path"].replace(".pdf", f"_{lang}.pdf").replace("uploads", "outputs")
#         reconstruct_pdf(state["pdf_path"], translated_pages_data, lang, out_path)
#         output_files.append(out_path)

#     return {"output_files": output_files}

# workflow = StateGraph(PDFState)
# workflow.add_node("extract", extract_node)
# workflow.add_node("process", translate_and_reconstruct_node)

# workflow.set_entry_point("extract")
# workflow.add_edge("extract", "process")
# workflow.add_edge("process", END)

# app_graph = workflow.compile()


# # version 2
# import os
# import time
# from typing import TypedDict, List
# from langgraph.graph import StateGraph, END
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.messages import HumanMessage
# from pdf_utils import pdf_to_base64_images, html_to_pdf

# # Gemini 2.5 Flash is excellent for Vision + Coding + Translation
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

# class PDFState(TypedDict):
#     pdf_path: str
#     target_languages: List[str]
#     page_images: List[str]  # Base64 images
#     output_files: List[str]

# def extract_images_node(state: PDFState):
#     """Agent Step 1: 'See' the document by converting it to images."""
#     print("Extracting images for Vision Agent...")
#     images = pdf_to_base64_images(state["pdf_path"])
#     return {"page_images": images}

# def vision_translation_node(state: PDFState):
#     """Agent Step 2 & 3: Analyze layout, Translate, and Generate HTML."""
#     target_languages = state["target_languages"]
#     page_images = state["page_images"]
#     output_files = []

#     for lang in target_languages:
#         print(f"Agent starting translation for: {lang}")
#         translated_html_pages = []
        
#         for page_num, b64_img in enumerate(page_images):
#             print(f"  -> Processing page {page_num + 1}...")
            
#             # THE AGENTIC PROMPT
#             prompt = f"""You are an Expert Frontend Developer and Medical/Legal Translator.
#             I have provided an image of a document page.
            
#             YOUR MISSION:
#             1. Recreate the exact visual layout of this document using HTML5 and inline CSS.
#             2. Translate ALL text into {lang}.
#             3. Use CSS Flexbox or CSS Grid to perfectly align tables, signature blocks, and columns.
#             4. PRESERVE ALL FORM ELEMENTS: Keep underscores (___), checkboxes ([ ]), and empty spaces exactly where they are.
#             5. TRANSLITERATE names of people and places accurately into the {lang} script.
#             6. "Subject" MUST be translated contextually as "Participant/Patient".
            
#             OUTPUT FORMAT:
#             Return ONLY valid HTML code. Do not include markdown formatting like ```html. Do not include <html> or <body> tags, just the inner content (divs, tables, p tags).
#             """
            
#             # Create Multimodal Message
#             message = HumanMessage(
#                 content=[
#                     {"type": "text", "text": prompt},
#                     {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
#                 ]
#             )
            
#             # Retry Logic for Rate Limits
#             max_retries = 3
#             for attempt in range(max_retries):
#                 try:
#                     response = llm.invoke([message])
                    
#                     # Clean the output (remove markdown code blocks if Gemini accidentally adds them)
#                     clean_html = response.content.replace("```html", "").replace("```", "").strip()
#                     translated_html_pages.append(clean_html)
#                     break
                    
#                 except Exception as e:
#                     if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
#                         print(f"Rate limit hit. Waiting 15s... (Attempt {attempt+1})")
#                         time.sleep(15)
#                     else:
#                         print(f"Error on page {page_num+1}: {e}")
#                         translated_html_pages.append(f"<p>Error translating page {page_num+1}</p>")
#                         break
            
#             time.sleep(3) # Safe delay between pages
            
#         # Reconstruct the PDF using the generated HTML
#         out_path = state["pdf_path"].replace(".pdf", f"_{lang}.pdf").replace("uploads", "outputs")
#         print(f"Rendering final PDF for {lang}...")
#         html_to_pdf(translated_html_pages, out_path)
#         output_files.append(out_path)

#     return {"output_files": output_files}

# # Build LangGraph Workflow
# workflow = StateGraph(PDFState)
# workflow.add_node("extract", extract_images_node)
# workflow.add_node("process", vision_translation_node)

# workflow.set_entry_point("extract")
# workflow.add_edge("extract", "process")
# workflow.add_edge("process", END)

# app_graph = workflow.compile()

# # verion 3 
# import os
# import time
# import concurrent.futures
# from typing import TypedDict, List
# from langgraph.graph import StateGraph, END
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.messages import HumanMessage
# from pdf_utils import pdf_to_base64_images, html_to_pdf

# # Using Gemini 2.5 Flash
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

# class PDFState(TypedDict):
#     pdf_path: str
#     target_languages: List[str]
#     page_images: List[str]
#     output_files: List[str]

# def extract_images_node(state: PDFState):
#     print("Extracting images for Vision Agent...")
#     images = pdf_to_base64_images(state["pdf_path"])
#     return {"page_images": images}

# def vision_translation_node(state: PDFState):
#     target_languages = state["target_languages"]
#     page_images = state["page_images"]
#     output_files = []

#     for lang in target_languages:
#         print(f"\nAgent starting translation for: {lang}")
        
#         # Function to process a single page (Allows Parallel Execution)
#         def process_single_page(page_data):
#             page_num, b64_img = page_data
#             print(f"  -> Processing page {page_num + 1}...")
            
#             prompt = f"""You are an Expert Frontend Developer and Medical/Legal Translator.
#             I have provided an image of a document page.
            
#             YOUR MISSION:
#             1. Recreate the exact visual layout of this document using HTML5.
#             2. Translate ALL text into {lang}.
#             3. TABLES MUST BE FULL WIDTH: Use <table style="width: 100%;"> for all tables.
#             4. CONTINUOUS FLOW: Do not add artificial page breaks.
#             5. PRESERVE ALL FORM ELEMENTS: Keep underscores (___), checkboxes ([ ]), and empty spaces exactly where they are.
#             6. TRANSLITERATE names of people and places accurately into the {lang} script.
#             7. "Subject" MUST be translated contextually as "Participant/Patient".
            
#             OUTPUT FORMAT:
#             Return ONLY valid HTML code. Do not include markdown formatting like ```html. Do not include <html> or <body> tags, just the inner content (divs, tables, p tags).
#             """
            
#             message = HumanMessage(
#                 content=[
#                     {"type": "text", "text": prompt},
#                     {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
#                 ]
#             )
            
#             max_retries = 3
#             for attempt in range(max_retries):
#                 try:
#                     response = llm.invoke([message])
#                     clean_html = response.content.replace("```html", "").replace("```", "").strip()
#                     return page_num, clean_html
#                 except Exception as e:
#                     if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
#                         print(f"Rate limit hit on page {page_num+1}. Waiting 15s... (Attempt {attempt+1})")
#                         time.sleep(15)
#                     else:
#                         print(f"Error on page {page_num+1}: {e}")
#                         return page_num, f"<p>Error translating page {page_num+1}</p>"
            
#             return page_num, f"<p>Failed to translate page {page_num+1}</p>"

#         # FIX: Safe Parallel Processing (Cuts time in half!)
#         # max_workers=2 ensures we process fast but don't instantly trigger Google's 15 RPM limit
#         translated_pages_unordered = []
#         with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
#             results = executor.map(process_single_page, enumerate(page_images))
#             for result in results:
#                 translated_pages_unordered.append(result)
                
#         # Sort pages back into correct order (since parallel processing finishes out of order)
#         translated_pages_unordered.sort(key=lambda x: x[0])
#         translated_html_pages = [html for num, html in translated_pages_unordered]
            
#         # Reconstruct the PDF
#         out_path = state["pdf_path"].replace(".pdf", f"_{lang}.pdf").replace("uploads", "outputs")
#         print(f"Rendering final continuous PDF for {lang}...")
#         html_to_pdf(translated_html_pages, out_path)
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
import concurrent.futures
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from pdf_utils import pdf_to_base64_images, html_to_pdf

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

class PDFState(TypedDict):
    pdf_path: str
    target_languages: List[str]
    page_images: List[str]
    output_files: List[str]

def extract_images_node(state: PDFState):
    print("Extracting images for Vision Agent...")
    images = pdf_to_base64_images(state["pdf_path"])
    return {"page_images": images}

def vision_translation_node(state: PDFState):
    target_languages = state["target_languages"]
    page_images = state["page_images"]
    output_files = []

    for lang in target_languages:
        print(f"\nAgent starting translation for: {lang}")
        
        def process_single_page(page_data):
            page_num, b64_img = page_data
            print(f"  -> Processing page {page_num + 1}...")
            
            # THE UPDATED PROMPT (Fixes Boxes and Signatures)
            prompt = f"""You are an Expert Frontend Developer and Medical/Legal Translator.
            Recreate the exact visual layout of the provided document image using HTML5, and translate ALL text into {lang}.
            
            CRITICAL CODING RULES (MUST FOLLOW):
            1. DATA TABLES vs LAYOUT TABLES:
               - If you see an actual table with visible black grid lines, you MUST use `<table class="grid-table">`.
               - If you are aligning signature blocks, dates, or headers side-by-side, use a normal `<table>` (which has no borders).
            2. NO INPUT TAGS: Do NOT use <input> tags. Use literal text like `[ ]` for checkboxes and `_________` for blank lines. Match the approximate length of the original blank lines.
            3. STRICT TABLE WIDTHS: For grid-tables, assign percentage widths to the columns in the first row (e.g., `<td style="width: 15%;">`) to prevent distortion.
            4. Do not use absolute positioning (`position: absolute`).
            
            TRANSLATION RULES:
            - "Subject" MUST be translated contextually as "Participant/Patient".
            - "Initial" MUST be translated as "Signature/Sign".
            - TRANSLITERATE names of people and places accurately into the {lang} script.
            - DO NOT translate email addresses, URLs, or pure numbers.
            
            OUTPUT FORMAT:
            Return ONLY valid HTML code. Do not include markdown formatting like ```html. Do not include <html>, <head>, or <body> tags, just the inner content.
            """
            
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                ]
            )
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = llm.invoke([message])
                    clean_html = response.content.replace("```html", "").replace("```", "").strip()
                    return page_num, clean_html
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        print(f"Rate limit hit on page {page_num+1}. Waiting 15s... (Attempt {attempt+1})")
                        time.sleep(15)
                    else:
                        print(f"Error on page {page_num+1}: {e}")
                        return page_num, f"<p>Error translating page {page_num+1}</p>"
            
            return page_num, f"<p>Failed to translate page {page_num+1}</p>"

        # Parallel Processing (2 pages at a time)
        translated_pages_unordered = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            results = executor.map(process_single_page, enumerate(page_images))
            for result in results:
                translated_pages_unordered.append(result)
                
        # Sort pages back into correct order
        translated_pages_unordered.sort(key=lambda x: x[0])
        translated_html_pages = [html for num, html in translated_pages_unordered]
            
        # Reconstruct the PDF
        out_path = state["pdf_path"].replace(".pdf", f"_{lang}.pdf").replace("uploads", "outputs")
        print(f"Rendering final continuous PDF for {lang}...")
        html_to_pdf(translated_html_pages, out_path)
        output_files.append(out_path)

    return {"output_files": output_files}

workflow = StateGraph(PDFState)
workflow.add_node("extract", extract_images_node)
workflow.add_node("process", vision_translation_node)

workflow.set_entry_point("extract")
workflow.add_edge("extract", "process")
workflow.add_edge("process", END)

app_graph = workflow.compile()