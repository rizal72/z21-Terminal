import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import LocoImage from './LocoImage';

const PANEL_WIDTH = 420;
const PANEL_MAX_HEIGHT = 420;
const MOBILE = '(max-width: 767px)';

// The lock counts, so a picker closing cannot unlock the page while another
// list, or the consist manager, still holds it.
let lockCount = 0;
let savedOverflow = '';

function lockScroll() {
  if (lockCount === 0) savedOverflow = document.body.style.overflow;
  lockCount += 1;
  document.body.style.overflow = 'hidden';
}

function unlockScroll() {
  lockCount = Math.max(0, lockCount - 1);
  if (lockCount === 0) document.body.style.overflow = savedOverflow;
}

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
  const [isMobile, setIsMobile] = useState(() => window.matchMedia(MOBILE).matches);
  const buttonRef = useRef(null);
  const listRef = useRef(null);
  const closeRef = useRef(null);
  const lastRect = useRef(null);
  const listId = useId();

  const items = options.filter(
    (option) => !(option.type === 'locomotive' && exclude.includes(option.address))
  );
  const selectedIndex = value
    ? items.findIndex((o) => o.type === value.type && o.address === value.address)
    : -1;
  const selected = selectedIndex >= 0 ? items[selectedIndex] : null;

  useEffect(() => {
    const onOtherOpened = (event) => {
      if (event.detail !== listId) setOpen(false);
    };
    document.addEventListener('loco-picker-open', onOtherOpened);
    return () => document.removeEventListener('loco-picker-open', onOtherOpened);
  }, [listId]);

  // Keep the same mobile/desktop decision as the layout.
  useEffect(() => {
    const query = window.matchMedia(MOBILE);
    const onChange = () => setIsMobile(query.matches);
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  const close = (refocus = false) => {
    setOpen(false);
    if (refocus) buttonRef.current?.focus();
  };

  const openList = () => {
    // One list at a time: every picker closes when another one announces itself.
    document.dispatchEvent(new CustomEvent('loco-picker-open', { detail: listId }));
    const box = buttonRef.current?.getBoundingClientRect();
    if (box) {
      const measured = { top: box.top, left: box.left, width: box.width, height: box.height };
      lastRect.current = measured;
      setRect(measured);
    }
    setActive(selectedIndex >= 0 ? selectedIndex : 0);
    setOpen(true);
  };

  const choose = (option) => {
    if (!option) return;
    onChange({ type: option.type, address: option.address });
    close(true);
  };

  // Geometry follows the button: a layout shift above it would otherwise leave
  // the panel where the button used to be.
  useEffect(() => {
    if (!open) return undefined;

    let frame = 0;
    const tick = () => {
      const element = buttonRef.current;
      if (element) {
        const box = element.getBoundingClientRect();
        const known = lastRect.current;
        if (
          !known ||
          known.top !== box.top ||
          known.left !== box.left ||
          known.width !== box.width ||
          known.height !== box.height
        ) {
          const measured = { top: box.top, left: box.left, width: box.width, height: box.height };
          lastRect.current = measured;
          setRect(measured);
        }
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;

    const onPointerDown = (event) => {
      if (!event.target.closest('[data-loco-picker]')) setOpen(false);
    };

    document.addEventListener('mousedown', onPointerDown);
    lockScroll();
    listRef.current?.focus({ preventScroll: true });

    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      unlockScroll();
    };
  }, [open]);

  const onKeyDown = (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      // ESC is also the global emergency stop: keep it inside the list.
      event.stopPropagation();
      close(true);
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
    } else if (event.key === 'Tab') {
      event.preventDefault();
      if (isMobile && closeRef.current) {
        const focusable = [closeRef.current, listRef.current].filter(Boolean);
        const index = focusable.indexOf(document.activeElement);
        const step = event.shiftKey ? -1 : 1;
        focusable[(index + step + focusable.length) % focusable.length].focus();
      } else {
        close(true);
      }
    }
  };

  // Below the button when there is room, above it otherwise.
  const panelStyle = () => {
    if (!rect || typeof window === 'undefined') return {};
    const width = Math.min(PANEL_WIDTH, window.innerWidth - 16);
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    const below = window.innerHeight - (rect.top + rect.height) - 8;
    const above = rect.top - 8;
    const placeBelow = below >= 240 || below >= above;
    const maxHeight = Math.max(160, Math.min(PANEL_MAX_HEIGHT, placeBelow ? below : above));
    return placeBelow
      ? { top: rect.top + rect.height + 4, left, width, maxHeight }
      : { bottom: window.innerHeight - rect.top + 4, left, width, maxHeight };
  };

  const list = (
    <ul
      ref={listRef}
      id={listId}
      role="listbox"
      tabIndex={-1}
      aria-label={title}
      aria-activedescendant={items[active] ? `${listId}-${active}` : undefined}
      className="min-h-0 flex-1 overflow-y-auto py-1 focus:outline-none"
    >
      {items.map((option, index) => {
        const isSelected = index === selectedIndex;
        return (
          <li
            key={`${option.type}-${option.address}`}
            id={`${listId}-${index}`}
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
    <div className="relative w-full min-w-0" onKeyDown={onKeyDown}>
      <button
        ref={buttonRef}
        type="button"
        data-loco-picker
        onClick={() => (open ? close() : openList())}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
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
          isMobile ? (
            <div data-loco-picker className="fixed inset-0 z-[100]">
              <div className="absolute inset-0 bg-black/70" onClick={() => close()} />
              <div
                role="dialog"
                aria-modal="true"
                aria-label={title}
                className="absolute inset-0 flex flex-col bg-control-black"
              >
                <div className="flex items-center justify-between border-b border-control-grey px-4 py-3">
                  <span className="font-display text-sm font-semibold uppercase tracking-wider text-signal-amber">
                    {title}
                  </span>
                  <button
                    ref={closeRef}
                    type="button"
                    onClick={() => close(true)}
                    className="flex h-8 w-8 items-center justify-center rounded border border-control-grey text-track-steel hover:border-signal-red hover:text-signal-red"
                    aria-label="Close"
                  >
                    <i className="fa-solid fa-xmark" />
                  </button>
                </div>
                {list}
              </div>
            </div>
          ) : (
            <div
              data-loco-picker
              style={panelStyle()}
              className="fixed z-[100] flex flex-col overflow-hidden rounded border border-control-grey bg-control-black shadow-2xl"
            >
              {list}
            </div>
          ),
          document.body
        )}
    </div>
  );
}
