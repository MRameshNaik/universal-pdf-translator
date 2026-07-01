from flask import Flask, request, send_file, Response, stream_with_context
from flask_cors import CORS
import os
import zipfile
import time
import queue
from dotenv import load_dotenv
from logger import log_queues, send_log

os.environ["GIO_USE_VFS"] = "local"
load_dotenv()

from graph import app_graph

app = Flask(__name__)
CORS(app)

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

@app.route('/stream-logs/<client_id>')
def stream_logs(client_id):
    """SSE Endpoint: Streams real-time logs to the React frontend."""
    if client_id not in log_queues:
        log_queues[client_id] = queue.Queue()
        
    def generate():
        # Send 2KB of blank padding to instantly overflow the browser's buffer
        yield f": {' ' * 2048}\n\n"
        
        q = log_queues[client_id]
        while True:
            try:
                msg = q.get(timeout=15)
                yield f"data: {msg}\n\n"
                if msg == "DONE":
                    break
            except queue.Empty:
                yield f"data: PING\n\n"
                
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

@app.route('/translate', methods=['POST'])
def translate_pdf():
    request_start_time = time.time()
    
    if 'file' not in request.files:
        return {"error": "No file provided"}, 400
    
    file = request.files['file']
    languages = request.form.get('languages').split(',')
    client_id = request.form.get('client_id')
    
    send_log(client_id, f"[START] Received document: {file.filename}")
    send_log(client_id, f"[INFO] Target Languages: {', '.join(languages)}")
    
    if len(languages) > 3:
        return {"error": "Maximum 3 languages allowed"}, 400

    pdf_path = os.path.join("uploads", file.filename)
    file.save(pdf_path)

    initial_state = {
        "pdf_path": pdf_path,
        "target_languages": languages,
        "page_images": [],
        "page_texts": [],
        "output_files": [],
        "client_id": client_id # Passed to graph.py!
    }
    
    try:
        result = app_graph.invoke(initial_state)
        output_files = result["output_files"]

        if len(output_files) == 1:
            response_file = output_files[0]
        else:
            send_log(client_id, "[INFO] Zipping multiple PDFs...")
            zip_path = os.path.join("outputs", "translated_pdfs.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for f in output_files:
                    zipf.write(f, os.path.basename(f))
            response_file = zip_path
            
        total_time = time.time() - request_start_time
        send_log(client_id, f"[SUCCESS] Total process completed in {total_time:.1f} seconds.")
    except Exception as e:
        send_log(client_id, f"[ERROR] Pipeline failed: {str(e)}")
        response_file = None
    finally:
        send_log(client_id, "DONE")
            
    if response_file:
        return send_file(response_file, as_attachment=True)
    return {"error": "Translation failed"}, 500

if __name__ == '__main__':
    app.run(port=5000, debug=True, threaded=True)