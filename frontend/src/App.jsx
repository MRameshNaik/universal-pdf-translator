import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Upload, Languages, Loader2, Download, Terminal, CheckCircle2 } from 'lucide-react';

const AVAILABLE_LANGUAGES = [
  "English", "Hindi", "Telugu", "Tamil", "Kannada", "Malayalam", "Bengali", "Gujarati"
];

function App() {
  const [file, setFile] = useState(null);
  const [selectedLangs, setSelectedLangs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  
  const logsEndRef = useRef(null);
  const totalPagesRef = useRef(1);
  const pagesDoneRef = useRef(0);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleLangToggle = (lang) => {
    if (selectedLangs.includes(lang)) {
      setSelectedLangs(selectedLangs.filter(l => l !== lang));
    } else {
      if (selectedLangs.length < 3) setSelectedLangs([...selectedLangs, lang]);
      else alert("You can only select up to 3 languages at once.");
    }
  };

  const handleUpload = async () => {
    if (!file || selectedLangs.length === 0) return alert("Select a file and at least 1 language.");
    
    setLoading(true);
    setHasStarted(true);
    setLogs([]);
    setProgress(0);
    pagesDoneRef.current = 0;

    const clientId = Math.random().toString(36).substring(7);
    let postSent = false;
    
    // 1. Open SSE Connection FIRST
    // const eventSource = new EventSource(`http://localhost:5000/stream-logs/${clientId}`);
    const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";
    const eventSource = new EventSource(`${API_BASE_URL}/stream-logs/${clientId}`);
    
    // Wait for the connection to open BEFORE sending the heavy PDF
    eventSource.onopen = async () => {
      if (postSent) return;
      postSent = true;
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('languages', selectedLangs.join(','));
      formData.append('client_id', clientId);

      try {
        // const response = await axios.post('http://localhost:5000/translate', formData, {
        const response = await axios.post(`${API_BASE_URL}/translate`, formData, {
          responseType: 'blob', 
        });

        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', selectedLangs.length > 1 ? 'translated_pdfs.zip' : `translated_${selectedLangs[0]}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } catch (error) {
        console.error(error);
        setLogs(prev => [...prev, "[ERROR] Translation failed or server crashed."]);
        eventSource.close();
        setLoading(false);
      }
    };
    
    eventSource.onmessage = (event) => {
      const msg = event.data;
      if (msg === "PING") return;
      if (msg === "DONE") {
        setProgress(100);
        eventSource.close();
        setLoading(false);
        return;
      }

      setLogs(prev => [...prev, msg]);

      if (msg.includes("Extracted") && msg.includes("pages")) {
        const match = msg.match(/Extracted (\d+) pages/);
        if (match) totalPagesRef.current = parseInt(match[1]);
        setProgress(10);
      } else if (msg.includes("[SUCCESS] Page") || msg.includes("[FALLBACK] Embedding")) {
        pagesDoneRef.current += 1;
        const totalExpected = totalPagesRef.current * selectedLangs.length;
        const currentProgress = 10 + Math.floor((pagesDoneRef.current / totalExpected) * 80);
        setProgress(currentProgress);
      } else if (msg.includes("Rendering PDF")) {
        setProgress(95);
      }
    };
    
    eventSource.onerror = () => {
        if(!postSent) {
            setLogs(prev => [...prev, "[ERROR] Failed to connect to log server."]);
            setLoading(false);
            eventSource.close();
        }
    };
  };

  // Keep only the last 3 logs for a clean UI
  const visibleLogs = logs.slice(-3);

  return (
    <div className="min-h-screen bg-slate-50 p-6 font-sans text-slate-800 flex flex-col items-center">
      
      <div className="mb-8 text-center mt-10">
        <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">Enterprise Document AI</h1>
        <p className="text-slate-500 mt-2 text-lg">Agentic Vision-to-HTML Translation Pipeline</p>
      </div>

      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-sm border border-slate-200 p-8 flex flex-col">
        
        <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center mb-8 hover:bg-slate-50 transition-colors">
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} className="hidden" id="file-upload" />
          <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
            <Upload className="w-10 h-10 text-blue-600 mb-3" />
            <span className="text-slate-700 font-semibold">{file ? file.name : "Click to upload PDF"}</span>
            <span className="text-slate-400 text-sm mt-1">Max 10MB</span>
          </label>
        </div>

        <div className="mb-6">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center">
            <Languages className="w-4 h-4 mr-2"/> Target Languages (Max 3)
          </h3>
          <div className="flex flex-wrap gap-2">
            {AVAILABLE_LANGUAGES.map(lang => (
              <button
                key={lang}
                onClick={() => handleLangToggle(lang)}
                className={`px-3 py-1.5 rounded-lg border text-sm font-medium transition-all ${
                  selectedLangs.includes(lang) 
                  ? 'bg-blue-600 text-white border-blue-600 shadow-md' 
                  : 'bg-white text-slate-600 border-slate-200 hover:border-blue-400'
                }`}
              >
                {lang}
              </button>
            ))}
          </div>
        </div>

        {/* THE TERMINAL & PROGRESS BAR (Sandwiched perfectly) */}
        {hasStarted && (
          <div className="w-full bg-slate-900 rounded-xl p-4 mb-6 shadow-inner animate-fade-in">
            <div className="flex justify-between items-center mb-2">
              <span className="text-slate-300 text-xs font-mono flex items-center">
                <Terminal className="w-3 h-3 mr-2"/> Agent Status
              </span>
              <span className="text-blue-400 text-xs font-bold flex items-center">
                {progress === 100 ? <><CheckCircle2 className="w-3 h-3 mr-1"/> Complete</> : `${progress}%`}
              </span>
            </div>
            
            <div className="w-full bg-slate-800 rounded-full h-1.5 mb-3">
              <div 
                className="bg-blue-500 h-1.5 rounded-full transition-all duration-300 ease-out" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            
            <div className="font-mono text-xs text-slate-400 h-[54px] flex flex-col justify-end">
              {visibleLogs.length === 0 ? (
                <div className="text-slate-500 italic">Connecting to Agent...</div>
              ) : (
                visibleLogs.map((log, index) => (
                  <div key={index} className={`truncate leading-relaxed ${
                    log.includes("[ERROR]") || log.includes("[WARNING]") || log.includes("[FALLBACK]") ? "text-amber-400" :
                    log.includes("[SUCCESS]") ? "text-emerald-400" :
                    log.includes("[INFO]") ? "text-blue-400" : "text-slate-300"
                  }`}>
                    {log}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={loading || !file || selectedLangs.length === 0}
          className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold py-3.5 px-4 rounded-xl flex justify-center items-center disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-lg mt-auto"
        >
          {loading ? <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Processing...</> : <><Download className="w-5 h-5 mr-2" /> Translate Document</>}
        </button>

      </div>
    </div>
  );
}

export default App;