---
name: code-review
description: Review a source file for code quality, potential issues, and improvement suggestions.
---

# Code Review

## Steps

1. Search for common patterns that may indicate issues:
   ```
   Use grep to search for "TODO|FIXME|HACK|XXX" in the file
   ```

2. Check for error handling:
   ```
   Use grep to search for "try|except|raise" in the file
   ```

3. Evaluate the code against these criteria:
   - **Readability**: Are names clear? Is the structure logical?
   - **Error handling**: Are failures handled gracefully?
   - **Complexity**: Are there overly long functions or deep nesting?
   - **Security**: Any hardcoded secrets, unsafe operations, or injection risks?

4. Produce a review with:
   - **Strengths**: What the code does well (2-3 points)
   - **Issues**: Problems found, ranked by severity
   - **Suggestions**: Concrete improvements with code examples where helpful
