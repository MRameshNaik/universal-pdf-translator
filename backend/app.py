from flask import Flask, request, send_file
from flask_cors import CORS
import os
import zipfile
from dotenv import load_dotenv

# LOAD ENV FIRST
load_dotenv()

# THEN IMPORT GRAPH
from graph import app_graph

app = Flask(__name__)
CORS(app)

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

@app.route('/translate', methods=['POST'])
def translate_pdf():
    if 'file' not in request.files:
        return {"error": "No file provided"}, 400
    
    file = request.files['file']
    languages = request.form.get('languages').split(',')
    
    if len(languages) > 3:
        return {"error": "Maximum 3 languages allowed"}, 400

    pdf_path = os.path.join("uploads", file.filename)
    file.save(pdf_path)

    initial_state = {
        "pdf_path": pdf_path,
        "target_languages": languages,
        "extracted_pages": [],
        "output_files": []
    }
    
    result = app_graph.invoke(initial_state)
    output_files = result["output_files"]

    if len(output_files) == 1:
        return send_file(output_files[0], as_attachment=True)
    
    zip_path = os.path.join("outputs", "translated_pdfs.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for f in output_files:
            zipf.write(f, os.path.basename(f))
            
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(port=5000, debug=True)