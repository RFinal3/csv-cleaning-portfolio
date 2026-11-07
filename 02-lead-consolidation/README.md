# Australian lead consolidation

Fictional, generated practice data. Practice work, not paid-client work. This project uses the workflow I use for client work: an AI agent did the first pass on the code and outputs, and I reviewed the results and delivered them. Kit, named in the brief, is a separate AI agent that graded the exercise; grades are exercise feedback, not credentials.

Email and website domains carry the reserved `.example` ending (for example `gmail.com.example`), so no address can belong to a real person or business. The outputs were rerun after that change and still match. See the [top-level README](../README.md).

Mapped seven source schemas into one lead list, normalized Australian phones and locations, filled blanks across duplicate records and retained review reasons.

## Evidence

Original input copies: 7 CSV file(s), 162 source data records (including blank lines). Existing supplied outputs: 120 clean/master and 9 review records, excluding headers. Blank/junk records can be included in input counts. supplied-output holds the delivered files (with the domain change); rerunning the script regenerates them exactly. See [examples](EXAMPLES.md) and the preserved original brief (brief.md).

## How to run

Python 3, standard library only. From this project folder in a permitted environment, use a fresh run-output folder:

```powershell
python clean_job2.py inputs run-output
```

The script writes generated outputs (and a summary for Jobs 2–4) into run-output; Job 1 also writes column-report.txt. Reusing that folder overwrites generated files. Keep supplied-output as the comparison snapshot. Jobs 2–4 accept explicit input/output arguments; only their copied path defaults were normalized.

**Reproduced on 7 November 2026.** The script was run on the included inputs with Python 3.14 on Windows, and both generated files matched `supplied-output` byte for byte (120 master, 9 review). Reconciliation: 162 input records − 3 blank − 2 test − 28 merged = 129 output rows. This shows the saved results reproduce from the saved inputs; it does not show the script handles every possible file.

## Limitations

Validation flags are retained from the first merged record rather than recalculated after filling fields. Shared-inbox code separates differing names even when phones match; the brief/comment requires different names AND different phones. Blank/TBD phones are currently allowed; current supplied outputs are 120 master / 9 review. Website and Lead Score are omitted by the agreed exercise schema.

## Clarifications and decisions

**Simulated client exchange (practice roleplay).** Question: should Joshua Wright and Chloe Hill, whose source phones are TBD, be held for review? Decision: keep them with blank phones; never invent numbers. The current code implements this correction and supplied outputs contain 120 master / 9 review, replacing the historical 118/11 snapshot.