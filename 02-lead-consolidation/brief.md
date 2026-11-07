# Practice Job #2 — Lead list cleanup & consolidation

## The job (modeled on a real posting)

A client in Sydney, Australia posted on Upwork ("Excel Data Cleanup &
Consolidation", $170 fixed price, posted December 15, 2025, intermediate
level, 50+ proposals). They have **7 separate spreadsheets of lead contact
details, each in a different format with inconsistent columns**, and want
them cleaned, standardised, and consolidated into **one master spreadsheet**
that is easy to filter, sort, and use for CRM / outreach.

Scope, in the client's words:

- Review 7 files with different formats and data fields
- Standardise everything into one clean master spreadsheet
- Create a clear, logical column structure (Name, Email, Phone, Location,
  Role, Notes, Source, etc.)
- Clean messy data (duplicates, inconsistent formatting, blank fields
  where possible)
- De-duplicate contacts intelligently (the same leads appear across
  multiple files)
- Flag any missing or unclear data rather than guessing

Deliverables: 1 consolidated file with clear headings, plus notes
explaining any assumptions or issues found.

**Note:** that posting has since been filled (1 hire), so this is a
practice model built from it, not a live application. The 7 files below
are fake data built to match the posting's description.

## Your files

| File | Source | Its quirks |
| --- | --- | --- |
| 01_tradeshow.csv | trade show | Combined name, combined "City, ST" location, some "Last, First" names |
| 02_webinar.csv | webinar | Lowercase headers, "organisation", separate city/state, comments for notes |
| 03_crm_export.csv | CRM export | "Contact"/"Tel"/"Title" headers, extra Website column |
| 04_old_spreadsheet.csv | old spreadsheet | ALL-CAPS headers and values, full state names in location |
| 05_linkedin.csv | LinkedIn | "Position" for role, extra Lead Score column |
| 06_referrals.csv | referrals | No notes column, extra whitespace, lowercase companies |
| 07_event_list.csv | event list | Headers with no spaces, "City ST" location with no comma |

## Target master schema

`first_name, last_name, email, phone, company, role, city, state, notes, source`

## Rules

- **Phones:** Australian mobiles, formatted `04xx xxx xxx`. Convert
  international forms: `+61 4xx xxx xxx` and `614xxxxxxxxx` both become
  `04xx xxx xxx` (drop the 61, add the 0).
- **Emails:** lowercase, trimmed.
- **Names:** Title Case, trimmed. Combined names split on the first space
  (everything after it is the last name). Some combined names are written
  `Last, First` — flip those.
- **States:** 2-letter uppercase Australian codes (NSW, VIC, QLD, SA, WA,
  TAS, NT, ACT). Full state names map to their code.
- **Locations:** combined locations split into city + state. They appear
  as `City, ST`, `City, Full State Name`, and `City ST` (no comma).
- **Companies / roles:** Title Case, trimmed.
- **Placeholder junk:** `N/A`, `null`, `-`, `TBD`, `unknown` (and blanks)
  mean "no value". Normalise them to blank — never invent a replacement.
- **Columns outside the master schema** (Website, Lead Score) are dropped;
  list them in your summary.
- **Source:** the file the record came from. If a record appears in
  several files, name any one of them.
- **Dedupe:** same normalised email = same lead. Merge copies into one
  row, filling in any blank fields from the other copies.
- **Shared-inbox exception:** if rows share an email but have a different
  name AND a different phone, treat them as different people sharing an
  inbox — keep both rows. (You learned this one the hard way in Job #1;
  this time the rule is stated up front.)
- **Review file:** rows you cannot fix go to a separate review file with
  a reason, using the master columns. A row goes to review if: the name
  is missing, the email is missing, the email is invalid, or the phone
  is invalid. Fully blank rows and obvious test rows are deleted, not
  reviewed.
- **Never invent data.** If a value can't be settled from the files,
  flag it — don't guess it.
- **Row order** in the master file doesn't matter for grading.

## Deliverables (same as Job #1)

1. The consolidated master CSV
2. A review CSV with a reason per row
3. A short summary: row counts (in / clean / review / removed), what you
   dropped and why, any assumptions, and anything you'd flag to the client
   at the end (per your "before I finish this up…" rule)
