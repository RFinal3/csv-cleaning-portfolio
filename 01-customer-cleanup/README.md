# Customer list cleanup

Fictional, generated practice data. Practice work, not paid-client work. I wrote all of the Python for this project myself. A Claude agent coached me through it, pointing me to documentation and giving pseudocode when I asked. Grades mentioned in the files are exercise feedback, not credentials.

Email and website domains carry the reserved `.example` ending (for example `gmail.com.example`), so no address can belong to a real person or business. The outputs were rerun after that change and still match. See the [top-level README](../README.md).

Standardized customer names, emails, phones, states, ZIPs, dates and money, with uncertain rows separated for review. The email-only duplicate rule illustrates why identity decisions need careful scope.

## Evidence

Original input copies: 1 CSV file(s), 117 source data records (including blank lines). Existing supplied outputs: 88 clean/master and 13 review records, excluding headers. Blank/junk records can be included in input counts. supplied-output holds the delivered files (with the domain change); rerunning the script regenerates them exactly. See [examples](EXAMPLES.md) and the preserved original brief (Problem.txt).

## How to run

Python 3, standard library only. From this project folder in a permitted environment, use a fresh run-output folder:

```powershell
New-Item -ItemType Directory run-output
Copy-Item inputs/customers_messy.csv run-output/customers_messy.csv
Set-Location run-output
python ../cleaning_script.py
```

The script writes generated outputs (and a summary for Jobs 2–4) into run-output; Job 1 also writes column-report.txt. Reusing that folder overwrites generated files. Keep supplied-output as the comparison snapshot. Jobs 2–4 accept explicit input/output arguments; only their copied path defaults were normalized.

**Reproduced on 7 November 2026.** The script was run on the included input with Python 3.14 on Windows, and both generated files matched `supplied-output` byte for byte (88 clean, 13 review). Reconciliation: 117 input records = 88 clean + 13 review + 13 duplicates removed + 3 blank. This shows the saved results reproduce from the saved input; it does not show the script handles every possible file.

## Limitations

Email-only deduplication can remove a distinct customer record sharing an address. Current code keeps the earliest signup. Leading-zero ZIP candidates and test rows stay in review; restoring ZIPs or deleting test rows are lessons/proposed policy changes, not implemented fixes. Basic email syntax checks do not establish deliverability. The script prints a count summary but does not write the change-summary file the brief asked for; that summary was written separately for the original delivery.

## Lessons learned (hypothetical retrospective; no mock-client Q&A)

Two separate customer pairs share email addresses despite differing customer details: IDs 1016/1096 and 1021/1061. A question to ask before applying a data-loss rule would be: keep both distinct customer records, or merge by earliest signup? The recommendation is to keep both. Current code still deduplicates by email; this lesson is not an implemented fix. Ask about scope and data-loss decisions before applying them, and present unresolved exceptions at handoff.
