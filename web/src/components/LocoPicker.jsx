import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import LocoImage from './LocoImage';

const PANEL_WIDTH = 420;
const PANEL_MAX_HEIGHT = 420;

/**
 * Pictures for an option: one for a locomotive, lead + rear for a consist.
 */
function OptionImages({ option, className = '' }) {
  const locomotives = option?.type === 'consist' && option.locomotives?.length
    ? option.locomotives
    : option
      ? [{ address: option.address }]
      : [];

  if (!locomotives.length) return null;

  const width = locomotives.length > 1 ? 'w-1/2' : 'w-full';
  return (
    <span className={`flex items-center justify-center gap-0.5 overflow-hidden ${className}`}>
      {locomotives.slice(0, 2).map((loco) => (
        <LocoImage
          key={loco.address}
          address={loco.address}
          className={`${width} h-full object-contain`}
        />
      ))}
    </span>
  );
}

function subtitle(option) {
  if (option.type === 'consist') {
    return `Consist ${option.address}${option.trackName ? ` - ${option.trackName}` : ''}`;
  }
  return `Loco #${option.address}${option.inConsist ? ` - in consist ${option.inConsist} (functions only)` : ''}`;
}

/**
 * Locomotive/consist selector with pictures.
 *
 * Replaces the native <select>, which cannot show images. One component on
 * both surfaces: a full screen sheet on mobile, a panel under the button on
 * desktop. Keyboard: arrows move, Enter selects, Escape closes.
 *
 * Options: { type: 'locomotive' | 'consist', address, name, label,
 *            locomotives?: [{ address, name }], trackName?, inConsist? }
 */
export default function LocoPicker({
  value,
  options,
  onChange,
  placeholder = 'Select locomotive or consist',
  exclude = [],
  invalid = false,
  title = 'Select',
}) {
  const [open, setOpen] = useState(false);
  const [rect, setRect] = useState(null);
  const [active, setActive] = useState(0);
  const buttonRef = useRef(null);

  const items = options.filter(
    (option) => !(option.type === 'locomotive' && exclude.includes(option.address))
  );
  const selectedIndex = value
    ? items.findIndex((o) => o.type === value.type && o.address === value.address)
    : -1;
  const selected = selectedIndex >= 0 ? items[selectedIndex] : null;

  const close = () => setOpen(false);

  const openList = () => {
    setRect(buttonRef.current.getBoundingClientRect());
    setActive(selectedIndex >= 0 ? selectedIndex : 0);
    setOpen(true);
  };

  const choose = (option) => {
    if (!option) return;
    onChange({ type: option.type, address: option.address });
    close();
  };

  useEffect(() => {
    if (!open) return;

    const updateRect = () => setRect(buttonRef.current?.getBoundingClientRect() ?? null);
    const onPointerDown = (event) => {
      if (!event.target.closest('[data-loco-picker]')) close();
    };

    window.addEventListener('resize', updateRect);
    window.addEventListener('scroll', updateRect, true);
    document.addEventListener('mousedown', onPointerDown);
    // Restore what was there: the consist manager also locks the body.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('resize', updateRect);
      window.removeEventListener('scroll', updateRect, true);
      document.removeEventListener('mousedown', onPointerDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  const onKeyDown = (event) => {
    if (event.key === 'Escape') {
      close();
      return;
    }
    if (!open) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Enter') {
        event.preventDefault();
        openList();
      }
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((index) => Math.min(index + 1, items.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      choose(items[active]);
    }
  };

  // Below the button when there is room, above it otherwise.
  const panelStyle = () => {
    if (!rect) return {};
    const width = Math.min(PANEL_WIDTH, window.innerWidth - 16);
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    const below = window.innerHeight - rect.bottom - 8;
    const above = rect.top - 8;
    const placeBelow = below >= 240 || below >= above;
    const maxHeight = Math.max(160, Math.min(PANEL_MAX_HEIGHT, placeBelow ? below : above));
    return placeBelow
      ? { top: rect.bottom + 4, left, width, maxHeight }
      : { bottom: window.innerHeight - rect.top + 4, left, width, maxHeight };
  };

  const list = (
    <ul role="listbox" className="min-h-0 flex-1 overflow-y-auto py-1">
      {items.map((option, index) => {
        const isSelected = index === selectedIndex;
        return (
          <li
            key={`${option.type}-${option.address}`}
            role="option"
            aria-selected={isSelected}
            onMouseEnter={() => setActive(index)}
            onClick={() => choose(option)}
            className={`flex cursor-pointer items-center gap-3 px-3 py-2 ${
              active === index ? 'bg-control-dark' : ''
            } ${isSelected ? 'bg-signal-amber/10' : ''}`}
          >
            <OptionImages option={option} className="h-8 w-16 shrink-0 md:w-24" />
            <span className="min-w-0 flex-1">
              <span className="block truncate font-mono text-sm text-white">
                {option.name || option.label}
              </span>
              <span className="block truncate text-xs text-track-steel">{subtitle(option)}</span>
            </span>
            {isSelected && <i className="fa-solid fa-check text-xs text-signal-amber" />}
          </li>
        );
      })}
      {!items.length && (
        <li className="px-3 py-4 text-sm text-track-steel">No locomotives available</li>
      )}
    </ul>
  );

  return (
    <div className="relative w-full min-w-0">
      <button
        ref={buttonRef}
        type="button"
        data-loco-picker
        onClick={() => (open ? close() : openList())}
        onKeyDown={onKeyDown}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`flex w-full min-w-0 items-center gap-2 rounded border bg-control-dark px-2 py-1.5 text-left transition-colors focus:outline-none ${
          invalid ? 'border-signal-red' : 'border-control-grey hover:border-signal-amber focus:border-signal-amber'
        }`}
      >
        <OptionImages
          option={selected}
          className="h-8 w-10 shrink-0 rounded bg-control-black md:h-9 md:w-[120px]"
        />
        <span className={`min-w-0 flex-1 truncate font-mono text-sm ${selected ? 'text-white' : 'text-track-steel'}`}>
          {selected ? selected.label : placeholder}
        </span>
        <i
          className={`fa-solid fa-chevron-down text-xs text-track-steel transition-transform ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>

      {open &&
        createPortal(
          <>
            {/* Mobile: full screen sheet */}
            <div data-loco-picker className="fixed inset-0 z-[100] md:hidden">
              <div className="absolute inset-0 bg-black/70" onClick={close} />
              <div className="absolute inset-0 flex flex-col bg-control-black">
                <div className="flex items-center justify-between border-b border-control-grey px-4 py-3">
                  <span className="font-display text-sm font-semibold uppercase tracking-wider text-signal-amber">
                    {title}
                  </span>
                  <button
                    type="button"
                    onClick={close}
                    className="flex h-8 w-8 items-center justify-center rounded border border-control-grey text-track-steel hover:border-signal-red hover:text-signal-red"
                    aria-label="Close"
                  >
                    <i className="fa-solid fa-xmark" />
                  </button>
                </div>
                {list}
              </div>
            </div>

            {/* Desktop: panel under the button */}
            <div
              data-loco-picker
              style={panelStyle()}
              className="fixed z-[100] hidden flex-col overflow-hidden rounded border border-control-grey bg-control-black shadow-2xl md:flex"
            >
              {list}
            </div>
          </>,
          document.body
        )}
    </div>
  );
}
