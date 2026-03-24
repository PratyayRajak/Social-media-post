import { useEffect, useMemo, useRef, useState } from 'react';

import Loader from '../components/Loader';
import PlatformContentEditor from '../components/PlatformContentEditor';
import PlatformPicker from '../components/PlatformPicker';
import ResultCard from '../components/ResultCard';
import UploadForm from '../components/UploadForm';
import { generatePlatformCaptions, postVideo, scheduleVideo } from '../services/api';

const DEFAULT_PLATFORMS = ['facebook', 'instagram', 'youtube', 'linkedin'];
const SUPPORTED_PLATFORMS = {
  image: ['facebook', 'instagram', 'linkedin'],
  video: ['facebook', 'instagram', 'youtube', 'linkedin'],
};

function getMediaType(file) {
  if (!file?.type) return null;
  if (file.type.startsWith('image/')) return 'image';
  if (file.type.startsWith('video/')) return 'video';
  return null;
}

function trimPlatformContent(platforms, existing = {}) {
  return platforms.reduce((acc, platform) => {
    if (existing[platform]) {
      acc[platform] = existing[platform];
    }
    return acc;
  }, {});
}

function buildEffectivePlatformContent(platforms, title, description, overrides = {}) {
  return platforms.reduce((acc, platform) => {
    const current = overrides[platform] || {};
    acc[platform] = {
      title: current.title ?? title,
      description: current.description ?? description,
    };
    return acc;
  }, {});
}

