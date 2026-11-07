#!/usr/bin/env python3
"""
clean_job4.py - test-job-4 e-commerce sales export cleanup.

Reads the 3 source CSVs (read-only) and writes:
    master.csv   - cleaned sales lines in the master schema
    review.csv   - flagged lines, each with a reason
    summary.txt  - counts, reconciliation, dropped order IDs, revenue total

Master schema:
  order_id, customer_first, customer_last, customer_email, customer_phone,
  sku, product, qty, unit_price, line_total, order_date, status, source

Rules (brief.md is the source of truth):
  * Dates -> ISO YYYY-MM-DD. Slash dates are DAY-FIRST always.
             Impossible -> review 'date invalid'; blank -> 'date missing'.
  * Money -> plain 2dp. Strip $/AUD/USD. When both . and , appear the LAST
             is the decimal. A single comma with exactly 2 digits after is a
             decimal comma. Unparseable -> 'price invalid'; blank -> missing.
  * line_total = qty x unit_price.
  * POS Total check: must agree with qty x unit_price within 1 cent, else
             'total mismatch'. Never silently fix.
  * qty integer; negative = return (kept, negative line_total); zero or
             non-numeric -> review.
  * sku canonical AAA-9999. Blank -> 'SKU missing'; wrong shape -> 'invalid SKU'.
  * status kept as completed/pending. Cancelled + refunded REMOVED outright
             (counted, not reviewed).
  * Phones are NEVER a review trigger in this job - carried as text.
  * Dedupe 1: same order_id + sku -> collapse identical copies; if the copies
             disagree on qty or price the whole group -> 'order conflict'.
  * Dedupe 2: same email + date + sku + total with different order_id -> keep
             the first in file order (01 -> 02 -> 03); list the dropped ID.
  * Product check: one SKU with two product names -> all those lines ->
             'product mismatch'.
  * Customer check: same phone + last name with different emails -> those
             lines -> 'possible duplicate customer'.
  * Junk deleted: blank rows, repeated headers, TOTAL rows, test rows.

ASSUMPTION (flagged to client): "returns included" in the revenue total is
read as negative-quantity lines, not status=refunded lines (which are removed
outright per the brief).

SAFETY RULE: an unrecognised source column stops the job.
"""

import csv
import glob
import os
import re
import sys
from collections import OrderedDict, defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

DEFAULT_SRC = "inputs"
DEFAULT_OUT = "run-output"

SRC_DIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
OUT_DIR = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT

MASTER_COLS = ["order_id", "customer_first", "customer_last", "customer_email",
               "customer_phone", "sku", "product", "qty", "unit_price",
               "line_total", "order_date", "status", "source"]

KNOWN_HEADERS = {
    "Order ID", "Order #", "ORDER", "order_id",
    "Customer Name", "Full Name", "NAME", "name",
    "First Name", "Last Name",
    "Email", "EMAIL", "email",
    "Phone", "PHONE", "phone",
    "SKU", "sku",
    "Product", "Item", "PRODUCT", "product",
    "Quantity", "Qty", "QTY",
    "Unit Price", "Price", "PRICE",
    "Total", "Store",
    "Order Date", "Date", "DATE",
    "Status", "STATUS",
    "Website", "Notes", "Last Contact",
}

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

TEST_EMAILS = {"test@test.com", "asdf@asdf.com"}
TEST_NAMES = {"test user", "asdf asdf"}

LOWER_WORDS = {"and", "of", "the", "a", "an", "in", "on", "at", "for", "to"}


# ------------------------------------------------------------------ helpers

def clean_text(raw):
    if raw is None:
        return ""
    return " ".join(raw.split())


def title_case(value):
    if not value:
        return ""
    words = value.split()
    out = []
    for i, word in enumerate(words):
        low = word.lower()
        if i > 0 and low in LOWER_WORDS:
            out.append(low)
        elif word == "&":
            out.append("&")
        else:
            out.append(word[:1].upper() + word[1:].lower())
    return " ".join(out)


