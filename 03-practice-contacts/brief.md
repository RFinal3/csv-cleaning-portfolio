# CSV Practice Job #3 — Dental Practice Contact Lists

**Modeled on a real posting.** Upwork: "Excel expert needed to export data
from multiple excel spreadsheets" — consolidate multiple spreadsheets of
dental practice contacts, remove duplicates, and keep only complete
records (with valid email addresses). US client (Dallas), hourly, expert
level, time-sensitive ("ready by tomorrow"). Like Job #2, the real posting
had no data attached — clients describe the mess and share files privately
after hiring — so the files below are fake data modeled on the posting.

**How this job runs:** same as Job #2. Your agents do the cleaning pass,
you review and send, Kit grades. Nothing here goes to a real client.

**Difficulty:** same band as Job #2. Different shape, not harder: US data
instead of AU, two phone columns instead of one, and a combined address
field instead of split location columns.

## The files (159 rows total)

| File | Rows | What's different about it |
|---|---|---|
| `01_referral_list.csv` | 30 | Combined "Contact" name; some "Last, First"; dashed phones |
| `02_state_board.csv` | 34 | Split names; dotted phones; has a `Website` column to drop |
| `03_insurance_dir.csv` | 31 | ALL-CAPS file; phones with no separators |
| `04_conference.csv` | 33 | Combined names; parenthesised phones; has a `Notes` column to drop |
| `05_old_crm.csv` | 31 | Lowercase headers; `+1` phones; extra spaces; has a `Last Contact` column to drop |

## Master schema

`company, address, first_name, last_name, cell_phone, office_phone, email, source`

## Rules

- **Phones:** US format `(xxx) xxx-xxxx`. Strip `+1`; dots, dashes, spaces
  and bare digits all normalise to it. Office phones sometimes carry an
  extension — keep it as `xNN` after the number (e.g. `(214) 555-0123 x45`).
  `ext.`, `Ext` and `x` all mean the same thing.
- **Email:** lowercase, trimmed. A missing or invalid email is never guessed.
- **Names:** Title Case. Combined names split into first/last; `Last, First`
  forms handled.
- **Address:** one field, kept as `street, city, ST ZIP`. Street words Title
  Cased with abbreviations expanded (`St` → `Street`, `Ave` → `Avenue`,
  `Rd` → `Road`, `Blvd` → `Boulevard`, `Dr` → `Drive`, `Ste` → `Suite`,
  `Apt` → `Apartment`). City Title Case, state uppercase, ZIP preserved
  exactly as text — including leading zeros (Boston `02108`, Newark `07102`).
- **Placeholders** (`N/A`, `null`, `-`, `TBD`, `unknown`) mean blank. Never
  invent a value.
- **Dedupe:** normalised email = the same contact. Merge copies, filling
  blanks from whichever copy has the value.
- **Shared inboxes (stated up front, Job #1's lesson):** if the same email
  belongs to people with a different name AND different phones, they are
  distinct people sharing an inbox — keep both rows, don't merge them.
- **Review, don't guess:** a row goes to the review file (with a reason) if
  it has no name at all, no email, an invalid email, or an invalid phone
  (cell or office). A blank phone is kept blank in the master — blank is
  not invalid.
- **Company completeness is judged AFTER merging:** a contact goes to
  review for a missing company only if NO copy of it has a company. If one
  copy has it, the merged row keeps it.
- **Dropped columns:** `Website` (state board), `Notes` (conference) and
  `Last Contact` (old CRM) are outside the master schema — leave them out
  and list them in the summary.
- **Deleted outright:** fully blank rows and obvious test rows.
- **Source:** the file (or files) the record came from. Any file it appears
  in is acceptable.

## Deliverables

1. `master.csv` — one clean master file in the schema above.
2. `review.csv` — flagged rows in the same layout, plus a `reason` column.
3. `summary.txt` — per-file row counts, what was merged/removed/reviewed,
   dropped columns, and a reconciliation (input = master + review + removed).
