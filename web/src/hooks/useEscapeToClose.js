import { useEffect, useRef } from 'react';

/**
 * Escape closes the overlay instead of reaching the global emergency stop.
 *
 * The global stop listens on `window` in the bubble phase; this one uses the
 * capture phase, so it runs first and stops the event. With nothing open,
 * Escape still toggles track power.
 */
export default function useEscapeToClose(onClose) {
  const closeRef = useRef(onClose);

  useEffect(() => {
    closeRef.current = onClose;
  });

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      event.stopPropagation();
      closeRef.current?.();
    };

    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, []);
}
