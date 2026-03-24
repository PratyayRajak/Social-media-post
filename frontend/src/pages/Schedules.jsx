import { useCallback, useEffect, useState } from 'react';

import { cancelSchedule, getSchedules } from '../services/api';

const platformLabels = {
  facebook: 'Facebook',
  instagram: 'Instagram',
  youtube: 'YouTube',
  linkedin: 'LinkedIn',
};

const platformIcons = {
  facebook: '📘',
  instagram: '📸',
  youtube: '📺',
  linkedin: '💼',
};

const statusConfig = {
  queued: { label: 'Queued', color: 'text-slate-300', bg: 'bg-slate-500/10 border-slate-500/20', icon: '🕒' },
  uploading: { label: 'Uploading...', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20', icon: '📤' },
  ready: { label: 'Ready', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20', icon: '✅' },
  publishing: { label: 'Publishing...', color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20', icon: '⚡' },
  completed: { label: 'Published', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20', icon: '🎉' },
  failed: { label: 'Failed', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20', icon: '❌' },
};

const phaseLabels = {
  queued: { label: 'Queued', color: 'text-slate-400' },
  uploading: { label: 'Uploading', color: 'text-blue-400' },
  ready: { label: 'Ready', color: 'text-green-400' },
  publishing: { label: 'Publishing', color: 'text-yellow-400' },
  published: { label: 'Published', color: 'text-green-400' },
  failed: { label: 'Failed', color: 'text-red-400' },
};

export default function Schedules() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cancelling, setCancelling] = useState(null);
  const [, setTick] = useState(0);

  const fetchSchedules = useCallback(async () => {
    try {
      const data = await getSchedules();
      setSchedules(data.schedules || []);
      setError('');
    } catch (err) {
      setError('Failed to load scheduled posts.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSchedules();
    const dataInterval = setInterval(fetchSchedules, 3000);
    const tickInterval = setInterval(() => setTick((value) => value + 1), 1000);
    return () => {
      clearInterval(dataInterval);
      clearInterval(tickInterval);
    };
  }, [fetchSchedules]);

  const handleCancel = async (id) => {
    if (!confirm('Are you sure you want to cancel this scheduled post?')) return;
    setCancelling(id);
    try {
      await cancelSchedule(id);
      setSchedules((prev) => prev.filter((schedule) => schedule.id !== id));
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to cancel.');
    } finally {
      setCancelling(null);
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  const getCountdown = (scheduledAt) => {
    const diff = new Date(scheduledAt) - new Date();
    if (diff <= 0) return 'Publishing now...';

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m ${seconds}s`;
    return `${minutes}m ${seconds}s`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Scheduled Posts</h1>
          <p className="text-slate-400 text-sm mt-1">
            Track upload progress and manage scheduled photos or videos
          </p>
        </div>
        <button
          onClick={() => {
            setLoading(true);
            fetchSchedules();
          }}
          className="btn-secondary text-sm flex items-center gap-1.5"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {loading && schedules.length === 0 ? (
        <div className="card text-center py-12">
          <div className="animate-spin text-3xl mb-3">⏳</div>
          <p className="text-slate-400">Loading scheduled posts...</p>
        </div>
      ) : schedules.length === 0 ? (
        <div className="card text-center py-12">
          <div className="text-4xl mb-3">🗓️</div>
          <p className="text-slate-300 font-medium">No scheduled posts</p>
          <p className="text-slate-500 text-sm mt-1">
            Schedule a post from the Home page and it will appear here
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {schedules.map((schedule) => {
            const status = statusConfig[schedule.status] || statusConfig.uploading;
            const mediaLabel = schedule.mediaType === 'image' ? 'Photo' : 'Video';

            return (
              <div
                key={schedule.id}
                className={`card border ${status.bg} transition-all duration-300`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-lg">{status.icon}</span>
                      <h3 className="text-white font-semibold truncate">{schedule.title}</h3>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${status.bg} ${status.color} border`}>
                        {status.label}
                      </span>
                    </div>

                    {schedule.description && (
                      <p className="text-slate-400 text-sm mt-1 line-clamp-2">{schedule.description}</p>
                    )}

                    <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-slate-500">
                      <span>🗓️ {formatDate(schedule.scheduledAt)}</span>
                      <span>{schedule.mediaType === 'image' ? '🖼️' : '🎥'} {mediaLabel}</span>
                      {schedule.originalName && <span>📁 {schedule.originalName}</span>}
                      {schedule.fileSize && <span>📦 {formatFileSize(schedule.fileSize)}</span>}
                    </div>
                  </div>

                  <div className="flex-shrink-0">
                    {['queued', 'uploading', 'ready'].includes(schedule.status) && (
                      <button
                        onClick={() => handleCancel(schedule.id)}
                        disabled={cancelling === schedule.id}
                        className="text-red-400 hover:text-red-300 text-sm font-medium px-3 py-1.5 rounded-lg hover:bg-red-500/10 transition-colors disabled:opacity-50"
                      >
                        {cancelling === schedule.id ? '...' : 'Cancel'}
                      </button>
                    )}
                    {['completed', 'failed'].includes(schedule.status) && (
                      <button
                        onClick={() => handleCancel(schedule.id)}
                        disabled={cancelling === schedule.id}
                        className="text-slate-500 hover:text-slate-300 text-sm font-medium px-3 py-1.5 rounded-lg hover:bg-slate-700/50 transition-colors disabled:opacity-50"
                      >
                        {cancelling === schedule.id ? '...' : 'Remove'}
                      </button>
                    )}
                  </div>
                </div>

                {['queued', 'ready'].includes(schedule.status) && (
                  <div className="mt-4 bg-slate-800/50 rounded-xl p-4 text-center">
                    <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Publishes in</p>
                    <p className="text-2xl font-bold text-white font-mono">
                      {getCountdown(schedule.scheduledAt)}
                    </p>
                  </div>
                )}

                {schedule.status === 'uploading' && (
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-slate-400">Pre-uploading to platforms...</span>
                      <span className="text-blue-400 font-medium">{schedule.overallProgress || 0}%</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-blue-500 h-full rounded-full transition-all duration-500 ease-out"
                        style={{ width: `${schedule.overallProgress || 0}%` }}
                      />
                    </div>
                  </div>
                )}

                {schedule.platformStatus && (
                  <div className="mt-4 space-y-2">
                    {schedule.platforms.map((platform) => {
                      const platformState = schedule.platformStatus[platform];
                      if (!platformState) return null;

                      const phase = phaseLabels[platformState.phase] || phaseLabels.queued;

                      return (
                        <div key={platform} className="bg-slate-800/30 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span>{platformIcons[platform]}</span>
                              <span className="text-sm text-white font-medium">
                                {platformLabels[platform] || platform}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              {platformState.phase === 'uploading' && (
                                <span className="text-xs text-blue-400 font-mono">{platformState.progress}%</span>
                              )}
                              <span className={`text-xs font-medium ${phase.color}`}>
                                {phase.label}
                              </span>
                            </div>
                          </div>

                          {platformState.phase === 'uploading' && (
                            <div className="w-full bg-slate-700 rounded-full h-1.5 overflow-hidden mt-1">
                              <div
                                className="bg-blue-500 h-full rounded-full transition-all duration-300"
                                style={{ width: `${platformState.progress}%` }}
                              />
                            </div>
                          )}

                          {['ready', 'published'].includes(platformState.phase) && (
                            <div className="w-full bg-green-500/20 rounded-full h-1.5 mt-1">
                              <div className="bg-green-500 h-full rounded-full w-full" />
                            </div>
                          )}

                          {platformState.error && (
                            <p className="text-red-400 text-xs mt-1 truncate">{platformState.error}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {schedule.results && (
                  <div className="mt-4 pt-3 border-t border-slate-700/50">
                    <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">Publish Results</p>
                    <div className="space-y-1">
                      {schedule.results.map((result, index) => (
                        <div key={index} className="flex items-center gap-2 text-sm">
                          <span>{result.success ? '✅' : '❌'}</span>
                          <span className={result.success ? 'text-green-400' : 'text-red-400'}>
                            {platformLabels[result.platform] || result.platform}:
                          </span>
                          <span className="text-slate-400 text-xs truncate">
                            {result.success ? result.message : result.error}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
