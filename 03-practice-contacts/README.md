# Dental practice contact consolidation

Fictional, generated practice data. Practice work, not paid-client work. This project uses the workflow I use for client work: an AI agent did the first pass on the code and outputs, and I reviewed the results and delivered them. Kit, named in the brief, is a separate AI agent that graded the exercise; grades are exercise feedback, not credentials.

Email and website domains carry the reserved `.example` ending (for example `gmail.com.example`), so no address can belong to a real person or business. The outputs were rerun after that change and still match. See the [top-level README](../README.md).

Consolidated five contact exports with US phone extensions, address formatting, source tracking and review for invalid or incomplete records.

## Evidence

Original input copies: 5 CSV file(s), 159 source data records (including blank lines). Existing supplied outputs: 120 clean/master and 9 review records, excluding headers. Blank/junk records can be included in input counts. supplied-output holds the delivered files (with the domain change); rerunning the script regenerates them exactly. See [examples](EXAMPLES.md) and the preserved original brief (brief.md).

## How to run

Python 3, standard library only. From this project folder in a permitted environment, use a fresh run-output folder:

```powershell
python clean_job3.py inputs run-output
```

The script writes generated outputs (and a summary for Jobs 2–4) into run-output; Job 1 also writes column-report.txt. Reusing that folder overwrites generated files. Keep supplied-output as the comparison snapshot. Jobs 2–4 accept explicit input/output arguments; only their copied path defaults were normalized.

**Reproduced on 7 November 2026.** The script was run on the included inputs with Python 3.14 on Windows, and both generated files matched `supplied-output` byte for byte (120 master, 9 review). Reconciliation: 159 input records − 3 blank − 2 test − 25 merged = 129 output rows. This shows the saved results reproduce from the saved inputs; it does not show the script handles every possible file.

## Limitations

Phone validation flags are not recalculated after merging. Address formatting is heuristic and malformed addresses may pass through; title casing can alter names. Website, Notes and Last Contact are outside the target schema and omitted, including populated values. Confirm needed columns and address rules before applying this approach elsewhere.

## Clarifications and decisions

**Simulated client exchange (practice roleplay).** Question: should Zoe Lane in 05_old_crm.csv, file line 4, be dropped because her company is missing? Decision: retain her in review pending confirmation. If later confirmed to have no practice attached, the rehearsed fallback is master with a blank company. Current code/output keep her in review; the later fallback is not an automatic implemented move.
