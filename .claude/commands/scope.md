---
description: Clarify, plan, and get approval before doing any work on a task
---

When this command is invoked, the user will give you a task. Do NOT start working
on it right away. Follow this workflow strictly:

1. **Ask clarifying questions first.** Before touching any code or making any
   changes, ask the user **at least 5 clarifying questions** covering:
   - The underlying goal (what success looks like, why it matters)
   - The scope (what's included, what's explicitly out of scope)
   - Constraints (technical, time, compatibility, dependencies)
   - Exactly how they want it done (approach, conventions, preferences)
   - Anything ambiguous in the request
   Then **wait** for the user's answers. Do not proceed until they respond.

2. **Enter plan mode.** Once the user has answered, research the relevant code
   and context (read files, search the codebase, understand the existing
   patterns). Then produce a **complete, step-by-step plan** describing exactly
   how you'll carry out the task.

3. **Wait for explicit approval.** Present the plan and wait for the user's
   explicit go-ahead. Do **not** write or change anything until the user says
   to proceed (e.g. "go", "approved", "do it").

4. **Build it.** Only after the plan is approved, implement the task following
   the agreed plan.

The task is:

$ARGUMENTS