def split_name(combined):
    value = clean_text(combined)
    if not value:
        return "", ""
    if "," in value:
        last, _, first = value.partition(",")
        return title_case(first.strip()), title_case(last.strip())
    parts = value.split()
    if len(parts) == 1:
        return title_case(parts[0]), ""
    return title_case(parts[0]), title_case(" ".join(parts[1:]))


def parse_date(raw):
    """Return (iso, status). status = ok | blank | invalid. Day-first for slashes."""
    value = clean_text(raw)
    if not value:
        return "", "blank"

    # ISO YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", value)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d).isoformat(), "ok"
        except ValueError:
            return value, "invalid"

    # DD/MM/YYYY  (day-first, always)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", value)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d).isoformat(), "ok"
        except ValueError:
            return value, "invalid"

    # 'OCT 12, 2026' / 'MAR 15 2026'
    m = re.match(r"^([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})$", value)
    if m:
        mon = MONTHS.get(m.group(1)[:4].lower()) or MONTHS.get(m.group(1)[:3].lower())
        d, y = int(m.group(2)), int(m.group(3))
        if mon:
            try:
                return date(y, mon, d).isoformat(), "ok"
            except ValueError:
                return value, "invalid"
        return value, "invalid"

    # '03 JUL 2026' / '15 Mar 2026'
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{4})$", value)
    if m:
        d = int(m.group(1))
        mon = MONTHS.get(m.group(2)[:4].lower()) or MONTHS.get(m.group(2)[:3].lower())
        y = int(m.group(3))
        if mon:
            try:
                return date(y, mon, d).isoformat(), "ok"
            except ValueError:
                return value, "invalid"
        return value, "invalid"

    return value, "invalid"


def parse_money(raw):
    """Return (Decimal or None, status). status = ok | blank | invalid."""
    value = clean_text(raw)
    if not value:
        return None, "blank"
    if value.lower() in {"n/a", "null", "-", "tbd", "unknown"}:
        return None, "blank"

    v = value.replace("$", "").replace("AUD", "").replace("USD", "").strip()
    v = v.replace(" ", "")
    if not v or not re.search(r"\d", v):
        return None, "invalid"

    has_dot, has_comma = "." in v, "," in v
    if has_dot and has_comma:
        # The LAST separator is the decimal point.
        if v.rfind(".") > v.rfind(","):
            v = v.replace(",", "")
        else:
            v = v.replace(".", "").replace(",", ".")
    elif has_comma:
        after = v.split(",")[-1]
        if len(after) == 2 and v.count(",") == 1:
            v = v.replace(",", ".")
        else:
            v = v.replace(",", "")
    if not re.match(r"^-?\d+(\.\d+)?$", v):
        return None, "invalid"
    try:
        return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "ok"
    except Exception:
        return None, "invalid"


def parse_qty(raw):
    """Return (int or None, status)."""
    value = clean_text(raw)
    if not value:
        return None, "blank"
    v = value.replace(",", "")
    if not re.match(r"^-?\d+$", v):
        return None, "invalid"
    n = int(v)
    if n == 0:
        return None, "zero"
    return n, "ok"


def normalise_sku(raw):
    """Return (sku, status). status = ok | blank | invalid."""
    value = clean_text(raw).upper().replace(" ", "")
    if not value:
        return "", "blank"
    m = re.match(r"^([A-Z]+)-?(\d{4})$", value)
    if not m:
        return clean_text(raw), "invalid"
    return f"{m.group(1)}-{m.group(2)}", "ok"


def normalise_phone(raw):
    """Never a review trigger. Best-effort AU format, else carried as text."""
    value = clean_text(raw)
    if not value or value.lower() in {"n/a", "null", "-", "tbd", "unknown"}:
        return ""
    digits = re.sub(r"\D", "", value)
    if digits.startswith("61") and len(digits) == 11:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("04"):
        return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    return value


def normalise_email(raw):
    """Return (email, status). status = ok | blank | invalid.

    Emails ARE a review trigger in this job (the brief exempts phones only).
    """
    value = clean_text(raw).lower()
    if not value or value in {"n/a", "null", "-", "tbd", "unknown"}:
        return "", "blank"
    if " " in value or value.count("@") != 1:
        return value, "invalid"
    local, _, domain = value.partition("@")
    if not local or not domain or "." not in domain:
        return value, "invalid"
    if domain.startswith(".") or domain.endswith("."):
        return value, "invalid"
    return value, "ok"


