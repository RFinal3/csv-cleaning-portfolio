#!/usr/bin/env python3
"""
clean_job2.py - test-job-2 lead list cleanup & consolidation.

Reads the 7 source CSVs (read-only) and writes:
    master.csv        - the consolidated, cleaned lead list
    review.csv        - rows that could not be resolved, each with a reason
    summary.txt       - counts, drops, assumptions, and client resolutions

Rules implemented (source of truth = brief.md, owner rulings marked *OWNER*,
client confirmations marked *CLIENT*):
  * Phones   -> 04xx xxx xxx.  +61 4xx xxx xxx and 614xxxxxxxxx both become
                04xx xxx xxx.  Validity bar: exactly 10 digits starting 04.
                (An AU landline arriving in +61 form fails loudly rather than
                being silently reshaped into a fake mobile.)
  * Emails   -> lowercase + trimmed. Validity: must have '@', a dot in the
                domain, and no whitespace.  *OWNER*: a non-conforming email
                goes to REVIEW, not repair.
  * Names    -> Title Case, trimmed; 'Last, First' flipped.
  * States   -> 2-letter uppercase AU codes; full names mapped.
  * Locations-> 'City, ST' / 'City, Full State' / 'City ST' -> city + state.
  * Companies/roles -> Title Case, trimmed.
  * Junk     -> N/A, null, -, TBD, unknown, blanks => blank. Never invented.
  * Extra columns (Website, Lead Score) were empty in every row; OMITTED.
                *CLIENT*: confirmed they don't need them.
  * Source   -> *OWNER*: every file a record's data came from, joined ' | '.
  * Dedupe   -> same normalised email = same lead; merge, filling blanks.
                *OWNER*: conflicting non-blank values -> first wins, recorded.
                Notes: *OWNER* merge both with ' | '.
  * Shared inbox -> same email but different name AND different phone = two
                people; keep both.  (Compared AFTER normalisation.)
  * Review   -> missing name / missing email / invalid email / invalid phone.
                A BLANK phone is NOT a review reason - the brief only sends
                INVALID phones to review. TBD normalises to blank, so those
                rows stay in the master with an empty phone field.
                (Learned from the Job-2 grade: they were wrongly reviewed.)
  * Delete   -> fully blank rows and obvious test rows (counted in summary).

SAFETY RULE (learned in test-job-2): an unrecognised source column stops the
job. It is never silently dropped. A quiet drop hides real data.
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

MASTER_COLS = [
    "first_name", "last_name", "email", "phone", "company",
    "role", "city", "state", "notes", "source",
]

# Every source header we know how to place. Anything else is a hard stop.
KNOWN_HEADERS = {
    "Full Name", "NAME", "name", "FullName", "Contact",
    "First Name", "first_name", "Last Name", "last_name",
    "Email Address", "EmailAddress", "Email", "EMAIL", "email",
    "Phone", "PhoneNumber", "phone", "phone_number", "Tel", "PHONE",
    "Company", "CompanyName", "Company Name", "company", "organisation",
    "COMPANY",
    "Job Title", "JobTitle", "job_title", "Title", "Position", "role", "ROLE",
    "Location", "CityState", "LOCATION",
    "City", "city", "State", "state",
    "Notes", "Comments", "comments", "NOTES",
    "Website", "Lead Score",
}

JUNK = {"n/a", "na", "null", "none", "-", "--", "tbd", "unknown"}

STATE_NAMES = {
    "new south wales": "NSW",
    "victoria": "VIC",
    "queensland": "QLD",
    "south australia": "SA",
    "western australia": "WA",
    "tasmania": "TAS",
    "northern territory": "NT",
    "australian capital territory": "ACT",
}
STATE_CODES = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}

TEST_EMAILS = {"test@test.com", "asdf@asdf.com"}
TEST_NAMES = {"test user", "asdf asdf"}

LOWER_WORDS = {"and", "of", "the", "a", "an", "in", "on", "at", "for", "to"}


def clean_text(raw):
    if raw is None:
        return ""
    value = raw.strip()
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
        elif "-" in word:
            out.append("-".join(p[:1].upper() + p[1:].lower() for p in word.split("-")))
        else:
            out.append(word[:1].upper() + word[1:].lower())
    return " ".join(out)


def split_name(combined):
    value = combined.strip()
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
    value = clean_text(raw)
    if not value:
        return "", False, "phone missing"
    digits = re.sub(r"\D", "", value)
    if value.startswith("+61"):
        digits = "0" + digits[2:]
    elif digits.startswith("614") and len(digits) == 11:
        digits = "0" + digits[2:]
    if len(digits) != 10 or not digits.startswith("04"):
        return value, False, "phone invalid"
    return f"{digits[:4]} {digits[4:7]} {digits[7:]}", True, ""


def normalise_email(raw):
    value = clean_text(raw).lower()
    if not value:
        return "", False, "email missing"
    if " " in value or value.count("@") != 1:
        return value, False, "email invalid"
    local, _, domain = value.partition("@")
    if not local or not domain or "." not in domain:
        return value, False, "email invalid"
    if domain.startswith(".") or domain.endswith("."):
        return value, False, "email invalid"
    return value, True, ""


def normalise_state(value):
    value = clean_text(value)
    if not value:
        return ""
    upper = value.upper()
    if upper in STATE_CODES:
        return upper
    return STATE_NAMES.get(value.lower(), "")


def split_location(value):
    value = clean_text(value)
    if not value:
        return "", ""
    if "," in value:
        city, _, state = value.partition(",")
        return title_case(city.strip()), normalise_state(state)
    tokens = value.split()
    if tokens and tokens[-1].upper() in STATE_CODES:
        return title_case(" ".join(tokens[:-1])), tokens[-1].upper()
    if len(tokens) >= 2:
        code = normalise_state(" ".join(tokens[-2:]))
        if code:
            return title_case(" ".join(tokens[:-2])), code
    return title_case(value), ""


def build_reader(headers, fname):
    """Map a file's headers onto master concepts. Unknown header = hard stop."""
    idx = {h.strip(): i for i, h in enumerate(headers)}
    unknown = [h for h in idx if h not in KNOWN_HEADERS]
    if unknown:
        sys.exit(
            f"STOP: {fname} has unrecognised column(s): {unknown}\n"
            "Refusing to run rather than silently drop data.\n"
            "Add them to KNOWN_HEADERS (and to build_reader's get() calls) first."
        )

    def get(row, *names):
        for name in names:
            if name in idx:
                i = idx[name]
                return row[i] if i < len(row) else ""
        return ""

    def read(row):
        return {
            "full_name": get(row, "Full Name", "NAME", "name", "FullName", "Contact"),
            "first": get(row, "First Name", "first_name"),
            "last": get(row, "Last Name", "last_name"),
            "email": get(row, "Email Address", "EmailAddress", "Email", "EMAIL", "email"),
            "phone": get(row, "Phone", "PhoneNumber", "phone", "phone_number", "Tel", "PHONE"),
            "company": get(row, "Company", "CompanyName", "Company Name", "company",
                           "organisation", "COMPANY"),
            "role": get(row, "Job Title", "JobTitle", "job_title", "Title", "Position",
                        "role", "ROLE"),
            "location": get(row, "Location", "CityState", "LOCATION"),
            "city": get(row, "City", "city"),
            "state": get(row, "State", "state"),
            "notes": get(row, "Notes", "Comments", "comments", "NOTES"),
            "website": get(row, "Website"),
            "lead_score": get(row, "Lead Score"),
        }

    return read


