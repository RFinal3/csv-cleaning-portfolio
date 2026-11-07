# Before and after examples

Generated fictional practice data. These are excerpts from original input copies and existing supplied output, not a rerun. Record numbers below count parsed CSV records after the header, including empty-field records; they are not physical file line numbers. Matching a record here does not prove every merge decision.

Email and website domains in these excerpts carry the reserved `.example` ending added before publishing; see the [top-level README](../README.md).

## Example 1

Before: inputs/01_tradeshow.csv, parsed record 2.

```json
{
  "Full Name": "Jack Roberts",
  "Email Address": "jack.roberts@tasmaniantimbertraders.com.au.example",
  "Phone": "0483 170 889",
  "Company": "Tasmanian Timber Traders",
  "Job Title": "Chief Executive",
  "Location": "Perth, WA",
  "Notes": "Follow up in June"
}
```

After: supplied-output/master.csv, parsed record 1. This is the corresponding supplied record; other copies may contribute merged fields.

```json
{
  "first_name": "Jack",
  "last_name": "Roberts",
  "email": "jack.roberts@tasmaniantimbertraders.com.au.example",
  "phone": "0483 170 889",
  "company": "Tasmanian Timber Traders",
  "role": "Chief Executive",
  "city": "Perth",
  "state": "WA",
  "notes": "Follow up in June",
  "source": "01_tradeshow.csv"
}
```

## Example 2

Before: inputs/01_tradeshow.csv, parsed record 3.

```json
{
  "Full Name": "Nicole Hill",
  "Email Address": "nicole.hill@harbourviewlogistics.com.au.example",
  "Phone": "0474 135 631",
  "Company": "Harbourview Logistics",
  "Job Title": "Office Manager",
  "Location": "Adelaide, SA",
  "Notes": "Existing customer, new branch"
}
```

After: supplied-output/master.csv, parsed record 2. This is the corresponding supplied record; other copies may contribute merged fields.

```json
{
  "first_name": "Nicole",
  "last_name": "Hill",
  "email": "nicole.hill@harbourviewlogistics.com.au.example",
  "phone": "0474 135 631",
  "company": "Harbourview Logistics",
  "role": "Office Manager",
  "city": "Adelaide",
  "state": "SA",
  "notes": "Existing customer, new branch",
  "source": "01_tradeshow.csv | 04_old_spreadsheet.csv"
}
```
