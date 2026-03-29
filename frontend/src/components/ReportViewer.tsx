import React from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../api/client';

interface Props {
  sessionId: string;
  report: string;
}

export default function ReportViewer({ sessionId, report }: Props) {
  const handleDownload = () => {
    window.open(api.getReportDownloadUrl(sessionId), '_blank');
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Analysis Report</h2>
          <p className="text-sm text-gray-500 mt-0.5">Your thematic analysis is complete.</p>
        </div>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={handleDownload}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Download .md
        </button>
      </div>

      <div className="card p-8">
        <div className="markdown-body max-w-none">
          <ReactMarkdown>{report}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
