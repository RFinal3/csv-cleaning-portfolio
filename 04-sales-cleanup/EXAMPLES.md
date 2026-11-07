# Before and after examples

Generated fictional practice data. These are excerpts from original input copies and existing supplied output, not a rerun. Record numbers below count parsed CSV records after the header, including empty-field records; they are not physical file line numbers. Matching a record here does not prove every merge decision.

Email and website domains in these excerpts carry the reserved `.example` ending added before publishing; see the [top-level README](../README.md).

## Example 1

Before: inputs/01_shopify_export.csv, parsed record 1.

```json
{
  "Order ID": "SH-1043",
  "Customer Name": "Emily Campbell",
  "Email": "emily.campbell@gmail.com.example",
  "Phone": "0416 853 429",
  "SKU": "KTN-1015",
  "Product": "Glass Storage Jars",
  "Quantity": "3",
  "Unit Price": "$28.50",
  "Order Date": "2026-07-12",
  "Status": "Completed"
}
```

After: supplied-output/master.csv, parsed record 1. This is the corresponding supplied record; other copies may contribute merged fields.

```json
{
  "order_id": "SH-1043",
  "customer_first": "Emily",
  "customer_last": "Campbell",
  "customer_email": "emily.campbell@gmail.com.example",
  "customer_phone": "0416 853 429",
  "sku": "KTN-1015",
  "product": "Glass Storage Jars",
  "qty": "3",
  "unit_price": "28.50",
  "line_total": "85.50",
  "order_date": "2026-07-12",
  "status": "completed",
  "source": "01_shopify_export.csv"
}
```

## Example 2

Before: inputs/01_shopify_export.csv, parsed record 2.

```json
{
  "Order ID": "SH-1007",
  "Customer Name": "Amanda White",
  "Email": "amanda.white@bigpond.com.example",
  "Phone": "0482 831 285",
  "SKU": "hme-1016",
  "Product": "Picture Frame Set",
  "Quantity": "5",
  "Unit Price": "$21.99",
  "Order Date": "2026-10-21",
  "Status": "Completed"
}
```

After: supplied-output/master.csv, parsed record 2. This is the corresponding supplied record; other copies may contribute merged fields.

```json
{
  "order_id": "SH-1007",
  "customer_first": "Amanda",
  "customer_last": "White",
  "customer_email": "amanda.white@bigpond.com.example",
  "customer_phone": "0482 831 285",
  "sku": "HME-1016",
  "product": "Picture Frame Set",
  "qty": "5",
  "unit_price": "21.99",
  "line_total": "109.95",
  "order_date": "2026-10-21",
  "status": "completed",
  "source": "01_shopify_export.csv"
}
```
