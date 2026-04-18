import React, { useState, useEffect, useCallback } from 'react';
import { api, Session, PipelineState } from './api/client';
import ResearchBriefForm from './components/ResearchBriefForm';
import TranscriptUpload from './components/TranscriptUpload';
import PipelineProgress from './components/PipelineProgress';
import CodeReviewEditor from './components/CodeReviewEditor';
import POVSelector from './components/POVSelector';
import RecommendationSelector from './components/RecommendationSelector';
import ReportViewer from './components/ReportViewer';

const STATE_LABELS: Record<PipelineState, string> = {
  idle: 'Setup',
  processing_transcripts: 'Analyzing Transcripts',
  awaiting_code_review: 'Code Review Needed',
  processing_themes: 'Generating Themes',
  awaiting_pov_selection: 'POV Selection Needed',
  processing_recommendations: 'Generating Recommendations',
  awaiting_recommendation_selection: 'Select Recommendations',
  writing_report: 'Writing Report',
  complete: 'Complete',
  error: 'Error',
};

const STATE_COLORS: Record<PipelineState, string> = {
  idle: 'bg-gray-100 text-gray-600',
  processing_transcripts: 'bg-blue-100 text-blue-700',
  awaiting_code_review: 'bg-amber-100 text-amber-700',
  processing_themes: 'bg-blue-100 text-blue-700',
  awaiting_pov_selection: 'bg-amber-100 text-amber-700',
  processing_recommendations: 'bg-blue-100 text-blue-700',
  awaiting_recommendation_selection: 'bg-amber-100 text-amber-700',
  writing_report: 'bg-blue-100 text-blue-700',
  complete: 'bg-green-100 text-green-700',
  error: 'bg-red-100 text-red-700',
};

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showNewSession, setShowNewSession] = useState(false);
  const [newSessionStep, setNewSessionStep] = useState<'brief' | 'upload'>('brief');
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);
  const [loadingSession, setLoadingSession] = useState(false);

  const refreshSessions = useCallback(async () => {
    try {
      const list = await api.getSessions();
      setSessions(list);
    } catch { /* ignore */ }
  }, []);

  const refreshActiveSession = useCallback(async () => {
    if (!activeSessionId) return;
    try {
      const s = await api.getSession(activeSessionId);
      setActiveSession(s);
    } catch { /* ignore */ }
  }, [activeSessionId]);

  useEffect(() => {
    refreshSessions();
    const interval = setInterval(refreshSessions, 10000);
    return () => clearInterval(interval);
  }, [refreshSessions]);

  useEffect(() => {
    if (activeSessionId) {
      refreshActiveSession();
    }
  }, [activeSessionId, refreshActiveSession]);

  // Poll active session for state changes during processing
  useEffect(() => {
    const isProcessing = activeSession && [
      'processing_transcripts', 'processing_themes',
      'processing_recommendations', 'writing_report'
    ].includes(activeSession.state);

    if (!isProcessing) return;

    const interval = setInterval(refreshActiveSession, 3000);
    return () => clearInterval(interval);
  }, [activeSession?.state, refreshActiveSession]);

  const handleBriefComplete = async (data: { researchQuestion: string; participants: string; method: string }) => {
    try {
      const session = await api.createSession(data.researchQuestion, data.participants, data.method);
      setPendingSessionId(session.id);
      setNewSessionStep('upload');
      refreshSessions();
    } catch (e) {
      // Error handling is in the form component
    }
  };

  const handlePipelineStarted = () => {
    if (pendingSessionId) {
      setShowNewSession(false);
      setNewSessionStep('brief');
      setActiveSessionId(pendingSessionId);
      setPendingSessionId(null);
      refreshSessions();
      setTimeout(() => refreshActiveSession(), 1000);
    }
  };

  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    setShowNewSession(false);
    setLoadingSession(true);
    try {
      const s = await api.getSession(id);
      setActiveSession(s);
    } finally {
      setLoadingSession(false);
    }
  };

  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this session?')) return;
    await api.deleteSession(id);
    if (activeSessionId === id) {
      setActiveSessionId(null);
      setActiveSession(null);
    }
    refreshSessions();
  };

  const handleStateChange = useCallback(() => {
    refreshActiveSession();
    refreshSessions();
  }, [refreshActiveSession, refreshSessions]);

  // Render the main content based on session state
  const renderContent = () => {
    if (showNewSession) {
      if (newSessionStep === 'brief') {
        return <ResearchBriefForm onNext={handleBriefComplete} />;
      }
      if (newSessionStep === 'upload' && pendingSessionId) {
        return (
          <TranscriptUpload
            sessionId={pendingSessionId}
            onPipelineStarted={handlePipelineStarted}
          />
        );
      }
    }

    if (!activeSession) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8 space-y-4">
          <div className="w-16 h-16 bg-brand-100 rounded-2xl flex items-center justify-center">
            <svg className="w-8 h-8 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Thematic Analysis Agent</h2>
            <p className="text-gray-500 mt-1">Create a new analysis session or select one from the sidebar.</p>
          </div>
          <button className="btn-primary" onClick={() => { setShowNewSession(true); setNewSessionStep('brief'); }}>
            New Analysis
          </button>
        </div>
      );
    }

    if (loadingSession) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
        </div>
      );
    }

    const s = activeSession;

    return (
      <div className="p-6 space-y-6 max-w-4xl mx-auto">
        {/* Session header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-bold text-gray-900 line-clamp-2">
              {s.research_brief ? s.research_brief.slice(0, 100) + (s.research_brief.length > 100 ? '...' : '') : 'Untitled Analysis'}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATE_COLORS[s.state]}`}>
                {STATE_LABELS[s.state]}
              </span>
              <span className="text-xs text-gray-400">
                {s.transcripts ? Object.keys(s.transcripts).length : 0} transcript(s)
              </span>
              {s.participants?.length > 0 && (
                <span className="text-xs text-gray-400">{s.participants.length} participant(s)</span>
              )}
            </div>
          </div>
        </div>

        {/* Error state */}
        {s.state === 'error' && s.error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700 text-sm font-medium">Pipeline Error</p>
            <p className="text-red-600 text-sm mt-1">{s.error}</p>
            <button
              className="mt-2 btn-secondary text-sm py-1.5"
              onClick={handleStateChange}
            >
              Refresh
            </button>
          </div>
        )}

        {/* Progress (shown during processing states and waiting states) */}
        {['processing_transcripts', 'processing_themes', 'processing_recommendations',
          'writing_report', 'awaiting_code_review', 'awaiting_pov_selection',
          'awaiting_recommendation_selection', 'complete'].includes(s.state) && (
          <PipelineProgress
            sessionId={s.id}
            state={s.state}
            progressLog={s.progress_log || []}
            onStateChange={handleStateChange}
          />
        )}

        {/* Human gates */}
        {s.state === 'awaiting_code_review' && s.codes?.length > 0 && (
          <CodeReviewEditor
            sessionId={s.id}
            codes={s.codes}
            quotes={s.quotes || []}
            onSubmit={handleStateChange}
          />
        )}

        {s.state === 'awaiting_pov_selection' && s.povs?.length > 0 && (
          <POVSelector
            sessionId={s.id}
            povs={s.povs}
            themes={s.themes}
            onSelect={handleStateChange}
          />
        )}

        {s.state === 'awaiting_recommendation_selection' && s.recommendations?.length > 0 && (
          <RecommendationSelector
            sessionId={s.id}
            recommendations={s.recommendations}
            onSelect={handleStateChange}
          />
        )}

        {/* Report */}
        {s.state === 'complete' && s.report && (
          <ReportViewer sessionId={s.id} report={s.report} />
        )}

        {/* Validation warnings */}
        {s.validation_results && Object.keys(s.validation_results).length > 0 && (
          <ValidationWarnings results={s.validation_results} />
        )}
      </div>
    );
  };

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <div className={`flex-shrink-0 ${sidebarOpen ? 'w-72' : 'w-0'} transition-all duration-200 overflow-hidden`}>
        <div className="w-72 h-full flex flex-col bg-white border-r border-gray-200">
          {/* Logo */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-brand-600 rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <span className="font-semibold text-gray-900 text-sm">Thematic Analysis</span>
            </div>
          </div>

          {/* New session button */}
          <div className="p-3">
            <button
              className="btn-primary w-full py-2 text-sm flex items-center justify-center gap-1.5"
              onClick={() => { setShowNewSession(true); setNewSessionStep('brief'); setActiveSessionId(null); }}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Analysis
            </button>
          </div>

          {/* Sessions list */}
          <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
            {sessions.length === 0 ? (
              <p className="text-xs text-gray-400 text-center py-4">No sessions yet</p>
            ) : (
              sessions.map(s => (
                <button
                  key={s.id}
                  onClick={() => handleSelectSession(s.id)}
                  className={`w-full text-left rounded-lg px-3 py-2.5 transition-colors group ${
                    activeSessionId === s.id ? 'bg-brand-50 border border-brand-200' : 'hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-start justify-between gap-1">
                    <p className="text-sm font-medium text-gray-800 line-clamp-1 flex-1">
                      {s.research_brief ? s.research_brief.slice(0, 50) : 'Untitled'}
                    </p>
                    <button
                      onClick={e => handleDeleteSession(s.id, e)}
                      className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 flex-shrink-0 mt-0.5"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${STATE_COLORS[s.state]}`}>
                      {STATE_LABELS[s.state]}
                    </span>
                    <span className="text-xs text-gray-400">
                      {new Date(s.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Toggle sidebar button */}
      <button
        className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-white border border-gray-200 rounded-r-lg p-1 shadow-sm hover:bg-gray-50 transition-transform"
        style={{ left: sidebarOpen ? '272px' : '0px' }}
        onClick={() => setSidebarOpen(v => !v)}
      >
        <svg className={`w-4 h-4 text-gray-500 transition-transform ${sidebarOpen ? '' : 'rotate-180'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        {renderContent()}
      </div>
    </div>
  );
}

// Validation warnings component
function ValidationWarnings({ results }: { results: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const warningKeys = Object.keys(results).filter(k =>
    ['preprocessing_warnings', 'accuracy_issues', 'inter_rater_candidates',
      'bias_flags', 'screener_coverage_warnings', 'thin_description_themes',
      'grounding_issues', 'research_alignment_warnings', 'pre_write_checks',
      'consistency_issues'].includes(k)
  );

  if (warningKeys.length === 0) return null;

  return (
    <div className="card border-yellow-200 bg-yellow-50">
      <button
        className="w-full px-4 py-3 flex items-center justify-between text-left"
        onClick={() => setExpanded(v => !v)}
      >
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-sm font-semibold text-yellow-800">
            {warningKeys.length} validation warning{warningKeys.length > 1 ? 's' : ''}
          </span>
        </div>
        <svg className={`w-4 h-4 text-yellow-600 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {warningKeys.map(key => {
            const value = results[key];
            return (
              <div key={key}>
                <p className="text-xs font-semibold text-yellow-700 uppercase tracking-wide mb-1">
                  {key.replace(/_/g, ' ')}
                </p>
                {Array.isArray(value) ? (
                  <ul className="space-y-0.5">
                    {(value as string[]).slice(0, 5).map((item, i) => (
                      <li key={i} className="text-xs text-yellow-700">• {typeof item === 'string' ? item : JSON.stringify(item)}</li>
                    ))}
                    {value.length > 5 && <li className="text-xs text-yellow-500">...and {value.length - 5} more</li>}
                  </ul>
                ) : (
                  <p className="text-xs text-yellow-700">{String(value)}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
