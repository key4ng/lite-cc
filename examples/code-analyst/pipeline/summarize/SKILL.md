---
name: summarize
description: Read a source file and produce a structured summary of its purpose, key components, and dependencies.
---

# File Summary

## Steps

1. Read the target file using `read_file`.
2. Count the lines of code:
   ```bash
   wc -l <filepath>
   ```
3. Identify imports and external dependencies.
4. Produce a summary with:
   - **Purpose**: What the file does (1-2 sentences)
   - **Key components**: Classes, functions, or constants defined
   - **Dependencies**: External packages and internal modules imported
   - **Lines of code**: Total count
