---
name: ensemble-review
description: Review code changes using multiple models in parallel, then synthesize a unified report.
---

# Ensemble Review

## Steps

1. Get the diff to review:
   - Run `git diff main...HEAD` via bash to get the current branch's changes
   - If no changes found, tell the user there are no changes to review

2. Spawn 3 subagents, each with a different model. Give each the diff as part of the prompt:

   Models to use:
   - `oci/openai.gpt-5.4`
   - `oci/google.gemini-2.5-flash`
   - `oci/xai.grok-code-fast-1`

   Use `spawn_subagent` for each model with this prompt (include the diff inline):
   > Review this code diff. Identify bugs, security issues, performance problems,
   > and readability concerns. For each issue, provide the file, line, severity
   > (critical/warning/info), and a brief explanation.
   >
   > <diff>
   > {paste the diff here}
   > </diff>

   Use tools: ["read_file", "list_files", "grep"] so reviewers can check surrounding code.

3. Collect all 3 reviews. Note any subagents that failed and which models succeeded.

4. Synthesize a unified report:
   - **Consensus issues**: flagged by 2+ models (high confidence)
   - **Unique findings**: flagged by only 1 model (review manually)
   - **Summary**: overall assessment combining all perspectives

5. Present the report to the user.
