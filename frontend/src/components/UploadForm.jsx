import { useCallback, useEffect, useRef, useState } from 'react';

const ACCEPTED_TYPES = [
  'video/mp4',
  'video/quicktime',
  'video/x-msvideo',
  'video/webm',
  'video/x-matroska',
  'image/jpeg',
  'image/png',
  'image/webp',
].join(',');

function getMediaType(file) {
  if (!file?.type) return null;
  if (file.type.startsWith('video/')) return 'video';
  if (file.type.startsWith('image/')) return 'image';
  return null;
}

export default function UploadForm({
  mediaFile,
  setMediaFile,
  title,
  setTitle,
  description,
  setDescription,
}) {
  const [dragActive, setDragActive] = useState(false);
  const [previewUrl, setPreviewUrl] = useState('');
  const inputRef = useRef(null);
  const mediaType = getMediaType(mediaFile);

  useEffect(() => {
    if (!mediaFile || mediaType !== 'image') {
      setPreviewUrl('');
      return;
    }

    const objectUrl = URL.createObjectURL(mediaFile);
    setPreviewUrl(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [mediaFile, mediaType]);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const applySelectedFile = useCallback((file) => {
    const nextMediaType = getMediaType(file);
    if (nextMediaType) {
      setMediaFile(file);
    }
  }, [setMediaFile]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      applySelectedFile(e.dataTransfer.files[0]);
    }
  }, [applySelectedFile]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      applySelectedFile(e.target.files[0]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  };

  const removeFile = (e) => {
    e.stopPropagation();
    setMediaFile(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Upload Photo or Video
        </label>
        <div
          className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
            dragActive
              ? 'border-blue-500 bg-blue-500/10'
              : mediaFile
              ? 'border-green-500/50 bg-green-500/5'
              : 'border-slate-700 hover:border-slate-500 bg-slate-800/50'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            onChange={handleFileChange}
            className="hidden"
          />

          {mediaFile ? (
            <div className="space-y-3">
              {mediaType === 'image' && previewUrl ? (
                <img
                  src={previewUrl}
                  alt={mediaFile.name}
                  className="mx-auto max-h-48 rounded-xl border border-slate-700 object-contain"
                />
              ) : (
                <div className="text-4xl">{mediaType === 'video' ? '🎥' : '🖼️'}</div>
              )}
              <div>
                <p className="text-white font-medium break-all">{mediaFile.name}</p>
                <p className="text-slate-400 text-sm">
                  {mediaType === 'image' ? 'Photo' : 'Video'} · {formatFileSize(mediaFile.size)}
                </p>
              </div>
              <button
                type="button"
                onClick={removeFile}
                className="text-red-400 hover:text-red-300 text-sm underline"
              >
                Remove
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-3xl">🗂️</div>
              <p className="text-slate-300">Drag and drop your media here</p>
              <p className="text-slate-500 text-sm">or click to browse</p>
              <p className="text-slate-600 text-xs mt-2">
                Supported: MP4, MOV, AVI, WebM, MKV, JPG, PNG, WebP
              </p>
            </div>
          )}
        </div>
      </div>

      <div>
        <label htmlFor="title" className="block text-sm font-medium text-slate-300 mb-2">
          Title / Headline
        </label>
        <input
          id="title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Enter a title for the post..."
          className="input-field"
        />
      </div>

      <div>
        <label htmlFor="description" className="block text-sm font-medium text-slate-300 mb-2">
          Description / Caption
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Enter the caption..."
          rows={4}
          className="input-field resize-none"
        />
      </div>
    </div>
  );
}
