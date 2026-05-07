Walk through every open GitHub issue for the SC Profile Editor repository, read each one carefully, and produce a triage report grouped by recommended next action.

# Invocation

`/issues` — process every open issue and produce the report.

(For drilling into a single issue interactively, use `gh issue view <N>` directly — this command is for sweeping the whole backlog.)

# Repository

`Osiris-DevWorks/sc-profile-editor`

# Behavior

This is a **read-only** command. Do not close, label, comment on, or otherwise mutate issues on GitHub. Produce a report; the user decides what to act on.

## 1. Fetch the full backlog

Use `gh` (it reuses the user's existing GitHub auth — no API token plumbing needed). If `gh` is not on PATH, fail loudly with a clear message instead of guessing.

```
gh issue list --repo Osiris-DevWorks/sc-profile-editor --state open --limit 200 \
  --json number,title,labels,createdAt,updatedAt,author,comments,body,url
```

That single call returns body + comment counts. For issues where the comment count is non-zero and the body alone is ambiguous, fetch the comments too:

```
gh issue view <N> --repo Osiris-DevWorks/sc-profile-editor --comments
```

Don't fetch comments for every issue up front — that's `N` API calls when you might only need a handful. Be selective.

## 2. For each issue, decide a verdict

Read each issue and classify it into one of:

- **fix-now** — clearly actionable, scoped, and the fix likely lives in this repo. Estimate effort: S / M / L.
- **needs-info** — bug report or feature request that's missing reproducer, version, log, or scope. Note exactly what's missing.
- **stale** — last activity >6 months ago AND no recent comments AND not pinned. Likely safe to close after a "still relevant?" ping.
- **duplicate** — looks like another open issue. Reference the suspected primary by `#N`.
- **fixed-in-code** — the symptom described appears resolved by current code (check `docs/CHANGELOG.md` and recent git log against the description). Recommend closing with reference to the fixing commit/version.
- **wontfix-out-of-scope** — outside this app's scope (Linux/macOS port, third-party integration we don't own, etc.). Recommend closing with explanation.
- **discussion** — design/feedback/idea thread. No fix to ship; track separately.

Don't force a verdict — if the issue is genuinely ambiguous, mark it `unclear` and note what would tip you one way or the other.

## 3. Cross-check against current code before claiming "fixed-in-code"

Before saying an issue is fixed:

- Search `docs/CHANGELOG.md` for the issue number (e.g. `#14`) — it's often referenced.
- `git log --all --grep="#<N>"` to find commits that mention it.
- If the issue describes a symptom in a specific file, read that file and verify the symptom isn't reproducible from the current code.

A confident "fixed-in-code" verdict needs at least one of: changelog mention, commit reference, or a code read that contradicts the bug description. Otherwise downgrade to `unclear`.

## 4. Output format

Lead with a one-line tally:

```
N open · X fix-now · Y needs-info · Z stale · W fixed-in-code · ...
```

Then group by verdict, highest-priority first (fix-now → fixed-in-code → needs-info → duplicate → stale → wontfix → discussion → unclear). Within each group:

```
#<N> — <title>
  <one-sentence summary>
  Verdict: <verdict>[ · effort: S/M/L][ · suspected dup of #<M>]
  Next action: <one short imperative sentence>
```

Keep each issue's block to ~3 lines. The user is scanning, not reading prose.

End with:

```
Recommended sweep order: <#X, #Y, #Z>  (the fix-now items, ordered by leverage)
```

# Output style

- Lead with the tally; no preamble.
- Issue numbers as `#N` so they're click-targets in the terminal.
- Don't fabricate URLs — the JSON gave you `url`, use it.
- Don't volunteer to fix anything in the report itself. The user picks the order.
- If the backlog is empty, say so and stop — don't pad with structure.
