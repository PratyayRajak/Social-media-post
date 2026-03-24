export default function ResultCard({ results }) {
  if (!results || results.length === 0) return null;

  const platformLabels = {
    facebook: 'Facebook',
    instagram: 'Instagram',
    youtube: 'YouTube',
    x: 'X',
    linkedin: 'LinkedIn',
    threads: 'Threads',
  };

  return (
    <div className="card mt-6">
      <h3 className="text-lg font-semibold text-white mb-4">Results</h3>
      <div className="space-y-3">
        {results.map((result, index) => (
          <div
            key={index}
            className={`flex items-start gap-3 p-4 rounded-xl ${
              result.success
                ? 'bg-green-500/10 border border-green-500/20'
                : 'bg-red-500/10 border border-red-500/20'
            }`}
          >
            <span className="text-xl flex-shrink-0 mt-0.5">
              {result.success ? '✅' : '❌'}
            </span>
            <div className="flex-1 min-w-0">
              <p className={`font-medium ${result.success ? 'text-green-400' : 'text-red-400'}`}>
                {platformLabels[result.platform] || result.platform}
              </p>
              <p className="text-sm text-slate-400 mt-0.5 break-words">
                {result.success
                  ? result.message || 'Posted successfully!'
                  : result.error || 'Failed to post.'}
              </p>
              {result.videoUrl && (
                <a
                  href={result.videoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-400 hover:text-blue-300 underline mt-1 inline-block"
                >
                  View on YouTube →
                </a>
              )}
              {result.tweetUrl && (
                <a
                  href={result.tweetUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-400 hover:text-blue-300 underline mt-1 inline-block"
                >
                  View on X →
                </a>
              )}
              {result.threadUrl && (
                <a
                  href={result.threadUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-400 hover:text-blue-300 underline mt-1 inline-block"
                >
                  View on Threads →
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
