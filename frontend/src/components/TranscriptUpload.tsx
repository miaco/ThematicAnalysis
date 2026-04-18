import React, { useState, useCallback } from 'react';
import { api } from '../api/client';

interface TranscriptUploadProps {
  sessionId: string;
  onPipelineStarted: () => void;
}

export default function TranscriptUpload({ sessionId, onPipelineStarted }: TranscriptUploadProps) {
  const [transcriptSourceUrl, setTranscriptSourceUrl] = useState('');
  const [screenerText, setScreenerText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);

  const handleFiles = useCallback((newFiles: FileList | null) => {
    if (!newFiles) return;
    const txtFiles = Array.from(newFiles).filter(f =>
      f.name.endsWith('.txt') || f.name.endsWith('.pdf') || f.name.endsWith('.docx') || f.type === 'text/plain' || f.type === 'application/pdf' || f.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    );
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name));
      const added = txtFiles.filter(f => !existing.has(f.name));
      return [...prev, ...added];
    });
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const handleStart = async () => {
    if (files.length === 0) { setError('Please upload at least one transcript.'); return; }

    const trimmedUrl = transcriptSourceUrl.trim();
    if (trimmedUrl) {
      try {
        const parsed = new URL(trimmedUrl);
        if (!['http:', 'https:'].includes(parsed.protocol)) {
          setError('Transcript source link must start with http:// or https://.');
          return;
        }
      } catch {
        setError('Please enter a valid transcript source link.');
        return;
      }
    }

    setError('');
    setWarnings([]);
    setLoading(true);

    try {
      // Set screener questions if provided
      const questions = screenerText.split('\n').map(q => q.trim()).filter(Boolean);
      if (questions.length > 0) {
        await api.setScreener(sessionId, questions);
      }

      // Upload transcripts
      await api.uploadTranscripts(sessionId, files);

      // Fetch from URL if provided and it looks like a direct file link
      if (trimmedUrl) {
        try {
          await api.fetchTranscriptFromUrl(sessionId, trimmedUrl);
        } catch {
          // Non-fatal — the URL may be a folder link, not a direct file
        }
      }

      // Start pipeline
      await api.runPipeline(sessionId);

      onPipelineStarted();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Upload Transcripts</h1>
        <p className="text-gray-500 text-sm">Upload your interview transcripts and optionally configure screener questions for demographic segmentation.</p>
      </div>

      <div className="card p-5 space-y-3">
        <div>
          <label className="block text-sm font-semibold text-gray-700">Transcript Source Link</label>
          <p className="text-xs text-gray-500 mt-0.5">
            Optional. Link to a publicly accessible transcript file or folder (Google Drive, SharePoint, Dropbox). Direct file links (.txt, .pdf, .docx) will be fetched automatically when you start the analysis.
          </p>
        </div>
        <input
          className="input"
          type="url"
          placeholder="https://example.com/folder/your-transcripts"
          value={transcriptSourceUrl}
          onChange={e => setTranscriptSourceUrl(e.target.value)}
        />
      </div>

      {/* Screener Questions */}
      <div className="card p-5 space-y-3">
        <div>
          <label className="block text-sm font-semibold text-gray-700">Screener / Demographic Questions</label>
          <p className="text-xs text-gray-500 mt-0.5">One question per line. Used for participant segmentation in analysis.</p>
        </div>
        <textarea
          className="input resize-none h-24"
          placeholder={"job_title\nage_group\nyears_experience\ndepartment"}
          value={screenerText}
          onChange={e => setScreenerText(e.target.value)}
        />
      </div>

      {/* File Upload */}
      <div className="card p-5 space-y-3">
        <label className="block text-sm font-semibold text-gray-700">
          Transcripts <span className="text-red-500">*</span>
        </label>

        <div
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
            dragOver ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50'
          }`}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <div className="flex flex-col items-center gap-2">
            <svg className="w-10 h-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <div>
              <span className="text-brand-600 font-medium">Click to upload</span>
              <span className="text-gray-500"> or drag and drop</span>
            </div>
            <p className="text-xs text-gray-400">.txt, .pdf, and .docx files supported (max 10 MB each)</p>
          </div>
          <input
            id="file-input"
            type="file"
            multiple
            accept=".txt,.pdf,.docx"
            className="hidden"
            onChange={e => handleFiles(e.target.files)}
          />
        </div>

        {files.length > 0 && (
          <ul className="space-y-1 mt-2">
            {files.map((f, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-gray-700 bg-gray-50 rounded px-3 py-1.5">
                <svg className="w-4 h-4 text-brand-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="truncate flex-1">{f.name}</span>
                <span className="text-gray-400 flex-shrink-0">{(f.size / 1024).toFixed(1)}KB</span>
                <button
                  onClick={e => { e.stopPropagation(); setFiles(prev => prev.filter((_, j) => j !== i)); }}
                  className="text-gray-400 hover:text-red-500 flex-shrink-0"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 rounded-lg px-4 py-3 text-sm space-y-1">
          <p className="font-medium">Some files had issues:</p>
          {warnings.map((w, i) => <p key={i}>• {w}</p>)}
        </div>
      )}

      <button
        className="btn-primary w-full py-3 text-base"
        onClick={handleStart}
        disabled={loading}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Starting Analysis...
          </span>
        ) : (
          'Start Analysis'
        )}
      </button>
    </div>
  );
}
