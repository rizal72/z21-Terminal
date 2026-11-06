import { useState } from 'react';

/**
 * Locomotive picture from web/public/loco_images/<address>.jpg.
 * Falls back to the train glyph when the file is missing, so a locomotive
 * imported without a picture still renders.
 */
export default function LocoImage({ address, className = '' }) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return <i className={`fa-solid fa-train text-signal-amber ${className}`} aria-hidden="true" />;
  }

  return (
    <img
      src={`/loco_images/${address}.jpg`}
      alt=""
      className={className}
      onError={() => setFailed(true)}
      draggable={false}
    />
  );
}
