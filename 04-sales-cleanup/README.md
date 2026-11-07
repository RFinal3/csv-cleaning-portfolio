# Sales export cleanup

Fictional, generated practice data. Practice work, not paid-client work. This project uses the workflow I use for client work: an AI agent did the first pass on the code and outputs, and I reviewed the results and delivered them. Kit, named in the brief, is a separate AI agent that graded the exercise; grades are exercise feedback, not credentials.

Email and website domains carry the reserved `.example` ending (for example `gmail.com.example`), so no address can belong to a real person or business. The outputs were rerun after that change and still match. See the [top-level README](../README.md).

Normalized three sales exports, calculated line totals with Decimal, separated conflicting transactions and reconciled supplied revenue while retaining returns.

## Evidence

Original input copies: 3 CSV file(s), 288 source data records (including blank lines). Existing supplied outputs: 200 clean/master and 30 review records, excluding headers. Blank/junk records can be included in input counts. supplied-output holds the delivered files (with the domain change); rerunning the script regenerates them exactly. See [examples](EXAMPLES.md) and the preserved original brief (brief.md).

## How to run

Python 3, standard library only. From this project folder in a permitted environment, use a fresh run-output folder:

```powershell
python clean_job4.py inputs run-output
```

The script writes generated outputs (and a summary for Jobs 2–4) into run-output; Job 1 also writes column-report.txt. Reusing that folder overwrites generated files. Keep supplied-output as the comparison snapshot. Jobs 2–4 accept explicit input/output arguments; only their copied path defaults were normalized.

**Reproduced on 7 November 2026.** The script was run on the included inputs with Python 3.14 on Windows, and both generated files matched `supplied-output` byte for byte (200 master, 30 review). Every master line total equals quantity × unit price, and total revenue reproduced at 27,085.35. This shows the saved results reproduce from the saved inputs; it does not show the script handles every possible file.

## Limitations

Purchase-signature matching can collapse legitimate repeat purchases; first file order wins. The SKU regex accepts a variable-length letter prefix despite the AAA-9999 description. Date parsing and return/refund treatment need agreement. The preserved brief incorrectly calls 03/04/2026 “4 March”; day-first means 3 April 2026, consistent with the code. No date algorithm was changed. Negative-quantity returns are included; cancelled/refunded status lines are removed. Phone parse failures pass through under this exercise brief.

## Clarifications and decisions

**Simulated client exchange (practice roleplay).** Question: do returns and refunded orders count the same way? Decision: follow the separate brief rules: keep negative-quantity returns in revenue and remove cancelled/refunded status lines. The supplied master has four negative-quantity lines totaling -434.45 and total revenue 27,085.35. No real client received a submission.
