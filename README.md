# Check model CSVs before loading arrays

A small, AI-assisted Python teaching sample. It checks two educational 2D geometry tables and produces a JSON error report. It does not calculate forces, certify a structure or prove engineering correctness.

## Run

Python 3.10 or later. No third-party dependencies.

```sh
python3 model_check.py examples/nodes.csv examples/members.csv
python3 -m unittest -v
```

Exit code 0 means these input checks passed. Exit code 1 means errors were found. Both input files remain unchanged. All included data is synthetic.

## Input contract

| File | Required columns | Meaning |
| --- | --- | --- |
| Nodes | `node_id,x_m,y_m` | Text identifier and finite 2D coordinates in metres |
| Members | `member_id,start_node_id,end_node_id` | Text member identifier and two existing node identifiers |

Column order may vary. Extra or duplicate columns are rejected. Whitespace around values is stripped. Identifiers remain strings, so `001` and `1` are different. Coordinates use Python floating point. Coordinates that round to the same floating-point value compare equal.

The checks cover duplicate IDs, missing references, non-finite coordinates, zero-length members, malformed CSV, header/row shape, missing files and empty models. Error line numbers identify the physical line on which the CSV record ends, which matters for quoted multiline fields.

The checker deliberately does not assess supports, material properties, connectivity, stability, load cases, unit declarations beyond the column contract, or design-code compliance. Passing it cannot establish that a model is physically valid. Use it to catch input mistakes before a separate numerical analysis.

## Why this is useful in a tutorial

Importing CSV data directly into numeric arrays can lose leading zeros in identifiers and push broken references into a later solver failure. This example keeps identifiers as text, checks the tables together, and returns file/line diagnostics before any numerical analysis begins.

It is an independent software sample, not commissioned client work or an accepted article. The associated tutorial pitch has not earned a fee.
