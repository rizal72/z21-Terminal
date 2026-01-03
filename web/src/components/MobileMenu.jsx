export default function MobileMenu({
  onClose,
  onConsistManager,
  onAddController,
  onReloadRoster,
  onWakeLock,
  wakeLockActive,
  reloadingRoster
}) {
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-[60] md:hidden"
        onClick={onClose}
      />

      {/* Menu Panel */}
      <div className="fixed right-0 top-0 h-full w-[280px] bg-control-dark border-l border-control-grey z-[70] md:hidden animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-control-grey">
          <h2 className="text-lg font-display font-semibold text-signal-amber">
            Menu
          </h2>
          <button
            onClick={onClose}
            className="text-track-steel hover:text-signal-amber transition-colors"
          >
            <i className="fa-solid fa-times text-xl"></i>
          </button>
        </div>

        {/* Menu Items */}
        <div className="p-4 space-y-3">
          {/* Consist Manager */}
          <button
            onClick={onConsistManager}
            className="w-full flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey transition-colors text-left"
          >
            <i className="fa-solid fa-gears text-signal-amber text-xl"></i>
            <span className="font-sans text-sm">Consist Manager</span>
          </button>

          {/* Add Controller */}
          <button
            onClick={onAddController}
            className="w-full flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey transition-colors text-left"
          >
            <i className="fa-solid fa-plus text-signal-green text-xl"></i>
            <span className="font-sans text-sm">Add Controller</span>
          </button>

          {/* Reload Roster */}
          <button
            onClick={onReloadRoster}
            disabled={reloadingRoster}
            className="w-full flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey transition-colors text-left disabled:opacity-50"
          >
            <i className={`fa-solid ${reloadingRoster ? 'fa-spinner fa-spin' : 'fa-rotate-right'} text-track-steel text-xl`}></i>
            <span className="font-sans text-sm">
              {reloadingRoster ? 'Reloading...' : 'Reload Roster'}
            </span>
          </button>

          {/* Keep Screen Awake */}
          {'wakeLock' in navigator && (
            <button
              onClick={onWakeLock}
              className="w-full flex items-center gap-3 p-3 bg-control-black rounded hover:bg-control-grey transition-colors text-left"
            >
              <i className={`fa-solid fa-moon text-xl ${wakeLockActive ? 'text-signal-green' : 'text-track-steel'}`}></i>
              <span className="font-sans text-sm">
                {wakeLockActive ? 'Screen Awake ✓' : 'Keep Screen Awake'}
              </span>
            </button>
          )}
        </div>
      </div>
    </>
  );
}