def build_reader(headers, fname):
    idx = {h.strip(): i for i, h in enumerate(headers)}
    unknown = [h for h in idx if h not in KNOWN_HEADERS]
    if unknown:
        sys.exit(
            f"STOP: {fname} has unrecognised column(s): {unknown}\n"
            "Refusing to run rather than silently drop data.\n"
            "Add them to KNOWN_HEADERS and build_reader's get() calls first."
        )

    def get(row, *names):
        for name in names:
            if name in idx:
                i = idx[name]
                return row[i] if i < len(row) else ""
        return ""

    def read(row):
        return {
            "order_id": get(row, "Order ID", "Order #", "ORDER", "order_id"),
            "full_name": get(row, "Customer Name", "Full Name", "NAME", "name"),
            "first": get(row, "First Name"),
            "last": get(row, "Last Name"),
            "email": get(row, "Email", "EMAIL", "email"),
            "phone": get(row, "Phone", "PHONE", "phone"),
            "sku": get(row, "SKU", "sku"),
            "product": get(row, "Product", "Item", "PRODUCT", "product"),
            "qty": get(row, "Quantity", "Qty", "QTY"),
            "price": get(row, "Unit Price", "Price", "PRICE"),
            "total": get(row, "Total"),
            "order_date": get(row, "Order Date", "Date", "DATE"),
            "status": get(row, "Status", "STATUS"),
            "store": get(row, "Store"),
        }

    return read


# ------------------------------------------------------------------ main

