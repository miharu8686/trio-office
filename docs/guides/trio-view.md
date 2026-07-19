# Trio View — Design Notes

trio-office visualizes a three-role development system on top of the
claude-office pixel office:

- **PO (Product Owner)** — the human. Decides scope, reviews results,
  answers permission requests, issues the next instruction.
- **Designer** — the role that turns intent into implementable units
  (state files, unit instructions, judgment heuristics). May be human,
  a separate model session, or the same human as the PO.
- **CC (Claude Code)** — the executing agent: the boss character and its
  subagent employees, exactly what upstream claude-office already draws.

## What we can and cannot measure

Hooks only instrument the CC side. The office therefore *shows* CC working,
but the interesting bottleneck in a trio system is usually the opposite
direction: **CC waiting on the PO**. That waiting state is measurable without
instrumenting the human at all, because it is exactly the set of hook events
that end a CC turn:

| Event               | Meaning                        | Desk item    |
|---------------------|--------------------------------|--------------|
| `Stop`              | CC finished, report delivered  | 完了報告     |
| `PermissionRequest` | CC blocked on an approval      | 許可待ち     |
| `Notification`      | CC asks for input              | 入力待ち     |

Each such event stacks a document on the **PO REVIEW desk**. The next
`UserPromptSubmit` in the same session clears that session's stack — the PO
has judged and issued the next instruction. A `Stop` also clears any
permission/input items first: a finished turn means those blocks were
resolved, so only the report remains waiting. Stack height and per-item age
("waiting 12m") make the current bottleneck visible at a glance: a tall,
aging stack means the human is the constraint, not the agent.

## Why the Designer is not drawn (yet)

Design work happens outside the hook-instrumented boundary (editing state
files, writing unit instructions), so there is no event source to render
honestly. Rather than fake it, the MVP omits the role. Future extension:
watch designated state/instruction files (mtime or git activity) and light
up a Designer desk when they change, or accept explicit "design session"
markers via the events API.
