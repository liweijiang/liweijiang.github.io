# SEAL-Guard Build Plan

The goal: a small checker that sits next to an agent and does two jobs.

1. Before the agent reads its context, label where each piece came from and flag
   anything suspicious.
2. Before the agent does something, check the action and decide: allow, ask the
   user, or block.

It remembers what it flagged earlier, so a bad action later can be traced back to a
suspicious input from before. It can also take an optional policy and flag things
that break that specific policy, on top of the common-sense risks it always checks.

Below is the order I'd build it in. Each phase says what you build and how the
existing AgentDoG work saves you time.

---

## Phase 0 — Decide the scope (a few days)

Write down, in one page:

- The list of attacks you want to stop (fake instructions hidden in tool results,
  poisoned documents, sending data to outsiders, destructive commands, the agent
  drifting off the user's original request).
- The two kinds of risk you report: common-sense risks (always on) and policy
  risks (only when a policy is given).
- What "success" looks like: fewer attacks get through, and normal tasks still work
  without being blocked.

This keeps you honest later about what the project is and isn't.

---

## Phase 1 — The plumbing, no model yet (1–2 weeks)

First, settle on the trajectory format. Adopt **ATIF** (the Harbor Agent Trajectory
Interchange Format) instead of inventing your own. It already has steps, tool calls,
observations, multi-turn, and an `extra` field to hang your annotations on, and
several real agents (Claude Code, Codex, OpenHands, Gemini CLI) already emit it. You
also get Harbor's validator and data models for free, so you can confirm your inputs
are well-formed without writing that yourself.

Then build the part that hooks into an agent loop and grabs two things:

- a tool result just after it comes back, before the agent reads it, and
- the action the agent wants to take, just before it runs (in ATIF terms: a step
  that has `tool_calls` but no `observation` yet).

Tag each piece by where it came from using simple rules (no model needed): system
prompt and user message are trusted; tool results, fetched web pages, and documents
are untrusted and should be treated as data only. Point at things using ATIF ids
(e.g. `step:3#obs:call_2`). At this point you have the "labeling" layer working with
plain rules and zero model cost.

**How AgentDoG helps:** their released trajectories use a clear
`[USER] / [AGENT] / [ENVIRONMENT]` structure with tool lists attached, so they
convert cleanly into ATIF. You can practice your tagging code on their data instead
of collecting your own.

---

## Phase 2 — The checker model (3–5 weeks)

Train a small model to do the two jobs: flag suspicious incoming pieces, and judge
proposed actions. Start small (a sub-1B or ~2B model) so it's cheap to run on every
step.

Getting the training data is the main work, and this is where you save the most
time:

- Take AgentDoG / ATBench trajectories. They already mark which trajectories are
  unsafe and why.
- Their "risk source" labels tell you which incoming piece was the problem — that
  becomes your input-side training signal.
- Their "failure mode" and "harm" labels tell you which action was the problem —
  that becomes your output-side training signal.
- Use a strong model (or AgentDoG's own bigger model) as a teacher to write the
  plain-language `description`, `why_it_matters`, and the correct `recommended_action`
  for each case.

**How AgentDoG helps:** you reuse their trajectories, their labels, and their
data-generation pipeline instead of building a dataset from scratch. You also
borrow their recipe for training a good checker from only about a thousand
well-chosen examples.

---

## Phase 3 — Memory across steps (1–2 weeks)

This is the part that makes the project stand out, so don't skip it.

Carry a running record through the whole run: what's been flagged, what the agent
has already done, and what the user originally asked for. When the agent proposes an
action, check it against that record — not just the current step. If an action
traces back to something flagged earlier, connect them and say so (the
`traces_back_to` field).

The test case to nail: a suspicious instruction comes in at step 2, and the harmful
action happens at step 9. A checker that only looks at step 9 misses it. Yours
catches it because it remembers.

**How AgentDoG helps:** their harder benchmark sets include exactly these
"the trigger and the harm are far apart" cases, so you have ready-made examples to
test against.

---

## Phase 4 — Policy mode (2–3 weeks)

Add the optional policy input. When no policy is given, you only report common-sense
risks. When a policy is given, you also flag things that break it, and point back to
the exact rule (id, clause, and the requirement in plain words).

Start with policies written as plain text. The interesting test: give the checker
policies it has never seen during training and see if it can still follow them. That
ability — handling new rules on the fly — is something the fixed-category checkers
can't do, so it's worth showing off.

---

## Phase 5 — Make it fast enough (1 week)

Checking twice on every step is slow. Cut the cost:

- On the input side, only re-check pieces that are new since last step.
- On the output side, only run the full check on actions that actually matter —
  sending, deleting, paying, replying to the user. Let harmless read-only steps
  through on a fast path.

Measure the added delay and report it honestly.

---

## Phase 6 — Evaluate (2–3 weeks)

Show two numbers and the trade-off between them:

- **Attacks stopped:** run known attack test sets (AgentDojo, InjecAgent, and
  AgentDoG's harder benchmarks). Report how many attacks the layer blocks.
- **Normal tasks preserved:** run benign tasks and report how often the layer wrongly
  blocks or nags. A guard that blocks everything is useless.

Then the key comparison: run the same agent with the layer on and off, so the
improvement is clearly from your layer and not the underlying model. Call out the
"trigger and harm far apart" cases separately, since that's where your memory design
should win.

**How AgentDoG helps:** you can use their existing checker as one of your comparison
points, and their benchmark as one of your test sets.

---

## Phase 7 — Stretch: teach the agent to need the layer less (later)

Take the labeled, annotated runs you've produced and fine-tune the underlying agent
on them. Then test whether the agent stays safer even with your layer turned off. If
it does, you've shown that an external checker can be "baked into" the model over
time. That's a strong follow-up result, but it's optional and comes after the core
system works.

---

## How to stay different from AgentDoG (keep repeating this)

AgentDoG looks at a whole run after the fact and gives it a grade. SEAL-Guard sits
inside the run, labels inputs before the agent reads them, checks actions before they
happen, and remembers across steps so it can connect a late action to an early
warning. Same labels, different job and different timing. Say this plainly in the
paper so reviewers don't mistake one for the other.