def is_blank_row(fields):
    return not any(str(v).strip() for v in fields.values())


def is_test_row(rec):
    return (rec["email"].lower() in TEST_EMAILS
            or f"{rec['first_name']} {rec['last_name']}".strip().lower() in TEST_NAMES)


def main():
    sources = sorted(glob.glob(os.path.join(SRC_DIR, "??_*.csv")))
    if not sources:
        sys.exit(f"No source files matching NN_*.csv found in {SRC_DIR}")

    records = []
    counts = OrderedDict()
    dropped = {"blank": [], "test": []}
    empty_cols = {"Website": [], "Lead Score": []}

    for path in sources:
        fname = os.path.basename(path)
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
        if not rows:
            counts[fname] = 0
            continue

        reader = build_reader(rows[0], fname)
        data = rows[1:]
        counts[fname] = len(data)

        # Record which files carry the out-of-schema columns, and whether empty.
        header_set = {h.strip() for h in rows[0]}
        for col in ("Website", "Lead Score"):
            if col in header_set:
                i = [h.strip() for h in rows[0]].index(col)
                n = sum(1 for r in data if i < len(r) and r[i].strip())
                empty_cols[col].append((fname, n, len(data)))

        for offset, row in enumerate(data, start=2):
            fields = reader(row)
            if is_blank_row(fields):
                dropped["blank"].append(f"{fname}:{offset}")
                continue

            if fields["full_name"].strip():
                first, last = split_name(fields["full_name"])
            else:
                first = title_case(clean_text(fields["first"]))
                last = title_case(clean_text(fields["last"]))

            email, email_ok, email_reason = normalise_email(fields["email"])
            phone, phone_ok, phone_reason = normalise_phone(fields["phone"])

            if fields["location"].strip():
                city, state = split_location(fields["location"])
            else:
                city = title_case(clean_text(fields["city"]))
                state = normalise_state(fields["state"])

            rec = {
                "first_name": first, "last_name": last, "email": email,
                "phone": phone,
                "company": title_case(clean_text(fields["company"])),
                "role": title_case(clean_text(fields["role"])),
                "city": city, "state": state,
                "notes": clean_text(fields["notes"]),
                "source": fname, "_line": offset,
                "_email_ok": email_ok, "_phone_ok": phone_ok,
                "_email_reason": email_reason, "_phone_reason": phone_reason,
            }
            if is_test_row(rec):
                dropped["test"].append(
                    f"{fname}:{offset} ({rec['first_name']} {rec['last_name']})")
                continue
            records.append(rec)

    # ------------------------------------------------------------ dedupe
    merged = OrderedDict()
    conflicts = []
    unreviewable = []

    for rec in records:
        if rec["_email_ok"]:
            merged.setdefault(rec["email"], []).append(rec)
        else:
            unreviewable.append(rec)

    master, review = [], []

    for email, group in merged.items():
        identities = OrderedDict()
        for rec in group:
            sig = (f"{rec['first_name']} {rec['last_name']}".strip().lower(),
                   re.sub(r"\D", "", rec["phone"]))
            identities.setdefault(sig, []).append(rec)

        names = {sig[0] for sig in identities}
        shared_inbox = len(identities) > 1 and len(names) > 1
        buckets = list(identities.values()) if shared_inbox else [group]

        for bucket in buckets:
            primary = dict(bucket[0])
            for other in bucket[1:]:
                for col in MASTER_COLS:
                    if col in ("email", "source"):
                        continue
                    a, b = primary[col], other[col]
                    if col == "notes":
                        if b and b != a:
                            primary[col] = f"{a} | {b}" if a else b
                        continue
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

            reasons = []
            if not primary["first_name"] and not primary["last_name"]:
                reasons.append("name missing")
            if not primary["_email_ok"]:
                reasons.append(primary["_email_reason"] or "email invalid")
            # Only INVALID phones go to review. Blank is allowed in the master.
            if not primary["_phone_ok"] and primary["_phone_reason"] == "phone invalid":
                reasons.append("phone invalid")
            if reasons:
                review.append({**primary, "_reason": "; ".join(reasons)})
            else:
                master.append(primary)

    for rec in unreviewable:
        reasons = []
        if not rec["first_name"] and not rec["last_name"]:
            reasons.append("name missing")
        reasons.append(rec["_email_reason"] or "email invalid")
        if not rec["_phone_ok"] and rec["_phone_reason"] == "phone invalid":
            reasons.append("phone invalid")
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
    lines = ["test-job-2 - cleanup summary", "=" * 60, "", "ROW COUNTS"]
    for fname, n in counts.items():
        lines.append(f"  {fname:<26} {n:>3} rows in")
    lines.append(f"  {'TOTAL IN':<26} {total_in:>3}")
    lines.append("")
    lines.append(f"  removed (fully blank)      {len(dropped['blank'])}")
    lines.append(f"  removed (test rows)        {len(dropped['test'])}")
    lines.append(f"  master rows                {len(master)}")
    lines.append(f"  review rows                {len(review)}")
    absorbed = len(records) - len(master) - len(review)
    lines.append(f"  merged duplicates absorbed {absorbed}")
    lines.append(f"  check: {total_in} in - {len(dropped['blank'])} blank - "
                 f"{len(dropped['test'])} test - {absorbed} merged "
                 f"= {len(master) + len(review)} output rows")
    lines.append("")
    if dropped["blank"]:
        lines.append("  blank rows deleted: " + ", ".join(dropped["blank"]))
    if dropped["test"]:
        lines.append("  test rows deleted:  " + ", ".join(dropped["test"]))
    lines.append("")
    lines.append("COLUMNS OMITTED (outside the master schema)")
    for col, found in empty_cols.items():
        for fname, populated, total in found:
            state = "EMPTY in every row" if populated == 0 else f"{populated}/{total} populated"
            lines.append(f"  {col:<12} in {fname:<24} {state} - omitted")
    lines.append("  Client confirmed (2nd reply) these are not needed.")
    lines.append("")
    lines.append("CONFLICTS (same lead, two non-blank values - first copy kept)")
    if conflicts:
        lines.extend(f"  {c}" for c in conflicts)
    else:
        lines.append("  none")
    lines.append("")
    lines.append("CLIENT RESOLUTIONS (all confirmed, no further questions open)")
    lines.append("  1. Website / Lead Score columns: empty in every row; omitted.")
    lines.append("     Client confirmed they're not needed.")
    lines.append("  2. Contacts with no phone recorded (TBD or blank): kept in the")
    lines.append("     MASTER with the phone field empty - a blank phone is not a")
    lines.append("     review reason, only an invalid one is. Client confirmed.")
    lines.append("  3. One number with extra digits (12 digits, 04-prefixed): left")
    lines.append("     exactly as recorded and flagged for review. Client agreed")
    lines.append("     not to correct on a guess.")
    lines.append("  4. Non-conforming emails (no '@', truncated after '@', no domain")
    lines.append("     ending): left untouched and flagged. Client will verify.")
    lines.append("  5. Contacts with no email address: left in review, not guessed.")
    lines.append("     Client confirmed.")
    lines.append("  6. Two addresses each shared by two different people: kept as")
    lines.append("     separate rows. Client confirmed the handling.")
    lines.append("  7. Shorter company email domains (zoe.lane@coralcoast.com.au in")
    lines.append("     02_webinar.csv row 5; nina.foster@banksia.com.au in")
    lines.append("     04_old_spreadsheet.csv row 18): left exactly as received.")
    lines.append("     Client will check whether they're older addresses.")
    lines.append("  8. Row with no name (06_referrals.csv row 6): stays on the review")
    lines.append("     list, not in the master, until the client identifies it.")

    with open(os.path.join(OUT_DIR, "summary.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"Wrote to {OUT_DIR}")
    print(f"  rows in    : {total_in}")
    print(f"  master     : {len(master)}")
    print(f"  review     : {len(review)}")
    print(f"  deleted    : {len(dropped['blank'])} blank, {len(dropped['test'])} test")
    print(f"  conflicts  : {len(conflicts)}")


if __name__ == "__main__":
    main()