def main():
    sources = sorted(glob.glob(os.path.join(SRC_DIR, "*.csv")))
    sources = [p for p in sources if re.match(r"^\d\d_", os.path.basename(p))]
    if not sources:
        sys.exit(f"No source files matching NN_*.csv found in {SRC_DIR}")

    lines = []
    counts = OrderedDict()
    removed = {"blank": [], "header": [], "total": [], "cancelled": [], "refunded": [], "test": []}
    dropped_cols = {"Store": [], "Total": []}

    for path in sources:
        fname = os.path.basename(path)
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
        if not rows:
            counts[fname] = 0
            continue

        headers = [h.strip() for h in rows[0]]
        reader = build_reader(headers, fname)
        data = rows[1:]
        counts[fname] = len(data)

        for col in dropped_cols:
            if col in headers:
                i = headers.index(col)
                n = sum(1 for r in data if i < len(r) and r[i].strip())
                dropped_cols[col].append((fname, n, len(data)))

        for offset, row in enumerate(data, start=2):
            ref = f"{fname}:{offset}"

            if not any(c.strip() for c in row):
                removed["blank"].append(ref)
                continue

            first_cell = clean_text(row[0]).upper() if row else ""
            if first_cell in ("ORDER", "ORDER ID", "ORDER #"):
                removed["header"].append(ref)
                continue
            if first_cell.startswith("TOTAL"):
                removed["total"].append(ref)
                continue

            fields = reader(row)

            if fields["full_name"].strip():
                first, last = split_name(fields["full_name"])
            else:
                first = title_case(clean_text(fields["first"]))
                last = title_case(clean_text(fields["last"]))

            email, email_status = normalise_email(fields["email"])
            if email in TEST_EMAILS or f"{first} {last}".strip().lower() in TEST_NAMES:
                removed["test"].append(f"{ref} ({first} {last})")
                continue

            status = clean_text(fields["status"]).lower()
            if status == "cancelled":
                removed["cancelled"].append(ref)
                continue
            if status == "refunded":
                removed["refunded"].append(ref)
                continue

            sku, sku_status = normalise_sku(fields["sku"])
            price, price_status = parse_money(fields["price"])
            qty, qty_status = parse_qty(fields["qty"])
            iso, date_status = parse_date(fields["order_date"])
            pos_total, pos_status = parse_money(fields["total"])

            rec = {
                "order_id": clean_text(fields["order_id"]),
                "customer_first": first,
                "customer_last": last,
                "customer_email": email,
                "customer_phone": normalise_phone(fields["phone"]),
                "sku": sku,
                "product": title_case(clean_text(fields["product"])),
                "qty": qty,
                "unit_price": price,
                "line_total": (qty * price) if (qty is not None and price is not None) else None,
                "order_date": iso,
                "status": status,
                "source": fname,
                "_line": offset,
                "_sku_status": sku_status,
                "_price_status": price_status,
                "_qty_status": qty_status,
                "_date_status": date_status,
                "_pos_total": pos_total,
                "_pos_status": pos_status,
                "_raw_price": clean_text(fields["price"]),
                "_raw_qty": clean_text(fields["qty"]),
                "_raw_date": clean_text(fields["order_date"]),
                "_raw_sku": clean_text(fields["sku"]),
                "_email_status": email_status,
            }
            lines.append(rec)

    # ------------------------------------------------------- dedupe 1: same order+sku
    groups = OrderedDict()
    for rec in lines:
        key = (rec["order_id"], rec["sku"])
        groups.setdefault(key, []).append(rec)

    review_reasons = defaultdict(list)   # id(rec) -> [reasons]
    conflicts_reported = []
    genuine_conflicts = []
    collapsed_copies = []

    collapsed = []
    for key, group in groups.items():
        # Compare PARSED values, not raw strings: '$21.99' in Shopify and
        # '21,99' in the manual file are the same figure and must collapse.
        sigs = {(r["qty"], r["unit_price"], r["order_date"], r["product"])
                for r in group}
        if len(group) > 1 and len(sigs) > 1:
            for r in group:
                review_reasons[id(r)].append("order conflict")
            conflicts_reported.append(
                f"{key[0]} / {key[1]}: {len(group)} copies disagree "
                f"({group[0]['source']} vs " +
                ", ".join(sorted({g['source'] for g in group[1:]})) + ")")
            # keep the two categories apart - only these are real conflicts
            genuine_conflicts.append(conflicts_reported[-1])
            collapsed.extend(group)
        else:
            collapsed.append(group[0])
            if len(group) > 1:
                abandoned = [g["source"] for g in group[1:]]
                collapsed_copies.append(
                    f"{key[0]} / {key[1]}: {len(group)-1} identical duplicate copy "
                    f"collapsed (kept {group[0]['source']})")

    lines = collapsed

    # --------------------------------------------- per-line validity reasons
    for rec in lines:
        if rec["_email_status"] == "blank":
            review_reasons[id(rec)].append("email missing")
        elif rec["_email_status"] == "invalid":
            review_reasons[id(rec)].append("email invalid")
        if rec["_sku_status"] == "blank":
            review_reasons[id(rec)].append("SKU missing")
        elif rec["_sku_status"] == "invalid":
            review_reasons[id(rec)].append("invalid SKU")
        if rec["_price_status"] == "blank":
            review_reasons[id(rec)].append("price missing")
        elif rec["_price_status"] == "invalid":
            review_reasons[id(rec)].append("price invalid")
        if rec["_qty_status"] in ("zero", "invalid", "blank"):
            review_reasons[id(rec)].append("qty invalid")
        if rec["_date_status"] == "blank":
            review_reasons[id(rec)].append("date missing")
        elif rec["_date_status"] == "invalid":
            review_reasons[id(rec)].append("date invalid")
        if rec["_pos_status"] == "ok" and rec["line_total"] is not None and rec["_pos_total"] is not None:
            if abs(rec["_pos_total"] - rec["line_total"]) > Decimal("0.01"):
                review_reasons[id(rec)].append("total mismatch")

    # ------------------------------------------------ product check (by SKU)
    sku_products = defaultdict(set)
    for rec in lines:
        if rec["_sku_status"] == "ok" and rec["product"]:
            sku_products[rec["sku"]].add(rec["product"])
    bad_skus = {sku for sku, prods in sku_products.items() if len(prods) > 1}
    for rec in lines:
        if rec["sku"] in bad_skus:
            review_reasons[id(rec)].append("product mismatch")

    # ------------------------------------------------ customer check
    phone_last = defaultdict(set)
    for rec in lines:
        digits = re.sub(r"\D", "", rec["customer_phone"])
        if digits and rec["customer_last"]:
            key = (digits, rec["customer_last"].lower())
            if rec["customer_email"]:
                phone_last[key].add(rec["customer_email"])
    bad_cust = {k for k, emails in phone_last.items() if len(emails) > 1}
    for rec in lines:
        digits = re.sub(r"\D", "", rec["customer_phone"])
        if digits and (digits, rec["customer_last"].lower()) in bad_cust:
            review_reasons[id(rec)].append("possible duplicate customer")

    # ------------------------------------- split into review vs candidates
    review, candidates = [], []
    for rec in lines:
        reasons = review_reasons.get(id(rec), [])
        if reasons:
            review.append((rec, "; ".join(dict.fromkeys(reasons))))
        else:
            candidates.append(rec)

    # --------------------------- dedupe 2: same purchase, different order id
    # Group first so the report counts GROUPS, not individual drop events: a
    # purchase recorded in all three files is one match, not two. (Client check
    # caught this - the summary said seven when the files contain eight.)
    by_purchase = OrderedDict()
    cross_system_count = 0
    for rec in candidates:
        key = (rec["customer_email"], rec["order_date"], rec["sku"],
               str(rec["line_total"]))
        by_purchase.setdefault(key, []).append(rec)

    master = []
    dropped_ids = []
    for key, group in by_purchase.items():
        kept = group[0]
        master.append(kept)
        if len(group) > 1:
            ids = {g["order_id"] for g in group}
            others = [f"{g['order_id']} ({g['source']})" for g in group[1:]]
            cross = "cross-system" if len(ids) > 1 else "same id"
            dropped_ids.append(
                f"kept {kept['order_id']} ({kept['source']}); dropped "
                + ", ".join(others) + f" [{cross}]")
            for g in group[1:]:
                if g["order_id"] != kept["order_id"]:
                    cross_system_count += 1

    # ------------------------------------------------------------ output
    os.makedirs(OUT_DIR, exist_ok=True)

    def fmt(rec, key):
        v = rec.get(key)
        if key in ("unit_price", "line_total"):
            return "" if v is None else f"{v:.2f}"
        if key == "qty":
            return "" if v is None else str(v)
        return "" if v is None else str(v)

    def write_row(w, rec, extra=None):
        row = {k: fmt(rec, k) for k in MASTER_COLS}
        if extra is not None:
            row["reason"] = extra
        w.writerow(row)

    with open(os.path.join(OUT_DIR, "master.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MASTER_COLS)
        w.writeheader()
        for rec in master:
            write_row(w, rec)

    with open(os.path.join(OUT_DIR, "review.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MASTER_COLS + ["reason"])
        w.writeheader()
        for rec, reason in review:
            write_row(w, rec, reason)

    revenue = sum((r["line_total"] for r in master if r["line_total"] is not None),
                  Decimal("0"))
    review_revenue = sum((r["line_total"] for r, _ in review if r["line_total"] is not None),
                         Decimal("0"))
    returns = [r for r in master if r["qty"] is not None and r["qty"] < 0]

    total_in = sum(counts.values())
    removed_n = {k: len(v) for k, v in removed.items()}
    out_n = len(master) + len(review)
    reconciled = total_in - sum(removed_n.values())

    txt = []
    txt.append("test-job-4 - e-commerce sales export cleanup")
    txt.append("=" * 62)
    txt.append("")
    txt.append("ROW COUNTS")
    for fname, n in counts.items():
        txt.append(f"  {fname:<26} {n:>4} rows in")
    txt.append(f"  {'TOTAL IN':<26} {total_in:>4}")
    txt.append("")
    txt.append("REMOVED OUTRIGHT (not reviewed)")
    txt.append(f"  cancelled lines            {removed_n['cancelled']:>4}")
    txt.append(f"  refunded lines             {removed_n['refunded']:>4}")
    txt.append(f"  blank rows                 {removed_n['blank']:>4}")
    txt.append(f"  repeated header rows       {removed_n['header']:>4}")
    txt.append(f"  TOTAL summary rows         {removed_n['total']:>4}")
    txt.append(f"  obvious test rows          {removed_n['test']:>4}")
    txt.append(f"  {'TOTAL REMOVED':<26} {sum(removed_n.values()):>4}")
    txt.append("")
    txt.append(f"  master rows                {len(master):>4}")
    txt.append(f"  review rows                {len(review):>4}")
    txt.append("")
    txt.append(f"  RECONCILIATION: {total_in} in - {sum(removed_n.values())} removed "
               f"- {reconciled - out_n} deduped = {out_n} out "
               f"({len(master)} master + {len(review)} review)")
    txt.append("")
    txt.append(f"CROSS-SYSTEM MATCHES ({cross_system_count} purchases recorded under "
               f"different order IDs; first in file order kept)")
    if dropped_ids:
        for d in dropped_ids:
            txt.append(f"  {d}")
    else:
        txt.append("  none")
    txt.append("")
    txt.append(f"ORDER CONFLICTS ({len(genuine_conflicts)} - same order + item, "
               f"different qty or price; whole group to review)")
    if genuine_conflicts:
        for c in genuine_conflicts:
            txt.append(f"  {c}")
    else:
        txt.append("  none")
    txt.append("")
    txt.append(f"IDENTICAL DUPLICATE COPIES ({len(collapsed_copies)} - same data, "
               f"collapsed silently, not reviewed)")
    if collapsed_copies:
        for c in collapsed_copies:
            txt.append(f"  {c}")
    else:
        txt.append("  none")
    txt.append("")
    txt.append("PRODUCT MISMATCH (one SKU, more than one product name)")
    if bad_skus:
        for s in sorted(bad_skus):
            txt.append(f"  {s}: " + " | ".join(sorted(sku_products[s])))
    else:
        txt.append("  none")
    txt.append("")
    txt.append("POSSIBLE DUPLICATE CUSTOMERS (same phone + last name, different emails)")
    if bad_cust:
        for digits, lastname in sorted(bad_cust):
            txt.append(f"  {lastname.title()} / {digits}: " +
                       ", ".join(sorted(phone_last[(digits, lastname)])))
    else:
        txt.append("  none")
    txt.append("")
    txt.append("REVENUE")
    txt.append(f"  master revenue total       ${revenue:>12,.2f}")
    txt.append(f"  (review lines totalled     ${review_revenue:>12,.2f} - excluded)")
    txt.append(f"  lines with negative qty    {len(returns):>4} (returns, included above)")
    txt.append("")
    txt.append("COLUMNS OMITTED (outside the master schema)")
    for col, found in dropped_cols.items():
        if not found:
            txt.append(f"  {col:<10} (not present)")
            continue
        for fname, populated, total in found:
            txt.append(f"  {col:<10} in {fname:<26} {populated}/{total} populated - omitted")
    txt.append("")
    txt.append("ASSUMPTIONS FLAGGED TO THE CLIENT")
    txt.append("  1. Returns vs refunds, for the revenue figure. The brief removes")
    txt.append("     status=refunded/cancelled lines outright, and says the revenue")
    txt.append("     total includes returns. Read here as: negative-quantity lines")
    txt.append("     are returns and ARE counted; refunded/cancelled status lines are")
    txt.append("     removed and are NOT counted. Confirm this is what you want.")
    txt.append("  2. Phones are carried as-is where they don't parse - the brief")
    txt.append("     says they are never a review trigger in this job.")

    with open(os.path.join(OUT_DIR, "summary.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(txt) + "\n")

    print(f"Wrote to {OUT_DIR}")
    print(f"  rows in   : {total_in}")
    print(f"  master    : {len(master)}")
    print(f"  review    : {len(review)}")
    print(f"  removed   : {sum(removed_n.values())}")
    print(f"  revenue   : ${revenue:,.2f}")


if __name__ == "__main__":
    main()
