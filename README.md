# Assets & Accounts | The 529 Network

529assets.streamlit.app

Total assets and open accounts for every 529 plan on record, 2001Q4 to 2025Q4.
Four reported fields: state, plan name, assets, open accounts. No fund manager
names. The Intelligence Dashboard handles the harder analysis; this one stays
plain and beginner-readable.

## Sections
National · States · Plans · Compare · Movement · Data & Notes

## The record has two eras
This is the most important thing to know about the data.

- **2001Q4 to 2008Q4**: one combined row per state, labelled with the state
  name ("Alabama Prepaid", "Florida"), not a plan name.
- **2009Q4 onward**: individual plans, named.

National and state totals are sound across the whole record, because a sum is
a sum. Plan-level views only mean something after the split, so the Plans and
Compare tabs start at 2009Q4 and say so.

A consequence: one plan can appear under several names over time. Kansas's
Schwab plan is recorded under three.

## Open items in the source data
1. **2023Q1 repeats 2022Q4.** All 111 plans report identical assets and
   accounts in both periods, the only such pair in 24 years. The 12/31/2022
   workbook's internal title reads "Reporting date: March 31," so the year end
   file was likely loaded a second time as Q1 2023. 2022 reconciles to source
   exactly, which points at 2023Q1 as the suspect period.
2. **Alabama PACT 2022Q1** reports $76.1M against $232M to $257M in the other
   three quarters, with accounts nearly flat.

Both kept as reported. Neither silently corrected.

## Handling
- Rows with a Note and no figures (28) are closed or non-operational plans.
  Listed under Data & Notes, excluded from every total.
- Reporting is quarterly from 2021 and annual or semiannual before that. Year
  over year views appear only where the same quarter exists a year earlier.
- One plan reports zero accounts with nonzero assets (West Virginia Prepaid,
  2021Q3). Average balance returns n/a rather than dividing by zero.
- Wyoming runs no 529 plan and is uncolored on the map.
- The Private College 529 Plan carries state PRIVATE, has no geography, sits
  off the map, and is excluded from the jurisdiction count.
- Plan type is inferred from the plan name, not reported. Shown from 2003.

## Data
`data/529_data.csv`: `Year, Period, Date, State, PlanName, Accounts, AUM, Note`
6,340 rows · 6,312 reporting · 301 names · 69 periods.

Append new periods and reboot. No code changes required.

## Verification
Every headline figure was recomputed independently from the raw CSV and matches
what the app renders. All 69 periods, all 52 state values, and all 222 plans
(including retired ones) were exercised with zero exceptions.

## Deploy
Push to GitHub, point a Streamlit Community Cloud app at `app.py`.
`runtime.txt` pins Python 3.12 and `requirements.txt` pins every version.

## One plan, two spellings
The source spells 15 plans two ways, changing punctuation or casing partway
through, e.g. "Virginia CollegeAmerica" and "Virginia - CollegeAmerica". Left
alone, one plan reads as two and its history breaks in half; Virginia
CollegeAmerica's chart began in 2019 instead of 2009.

The loader merges them on a punctuation-blind key, adopts the most recent
spelling, and names the alias on the Plans tab. No two spellings ever report in
the same period, so nothing double counts, and the loader asserts that on every
run. National and state totals are unchanged, since only labels are merged.

## Movement tab
Ordered by dollars, not percent. Sorting by percent put a $2.5M plan (+59.8%)
above Virginia CollegeAmerica, which added $2.08B. The scatter sizes each
bubble by the assets the plan holds, so the large percentage swings visibly
belong to the small plans.

## 2026Q1: transposed rows in the published file
The website PDF for 3/31/2026 prints ten rows under the wrong plan names:

| State | Affected |
|---|---|
| Nevada | Vanguard and Wealthfront swapped |
| South Carolina | Future Scholar Advisor and Direct swapped |
| Virginia | Invest529 and Prepaid529 swapped |
| Texas | four way rotation across all four plans |

The survey submissions and the prior quarter agree with each other in every
case, so the loader uses the survey figures. Each corrected row carries a Note.
After correction every one of the ten moves within 10% quarter over quarter;
as printed, Vanguard would have fallen 98% and Wealthfront risen 4,600%.

National totals are unaffected, since every swap sits inside a single state.
2026Q1 reconciles to the published totals row: accounts exactly, assets to
within three cents of the source's own rounding.

Also in 2026Q1: Kentucky's Affordable Prepaid Tuition reports 1,127 accounts
against zero assets in both sources, Mississippi Prepaid's figures are carried
from 12-31-25, and two Kansas plans (Learning Quest Advisor, Schwab Learning
Quest) stop reporting.

## Dashboard-level plan type filter
The sidebar carries a Total / Savings / Prepaid selector, defaulting to Total.
It filters the whole dashboard: headline figures, every chart, both detail
tabs, the data table, and the CSV and Excel downloads all follow the choice.
Savings plus Prepaid reconciles to Total in every period.

Two things adapt to it rather than breaking:
- the savings vs prepaid split chart appears only under Total, since under a
  filter it would collapse to a single series. The largest-plans chart takes
  the full width instead.
- the narrative paragraph names the scope, so a filtered view never reads as
  though it were the national total.

## Withheld sections
Some sections are held back from the portal for now. The code is kept verbatim
in the app rather than deleted, so it can be restored without being rebuilt:

| Constant | Contains |
|---|---|
| `WITHHELD_COMPARE_AND_MOVEMENT` | the Compare and Movement tabs |
| `WITHHELD_DATA_NOTES` | the notes section of the Data tab |

To restore a tab: add its label back to the `st.tabs([...])` list, unindent the
block out of the string, and renumber its `tabs[n]` index. Nothing else about
it needs to change.

