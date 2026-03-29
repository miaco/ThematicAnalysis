import React, { useState } from 'react';
import { POV, api } from '../api/client';

interface Props {
  sessionId: string;
  povs: POV[];
  onSelect: () => void;
}

export default function POVSelector({ sessionId, povs, onSelect }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleConfirm = async () => {
    if (!selected) { setError('Please select a Point of View.'); return; }
    setLoading(true);
    setError('');
    try {
      await api.selectPOV(sessionId, selected);
      onSelect();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Selection failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Select Your Analytical Perspective</h2>
        <p className="text-sm text-gray-500 mt-1">
          Choose the Point of View that best aligns with your research goals. This will guide the recommendations and final report.
        </p>
      </div>

      <div className="grid gap-4">
        {povs.map((pov, i) => {
          const isSelected = selected === pov.id;
          return (
            <button
              key={pov.id}
              onClick={() => setSelected(pov.id)}
              className={`card p-5 text-left transition-all ${
                isSelected
                  ? 'border-brand-500 ring-2 ring-brand-200 bg-brand-50'
                  : 'hover:border-brand-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-start gap-4">
                {/* Radio indicator */}
                <div className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                  isSelected ? 'border-brand-500 bg-brand-500' : 'border-gray-300'
                }`}>
                  {isSelected && <div className="w-2 h-2 bg-white rounded-full" />}
                </div>

                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
                      POV {i + 1}
                    </span>
                    <h3 className={`font-semibold text-base ${isSelected ? 'text-brand-800' : 'text-gray-900'}`}>
                      {pov.title}
                    </h3>
                  </div>

                  <p className={`text-sm ${isSelected ? 'text-brand-700' : 'text-gray-600'}`}>
                    {pov.description}
                  </p>

                  <div>
                    <p className="text-xs font-semibold text-gray-500 mb-1">Rationale</p>
                    <p className="text-xs text-gray-500 leading-relaxed">{pov.rationale}</p>
                  </div>

                  {pov.supporting_themes.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1">Supporting Themes</p>
                      <div className="flex flex-wrap gap-1.5">
                        {pov.supporting_themes.map(theme => (
                          <span
                            key={theme}
                            className={`text-xs px-2 py-0.5 rounded-full ${
                              isSelected ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {theme}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {error && <div className="bg-red-50 text-red-700 text-sm px-4 py-2 rounded-lg border border-red-200">{error}</div>}

      <button
        className="btn-primary w-full py-3"
        onClick={handleConfirm}
        disabled={loading || !selected}
      >
        {loading ? 'Confirming...' : 'Confirm Selection & Generate Recommendations'}
      </button>
    </div>
  );
}
