/**
 * Notification Component
 *
 * Generic notification overlay that displays messages with auto-dismiss.
 * Supports multiple notification types (success, info, warning, error).
 * Can display multiple notifications stacked vertically.
 *
 * Managed by useNotification hook.
 */

export default function Notification({ notifications }) {
  if (!notifications || notifications.length === 0) return null;

  return (
    <div className="fixed inset-0 z-[200] flex flex-col items-center justify-center pointer-events-none gap-3">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={`bg-control-dark/90 backdrop-blur-sm border ${notification.borderClass} rounded-lg px-6 py-3 shadow-2xl pointer-events-auto`}
          style={{
            animation: `fade-in-out ${notification.duration}ms ease-in-out forwards`
          }}
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
