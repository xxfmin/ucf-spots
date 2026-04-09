/**
 * Shared loading spinner used in page/sidebar loading states.
 */
export function LoadingSpinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 border-4 border-zinc-800 rounded-full"></div>
        <div className="absolute inset-0 border-4 border-yellow-400 border-t-transparent rounded-full animate-spin"></div>
      </div>
      <p className="text-sm text-zinc-400">{label}</p>
    </div>
  );
}
