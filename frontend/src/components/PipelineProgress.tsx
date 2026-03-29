import React, { useEffect, useRef, useState } from 'react';
import { PipelineState, ProgressEntry, createProgressStream } from '../api/client';

interface Props {
  sessionId: string;
  state: PipelineState;
  progressLog: ProgressEntry[];
  onStateChange: () => void;
}

const PIPELINE_STEPS: { key: PipelineState | string; label: string; description: string }[] = [
  { key: 'processing_transcripts', label: 'Transcript Analysis', description: 'Extracting quotes and participants' },
  { key: 'awaiting_code_review', label: 'Code Review', description: 'Human review of open codes' },
  { key: 'processing_themes', label: 'Theme Generation', description: 'Identifying themes and literature' },
  { key: 'awaiting_pov_selection', label: 'POV Selection', description: 'Human selects analytical perspective' },
  { key: 'processing_recommendations', label: 'Recommendations', description: 'Generating actionable insights' },
  { key: 'awaiting_recommendation_selection', label: 'Rec. Selection', description: 'Human finalizes recommendations' },
  { key: 'writing_report', label: 'Report Writing', description: 'Composing the full report' },
  { key: 'complete', label: 'Complete', description: 'Analysis finished' },
];

function getStepStatus(stepKey: string, currentState: PipelineState): 'complete' | 'running' | 'pending' {
  const order = ['processing_transcripts', 'awaiting_code_review', 'processing_themes',
    'awaiting_pov_selection', 'processing_recommendations', 'awaiting_recommendation_selection',
    'writing_report', 'complete'];
  const stepIdx = order.indexOf(stepKey);
  const currentIdx = order.indexOf(currentState);
  if (currentIdx > stepIdx) return 'complete';
  if (currentIdx === stepIdx) return 'running';
  return 'pending';
}

export default function PipelineProgress({ sessionId, state, progressLog, onStateChange }: Props) {
  const [liveLog, setLiveLog] = useState<ProgressEntry[]>(progressLog);
  const [streaming, setStreaming] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);
  const stopStreamRef = useRef<(() => void) | null>(null);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [liveLog]);

  // Start streaming when in a processing state
  const isProcessing = ['processing_transcripts', 'processing_themes', 'processing_recommendations', 'writing_report'].includes(state);

  useEffect(() => {
    if (!isProcessing) {
      setStreaming(false);
      if (stopStreamRef.current) { stopStreamRef.current(); stopStreamRef.current = null; }
      return;
    }

    setStreaming(true);
    const stop = createProgressStream(
      sessionId,
      (event) => {
        setLiveLog(prev => {
          const exists = prev.some(e => e.timestamp === event.timestamp && e.message === event.message);
          return exists ? prev : [...prev, event];
        });
      },
      () => {
        setStreaming(false);
        onStateChange();
      },
      () => {
        setStreaming(false);
        onStateChange();
      }
    );
    stopStreamRef.current = stop;
    return () => { stop(); stopStreamRef.current = null; };
  }, [sessionId, isProcessing]);

  return (
    <div className="space-y-6">
      {/* Pipeline Steps */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Analysis Pipeline</h2>
        <div className="space-y-3">
          {PIPELINE_STEPS.map((step) => {
            const status = getStepStatus(step.key, state);
            return (
              <div key={step.key} className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {status === 'complete' && (
                    <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center">
                      <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                  {status === 'running' && (
                    <div className="w-6 h-6 rounded-full bg-brand-500 flex items-center justify-center">
                      {streaming ? (
                        <svg className="animate-spin w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                      ) : (
                        <div className="w-2 h-2 bg-white rounded-full" />
                      )}
                    </div>
                  )}
                  {status === 'pending' && (
                    <div className="w-6 h-6 rounded-full border-2 border-gray-300" />
                  )}
                </div>
                <div>
                  <p className={`text-sm font-medium ${status === 'complete' ? 'text-green-700' : status === 'running' ? 'text-brand-700' : 'text-gray-400'}`}>
                    {step.label}
                  </p>
                  <p className="text-xs text-gray-400">{step.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live Log */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-sm font-semibold text-gray-700">Progress Log</h3>
          {streaming && (
            <span className="flex items-center gap-1 text-xs text-brand-600">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500" />
              </span>
              Live
            </span>
          )}
        </div>
        <div className="h-48 overflow-y-auto space-y-1 pr-1">
          {liveLog.length === 0 ? (
            <p className="text-xs text-gray-400 italic">No log entries yet...</p>
          ) : (
            liveLog.map((entry, i) => (
              <div key={i} className="flex gap-2 text-xs">
                <span className="text-gray-400 flex-shrink-0 w-20">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
                <span className={`font-medium flex-shrink-0 w-28 truncate ${
                  entry.stage === 'error' ? 'text-red-500' : 'text-brand-600'
                }`}>
                  [{entry.stage}]
                </span>
                <span className="text-gray-700">{entry.message}</span>
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
