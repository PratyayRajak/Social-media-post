export default function Loader({ message = 'Posting your media...', detail = 'This may take a few minutes for large videos...', onCancel }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative w-16 h-16 mb-4">
        <div className="absolute inset-0 rounded-full border-4 border-slate-700"></div>
        <div className="absolute inset-0 rounded-full border-4 border-blue-500 border-t-transparent animate-spin"></div>
      </div>
      <p className="text-slate-300 font-medium">{message}</p>
      <p className="text-slate-500 text-sm mt-1">{detail}</p>
      {onCancel && (
        <button
          type="button"
          onClick={onCancel}
          className="mt-4 px-4 py-2 text-sm text-red-400 hover:text-red-300 border border-red-500/30 hover:border-red-500/50 rounded-lg transition-colors"
        >
          Cancel Upload
        </button>
      )}
    </div>
  );
}
