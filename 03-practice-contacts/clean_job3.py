#!/usr/bin/env python3
"""
clean_job3.py - test-job-3 dental practice contact consolidation.

Reads the 5 source CSVs (read-only) and writes:
    master.csv   - consolidated contacts in the master schema
    review.csv   - rows that cannot be resolved, each with a reason
    summary.txt  - counts, merges, drops, dropped columns, reconciliation

Master schema: company, address, first_name, last_name, cell_phone,
               office_phone, email, source

Rules (brief.md is the source of truth):
  * Phones  -> (xxx) xxx-xxxx. Strip +1; dots/dashes/spaces/bare digits all
               normalise. Extensions kept as 'xNN' ('ext.', 'Ext', 'x' all
               mean the same). Validity: 10 digits, area code not starting 0.
  * Email   -> lowercase, trimmed. Never guessed. Missing/invalid -> review.
  * Names   -> Title Case; combined split; 'Last, First' flipped.
  * Address -> 'street, city, ST ZIP'. Street words Title Cased with
               abbreviations expanded. ZIP preserved exactly as text
               (leading zeros matter).
  * Junk    -> N/A, null, -, TBD, unknown, blanks => blank.
  * Dedupe  -> normalised email = same contact; merge, filling blanks.
  * Shared inbox -> same email, different name AND different phones = two
               people; keep both.
  * Review  -> no name at all / no email / invalid email / invalid phone
               (cell or office). A BLANK phone is fine - blank is not invalid.
  * Company completeness judged AFTER merging.
               ASSUMPTION (owner-approved as the safer route): a contact with
               no company in ANY copy goes to review. The brief implies this
               ("judged AFTER merging") without listing it as a trigger.
  * Dropped columns: Website (02), Notes (04), Last Contact (05).
  * Deleted: fully blank rows and obvious test rows.

SAFETY RULE: an unrecognised source column stops the job, never silently
drops data.
"""

import csv
import glob
import os
import re
import sys
from collections import OrderedDict

DEFAULT_SRC = "inputs"
DEFAULT_OUT = "run-output"

SRC_DIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
OUT_DIR = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT

MASTER_COLS = ["company", "address", "first_name", "last_name",
               "cell_phone", "office_phone", "email", "source"]

KNOWN_HEADERS = {
    "Company", "COMPANY", "Company Name", "company", "Practice Name",
    "Address", "ADDRESS", "address", "Street Address",
    "Contact", "Full Name", "name",
    "First", "Last", "FIRST NAME", "LAST NAME",
    "Cell", "Cell Phone", "CELL PHONE", "cell", "Mobile",
    "Office", "Office Phone", "OFFICE PHONE", "office", "Phone",
    "Email", "EMAIL", "email",
    "Website", "Notes", "Last Contact",
}

JUNK = {"n/a", "na", "null", "none", "-", "--", "tbd", "unknown", ""}

TEST_EMAILS = {"test@test.com", "asdf@asdf.com"}
TEST_NAMES = {"test user", "asdf asdf"}

# Street abbreviation expansion. Keyed lowercase on the bare word (no period).
STREET_MAP = {
    "st": "Street", "street": "Street",
    "ave": "Avenue", "av": "Avenue", "avenue": "Avenue",
    "rd": "Road", "road": "Road",
    "blvd": "Boulevard", "boulevard": "Boulevard",
    "dr": "Drive", "drive": "Drive",
    "ste": "Suite", "suite": "Suite",
    "apt": "Apartment", "apartment": "Apartment",
    "ln": "Lane", "lane": "Lane",
    "ct": "Court", "court": "Court",
    "pl": "Place", "place": "Place",
    "ter": "Terrace", "terrace": "Terrace",
    "cir": "Circle", "circle": "Circle",
    "pkwy": "Parkway", "parkway": "Parkway",
    "hwy": "Highway", "highway": "Highway",
}