Also removed from the live view for now: the share-of-national-assets figure on
the States tab, and the ten-largest-plans concentration caption on National.

## Infographic tab
Generates the print-ready period sheet as a PDF, PNG and HTML, with every
figure derived from `data/529_data.csv`. The published sheet and the dashboard
therefore cannot disagree.

**What is derived, not typed.** Assets, accounts, the annual series, the
headline, the deck, the plans-reporting count, and average balance. Average
balance is always assets divided by accounts and is labelled as derived on the
face of the sheet. Headline and deck wording can be edited before generating;
the numbers cannot.

**Like-for-like series.** A Q4 edition charts Q4 of each year, a Q1 edition
charts Q1 of each year. Quarter ends are never mixed. Because quarterly
reporting only starts in 2021, a Q1 edition has fewer points than a Q4 one.
That is the record, not a bug.

**Annotations** are computed. The generator marks the worst single-year fall in
the series if it exceeds 2%, so a future edition cannot inherit a hard-coded
year that no longer applies.

**Always the total.** The sheet covers savings and prepaid together regardless
of the sidebar plan type filter, matching its own footnote. The tab says so
when the sidebar is filtered.

### Chromium is required for PDF output
The layout depends on flexbox, so the PDF is rendered by headless Chromium via
Playwright. WeasyPrint and other pure-Python engines were tried and collapse the
two-column layout, so they are not a usable fallback.

- `packages.txt` carries the system libraries Chromium needs.
- The tab calls `playwright install chromium` on first use and caches it.
- If a browser cannot be started, the tab still produces the HTML and says so.
  Opening that HTML and printing to PDF gives the same sheet.

### Brand marks
`infographic/assets/mark-529.svg` is traced from the official logo supplied by
the Network and verified at 96.6% pixel overlap against the source. The white
swooshes are holes in the path rather than painted shapes, so the mark reads
correctly on any background: on the dark rail the rail colour shows through
them. It uses `currentColor`, so CSS decides whether it is white or green.

`infographic/assets/nast.svg` is still a text stand-in. Replace it with the
official vector under the same filename, using `fill="currentColor"`.

### Known figure difference
The published Q4 2025 sheet reads $602B. This record holds $602.9B for the same
quarter, which rounds to $603B. The gap is in the source figures, not the
generator. Confirm which is authoritative before publishing.

### Open item carried over from the generator
The delivered README flags that total assets include prepaid plans while the
published account count was labelled "529 savings accounts". If those two are
on different bases, assets divided by accounts is not an average balance. The
derived value reconciles to the published $34,084 within 0.1%, which shows the
Network's own average uses the same ratio, but that confirms the method is
shared, not that it is right. Worth settling before the next release.


### Fixes made to the delivered generator
The bundle shipped with several faults that only appear once it is driven by
live data. All are fixed:

| Fault | Effect | Fix |
|---|---|---|
| `assets/` folder absent | `build.py` crashed on the missing brand marks | Marks traced from the official logo |
| Account bars drew black | The chart emitted `class="col"`, which the stylesheet never defined | Restored the `bar` / `bar last` classes the CSS styles |
| Axis scales hard-coded at 640B, 20M and $40k | A future edition would overflow the plot silently. Assets are already $603B | Scales hold the published look while the data fits, then grow in clean steps |
| Caption hard-coded "the two periods ... in both cases" | Wrong for every edition with one dip or none | Caption is derived from the annotations actually drawn, and recovery is only claimed when the series shows it |
| Average-account panel styled but never rendered | The figures were computed and dropped | Panel restored to the layout |
| Only three points carried value labels | Far sparser than the published sheet | Every point on both charts is labelled, with annotated years and the endpoint emphasised |

### Layout faults found by driving the generator across editions
The first live run exposed overflow bugs that the single hand-authored JSON
never triggered. All are fixed and verified by measuring rendered bounding
boxes rather than by eye:

| Fault | Cause | Fix |
|---|---|---|
| Accounts hero clipped to "17.93N" | Hero began at x=466 in a 560-wide viewBox; the label needs ~96px | Plot narrowed, hero moved to x=452 |
| Left axis read "1" instead of "10" | The first bar is centred on the axis and covered the label's last digit | Axis labels moved clear of the bar |
| Left axis title read "NTS, M" | "accounts, M" was anchored at its right edge, running off canvas | Anchored from the left margin instead |
| Right axis values sat on the hero text | Both occupied the same band | Right labels pulled in, hero moved left |
| Average-account values overlapped the arrow | Flex columns shrank below their text | Columns fixed to content, shorter date, smaller face |
| "Plans reporting" and "Compare plans" wrapped | Panels too narrow for their titles | Row rebalanced, titles set to not wrap |
| Deck lost its last line | The head flex-shrank under the taller panel row | Head no longer shrinks |

Verified across eight editions: no SVG text outside its viewBox, no horizontal
overflow in any panel, deck clear of the head by 24px, and the page exactly
1056px tall. The only element that overflows is the decorative watermark, which
is clipped deliberately.

### Layout check
`python infographic/check_layout.py` renders nine editions and asserts, by
measuring bounding boxes in the browser rather than by eye, that no text sits
outside its viewBox, no axis label is hidden behind a bar or running into the
hero, the page is exactly 1056px, and the footer fits. Run it after touching
the template or the chart geometry. Every assertion in it corresponds to a bug
that shipped once.

One worth calling out: bars are centred on the axis end points, so the first
and last bar each extend half a bar width past the plot edge. Axis labels have
to clear `bw/2`, not a token few pixels. Getting this wrong on the left hid the
leading digit of the accounts axis; getting it wrong on the right hid the
leading digit of the balance axis.
