import React, { useState } from 'react';
import { Recommendation, api } from '../api/client';

interface Props {
  sessionId: string;
  recommendations: Recommendation[];
  onSelect: () => void;
}

export default function RecommendationSelector({ sessionId, recommendations, onSelect }: Props) {
  const [selected, setSelected] = useState<Set<string>>(
    new Set(recommendations.filter(r => r.selected).map(r => r.id))
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filterPriority, setFilterPriority] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  const toggle = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => setSelected(new Set(filtered.map(r => r.id)));
  const selectNone = () => setSelected(new Set());

  const handleSubmit = async () => {
    if (selected.size === 0) { setError('Please select at least one recommendation.'); return; }
    setLoading(true);
    setError('');
    try {
      await api.selectRecommendations(sessionId, Array.from(selected));
      onSelect();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  const filtered = filterPriority === 'all'
    ? recommendations
    : recommendations.filter(r => r.priority === filterPriority);

  const byPriority = (p: 'high' | 'medium' | 'low') =>
    recommendations.filter(r => r.priority === p);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Select Recommendations</h2>
        <p className="text-sm text-gray-500 mt-1">
          Choose which recommendations to include in your final report.
          {selected.size > 0 && <span className="ml-1 font-medium text-brand-600">{selected.size} selected</span>}
        </p>
      </div>

      {/* Summary counts */}
      <div className="grid grid-cols-3 gap-3">
        {(['high', 'medium', 'low'] as const).map(p => (
          <div key={p} className="card px-4 py-3 text-center">
            <span className={`badge-${p} inline-block mb-1`}>{p}</span>
            <p className="text-2xl font-bold text-gray-900">{byPriority(p).length}</p>
            <p className="text-xs text-gray-400">recommendations</p>
          </div>
        ))}
      </div>

      {/* Filter + actions */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-1">
          {(['all', 'high', 'medium', 'low'] as const).map(p => (
            <button
              key={p}
              onClick={() => setFilterPriority(p)}
              className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                filterPriority === p
                  ? 'bg-brand-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <button className="text-xs text-brand-600 hover:underline" onClick={selectAll}>Select all</button>
          <span className="text-gray-300">|</span>
          <button className="text-xs text-gray-500 hover:underline" onClick={selectNone}>Select none</button>
        </div>
      </div>

      {/* Recommendations list */}
      <div className="space-y-2">
        {filtered.map(rec => {
          const isSelected = selected.has(rec.id);
          return (
            <button
              key={rec.id}
              onClick={() => toggle(rec.id)}
              className={`w-full card p-4 text-left transition-all ${
                isSelected ? 'border-brand-400 bg-brand-50' : 'hover:bg-gray-50'
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Checkbox */}
                <div className={`flex-shrink-0 mt-0.5 w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                  isSelected ? 'bg-brand-500 border-brand-500' : 'border-gray-300'
                }`}>
                  {isSelected && (
                    <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>

                <div className="flex-1 space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`badge-${rec.priority}`}>{rec.priority}</span>
                    <span className="text-xs text-gray-400">{rec.supporting_theme}</span>
                  </div>
                  <p className={`text-sm ${isSelected ? 'text-brand-800' : 'text-gray-700'}`}>
                    {rec.text}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {error && <div className="bg-red-50 text-red-700 text-sm px-4 py-2 rounded-lg border border-red-200">{error}</div>}

      <button
        className="btn-primary w-full py-3"
        onClick={handleSubmit}
        disabled={loading || selected.size === 0}
      >
        {loading ? 'Processing...' : `Finalize ${selected.size} Recommendation(s) & Write Report`}
      </button>
    </div>
  );
}
