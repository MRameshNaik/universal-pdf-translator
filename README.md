# 🌐 Enterprise Document AI: Universal PDF Translator

![Agentic Workflow](https://img.shields.io/badge/Architecture-Agentic_AI-blue) ![Gemini](https://img.shields.io/badge/Model-Gemini_2.5_Flash-orange) ![Docker](https://img.shields.io/badge/Deployment-Dockerized-blue)

A State-of-the-Art (SOTA) Multimodal AI pipeline that translates complex PDFs (Clinical Trials, Legal Forms, Resumes, and Reports) into multiple languages while **flawlessly preserving the original visual layout**. 

Specially optimized for complex Indian scripts (Hindi, Telugu, Tamil, Malayalam, etc.), this engine abandons traditional, error-prone PDF text-overwriting in favor of a **Vision-to-HTML Agentic Architecture**.

---

## 🧠 The Essence of the Project

Traditional PDF translators fail because PDFs are not text documents; they are canvases of absolute coordinates. When translating English into Indian languages, the text expands by 30-50%, causing translated words to bleed out of boxes, overlap, and destroy table structures. Furthermore, complex Indian ligatures (matras/ottus) often fail to render, resulting in the dreaded "Tofu" (blank box) bug.

**This project solves PDF translation by treating it as a Frontend Development task.** 
Using **Gemini 2.5 Flash (Vision)** orchestrated by **LangGraph**, the AI "looks" at the document, translates the text contextually, and writes pure HTML5/CSS to rebuild the document from scratch. Finally, a HarfBuzz-enabled rendering engine (`WeasyPrint`) converts the HTML back into a pristine PDF.

---

## ✨ Key Innovations & Features

- **Dual-Channel Input:** Feeds the AI both high-resolution images (for layout understanding) and raw extracted text (for spelling accuracy), eliminating OCR hallucinations.
- **Complex Layout Preservation:** Automatically detects and perfectly recreates grid tables, checkboxes (`[ ]`), and side-by-side signature blocks.
- **Smart Form-Field Interception:** Uses Python Regex to intercept AI-generated underscores and replace them with unbreakable CSS `<span class="form-blank"></span>` components, ensuring fill-in-the-blank lines never distort table widths.
- **HarfBuzz Font Shaping:** Natively supports complex Indian scripts using local Google Noto Fonts, guaranteeing perfect typography.
- **Enterprise Resilience:** Includes Exponential Backoff for API rate limits, BeautifulSoup4 for auto-repairing broken AI-generated HTML, and a "Graceful Fallback" that injects the original English text if a page fails to translate.
- **Real-Time SSE UI:** A sleek React frontend featuring a live terminal and mathematical progress bar that streams the Agent's thought process in real-time.

---

## 🏗️ System Architecture

1. **The Eye (`PyMuPDF` & `pdfplumber`):** Converts uploaded PDFs into 150 DPI Base64 images and extracts raw text.
2. **The Brain (`LangGraph` & `Gemini 1.5 Flash`):** An Agentic workflow processes pages in parallel. Using strict XML-tagged prompts, the AI translates the text and generates structural HTML5.
3. **The Sanitizer (`BeautifulSoup4` & `Regex`):** Cleans the AI's output, auto-closes broken HTML tags, and injects strict CSS components.
4. **The Builder (`WeasyPrint`):** Renders the sanitized HTML back into a downloadable PDF using embedded Unicode fonts.

---

## 💻 Tech Stack

*   **AI & Orchestration:** LangChain, LangGraph, Google Gemini 1.5 Flash (Multimodal)
*   **Backend:** Python 3.11, Flask, Gunicorn, PyMuPDF, WeasyPrint, BeautifulSoup4
*   **Frontend:** React, Vite, Tailwind CSS, Server-Sent Events (SSE)
*   **Infrastructure:** Docker, Docker Compose

---

## 🚀 How to Run Locally

This application is fully Dockerized to ensure complex C++ rendering libraries (GTK3/Pango) install perfectly on any machine.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- A Google Gemini API Key.

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/universal-pdf-translator.git
   cd universal-pdf-translator
