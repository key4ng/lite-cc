---
name: flowchart
description: Trace the execution flow of a source file and produce a text-based flowchart.
---

# Execution Flow

## Steps

1. Identify the main entry point or public functions in the file.
2. Trace the call chain — which functions call which, and in what order.
3. Note any branching logic (if/else, loops, error handling).
4. Produce an ASCII flowchart showing the execution flow, e.g.:

```
main()
  → load_config()
  → build_client()
  → run_loop()
      → call_api()
      → if error → handle_error()
      → else → process_result()
```

5. Add a brief explanation of each step in the flow.
