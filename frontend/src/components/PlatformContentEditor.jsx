const PLATFORM_LABELS = {
  facebook: 'Facebook',
  instagram: 'Instagram',
  youtube: 'YouTube',
  linkedin: 'LinkedIn',
};

function getDescriptionLabel(platform) {
  if (platform === 'youtube') return 'Description';
  return 'Caption';
}

export default function PlatformContentEditor({
  platforms,
  platformContent,
  setPlatformContent,
  baseTitle,
  baseDescription,
  disabled = false,
}) {
  if (!platforms.length) return null;

  const updatePlatformField = (platform, field, value) => {
    setPlatformContent((current) => ({
      ...current,
      [platform]: {
        ...(current[platform] || {}),
        [field]: value,
      },
    }));
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium text-slate-300">Platform Versions</h3>
        <p className="text-xs text-slate-500 mt-1">
          AI can draft these for you, then you can edit any platform before posting.
        </p>
      </div>

      <div className="space-y-4">
        {platforms.map((platform) => {
          const content = platformContent[platform] || {};
          const title = content.title ?? baseTitle;
          const description = content.description ?? baseDescription;

          return (
            <div key={platform} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 space-y-3">
              <div>
                <p className="text-sm font-semibold text-white">{PLATFORM_LABELS[platform] || platform}</p>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => updatePlatformField(platform, 'title', e.target.value)}
                  className="input-field"
                  disabled={disabled}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">{getDescriptionLabel(platform)}</label>
                <textarea
                  value={description}
                  onChange={(e) => updatePlatformField(platform, 'description', e.target.value)}
                  rows={platform === 'youtube' ? 5 : 4}
                  className="input-field resize-none"
                  disabled={disabled}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
