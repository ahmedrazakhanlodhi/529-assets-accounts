# Assets & Accounts | The 529 Network

A member dashboard on the full 529 record, 2001Q4 to 2025Q4. Built on four
reported fields: state, plan name, assets, and open accounts. Plan type is
derived from the plan name. No fund manager names.

## What changed in this version
- 2022 added. It was the only gap in the master.
- Source: the four CSPN website workbooks (3/31, 6/30, 9/30, 12/31 2022).
- Reconciled to each file's own National totals row: zero difference in
  assets and accounts, all four quarters.
- Plan names and states taken from the master's 2021Q4 and 2023Q1 rosters,
  so no new naming was introduced. All 112 matched.
- Tennessee BEST Prepaid and West Virginia Prepaid closed 3Q 2021 and
  correctly carry no 2022 rows.

## Two findings, surfaced in the Coverage tab
1. **2023Q1 repeats 2022Q4.** With 2022 loaded, all 111 plans report identical
   assets and accounts in both periods. No other consecutive pair in 24 years
   does this. The 12/31/2022 workbook's internal title reads "Reporting date:
   March 31," so the year-end file was likely ingested twice. 2022 reconciles
   to source exactly, which points at 2023Q1 as the suspect period.
2. **Alabama PACT 2022Q1** reports $76.1M against $232M to $257M in the other
   three quarters, with accounts nearly flat. Kept as reported, flagged.

Neither was silently corrected.

## Sections
National · Map · States · Plans · Compare · Change · Coverage ·
Data & Downloads · About

## Data
`data/529_data.csv`: `Year, Period, Date, State, PlanName, Accounts, AUM, Note`

Rows with a Note and no figures are closed or non-operational plans. They appear
in Coverage and are excluded from every total.

Reporting is quarterly from 2021 and annual or semiannual before that, so the
timeline is not evenly spaced. Year over year views appear only where the same
quarter exists one year earlier.

## Deploy (Streamlit Community Cloud)
Push to GitHub, point a new app at `app.py`. `runtime.txt` pins Python 3.12 and
`requirements.txt` pins every version, which protects against platform-side
Python regressions.
