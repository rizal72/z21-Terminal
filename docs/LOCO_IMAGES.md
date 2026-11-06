# Locomotive Pictures and the Roster Picker

Every locomotive and consist is chosen through one control that shows the
picture: a button with the image, the name and a chevron. Clicking it opens the
list; on a phone the list takes the whole screen.

The native `<select>` is gone from every locomotive chooser: an `<option>` can
only hold text, so the picture could never appear inside it.

## Pictures

Files live in `web/public/loco_images/<dcc_address>.jpg`, 480 px wide, about
20 KB each. The address is the key, so no mapping is needed anywhere: the
frontend builds `/loco_images/<address>.jpg`.

They come from JMRI's `iconFilePath` — the side view DecoderPro shows in its
Icon column — and they are committed. The PC never reads the JMRI roster: the
pictures are static assets of the frontend.

Regenerate them on the Mac (the only machine with JMRI):

```bash
venv/bin/python scripts/utils/import_loco_images.py              # every loco in config.json
venv/bin/python scripts/utils/import_loco_images.py --address 2  # one loco
venv/bin/python scripts/utils/import_loco_images.py --dry-run    # show, write nothing
```

A locomotive without a file falls back to the Font Awesome train glyph, so an
import that skips the picture still works.

## The picker

`web/src/components/LocoPicker.jsx`, with `LocoImage.jsx` for the picture.

- **Desktop**: panel under the button, 420 px wide, max 420 px tall, flips
  above the button when there is no room below.
- **Mobile**: full screen sheet with a close button.
- One row per entry: picture (two for a consist, lead and rear), name, address
  and, for a locomotive already coupled, the consist it belongs to.
- Keyboard: arrows move, Enter selects, Escape closes. No type-ahead.
- The list is rendered in a portal on `document.body`, at `z-[100]`: the
  controller panel has a `transform` (GPU isolation), which would turn a
  `position: fixed` child into a panel-sized box, and the consist manager modal
  sits at `z-90`.

Used in `ConsistController.jsx` (both the empty and the selected state) and in
`ConsistForm.jsx` for lead and rear, where `exclude` hides the locomotive
already picked on the other side. `ConsistCard.jsx` shows static thumbnails.

## Limits

- No search or type-ahead: the list is short enough to scan.
- The 40 px thumbnail on mobile is a crop; the full picture is in the sheet.
- A new locomotive needs the import script run on the Mac, then a commit.
