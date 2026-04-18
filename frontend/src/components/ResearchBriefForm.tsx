import React, { useState } from 'react';

interface ResearchBriefFormProps {
  onNext: (data: {
    researchQuestion: string;
    participants: string;
    method: string;
  }) => void;
}

export default function ResearchBriefForm({ onNext }: ResearchBriefFormProps) {
  const [researchQuestion, setResearchQuestion] = useState('');
  const [participants, setParticipants] = useState('');
  const [method, setMethod] = useState('');
  const [error, setError] = useState('');

  const handleNext = () => {
    if (!researchQuestion.trim()) {
      setError('Please provide a research question.');
      return;
    }
    setError('');
    onNext({ researchQuestion, participants, method });
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Research Brief</h1>
        <p className="text-gray-500 text-sm">
          Define your research scope before uploading transcripts. This information guides the
          AI analysis at every stage of the pipeline.
        </p>
      </div>

      {/* Research Question */}
      <div className="card p-5 space-y-3">
        <label className="block text-sm font-semibold text-gray-700">
          Research Question <span className="text-red-500">*</span>
        </label>
        <p className="text-xs text-gray-500">
          What is the central question or objective of your study? Be as specific as possible.
        </p>
        <textarea
          className="input resize-none h-28"
          placeholder="E.g. 'How do remote workers experience work-life balance challenges, and what coping strategies do they employ to manage the blurred boundaries between professional and personal life?'"
          value={researchQuestion}
          onChange={e => setResearchQuestion(e.target.value)}
        />
      </div>

      {/* Participants */}
      <div className="card p-5 space-y-3">
        <label className="block text-sm font-semibold text-gray-700">
          Participants
        </label>
        <p className="text-xs text-gray-500">
          Describe who was interviewed — their roles, demographics, how they were recruited, and how many.
        </p>
        <textarea
          className="input resize-none h-28"
          placeholder="E.g. '12 full-time employees across product, engineering, and design at a mid-size SaaS company. Recruited via internal Slack channel. All had been working remotely for at least 6 months.'"
          value={participants}
          onChange={e => setParticipants(e.target.value)}
        />
      </div>

      {/* Method */}
      <div className="card p-5 space-y-3">
        <label className="block text-sm font-semibold text-gray-700">
          Method
        </label>
        <p className="text-xs text-gray-500">
          Describe the research method — interview format, duration, protocol, or any frameworks used.
        </p>
        <textarea
          className="input resize-none h-28"
          placeholder="E.g. 'Semi-structured interviews lasting 30-45 minutes conducted over Zoom. Protocol covered daily routines, challenges, coping mechanisms, and organizational support. Analysis follows Braun & Clarke reflexive thematic analysis.'"
          value={method}
          onChange={e => setMethod(e.target.value)}
        />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      <button
        className="btn-primary w-full py-3 text-base"
        onClick={handleNext}
      >
        Continue to Transcript Upload →
      </button>
    </div>
  );
}
