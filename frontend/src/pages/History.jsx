import { useCallback, useEffect, useState } from 'react';

import { deleteHistoryItem, getHistory } from '../services/api';

const platformLabels = {
  facebook: 'Facebook',
  instagram: 'Instagram',
  youtube: 'YouTube',
  linkedin: 'LinkedIn',
};

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export default function History() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [removing, setRemoving] = useState(null);

  const fetchHistory = useCallback(async () => {
    try {
      const data = await getHistory();
      setHistory(data.history || []);
      setError('');
    } catch (err) {
      setError('Failed to load post history.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleRemove = async (id) => {
    setRemoving(id);
    try {
      await deleteHistoryItem(id);
      setHistory((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to remove history item.');
    } finally {
      setRemoving(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Post History</h1>
          <p className="text-slate-400 text-sm mt-1">
            Review the outcome of published and scheduled posts
          </p>
        </div>
        <button onClick={fetchHistory} className="btn-secondary text-sm">
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="card text-center py-12">
          <p className="text-slate-400">Loading history...</p>
        </div>
      ) : history.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-slate-300 font-medium">No post history yet</p>
          <p className="text-slate-500 text-sm mt-1">
            Published posts will appear here after they finish.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {history.map((item) => {
            const statusClasses = item.success
              ? 'bg-green-500/10 border-green-500/20 text-green-400'
              : item.partial
              ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
              : 'bg-red-500/10 border-red-500/20 text-red-400';

            return (
              <div key={item.id} className="card border border-slate-800">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-white font-semibold truncate">{item.title}</h3>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${statusClasses}`}>
                        {item.success ? 'Success' : item.partial ? 'Partial' : 'Failed'}
                      </span>
                      <span className="text-xs text-slate-500 uppercase tracking-wide">
                        {item.source === 'scheduled' ? 'Scheduled' : 'Post Now'}
                      </span>
                    </div>

                    {item.description && (
                      <p className="text-slate-400 text-sm mt-2 line-clamp-2">{item.description}</p>
                    )}

                    <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-slate-500">
                      <span>{item.mediaType === 'image' ? '🖼️' : '🎥'} {item.mediaType === 'image' ? 'Photo' : 'Video'}</span>
                      {item.originalName && <span>📁 {item.originalName}</span>}
                      {item.fileSize && <span>📦 {formatFileSize(item.fileSize)}</span>}
                      <span>🕒 {formatDate(item.createdAt)}</span>
                      {item.scheduledAt && <span>📅 Scheduled for {formatDate(item.scheduledAt)}</span>}
                    </div>
                  </div>

                  <button
                    onClick={() => handleRemove(item.id)}
                    disabled={removing === item.id}
                    className="text-slate-500 hover:text-slate-300 text-sm font-medium px-3 py-1.5 rounded-lg hover:bg-slate-700/50 transition-colors disabled:opacity-50"
                  >
                    {removing === item.id ? '...' : 'Remove'}
                  </button>
                </div>

                {item.results?.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-800 space-y-2">
                    {item.results.map((result, index) => (
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
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
