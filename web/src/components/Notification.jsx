/**
 * Notification Component
 *
 * Toast-style notifications in bottom-right corner.
 * Supports multiple notification types (success, info, warning, error).
 *
 * Managed by useNotification hook.
 */

export default function Notification({ notifications }) {
  if (!notifications || notifications.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[200] flex flex-col gap-3 pointer-events-none">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={`bg-control-dark/95 border ${notification.borderClass} rounded-lg px-6 py-3 shadow-2xl animate-fade-in-out pointer-events-auto`}
        >
          <div className="flex items-center gap-3">
            {/* Icon */}
            <i className={`fa-solid ${notification.icon} ${notification.iconClass} text-lg`}></i>

            {/* Message */}
            <div className="text-xl font-display text-white">
              {notification.message}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
