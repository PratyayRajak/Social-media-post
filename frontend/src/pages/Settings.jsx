import { useState, useEffect } from 'react';
import { getSettings, saveSettings, exchangeYouTubeAuth } from '../services/api';

export default function Settings() {
  // Facebook
  const [fbPageId, setFbPageId] = useState('');
  const [fbAccessToken, setFbAccessToken] = useState('');

  // Instagram
  const [igUserId, setIgUserId] = useState('');
  const [igAccessToken, setIgAccessToken] = useState('');

  // YouTube
  const [ytClientId, setYtClientId] = useState('');
  const [ytClientSecret, setYtClientSecret] = useState('');
  const [ytAuthUrl, setYtAuthUrl] = useState('');
  const [ytAuthCode, setYtAuthCode] = useState('');
  const [ytConfigured, setYtConfigured] = useState(false);



  // LinkedIn
  const [liOrgId, setLiOrgId] = useState('');
  const [liPersonId, setLiPersonId] = useState('');
  const [liAccessToken, setLiAccessToken] = useState('');

  // AI
  const [anthropicApiKey, setAnthropicApiKey] = useState('');
  const [anthropicModel, setAnthropicModel] = useState('claude-3-5-haiku-latest');

  // UI state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [configured, setConfigured] = useState({ facebook: false, instagram: false, youtube: false, linkedin: false, ai: false });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await getSettings();
      setConfigured({
        facebook: data.facebook.configured,
        instagram: data.instagram.configured,
        youtube: data.youtube.configured,
        linkedin: data.linkedin?.configured || false,
        ai: data.ai?.configured || false,
      });
      setYtAuthUrl(data.youtube.authUrl || '');
      setYtConfigured(data.youtube.configured);
      if (data.ai?.model) setAnthropicModel(data.ai.model);
      // Don't pre-fill tokens (they're masked)
      if (data.facebook.pageId) setFbPageId(data.facebook.pageId);
      if (data.instagram.userId) setIgUserId(data.instagram.userId);
      if (data.linkedin?.orgId) setLiOrgId(data.linkedin.orgId);
      if (data.linkedin?.personId) setLiPersonId(data.linkedin.personId);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to load settings. Is the backend running?' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      const payload = {};
      if (fbPageId) payload.fbPageId = fbPageId;
      if (fbAccessToken) payload.fbAccessToken = fbAccessToken;
      if (igUserId) payload.igUserId = igUserId;
      if (igAccessToken) payload.igAccessToken = igAccessToken;
      if (ytClientId) payload.ytClientId = ytClientId;
      if (ytClientSecret) payload.ytClientSecret = ytClientSecret;
      if (liOrgId) payload.liOrgId = liOrgId;
      if (liPersonId) payload.liPersonId = liPersonId;
      if (liAccessToken) payload.liAccessToken = liAccessToken;
      if (anthropicApiKey) payload.anthropicApiKey = anthropicApiKey;
      if (anthropicModel) payload.anthropicModel = anthropicModel;

      const data = await saveSettings(payload);

      if (data.youtube?.authUrl) {
        setYtAuthUrl(data.youtube.authUrl);
      }

      setMessage({ type: 'success', text: 'Settings saved successfully!' });

      // Clear sensitive fields after saving
      setFbAccessToken('');
      setIgAccessToken('');
      setYtClientId('');
      setYtClientSecret('');
      setLiAccessToken('');
      setAnthropicApiKey('');

      // Refresh status
      await loadSettings();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || err.message || 'Failed to save settings.',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleYouTubeAuth = async () => {
    if (!ytAuthCode.trim()) return;

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      await exchangeYouTubeAuth(ytAuthCode.trim());
      setMessage({ type: 'success', text: 'YouTube authorized successfully!' });
      setYtAuthCode('');
      setYtConfigured(true);
      await loadSettings();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error || 'Failed to authorize YouTube.',
      });
    } finally {
      setSaving(false);
    }
  };

  const StatusBadge = ({ configured: isConfigured }) => (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${isConfigured
        ? 'bg-green-500/10 text-green-400 border border-green-500/20'
        : 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
        }`}
    >
      {isConfigured ? '✓ Connected' : '○ Not Set'}
    </span>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-slate-600 border-t-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">⚙ Settings</h1>
        <p className="text-slate-400 text-sm mt-1">
          Enter your platform credentials once — they're saved locally in your .env file
        </p>
      </div>

      {/* Message */}
      {message.text && (
        <div
          className={`p-4 rounded-xl border ${message.type === 'success'
            ? 'bg-green-500/10 border-green-500/20 text-green-400'
            : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}
        >
          {message.text}
        </div>
      )}

      {/* Facebook */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-blue-500">
              <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current inline">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
              </svg>
            </span>
            Facebook
          </h2>
          <StatusBadge configured={configured.facebook} />
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Page ID</label>
            <input
              type="text"
              value={fbPageId}
              onChange={(e) => setFbPageId(e.target.value)}
              placeholder="e.g. 123456789012345"
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Access Token</label>
            <input
              type="password"
              value={fbAccessToken}
              onChange={(e) => setFbAccessToken(e.target.value)}
              placeholder={configured.facebook ? '••••••••  (already saved — enter new to update)' : 'Paste your Page Access Token'}
              className="input-field"
            />
          </div>
        </div>
      </div>

      {/* Instagram */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-pink-500">
              <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current inline">
                <path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678a6.162 6.162 0 100 12.324 6.162 6.162 0 100-12.324zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405a1.441 1.441 0 11-2.882 0 1.441 1.441 0 012.882 0z" />
              </svg>
            </span>
            Instagram
          </h2>
          <StatusBadge configured={configured.instagram} />
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-slate-400 mb-1">User ID</label>
            <input
              type="text"
              value={igUserId}
              onChange={(e) => setIgUserId(e.target.value)}
              placeholder="e.g. 17841400123456789"
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Access Token</label>
            <input
              type="password"
              value={igAccessToken}
              onChange={(e) => setIgAccessToken(e.target.value)}
              placeholder={configured.instagram ? '••••••••  (already saved — enter new to update)' : 'Paste your Instagram Access Token (same as FB)'}
              className="input-field"
            />
          </div>
        </div>
      </div>

      {/* YouTube */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-red-500">
              <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current inline">
                <path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
              </svg>
            </span>
            YouTube
          </h2>
          <StatusBadge configured={configured.youtube} />
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Client ID</label>
            <input
              type="password"
              value={ytClientId}
              onChange={(e) => setYtClientId(e.target.value)}
              placeholder={configured.youtube ? '••••••••  (already saved)' : 'Paste your OAuth Client ID'}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Client Secret</label>
            <input
              type="password"
              value={ytClientSecret}
              onChange={(e) => setYtClientSecret(e.target.value)}
              placeholder={configured.youtube ? '••••••••  (already saved)' : 'Paste your OAuth Client Secret'}
              className="input-field"
            />
          </div>

          {/* YouTube OAuth Flow */}
          {ytAuthUrl && (
            <div className="mt-4 p-4 bg-slate-800 rounded-xl border border-slate-700">
              <p className="text-sm text-slate-300 mb-3">
                <strong>Step 2:</strong> After saving Client ID & Secret above, authorize YouTube:
              </p>
              <a
                href={ytAuthUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary inline-flex items-center gap-2 text-sm"
              >
                🔗 Authorize YouTube Access
              </a>
              <div className="mt-3">
                <label className="block text-sm text-slate-400 mb-1">
                  Paste the authorization code here:
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={ytAuthCode}
                    onChange={(e) => setYtAuthCode(e.target.value)}
                    placeholder="Paste code from redirect..."
                    className="input-field flex-1"
                  />
                  <button
                    onClick={handleYouTubeAuth}
                    disabled={!ytAuthCode.trim() || saving}
                    className="btn-primary text-sm px-4"
                  >
                    Verify
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>



      {/* LinkedIn */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-blue-500">
              <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current inline">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
              </svg>
            </span>
            LinkedIn
          </h2>
          <StatusBadge configured={configured.linkedin} />
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Organization ID (Company Page ID) — <span className="text-slate-500">for company pages</span></label>
            <input
              type="text"
              value={liOrgId}
              onChange={(e) => setLiOrgId(e.target.value)}
              placeholder="e.g. 12345678"
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Person ID — <span className="text-slate-500">for personal profiles (alternative to Org ID)</span></label>
            <input
              type="text"
              value={liPersonId}
              onChange={(e) => setLiPersonId(e.target.value)}
              placeholder="e.g. abc123XYZ"
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Access Token</label>
            <input
              type="password"
              value={liAccessToken}
              onChange={(e) => setLiAccessToken(e.target.value)}
              placeholder={configured.linkedin ? '••••••••  (already saved — enter new to update)' : 'Paste your OAuth Access Token'}
              className="input-field"
            />
          </div>
          <div className="mt-2 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
            <p className="text-xs text-slate-400">
              <strong className="text-slate-300">How to get LinkedIn credentials:</strong> Go to{' '}
              <a href="https://www.linkedin.com/developers/apps" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 underline">
                linkedin.com/developers
              </a>
              {' '}→ Create an app → For <strong>Company Page</strong> posting: request <code className="bg-slate-700 px-1 rounded text-xs">w_organization_social</code> permission and use your Organization ID. For <strong>personal profile</strong> posting: use <code className="bg-slate-700 px-1 rounded text-xs">w_member_social</code> permission and your Person ID.
            </p>
          </div>
        </div>
      </div>

      {/* AI Assistant */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-emerald-400">AI Assistant</span>
          </h2>
          <StatusBadge configured={configured.ai} />
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Anthropic API Key</label>
            <input
              type="password"
              value={anthropicApiKey}
              onChange={(e) => setAnthropicApiKey(e.target.value)}
              placeholder={configured.ai ? 'â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢  (already saved â€” enter new to update)' : 'Paste your Anthropic API key'}
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Model</label>
            <input
              type="text"
              value={anthropicModel}
              onChange={(e) => setAnthropicModel(e.target.value)}
              placeholder="claude-3-5-haiku-latest"
              className="input-field"
            />
          </div>
          <div className="mt-2 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
            <p className="text-xs text-slate-400">
              This powers the <strong className="text-slate-300">Adapt with AI</strong> button on the editor screen.
              The editor writes one base version and AI drafts platform-specific copy for review.
            </p>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="btn-primary w-full flex items-center justify-center gap-2 text-lg py-4"
      >
        {saving ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
            Saving...
          </>
        ) : (
          <>
            <span>💾</span>
            Save Credentials
          </>
        )}
      </button>

      {/* Help */}
      <div className="card text-sm text-slate-500 space-y-2">
        <p>
          <strong className="text-slate-400">Where are my tokens stored?</strong> — Locally in{' '}
          <code className="bg-slate-800 px-1.5 py-0.5 rounded text-xs">backend/.env</code>. Never sent anywhere
          except to the official platform APIs.
        </p>
        <p>
          <strong className="text-slate-400">Need help getting tokens?</strong> — Check the{' '}
          <code className="bg-slate-800 px-1.5 py-0.5 rounded text-xs">README.md</code> for step-by-step
          instructions.
        </p>
      </div>
    </div>
  );
}
