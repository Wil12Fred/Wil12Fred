# AI engineering — running repo work with agents

How an orchestrating agent drives acceptance across many repositories, and the
failures that already happened doing it. Each rule below cost time once.

## Roles

| Role | Does | Never |
|---|---|---|
| **Orchestrator** (main session) | inventory, gates, the standard, splitting work, verifying claims, talking to the owner | the bulk edits itself when they can be delegated |
| **Worker agent** | one disjoint set of repos, end to end: gates → standard → tests → CI green | touch a repo outside its set; decide owner questions |
| **Checker** (`check_repo.py`) | the deterministic criteria, same answer every run | judgement calls (is this person real? is this test meaningful?) |

## Splitting work
- **Disjoint repos per agent** — then each clone has exactly one writer and no
  worktrees are needed. Worktrees are for two agents in *one* repo.
- Group by stack (C++ graphics, C++ algorithms, web/Python/Java, mobile/coursework),
  4–6 repos per agent, one agent for any repo with security work.
- Write the standard **once** to a file and point every agent at it; a brief retyped
  five times drifts five ways.
- Centralize cross-repo mechanics *before* spawning (default-branch rename, renames,
  deletions): two agents racing on GitHub settings is unrecoverable confusion.

## Proof, not reports
- A worker's "all green" is a claim. The orchestrator re-runs a sample in a clean
  `git archive origin/main` export and repeats one mutation per report.
- **Red-without-fix**: commit the fix first, copy the file aside, break it, run the
  test, restore **from your copy** (never `git checkout --`, which restores the
  committed version and silently deletes unproved work), check the hash came back.
- A green workflow that ran zero tests is not a pass: grep the job log for the test
  runner's own summary line.
- Progress is counted as *validated*: report verified / in flight / pending, never a
  blended percentage.

## CI as the verification machine
- Tools not installed locally are not installed — CI installs them (apt in the runner:
  fpc/lazarus, spim, openmpi, libntl-dev, libfltk1.3-dev, Maven via wrapper, MySQL /
  Postgres service containers). Iterate push → poll → read log → fix.
- Poll the Actions API with `head_sha=<sha>`; wait until every run is `completed`.
- Job logs redirect to blob storage: `curl -sL` (drops the auth header on redirect);
  urllib forwards it and gets 401.
- A YAML value containing `: ` must be quoted or block-scalar, or GitHub shows a run
  with the file path as its name and **no jobs**.
- On Ubuntu runners `sh` is dash: call `bash ./gradlew`.
- CRA treats warnings as errors when `CI=true` — fix the warnings rather than
  setting `CI=false`.

## The owner's machine is not a test bench
- Ask before installing anything, even in user space. If something was installed,
  remove it when the work is done.
- GUI runs only under a private display: `env -u DISPLAY -u WAYLAND_DISPLAY xvfb-run -a`.
  A test once opened a black window on the owner's desktop; bake xvfb into `make test`
  so strangers are protected too.
- Never `git clean` a shared tree; stage by name.

## History rewrites (published repos)
1. `git bundle create ~/Projects/Personal/backups/<date>/<repo>.bundle --all`.
2. `git filter-branch` with `--index-filter` (remove paths) or `--tree-filter`
   (rewrite content) on every branch that is published.
3. `git push --force-with-lease=<branch>:<measured-sha>`.
4. `git remote prune origin`, expire reflog, `gc --prune=now` — a stale
   `origin/master` from before a branch rename kept the old data alive locally.
5. Verify in a **fresh `--mirror` clone from GitHub**.
6. Tell the owner GitHub may serve old SHAs until its own GC; only support can purge.
7. Old dependabot / PR branches carry the old history — delete them (owner's OK).

## Shell traps seen here
- zsh does not word-split `$var` (`set -- $spec` gives one argument); use
  `${=var}` or a Python script.
- `git -c "a=b -c c=d"` as one string fails; pass each `-c` separately.
- `rg`/`grep` output can be redacted in some agent environments — use it to find
  *where*, then read the file.
- `git filter-branch` has no `-q`.

## Identity and attribution
- Commit as the owner with the personal address used in that repo's history; never
  a work address. `*.local` hostnames are not addresses.
- Every agent commit carries the `Co-Authored-By` trailer.
- Rewriting history to change author e-mails is a gate-G3 fix, done once, with backup.

## Monitoring long runs
A poll loop that prints only on change (`n/N completed | ok: … | CI red: …`) gives
the owner a live count without noise; re-arm it when it expires. "Completed" is
defined by the checker + CI on GitHub, not by an agent saying so.
