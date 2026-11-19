# Starting Claude on this project (new computer)

Open Claude Code **inside the cloned repository folder** and paste this prompt:

```text
You are taking over the Legal Meaning Preservation (English/Hindi) project, a college NLP project
(CSET 346, PID-08) due for submission. Before doing anything:
1. Read HANDOVER.md completely (what is done, results, how to run, what is left).
2. Read CLAUDE.md (project spec, rules in §7, status in §1). Follow its rules exactly — in particular,
   never invent labels, results or legal text, and keep every disclosure about LLM labels in the paper.
3. Skim the last ~200 lines of docs/agents/agent-chat-history.md to see the decisions from 19 Nov 2026.
4. Run `.venv\Scripts\python -m pytest -q` (expect 46 passed) and report the result.
Then give me a short summary: what is finished, the headline results, and the open items from
HANDOVER.md §4 in priority order. Do not change any files until I tell you what to work on.
```

## Useful follow-up prompts

- **Human validation (highest priority):** "Help us score the 30-pair human validation workbook in
  data/annotation/pilot/ using guidelines/annotation_guidelines.md (we score, you explain the rubric), then
  compute LLM-vs-human correlation and add it to the paper with honest wording."
- **Rebuild everything after a change:** "Run `run_all.py report` and `paper\build.ps1`, then tell me which
  numbers in the paper changed."
- **Merge to main:** "Check that branch handover is merged into main on GitHub and that main passes the tests."

## How the project was built (context)
On 19 Nov 2026 three agents worked through a shared chat file (`agent-chat.md`, archived here as
`agent-chat-history.md`): CLAUDE-A (lead + data track), CLAUDE-B (reviewer, paper and slides) and CODEX
(builder, until its usage limit). That multi-agent setup is **not required** to continue: one Claude
session in this folder is enough. If you want to reuse it, `wait-turn.ps1` here is the turn-waiting
helper (copy it and `agent-chat.md` to the repo root).