LOWER_WORDS = {"and", "of", "the", "a", "an", "in", "on", "at", "for", "to"}


def clean_text(raw):
    if raw is None:
        return ""
    value = " ".join(raw.split())          # collapses runs of whitespace
    if value.lower() in JUNK:
        return ""
    return value


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
        elif "-" in word and len(word) > 1:
            out.append("-".join(p[:1].upper() + p[1:].lower() for p in word.split("-") if p))
        elif "'" in word:
            out.append(word[:1].upper() + word[1:].lower())
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


def normalise_phone(raw):
    """Return (formatted, status) where status is 'ok' | 'blank' | 'invalid'."""
    value = clean_text(raw)
    if not value:
        return "", "blank"

    # Split off an extension: 'x86', 'ext. 91', 'Ext 96', 'x 45'
    ext = ""
    m = re.search(r"(?:ext\.?|x)\s*(\d+)\s*$", value, re.IGNORECASE)
    if m:
        ext = m.group(1)
        value = value[:m.start()].strip()

    digits = re.sub(r"\D", "", value)
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]

    if len(digits) != 10 or digits[0] in "01":
        return clean_text(raw), "invalid"

    formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if ext:
        formatted = f"{formatted} x{ext}"
    return formatted, "ok"


def normalise_email(raw):
    """Return (email, status) where status is 'ok' | 'blank' | 'invalid'."""
    value = clean_text(raw).lower()
    if not value:
        return "", "blank"
    if " " in value or value.count("@") != 1:
        return value, "invalid"
    local, _, domain = value.partition("@")
    if not local or not domain or "." not in domain:
        return value, "invalid"
    if domain.startswith(".") or domain.endswith("."):
        return value, "invalid"
    return value, "ok"


def format_street(street):
    """Title-case street words and expand abbreviations."""
    words = street.split()
    out = []
    for i, word in enumerate(words):
        bare = word.rstrip(".").lower()
        if bare in STREET_MAP:
            out.append(STREET_MAP[bare])
        elif word.isdigit():
            out.append(word)
        else:
            out.append(title_case(word) if not word.isupper() else title_case(word.lower()))
    return " ".join(out)


def normalise_address(raw):
    """'street, city, ST ZIP' with cleaned parts. Returns '' if unusable."""
    value = clean_text(raw)
    if not value:
        return ""
    parts = [p.strip() for p in value.split(",")]
    if len(parts) != 3:
        # Unexpected shape: return the collapsed original rather than guess.
        return value
    street, city, tail = parts
    tail = " ".join(tail.split())
    m = re.match(r"^([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)$", tail)
    if not m:
        return f"{format_street(street)}, {title_case(city)}, {tail}"
    state, zipcode = m.group(1).upper(), m.group(2)
    return f"{format_street(street)}, {title_case(city)}, {state} {zipcode}"


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
            "company": get(row, "Company", "COMPANY", "Company Name", "company",
                           "Practice Name"),
            "address": get(row, "Address", "ADDRESS", "address", "Street Address"),
            "full_name": get(row, "Contact", "Full Name", "name"),
            "first": get(row, "First", "FIRST NAME"),
            "last": get(row, "Last", "LAST NAME"),
            "cell": get(row, "Cell", "Cell Phone", "CELL PHONE", "cell", "Mobile"),
            "office": get(row, "Office", "Office Phone", "OFFICE PHONE", "office", "Phone"),
            "email": get(row, "Email", "EMAIL", "email"),
            "website": get(row, "Website"),
            "notes": get(row, "Notes"),
            "last_contact": get(row, "Last Contact"),
        }

    return read


