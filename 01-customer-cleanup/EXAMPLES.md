# Before and after examples

Generated fictional practice data. These are excerpts from original input copies and existing supplied output, not a rerun. Record numbers below count parsed CSV records after the header, including empty-field records; they are not physical file line numbers. Matching a record here does not prove every merge decision.

Email and website domains in these excerpts carry the reserved `.example` ending added before publishing; see the [top-level README](../README.md).

## Example 1

Before: inputs/customers_messy.csv, parsed record 1.

```json
{
  "customer_id": "1025",
  "first_name": "Anthony",
  "last_name": "Hill",
  "email": "ANTHONY.HILL@ICLOUD.COM.EXAMPLE",
  "phone": "+1 303 804 5852",
  "city": "Boston",
  "state": "MA",
  "zip": "02197",
  "signup_date": "11/18/22",
  "total_spent": "$1,802.11"
}
```

After: supplied-output/customers_clean.csv, parsed record 1. This is the corresponding supplied record; other copies may contribute merged fields.

```json
{
  "customer_id": "1025",
  "first_name": "Anthony",
  "last_name": "Hill",
  "email": "anthony.hill@icloud.com.example",
  "phone": "(303) 804-5852",
  "city": "Boston",
  "state": "MA",
  "zip": "02197",
  "signup_date": "2022-11-18",
  "total_spent": "1802.11"
}
```

## Example 2

Before: inputs/customers_messy.csv, parsed record 2.

```json
{
  "customer_id": "1068",
  "first_name": "Karen Lee",
  "last_name": "",
  "email": "karen.lee@outlook.com.example",
  "phone": "305.370.7898",
  "city": "Miami",
  "state": "Florida",
  "zip": "33153",
  "signup_date": "16-Sep-2024",
  "total_spent": "602.69"
}
```

After: supplied-output/customers_clean.csv, parsed record 2. This is the corresponding supplied record; other copies may contribute merged fields.

```json
{
  "customer_id": "1068",
  "first_name": "Karen",
  "last_name": "Lee",
  "email": "karen.lee@outlook.com.example",
  "phone": "(305) 370-7898",
  "city": "Miami",
  "state": "FL",
  "zip": "33153",
  "signup_date": "2024-09-16",
  "total_spent": "602.69"
}
```
