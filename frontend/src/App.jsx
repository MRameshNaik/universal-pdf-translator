import React, { useState } from 'react';
import axios from 'axios';
import { Upload, Languages, Loader2, Download } from 'lucide-react';

const AVAILABLE_LANGUAGES = [
  "English", "Hindi", "Telugu", "Tamil", "Kannada", "Malayalam", "Bengali", "Gujarati"
];

function App() {
  const [file, setFile] = useState(null);
  const [selectedLangs, setSelectedLangs] = useState([]);
  const [loading, setLoading] = useState(false);

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
    const formData = new FormData();
    formData.append('file', file);
    formData.append('languages', selectedLangs.join(','));

    try {
      const response = await axios.post('http://localhost:5000/translate', formData, {
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
      alert("Translation failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-12 px-4">
      <div className="max-w-2xl w-full bg-white rounded-xl shadow-lg p-8">
        <h1 className="text-3xl font-bold text-center mb-2 text-gray-800">Universal PDF Translator</h1>
        <p className="text-center text-gray-500 mb-8">Upload any PDF (Forms, Resumes, Stories) and translate it into up to 3 languages.</p>

        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-8">
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} className="hidden" id="file-upload" />
          <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
            <Upload className="w-12 h-12 text-blue-500 mb-4" />
            <span className="text-gray-700 font-medium">{file ? file.name : "Click to upload PDF"}</span>
          </label>
        </div>

        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-4 flex items-center"><Languages className="w-5 h-5 mr-2"/> Select Target Languages (Max 3)</h3>
          <div className="flex flex-wrap gap-3">
            {AVAILABLE_LANGUAGES.map(lang => (
              <button
                key={lang}
                onClick={() => handleLangToggle(lang)}
                className={`px-4 py-2 rounded-full border text-sm font-medium transition-colors ${
                  selectedLangs.includes(lang) ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
                }`}
              >
                {lang}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleUpload}
          disabled={loading || !file || selectedLangs.length === 0}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg flex justify-center items-center disabled:opacity-50"
        >
          {loading ? <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Translating...</> : <><Download className="w-5 h-5 mr-2" /> Translate & Download</>}
        </button>
      </div>
    </div>
  );
}

export default App;