export default function Home() {
  const [mediaFile, setMediaFile] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [platforms, setPlatforms] = useState(DEFAULT_PLATFORMS);
  const [platformContent, setPlatformContent] = useState({});
  const [loading, setLoading] = useState(false);
  const [adapting, setAdapting] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [scheduleMode, setScheduleMode] = useState(false);
  const [scheduledAt, setScheduledAt] = useState('');
  const [scheduleSuccess, setScheduleSuccess] = useState('');
  const abortRef = useRef(null);

  const mediaType = useMemo(() => getMediaType(mediaFile), [mediaFile]);

  useEffect(() => {
    if (!mediaType) return;

    const allowed = new Set(SUPPORTED_PLATFORMS[mediaType] || []);
    setPlatforms((current) => current.filter((platform) => allowed.has(platform)));
  }, [mediaType]);

  useEffect(() => {
    setPlatformContent((current) => trimPlatformContent(platforms, current));
  }, [platforms]);

  const canPost = mediaFile && title.trim() && platforms.length > 0 && !loading && !adapting;
  const canSchedule = canPost && scheduledAt;
  const canGenerate = title.trim() && platforms.length > 0 && !loading && !adapting;

  const getMinDateTime = () => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 1);
    return now.toISOString().slice(0, 16);
  };

  const buildFormData = () => {
    const formData = new FormData();
    const effectivePlatformContent = buildEffectivePlatformContent(platforms, title.trim(), description.trim(), platformContent);
    formData.append('media', mediaFile);
    formData.append('title', title.trim());
    formData.append('description', description.trim());
    formData.append('platforms', JSON.stringify(platforms));
    formData.append('platformContent', JSON.stringify(effectivePlatformContent));
    return formData;
  };

  const handleGenerateCaptions = async () => {
    if (!canGenerate) return;

    setAdapting(true);
    setError('');

    try {
      const data = await generatePlatformCaptions({
        title: title.trim(),
        description: description.trim(),
        mediaType: mediaType || 'video',
        platforms,
      });

      setPlatformContent((current) => ({
        ...trimPlatformContent(platforms, current),
        ...(data.platformContent || {}),
      }));
    } catch (err) {
      const errMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        err.message ||
        'Failed to generate captions.';
      setError(errMsg);
    } finally {
      setAdapting(false);
    }
  };

  const handlePost = async () => {
    if (!canPost) return;

    setLoading(true);
    setResults(null);
    setError('');
    setScheduleSuccess('');

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const data = await postVideo(buildFormData(), { signal: controller.signal });
      setResults(data.results);
    } catch (err) {
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        // User cancelled — no error to show
      } else if (err.response?.data?.results) {
        setResults(err.response.data.results);
      } else {
        const errMsg =
          err.response?.data?.error ||
          err.response?.data?.message ||
          err.message ||
          'Something went wrong.';
        setError(errMsg);
      }
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setLoading(false);
  };

  const handleSchedule = async () => {
    if (!canSchedule) return;

    setLoading(true);
    setResults(null);
    setError('');
    setScheduleSuccess('');

    try {
      const formData = buildFormData();
      formData.append('scheduledAt', new Date(scheduledAt).toISOString());

      const data = await scheduleVideo(formData);
      handleReset();
      setScheduleSuccess(data.message || 'Post scheduled successfully!');
    } catch (err) {
      const errMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        err.message ||
        'Failed to schedule post.';
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setMediaFile(null);
    setTitle('');
    setDescription('');
    setPlatforms(DEFAULT_PLATFORMS);
    setPlatformContent({});
    setResults(null);
    setError('');
    setScheduleMode(false);
    setScheduledAt('');
  };

  const postingLabel = mediaType === 'image' ? 'photo' : 'video';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Create a Post</h1>
        <p className="text-slate-400 text-sm mt-1">
          Write one base caption, let AI adapt it for each selected platform, then edit before posting.
        </p>
      </div>

      {loading ? (
        <div className="card">
          <Loader
            message={`Posting ${postingLabel} to ${platforms.length} platform${platforms.length > 1 ? 's' : ''}...`}
            detail={mediaType === 'image' ? 'This usually finishes quickly unless a platform is processing the image.' : undefined}
            onCancel={handleCancel}
          />
        </div>
      ) : (
        <>
          <div className="card">
            <UploadForm
              mediaFile={mediaFile}
              setMediaFile={setMediaFile}
              title={title}
              setTitle={setTitle}
              description={description}
              setDescription={setDescription}
            />
          </div>

          <div className="card">
            <PlatformPicker selected={platforms} setSelected={setPlatforms} mediaType={mediaType} />
          </div>

          <div className="card space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-white">AI Platform Adaptation</h2>
                <p className="text-sm text-slate-400 mt-1">
                  Generate platform-specific titles and captions from your base copy.
                </p>
              </div>
              <button
                type="button"
                onClick={handleGenerateCaptions}
                disabled={!canGenerate}
                className="btn-secondary whitespace-nowrap"
              >
                {adapting ? 'Generating...' : 'Adapt with AI'}
              </button>
            </div>

            <PlatformContentEditor
              platforms={platforms}
              platformContent={platformContent}
              setPlatformContent={setPlatformContent}
              baseTitle={title}
              baseDescription={description}
              disabled={loading || adapting}
            />
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <label className="block text-sm font-medium text-slate-300">
                Schedule Post
              </label>
              <button
                type="button"
                onClick={() => {
                  setScheduleMode(!scheduleMode);
                  if (scheduleMode) setScheduledAt('');
                }}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${scheduleMode ? 'bg-blue-600' : 'bg-slate-700'}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${scheduleMode ? 'translate-x-6' : 'translate-x-1'}`}
                />
              </button>
            </div>
            {scheduleMode && (
              <div className="mt-3">
                <input
                  type="datetime-local"
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                  min={getMinDateTime()}
                  className="input-field"
                />
                <p className="text-slate-500 text-xs mt-2">
                  {mediaType === 'video'
                    ? 'Videos are pre-uploaded before publish time when the platform supports it.'
                    : 'Images publish directly at the scheduled time.'}
                </p>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            {scheduleMode ? (
              <button
                onClick={handleSchedule}
                disabled={!canSchedule}
                className="btn-primary flex-1 flex items-center justify-center gap-2 text-lg py-4"
              >
                <span>Schedule</span>
                <span>Post</span>
              </button>
            ) : (
              <button
                onClick={handlePost}
                disabled={!canPost}
                className="btn-primary flex-1 flex items-center justify-center gap-2 text-lg py-4"
              >
                <span>{mediaType === 'image' ? 'Image' : 'Media'}</span>
                <span>Post Now</span>
              </button>
            )}

            {results && (
              <button onClick={handleReset} className="btn-secondary">
                New Post
              </button>
            )}
          </div>

          {scheduleSuccess && (
            <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4">
              <p className="text-green-400 font-medium">Scheduled</p>
              <p className="text-green-300 text-sm mt-1">{scheduleSuccess}</p>
              <p className="text-green-300/70 text-xs mt-2">
                Track status on the <a href="/schedules" className="underline text-green-300 hover:text-green-200">Scheduled Posts</a> page.
              </p>
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
              <p className="text-red-400 font-medium">Error</p>
              <p className="text-red-300 text-sm mt-1">{error}</p>
            </div>
          )}

          <ResultCard results={results} />
        </>
      )}
    </div>
  );
}
