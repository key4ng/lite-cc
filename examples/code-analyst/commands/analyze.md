---
name: analyze
description: Full file analysis pipeline — summarize, trace execution flow, and review code quality.
---

# File Analysis

Run the complete analysis pipeline on the target file.

## Steps

1. Load the `summarize` skill and follow its instructions on the target file.
2. Load the `flowchart` skill and trace the execution flow.
3. Load the `code-review` skill and review the code quality.
4. Write the full analysis to `/tmp/analysis-report.txt`.
5. Present the complete report.
