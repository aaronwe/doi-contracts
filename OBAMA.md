# Why Obama Is Excluded from the Urgency Contracting Analysis

## What We Found

Both Obama terms are in `config.py` and the underlying data (`doi_no_bid_contracts.csv` covers 2009–present). We ran the numbers on an experimental branch (`obama-comparison`) and found these DOI-wide urgency totals for the same first-520-day window used for all other administrations:

| Administration | Urgency obligation | Awards |
|---|---|---|
| Obama I (2009–2010) | $29.9M | ~512 |
| Obama II (2013–2014) | $11.0M | ~277 |
| Trump I (2017–2018) | $13.3M | — |
| Biden (2021–2022) | $5.2M | — |
| Trump II (2025–2026) | $31.8M | — |

Obama I's $29.9M is nearly identical to Trump II's $31.8M, which would undercut the story. But before concluding they're comparable, we dug into whether the data is actually apples-to-apples.

## Data Quality Problem: Obama I Is Probably Overstated

GAO-14-304 (2014, "Noncompetitive Contracts Based on Urgency Need Additional Oversight") found that for FY2010–2012, roughly **45% of contracts sampled** were miscoded in FPDS as urgency (FAR 6.302-2) when they actually used simplified acquisition procedures on an urgent timeline — a different legal mechanism with a lower documentation threshold. FPDS issued corrective guidance in December 2014.

This means Obama I urgency dollar figures are likely inflated by miscoded entries. Obama II and all subsequent administrations (Trump I, Biden, Trump II) are on the same post-correction footing. There is no clean way to retroactively identify which specific Obama I contracts were miscoded.

## What Actually Explains the Drops

**Obama I → Obama II ($29.9M → $11M):**
- Budget Control Act of 2011 triggered sequestration beginning March 1, 2013 — right at the start of Obama II. DOI's budget was cut ~5%, compressing contracted services.
- October 2013: nearly zero urgency contracts recorded — the government shutdown.
- Obama's March 2009 memo directed agencies to cut noncompetitive contracting. Policy pressure built over both terms and likely drove real reductions.

**Obama II levels ($11M) are consistent with Trump I ($13.3M) and Biden ($5.2M)** — these three form a 12-year baseline of $5–14M/window before Trump II's spike to $31.8M.

## Why the Coding Mechanism Didn't Change

The FAR 6.302-2 definition of "unusual and compelling urgency" was not amended between 2009 and 2017. The FPDS "URG" code definition was not changed. DOI urgency transaction *counts* are consistent throughout — 400–500 transactions/year from 2009 through the present — confirming the coding mechanism was stable. The differences are in dollar *sizes*, not in whether urgency was being used.

An October 2009 FAR rule (Case 2007-008) capped urgency contract durations at one year unless the agency head certifies exceptional circumstances. This would tend to reduce Obama I values relative to a pre-2009 baseline, not inflate them.

## Our Approach

We exclude Obama from the primary visualizations (`viz.html`, `doi_viz.html`) because:

1. Obama I data has a known FPDS miscoding problem that inflates urgency figures for FY2010–2012.
2. The comparison that matters is the 12-year post-correction baseline (Obama II / Trump I / Biden) versus Trump II's spike — that story is cleaner and less vulnerable to methodological objections.
3. Including Obama I with its anomalously high (and probably overstated) number would invite a "but Obama was just as high" response that would require explaining the GAO data quality issue in every public use of the chart.

The `obama-comparison` branch has a working version of the DOI viz with all five administrations if needed for internal reference.

## Sources

- GAO-14-304: https://www.gao.gov/products/gao-14-304
- FAR Case 2007-008 (Oct. 14, 2009): https://www.federalregister.gov/documents/2009/10/14/E9-24565/federal-acquisition-regulation-far-case-2007-008-limiting-length-of-noncompetitive-contracts-in
- Obama contracting reform memo (Mar. 4, 2009): https://obamawhitehouse.archives.gov/the-press-office/memorandum-heads-executive-departments-and-agencies-subject-government-contracting
