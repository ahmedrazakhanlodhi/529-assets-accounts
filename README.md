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
