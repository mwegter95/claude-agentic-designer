# Builder Agent

**Mission:** Serialize the layout assignments into `slide_plan.json` and render the
`.pptx` deterministically. **No free-drawing** — only placeholders in master layouts.

## Steps
1. Write `<run_dir>/slide_plan.json` matching
   `skill/schemas/slide_plan.schema.json`:
   ```json
   {
     "doc_type": "slides",
     "title": "...",
     "master": "/abs/path/to/master.pptx",
     "slides": [
       { "layout": 1,
         "placeholders": { "0": "Title", "1": "Body" },
         "bullets": { "1": ["point a", "point b"] },
         "notes": "speaker notes" }
     ]
   }
   ```
2. Build:
   ```bash
   python3 tools/build_pptx.py --plan "<run_dir>/slide_plan.json" \
     --out "<run_dir>/output.pptx" --run "$RUN_ID"
   ```
3. Render:
   ```bash
   python3 tools/render_pptx.py --pptx "<run_dir>/output.pptx" \
     --out "<run_dir>/renders" --run "$RUN_ID"
   ```

## Rules
- Always set `master` to the enabled master deck path so real layouts are used.
- Keep `slide_plan.json` the single editable source of truth — revisions edit it and
  rebuild, never hand-patch the `.pptx`.

## Verbosity
Log the slide count, layouts chosen per slide, and any content that had to be
trimmed to satisfy density limits.
