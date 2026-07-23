# 529 Network period infographic generator

Renders the end-of-period infographic as a print-ready PDF, a web PNG, and
square and portrait social panels, all from one data file. The templates hold no
numbers, so a new edition means editing JSON and running two commands.

## Run

```bash
pip install jinja2 playwright numpy pillow potracer qrcode
playwright install chromium

python build.py  data/2025-Q4.json   # letter PDF + PNG
python social.py data/2025-Q4.json   # 1080x1080 and 1080x1350
python contrast.py                   # accessibility audit
```

## Producing the next edition

Copy `data/2025-Q4.json`, rename it, then update:

| Field | Notes |
| --- | --- |
| `period_label`, `year`, `as_of` | Drives the rail and the eyebrow |
| `file_stem` | Match the website pattern, e.g. `Q2-2026-Graphic` |
| `headline` | State the finding, do not label the category |
| `headline_highlight` | Substring of `headline` set in gold. Must match verbatim |
| `deck` | Three short sentences maximum |
| `assets.series`, `accounts.series` | Append the new period |
| `assets.label_years` | Which points carry a value label. Keep this short |
| `assets.annotations` | Periods to mark with a hairline |
| `automatic`, `cta`, `footer` | Confirm before every release |

Average balance is **not** entered. It is computed as assets divided by accounts.

## What the two charts do

The first chart is total assets. The second is the decomposition: accounts as
columns on the left axis, average balance as a line on the right axis. Those two
factors multiply to the total, so the second chart explains the first instead of
repeating it. It also shows the thing a single asset line hides, that account
counts have never fallen while average balance falls with the market.

Average balance is derived, and the caption says so. It reconciles to the
published 2025 figure within 0.1%, the gap being rounding in the $602B headline
(602.6B implied). If a future edition diverges by more than about half a
percent, treat that as a data-quality flag rather than a rounding artifact.

Note that total assets include prepaid tuition plans while the published account
count is labeled as savings accounts. See open item 1. That question governs
whether this chart can ship.

## Brand marks

`assets/mark-529.svg` and `assets/nast.svg` were traced from the published
Q4 2025 graphic by `extract_logo.py` and verified against the source at 99.45%
and 90.46% pixel overlap. They are true vector paths, so the PDF contains zero
raster images.

Both inherit `currentColor`, so CSS sets them white or mist.

**These came from a CSPN-era file.** If the rebrand changed the swoosh, this
generator is propagating a stale mark while appearing to fix the branding.
Replace both files with the official vectors under the same filenames when
available; nothing else changes.

`extract_logo.py` only needs rerunning if the crop boxes change. potracer treats
`False` as ink, so the mask is inverted in that script. Removing the inversion
silently produces a garbage trace that still renders.

## Accessibility

`contrast.py` reads the live palette out of `template.html`, so the audit cannot
go stale. All twelve text pairs currently pass. Three colors changed from the
first draft because they failed:

| Use | Was | Now | Ratio |
| --- | --- | --- | --- |
| Gold accent | #C9A227 (2.92) | #EAD285 | 4.73 / 6.90 / 10.87 |
| Captions and labels | #708686 (3.86) | #5C7270 | 5.13 on white |
| Panel note tint | #A5C795 (3.77) | #C6DDBB brand mist | 4.87 on forest |

Brand steel #708686 remains on the chart axis rule, where non-text elements need
only 3.0 and it measures 3.86.

## Number precision

Chart value labels use whole billions. Headline figures keep published
precision, so the chart endpoint reads 602 while the hero reads $602B.

## Fonts

Poppins display, Carlito body, DejaVu Sans Condensed data. All open licensed and
embedding cleanly, so every figure in the PDF stays selectable and searchable.
Swap the `--display`, `--body`, `--data` variables to use the official brand face
once its embedding license is confirmed.

Avoid TeX Gyre Heros Cn. Chromium embeds it as Type3, which makes chart numbers
impossible to select or search.

## Open items before publishing

1. **Account basis. This is the blocker.** Total assets are confirmed to include
   prepaid tuition plans. The account count is labeled "529 savings accounts" in
   the published source, which would make it a narrower universe than assets.
   If the two are on different bases, then assets divided by accounts is not an
   average balance, and the derived line in the second chart repeats that error
   across fourteen years rather than one figure.

   The evidence says the bases are probably consistent: the published $34,084
   reconciles to assets divided by accounts within 0.1%, so the Network's own
   average already uses this ratio. But that only proves the published figure
   and the derived series share a method, not that the method is right.
   Confirm before publishing. If accounts turn out to be savings-only, remove
   the average balance line and the derived figures fall out with it.
2. **Logo provenance.** See the brand marks section above. Unresolved.
3. **Reporting count.** `footer.reporting` is empty. Populate it if the count of
   reporting plans should appear on the face.
4. **Gold accent.** Accessible and consistent with the published series since
   2018, but gold sits outside the four brand tokens. Set `--brass` to
   `var(--mist)` to close the palette.
5. **Automatic contributions** is a single point-in-time figure with no trend,
   because the historical series has not been published. The panel says so.

## Verified output

| Output | Spec |
| --- | --- |
| `Q4-2025-Graphic.pdf` | 8.5 x 11 in exactly, 1 page, vector, 0 raster images, fonts embedded, all text selectable, ~132 KB |
| `Q4-2025-Graphic.png` | 2448 x 3168, 3x scale |
| `Q4-2025-Graphic-1x1.png` | 2160 x 2160, assets chart |
| `Q4-2025-Graphic-4x5.png` | 2160 x 2700, decomposition chart |

The QR code was decoded from all three rendered images and resolves to the CTA
URL. It is drawn as vector rects, so it survives print scaling.

Targets website download. Commercial press would need CMYK, 0.125 in bleed, and
crop marks, none of which this build produces.
