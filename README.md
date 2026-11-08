# CSV cleaning portfolio — Ryan Melanson

Four practice projects showing how I clean messy CSV files. I standardize formats, apply an agreed duplicate rule, consolidate exports with different layouts, and set aside anything uncertain in a review file instead of guessing.

All of the data here is **fictional and generated for practice**. None of this is paid client work. You can open any input file, compare it with the output, and run the scripts yourself.

**About the email addresses:** before publishing, I added the reserved `.example` ending to every email and website domain (`gmail.com` → `gmail.com.example`), so no address can belong to a real person or business. Everything else keeps the shape of the original practice data, including the deliberately broken addresses. The only exceptions are two obvious placeholders, `test@test.com` and `asdf@asdf.com`, which the first project's script recognizes as test rows.

| Project | Inputs | Clean / master | Review | My role |
|---|---:|---:|---:|---|
| [Customer list cleanup](01-customer-cleanup/README.md) | 1 CSV, 117 records | 88 | 13 | Wrote the code myself, with AI coaching |
| [Australian lead consolidation](02-lead-consolidation/README.md) | 7 CSVs, 162 records | 120 | 9 | Agent first pass; I reviewed and delivered |
| [Dental practice contacts](03-practice-contacts/README.md) | 5 CSVs, 159 records | 120 | 9 | Agent first pass; I reviewed and delivered |
| [Sales export cleanup](04-sales-cleanup/README.md) | 3 CSVs, 288 records | 200 | 30 | Agent first pass; I reviewed and delivered |

## How I work

For the first project I wrote all of the Python myself. A Claude agent coached me through it Socratically, pointing me to documentation and giving pseudocode when I asked.

The other three use the workflow I bring to client work. An AI agent does the first pass, and I check the output, the row counts and the review file before delivering. Clients deal with me, and I'm responsible for what they receive.

## What each project contains

- `inputs/`: the original messy files.
- `brief.md` or `Problem.txt`: the original exercise brief, kept as written.
- The cleaning script: Python 3, standard library only.
- `supplied-output/`: the cleaned and review files that were delivered.
- `EXAMPLES.md`: before-and-after records.
- `README.md`: how to run it, limitations, and decisions made along the way.

## Checked

On 7 November 2026, all four scripts were run on their included inputs (Python 3.14, Windows), before and after the email-domain change. Both times, all eight generated CSVs matched the files in `supplied-output` byte for byte, and the sales revenue reproduced at 27,085.35. That confirms the saved results reproduce. It does not mean the scripts handle every possible file, and each project README lists its known limitations.
