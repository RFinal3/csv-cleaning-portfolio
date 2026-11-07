# Before and after examples

Generated fictional practice data. These are excerpts from original input copies and existing supplied output, not a rerun. Record numbers below count parsed CSV records after the header, including empty-field records; they are not physical file line numbers. Matching a record here does not prove every merge decision.

Email and website domains in these excerpts carry the reserved `.example` ending added before publishing; see the [top-level README](../README.md).

## Example 1

Before: inputs/01_referral_list.csv, parsed record 1.

```json
{
  "Company": "Summit Dental Care",
  "Address": "2234 Grove Street, Denver, CO 80202",
  "Contact": "Emma Smith",
  "Cell": "303-803-4732",
  "Office": "303-844-7381",
  "Email": "emma.smith@summitdentalcare.com.example"
}
```

After: supplied-output/master.csv, parsed record 1. This is the corresponding supplied record; other copies may contribute merged fields.

```json
{
  "company": "Summit Dental Care",
  "address": "2234 Grove Street, Denver, CO 80202",
  "first_name": "Emma",
  "last_name": "Smith",
  "cell_phone": "(303) 803-4732",
  "office_phone": "(303) 844-7381",
  "email": "emma.smith@summitdentalcare.com.example",
  "source": "01_referral_list.csv | 04_conference.csv"
}
```

## Example 2

Before: inputs/01_referral_list.csv, parsed record 2.

```json
{
  "Company": "Pine Street Orthodontics",
  "Address": "6875 Hill Boulevard, Phoenix, AZ 85001",
  "Contact": "Singh, Olivia",
  "Cell": "602-825-6419",
  "Office": "602-840-4258 x86",
  "Email": "olivia.singh@pinestreetorthodontics.com.example"
}
```

After: supplied-output/master.csv, parsed record 2. This is the corresponding supplied record; other copies may contribute merged fields.

```json
{
  "company": "Pine Street Orthodontics",
  "address": "6875 Hill Boulevard, Phoenix, AZ 85001",
  "first_name": "Olivia",
  "last_name": "Singh",
  "cell_phone": "(602) 825-6419",
  "office_phone": "(602) 840-4258 x86",
  "email": "olivia.singh@pinestreetorthodontics.com.example",
  "source": "01_referral_list.csv"
}
```
