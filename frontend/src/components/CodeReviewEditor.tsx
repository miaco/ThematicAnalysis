import React, { useState } from 'react';
import { Code, Quote, EvaluationScores, api } from '../api/client';

function ScoreBadge({ scores }: { scores: EvaluationScores | null }) {
  if (!scores) return null;
  const avg = ((scores.coverage + scores.actionability + scores.distinctiveness + scores.relevance) / 4);
  const color = avg >= 4.0 ? 'bg-green-100 text-green-700' : avg >= 3.0 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${color}`} title={`Coverage: ${scores.coverage} | Actionability: ${scores.actionability} | Distinctiveness: ${scores.distinctiveness} | Relevance: ${scores.relevance}`}>
      {avg.toFixed(1)}/5
    </span>
  );
}

function ScoreBreakdown({ scores }: { scores: EvaluationScores | null }) {
  if (!scores) return null;
  const criteria = [
    { label: 'Coverage', value: scores.coverage },
    { label: 'Actionability', value: scores.actionability },
    { label: 'Distinctiveness', value: scores.distinctiveness },
    { label: 'Relevance', value: scores.relevance },
  ];
  return (
    <div className="flex flex-wrap gap-2 mt-1.5">
      {criteria.map(c => {
        const color = c.value >= 4.0 ? 'text-green-600' : c.value >= 3.0 ? 'text-yellow-600' : 'text-red-600';
        return (
          <span key={c.label} className="text-xs text-gray-500">
            {c.label}: <span className={`font-medium ${color}`}>{c.value.toFixed(1)}</span>
          </span>
        );
      })}
    </div>
  );
}

interface Props {
  sessionId: string;
  codes: Code[];
  quotes: Quote[];
  onSubmit: () => void;
}

export default function CodeReviewEditor({ sessionId, codes: initialCodes, quotes, onSubmit }: Props) {
  const [codes, setCodes] = useState<Code[]>(initialCodes);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editGroup, setEditGroup] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mergeSource, setMergeSource] = useState<string | null>(null);

  const getQuotesForCode = (code: Code) =>
    quotes.filter(q => code.quote_ids.includes(q.id));

  const startEdit = (code: Code) => {
    setEditingId(code.id);
    setEditLabel(code.label);
    setEditDesc(code.description);
    setEditGroup(code.group || '');
  };

  const saveEdit = () => {
    if (!editingId) return;
    setCodes(prev => prev.map(c =>
      c.id === editingId
        ? { ...c, label: editLabel, description: editDesc, group: editGroup || null }
        : c
    ));
    setEditingId(null);
  };

  const deleteCode = (id: string) => {
    setCodes(prev => prev.filter(c => c.id !== id));
  };

  const mergeCodes = (targetId: string) => {
    if (!mergeSource || mergeSource === targetId) { setMergeSource(null); return; }
    const source = codes.find(c => c.id === mergeSource);
    if (!source) return;
    setCodes(prev => prev
      .filter(c => c.id !== mergeSource)
      .map(c => c.id === targetId
        ? { ...c, quote_ids: [...new Set([...c.quote_ids, ...source.quote_ids])] }
        : c
      )
    );
    setMergeSource(null);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      await api.submitCodeReview(sessionId, codes);
      onSubmit();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  // Group codes
  const groups = Array.from(new Set(codes.map(c => c.group || 'Ungrouped')));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Code Review</h2>
          <p className="text-sm text-gray-500 mt-0.5">{codes.length} codes extracted. Review, edit, merge or delete before proceeding.</p>
        </div>
        <div className="flex gap-2">
          {mergeSource && (
            <span className="text-xs bg-yellow-100 text-yellow-700 px-3 py-1.5 rounded-full">
              Select target to merge into
            </span>
          )}
          <button
            className="btn-primary"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? 'Submitting...' : 'Submit Review'}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-700 text-sm px-4 py-2 rounded-lg border border-red-200">{error}</div>}

      {groups.map(group => (
        <div key={group} className="card overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-600">{group}</h3>
          </div>
          <div className="divide-y divide-gray-100">
            {codes.filter(c => (c.group || 'Ungrouped') === group).map(code => {
              const codeQuotes = getQuotesForCode(code);
              const isEditing = editingId === code.id;
              const isExpanded = expandedId === code.id;
              const isMergeSource = mergeSource === code.id;

              return (
                <div key={code.id} className={`p-4 ${isMergeSource ? 'bg-yellow-50' : ''}`}>
                  {isEditing ? (
                    <div className="space-y-2">
                      <input
                        className="input text-sm font-medium"
                        value={editLabel}
                        onChange={e => setEditLabel(e.target.value)}
                        placeholder="Code label"
                      />
                      <textarea
                        className="input text-sm resize-none h-16"
                        value={editDesc}
                        onChange={e => setEditDesc(e.target.value)}
                        placeholder="Description"
                      />
                      <input
                        className="input text-sm"
                        value={editGroup}
                        onChange={e => setEditGroup(e.target.value)}
                        placeholder="Group (optional)"
                      />
                      <div className="flex gap-2">
                        <button className="btn-primary text-sm py-1" onClick={saveEdit}>Save</button>
                        <button className="btn-secondary text-sm py-1" onClick={() => setEditingId(null)}>Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm text-gray-900">{code.label}</span>
                            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                              {codeQuotes.length} quote{codeQuotes.length !== 1 ? 's' : ''}
                            </span>
                            <ScoreBadge scores={code.scores} />
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">{code.description}</p>
                          <ScoreBreakdown scores={code.scores} />
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <button
                            className="text-xs text-gray-500 hover:text-brand-600 px-2 py-1 rounded hover:bg-brand-50"
                            onClick={() => startEdit(code)}
                          >Edit</button>
                          <button
                            className={`text-xs px-2 py-1 rounded ${isMergeSource ? 'text-yellow-700 bg-yellow-100' : mergeSource ? 'text-brand-600 hover:bg-brand-50' : 'text-gray-500 hover:text-brand-600 hover:bg-brand-50'}`}
                            onClick={() => mergeSource ? mergeCodes(code.id) : setMergeSource(code.id)}
                          >
                            {isMergeSource ? 'Cancel' : mergeSource ? 'Merge here' : 'Merge'}
                          </button>
                          <button
                            className="text-xs text-red-500 hover:bg-red-50 px-2 py-1 rounded"
                            onClick={() => deleteCode(code.id)}
                          >Delete</button>
                        </div>
                      </div>

                      {codeQuotes.length > 0 && (
                        <button
                          className="text-xs text-brand-600 mt-2 hover:underline"
                          onClick={() => setExpandedId(isExpanded ? null : code.id)}
                        >
                          {isExpanded ? 'Hide quotes' : `Show ${codeQuotes.length} quote(s)`}
                        </button>
                      )}

                      {isExpanded && (
                        <div className="mt-2 space-y-2">
                          {codeQuotes.map(q => (
                            <blockquote key={q.id} className="text-xs text-gray-600 border-l-2 border-brand-300 pl-3 italic">
                              "{q.text.length > 200 ? q.text.slice(0, 200) + '...' : q.text}"
                            </blockquote>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      <button
        className="btn-primary w-full py-3"
        onClick={handleSubmit}
        disabled={loading}
      >
        {loading ? 'Submitting...' : `Submit Review (${codes.length} codes) & Continue`}
      </button>
    </div>
  );
}
