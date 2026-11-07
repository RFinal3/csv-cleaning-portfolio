import csv
from datetime import datetime

with open("customers_messy.csv", newline="") as file:
    reader = csv.DictReader(file)
    data = list(reader)
    fieldheader = reader.fieldnames

with open("column-report.txt", "w") as report:
    for header in fieldheader:
        values = set()
        for row in data:
            values.add(row[header])
        report.write(f"{header}: {sorted(values)}\n")


state_codes = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}

TEST_EMAILS = {"test@test.com", "asdf@asdf.com"}

valid_codes = set(state_codes.values())

kept_emails = {}

clean_rows = []
review_rows = []
blank_count = 0


def clean_zip(raw):
    text = raw.strip()

    if text == "":
        return (None, "missing zip")

    digits = "".join(filter(str.isdigit, text))

    if digits == "00000" or digits == "12345":
        return (None, "invalid zip")

    if len(digits) == 5:
        return (digits, None)

    if len(digits) == 9:
        return (digits[:5], None)

    if len(digits) == 8:
        return (
            None,
            f"zip may be missing leading zero (likely 0{digits[:4]})",
        )

    return (None, "wrong number of zip digits")


def clean_phone(raw):
    text = raw.strip()

    if text == "":
        return (None, "missing phone")

    digits = "".join(filter(str.isdigit, text))

    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        return (None, "wrong number of phone digits")

    if digits == "0000000000":
        return (None, "invalid phone")

    formatted = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    return (formatted, None)


def clean_date(raw):
    text = raw.strip()

    if text == "":
        return (None, "missing date")

    formats = ["%d-%b-%Y", "%m/%d/%y", "%Y-%m-%d", "%m/%d/%Y"]

    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return (dt.strftime("%Y-%m-%d"), None)
        except ValueError:
            continue

    return (None, "invalid date")


def clean_state(raw):
    text = raw.strip()

    if text == "":
        return (None, "missing state")

    if text.upper() in valid_codes:
        return (text.upper(), None)

    if text.title() in state_codes:
        return (state_codes[text.title()], None)

    return (None, "invalid state")


def clean_money(raw):
    text = raw.strip()

    if text == "":
        return (None, "missing total_spent")

    text = text.replace("$", "").replace(",", "")

    try:
        value = float(text)
    except ValueError:
        return (None, "invalid total_spent")

    if value < 0:
        return (None, "negative total_spent")

    return (f"{value:.2f}", None)


def clean_email(raw):
    text = raw.strip().lower()

    if text == "":
        return (None, "missing email")

    parts = text.split("@")

    if len(parts) != 2:
        return (None, "invalid email - must contain exactly one @")

    local = parts[0]
    domain = parts[1]

    if local == "":
        return (None, "invalid email - missing local part")

    if "." not in domain:
        return (None, "invalid email - missing dot in domain")

    if domain.startswith(".") or domain.endswith("."):
        return (None, "invalid email - domain starts or ends with dot")

    return (text, None)


def fix_name_split(raw_first, raw_last, raw_email):
    first = raw_first.strip()
    last = raw_last.strip()
    email = raw_email.strip().lower()

    if last != "":
        return (first, last, None)

    words = first.split()

    if len(words) < 2:
        return (first, last, None)

    if len(words) > 2:
        return (None, None, "full name in first_name - cannot split safely")

    guess_first = words[0]
    guess_last = words[1]

    expected = guess_first.lower() + "." + guess_last.lower()

    if email.startswith(expected):
        return (guess_first, guess_last, None)

    return (None, None, "full name in first_name - email doesn't confirm order")


def clean_name(raw):
    text = raw.strip()

    if text == "":
        return (None, "missing name")

    return (text.title(), None)


def clean_city(raw):
    text = raw.strip()

    if text == "":
        return (None, "missing city")

    return (text.title(), None)


for row in data:
    if all(value.strip() == "" for value in row.values()):
        blank_count += 1
        continue

    if row["email"].strip().lower() in TEST_EMAILS:
        review_row = dict(row)
        review_row["review_reason"] = "looks like test data"
        review_rows.append(review_row)
        continue

    errors = []
    clean = {}

    clean["customer_id"] = row["customer_id"].strip()

    first, last, split_error = fix_name_split(
        row["first_name"], row["last_name"], row["email"]
    )
    if split_error:
        errors.append(split_error)
    else:
        clean["first_name"], err = clean_name(first)
        if err:
            errors.append(err)

        clean["last_name"], err = clean_name(last)
        if err:
            errors.append(err)

    clean["email"], err = clean_email(row["email"])
    if err:
        errors.append(err)

    clean["state"], err = clean_state(row["state"])
    if err:
        errors.append(err)

    clean["zip"], err = clean_zip(row["zip"])
    if err:
        errors.append(err)

    clean["phone"], err = clean_phone(row["phone"])
    if err:
        errors.append(err)

    clean["city"], err = clean_city(row["city"])
    if err:
        errors.append(err)

    clean["signup_date"], err = clean_date(row["signup_date"])
    if err:
        errors.append(err)

    clean["total_spent"], err = clean_money(row["total_spent"])
    if err:
        errors.append(err)

    if not errors:
        clean_rows.append(clean)
    else:
        review_row = dict(row)
        review_row["review_reason"] = "; ".join(errors)
        review_rows.append(review_row)

duplicate_count = 0

for row in clean_rows:
    email = row["email"]
    if email in kept_emails:
        duplicate_count += 1

        kept_row = kept_emails[email]

        if kept_row["signup_date"] > row["signup_date"]:
            kept_emails[email] = row

    else:
        kept_emails[email] = row

final_rows = list(kept_emails.values())


with open("customers_clean.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldheader)
    writer.writeheader()
    writer.writerows(final_rows)

with open("customers_review.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldheader + ["review_reason"])
    writer.writeheader()
    writer.writerows(review_rows)


print("--- Cleaning complete ---")
print("Clean rows:", len(clean_rows))
print("Review rows:", len(review_rows))
print("Blank rows:", blank_count)
print("Total rows:", len(data))
print("Duplicate emails:", duplicate_count)
print("Final rows:", len(final_rows))
