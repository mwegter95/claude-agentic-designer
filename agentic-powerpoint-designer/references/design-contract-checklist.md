# Design Contract — Exhaustive Extraction Checklist

Use this when ingesting the master deck (Phase 1). The goal is a complete,
machine-precise picture of the brand's design system so every later decision is a
lookup, not a guess. Work through every section. Record concrete values (exact hex,
point sizes, font names, EMU/inch positions, corner radii) — not vague impressions.

> Reminder: you have no code sandbox. "Extract" means *read it from the master with
> the add-in and write it down in your working notes*, then reuse it precisely.

## 1. Document & theme
- [ ] Slide size and aspect ratio (16:9, 4:3, custom).
- [ ] Theme name.
- [ ] Number of slide masters; the named layouts under each master.
- [ ] For each named layout: its purpose (title, section divider, content, two-column,
      stat/callout, quote, image-led/full-bleed, comparison, closing, divider, blank).

## 2. Color palette
- [ ] Theme colors as exact hex: Background 1/2, Text 1/2, Accent 1–6, Hyperlink,
      Followed Hyperlink.
- [ ] Role of each color: which is used for titles, body, accents, dividers, bars,
      backgrounds, icon fills, chart series.
- [ ] Tints/shades actually used (e.g. Accent 1 at 60%/40%/20%).
- [ ] Gradient fills: stop colors, stop positions, angle/direction, type
      (linear/radial).
- [ ] Any colors that appear in examples but are derived (overlays, transparencies).

## 3. Typography
- [ ] Heading (major) font family; Body (minor) font family; any tertiary/display font.
- [ ] Full type scale with point sizes for: slide title, subtitle/kicker, section
      title, heading, subheading, body, bullet levels 1–3, caption, footer, page number.
- [ ] Weight per level (light/regular/semibold/bold).
- [ ] Casing per level (Title Case, Sentence case, ALL CAPS, small caps).
- [ ] Letter-spacing/tracking and line spacing per level.
- [ ] Text color per level (map to palette roles, not raw hex where possible).
- [ ] Bullet glyphs and indents per level; numbered-list style.
- [ ] Paragraph alignment defaults (left/center) per layout.

## 4. Backgrounds
- [ ] Per layout: fill type — solid, gradient, picture, or pattern — with values.
- [ ] Background graphics baked into the layout/master (bars, shapes, watermarks).
- [ ] Decorative accent shapes and where they sit (corner wedge, side rail, footer band).
- [ ] Light vs. dark layout variants and when each is used.

## 5. Logos & brand marks
- [ ] All logo variants present (primary, reversed/white, mark-only, lockup).
- [ ] Placement per slide type (title, content footer, closing) — corner, size,
      and clear-space/margin.
- [ ] Which variant goes on light vs. dark backgrounds.
- [ ] Any partner/co-brand lockups and their rules.

## 6. Layout & grid
- [ ] Page margins (top/bottom/left/right).
- [ ] Column count and gutter widths; content safe area.
- [ ] Placeholder geometry for each named layout (position + size of title, body,
      image, and secondary placeholders).
- [ ] Baseline/alignment grid the examples snap to.

## 7. Components & shapes
- [ ] Default shape style: corner radius (sharp vs. rounded, exact radius), fill,
      line weight/color, shadow/elevation.
- [ ] Stat/callout block style (number size, label style, container fill).
- [ ] Dividers, accent bars, underlines (thickness, color, length).
- [ ] Icon style: line vs. filled, stroke weight, corner style, color treatment.
- [ ] Image treatment: full-bleed vs. framed, corner radius, duotone/overlay,
      drop shadow, aspect/crop conventions.
- [ ] Table style: header fill, banding, border weights, font.
- [ ] Chart style: series colors (in palette order), gridline treatment, label fonts.

## 8. Density & spacing rules
- [ ] Typical max bullets per content slide.
- [ ] Typical max words per bullet / line length.
- [ ] Whitespace expectations (airy vs. dense) seen in examples.
- [ ] Consistent inter-element spacing and padding within containers.

## 9. Subtle / signature features (do not skip)
These are what make a slide unmistakably on-brand. Capture each explicitly:
- [ ] Accent rule/underline under titles (color, thickness, offset).
- [ ] Footer content and style (text, divider line, alignment).
- [ ] Page-number style and position.
- [ ] Section color-coding (each section keyed to an accent color).
- [ ] Consistent icon stroke weight and size grid.
- [ ] Image corner radius and shadow as a repeated motif.
- [ ] Micro-shadows / subtle elevation on cards.
- [ ] Gradient or color overlays applied to photography.
- [ ] Specific bullet glyphs or numbered-step styling.
- [ ] Any repeated decorative accent (corner wedge, dotted rule, brand pattern).
- [ ] Title/kicker pairing pattern (small label above a large title).

## Output of this phase
A written **Design Contract**: palette (with roles), fonts + type scale, layout
library (named + intent + placeholder map), background rules, logo rules, component
styles, density rules, and an explicit **signature-features** list. Carry it forward
verbatim — every transformation decision references it.
