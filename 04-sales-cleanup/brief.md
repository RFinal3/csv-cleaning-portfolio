# CSV Practice Job #4 — E-Commerce Sales Export Cleanup (the hard one)

**Modeled on a real listing pattern.** Upwork sellers offering Shopify /
Etsy / POS sales-export cleanup describe the same job: duplicate order
rows across systems, mixed date standards, text where numbers should be,
and ambiguous records quarantined into a review file — never deleted.
This job is deliberately a step up from Jobs #2 and #3: the numbers have
to be *parsed and reconciled*, not just reformatted, and duplicates hide
behind different order IDs.

**How this job runs:** same as Jobs #2/#3. Your agents do the cleaning
pass, you review and send, Kit grades. Nothing here goes to a real client.

**Difficulty:** pretty hard. Bigger file (288 rows), more judgment calls,
and a checkable money total at the end. Expect the review file to be
bigger than last time — that's the job working as intended.

## The files (288 rows total)

| File | Rows | What's different about it |
|---|---|---|
| `01_shopify_export.csv` | 123 | Combined customer names; ISO dates; `$1,234.56` prices |
| `02_pos_export.csv` | 85 | Split names; `DD/MM/YYYY` dates; plain prices; has a `Total` column and a `Store` column to drop |
| `03_manual_orders.csv` | 80 | ALL-CAPS file; month-name dates; European decimal prices (`1.234,56`); includes a repeated header, a totals row, and blank lines |

## Master schema

`order_id, customer_first, customer_last, customer_email, customer_phone, sku, product, qty, unit_price, line_total, order_date, status, source`

## Rules — read all of these before starting

### Dates → ISO `YYYY-MM-DD`

- Slash dates are **day-first, always**: this is an Australian business,
  so `03/04/2026` is 4 March 2026, not April 3. (The "US vs UK" ambiguity
  is the trap in this job — the brief settles it: day-first.)
- ISO dates (`2026-03-15`) pass through. Month-name dates (`15 Mar 2026`,
  `Mar 15, 2026`) are accepted.
- An impossible date (30 February, month 13, day 32) goes to review as
  `date invalid`. A blank date goes to review as `date missing`.

### Money → plain number, 2 decimals, no symbols

- Strip `$`, `AUD`, `USD`.
- When both `.` and `,` appear, the **last** one is the decimal:
  `1,234.56` → `1234.56`, and `1.234,56` → `1234.56`.
- A single comma with exactly 2 digits after it is a decimal comma:
  `45,00` → `45.00`. Any other comma is a thousands separator.
- Unparseable prices go to review as `price invalid`; blank prices as
  `price missing`. Never invent a price.

### The line itself

- `line_total = qty × unit_price`, to 2 decimals.
- **POS Total check:** where the POS file has a `Total` column, it must
  agree with `qty × unit_price` within 1 cent. If it doesn't, the line
  goes to review as `total mismatch` — don't silently "fix" the total.
- `qty` is an integer. A **negative qty is a return**: keep it, with a
  negative `line_total`. Zero or non-numeric qty goes to review.
- `sku` is canonical `AAA-9999`, uppercase with a hyphen (`abc1234` →
  `ABC-1234`). Blank → review (`SKU missing`); anything that doesn't fit
  the pattern → review (`invalid SKU`).
- `status` is kept as `completed` or `pending`. **Cancelled and refunded
  lines are removed outright** — counted in the summary, not reviewed,
  because they aren't sales.
- Names: Title Case; combined names split; `Last, First` handled. Email:
  lowercase, never guessed. Phone: Australian `04xx xxx xxx` (`+61`/`61`
  converted); if a phone doesn't parse, carry it as-is — phones are
  **never** a review trigger in this job. Product: Title Case.

### Dedupe — two different kinds

1. **Same order, same item** (same `order_id` + `sku`): identical copies
   collapse to one row. If the copies disagree on qty or price, the
   whole group goes to review as `order conflict` — you can't tell which
   copy is right.
2. **Same purchase, different order ID** (same customer email + date +
   sku + total, but different `order_id` — the same sale recorded by two
   systems): keep the first in file order (`01` → `02` → `03`) and list
   the dropped order ID in the summary.

### Two group checks (lines that fail these go to review, whole groups)

- **Product check:** one SKU with two different product names → all
  those lines to review as `product mismatch`.
- **Customer check:** the same phone + last name with different emails →
  those lines to review as `possible duplicate customer`. (Same person
  with two emails, or two people sharing a phone — you can't tell, so
  flag it.)

### Junk — deleted outright

Blank rows, repeated header rows, `TOTAL` summary rows, and obvious test
rows.

### Source and summary

- **Source:** the file (or files) the record came from. Any file it
  appears in is acceptable.
- The summary must include per-file row counts, a reconciliation
  (input = master + review + removed), the cancelled/refunded counts,
  the dropped cross-system order IDs, **and the master revenue total**
  (the sum of all `line_total` values, returns included). That total is
  checkable — it has to tie to the file.

## Deliverables

1. `master.csv` — one clean master file in the schema above.
2. `review.csv` — flagged rows in the same layout, plus a `reason` column.
3. `summary.txt` — counts, reconciliation, dropped order IDs, and the
   master revenue total.