def main():
    sources = sorted(glob.glob(os.path.join(SRC_DIR, "*.csv")))
    sources = [p for p in sources if re.match(r"^\d\d_", os.path.basename(p))]
    if not sources:
        sys.exit(f"No source files matching NN_*.csv found in {SRC_DIR}")

    records = []
    counts = OrderedDict()
    dropped = {"blank": [], "test": []}
    dropped_cols = {"Website": [], "Notes": [], "Last Contact": []}

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
            fields = reader(row)

            if not any(str(v).strip() for v in fields.values()):
                dropped["blank"].append(f"{fname}:{offset}")
                continue

            if fields["full_name"].strip():
                first, last = split_name(fields["full_name"])
            else:
                first = title_case(clean_text(fields["first"]))
                last = title_case(clean_text(fields["last"]))

            email, email_status = normalise_email(fields["email"])
            cell, cell_status = normalise_phone(fields["cell"])
            office, office_status = normalise_phone(fields["office"])

            rec = {
                "company": title_case(clean_text(fields["company"])),
                "address": normalise_address(fields["address"]),
                "first_name": first,
                "last_name": last,
                "cell_phone": cell,
                "office_phone": office,
                "email": email,
                "source": fname,
                "_line": offset,
                "_email_status": email_status,
                "_cell_status": cell_status,
                "_office_status": office_status,
            }

            name_l = f"{first} {last}".strip().lower()
            if email in TEST_EMAILS or name_l in TEST_NAMES:
                dropped["test"].append(f"{fname}:{offset} ({first} {last})")
                continue

            records.append(rec)

    # ------------------------------------------------------------ dedupe
    merged = OrderedDict()
    conflicts = []
    unkeyable = []

    for rec in records:
        if rec["_email_status"] == "ok":
            merged.setdefault(rec["email"], []).append(rec)
        else:
            unkeyable.append(rec)

    master, review = [], []

    def review_reasons(rec):
        """Review triggers from the brief, plus the approved company assumption."""
        reasons = []
        if not rec["first_name"] and not rec["last_name"]:
            reasons.append("name missing")
        if rec["_email_status"] == "blank":
            reasons.append("email missing")
        elif rec["_email_status"] == "invalid":
            reasons.append("email invalid")
        if rec["_cell_status"] == "invalid":
            reasons.append("cell phone invalid")
        if rec["_office_status"] == "invalid":
            reasons.append("office phone invalid")
        if not rec["company"]:
            reasons.append("company missing")
        return reasons

    for email, group in merged.items():
        identities = OrderedDict()
        for rec in group:
            sig = (f"{rec['first_name']} {rec['last_name']}".strip().lower(),
                   re.sub(r"\D", "", rec["cell_phone"]),
                   re.sub(r"\D", "", rec["office_phone"]))
            identities.setdefault(sig, []).append(rec)

        names = {sig[0] for sig in identities}
        phones = {(sig[1], sig[2]) for sig in identities}
        shared_inbox = len(names) > 1 and len(phones) > 1
        buckets = list(identities.values()) if shared_inbox else [group]

        for bucket in buckets:
            primary = dict(bucket[0])
            for other in bucket[1:]:
                for col in MASTER_COLS:
                    if col in ("email", "source"):
                        continue
                    a, b = primary[col], other[col]
                    if not a and b:
                        primary[col] = b
                    elif a and b and a != b:
                        conflicts.append(
                            f"{email}: {col} '{a}' vs '{b}' "
                            f"({primary['source']} vs {other['source']}) - kept first")
            used = []
            for rec in bucket:
                if rec["source"] not in used:
                    used.append(rec["source"])
            primary["source"] = " | ".join(used)

            reasons = review_reasons(primary)
            if reasons:
                review.append({**primary, "_reason": "; ".join(reasons)})
            else:
                master.append(primary)

    for rec in unkeyable:
        reasons = review_reasons(rec)
        if not reasons:
            reasons.append("email invalid")
        review.append({**rec, "_reason": "; ".join(reasons)})

    # ------------------------------------------------------------ output
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(os.path.join(OUT_DIR, "master.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MASTER_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(master)

    with open(os.path.join(OUT_DIR, "review.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MASTER_COLS + ["reason"], extrasaction="ignore")
        w.writeheader()
        for rec in review:
            row = {k: rec[k] for k in MASTER_COLS}
            row["reason"] = rec["_reason"]
            w.writerow(row)

    total_in = sum(counts.values())
    absorbed = len(records) - len(master) - len(review)
    lines = ["test-job-3 - dental practice contact consolidation", "=" * 60, "", "ROW COUNTS"]
    for fname, n in counts.items():
        lines.append(f"  {fname:<26} {n:>3} rows in")
    lines.append(f"  {'TOTAL IN':<26} {total_in:>3}")
    lines.append("")
    lines.append(f"  removed (fully blank)      {len(dropped['blank'])}")
    lines.append(f"  removed (test rows)        {len(dropped['test'])}")
    lines.append(f"  master rows                {len(master)}")
    lines.append(f"  review rows                {len(review)}")
    lines.append(f"  merged duplicates absorbed {absorbed}")
    lines.append("")
    lines.append(f"  RECONCILIATION: {total_in} in - {len(dropped['blank'])} blank - "
                 f"{len(dropped['test'])} test - {absorbed} merged "
                 f"= {len(master) + len(review)} output rows")
    lines.append("")
    if dropped["blank"]:
        lines.append("  blank rows deleted: " + ", ".join(dropped["blank"]))
    if dropped["test"]:
        lines.append("  test rows deleted:  " + ", ".join(dropped["test"]))
    lines.append("")
    lines.append("COLUMNS OMITTED (outside the master schema)")
    for col, found in dropped_cols.items():
        if not found:
            lines.append(f"  {col:<14} (not present)")
            continue
        for fname, populated, total in found:
            lines.append(f"  {col:<14} in {fname:<24} {populated}/{total} populated - omitted")
    lines.append("")
    lines.append("CONFLICTS (same lead, two non-blank values - first copy kept)")
    if conflicts:
        lines.extend(f"  {c}" for c in conflicts)
    else:
        lines.append("  none")
    lines.append("")
    lines.append("ASSUMPTIONS AND NOTES")
    lines.append("  1. Company completeness: the brief says a contact's company is judged")
    lines.append("     after merging. A contact with no company in ANY copy therefore")
    lines.append("     goes to review as 'company missing' - this affected one contact")
    lines.append("     (Zoe Lane, 05_old_crm.csv row 4).")
    lines.append("     CLIENT CONFIRMED: leave her on the review list for now; she does")
    lines.append("     not know which practice she belongs to. STANDING INSTRUCTION, to")
    lines.append("     apply only if she is later confirmed to have no practice attached:")
    lines.append("     keep her in the MASTER with a blank company rather than dropping")
    lines.append("     her - 'I'd rather keep the contact than lose it.' Until that is")
    lines.append("     confirmed she stays flagged, not guessed at.")
    lines.append("  2. Blank phones (TBD or empty) are kept blank in the master, not")
    lines.append("     reviewed - the brief says blank is not invalid.")
    lines.append("  3. Rows with an invalid or missing email cannot be matched to any")
    lines.append("     other copy, so they are reviewed on their own.")
    lines.append("  4. Some contacts are at non-dental companies (hotels, breweries,")
    lines.append("     freight, tourism). The brief does not ask to filter these, so")
    lines.append("     they are kept as given.")
    lines.append("  5. ZIP codes are kept as text to preserve leading zeros.")

    with open(os.path.join(OUT_DIR, "summary.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"Wrote to {OUT_DIR}")
    print(f"  rows in   : {total_in}")
    print(f"  master    : {len(master)}")
    print(f"  review    : {len(review)}")
    print(f"  deleted   : {len(dropped['blank'])} blank, {len(dropped['test'])} test")
    print(f"  conflicts : {len(conflicts)}")


if __name__ == "__main__":
    main()
