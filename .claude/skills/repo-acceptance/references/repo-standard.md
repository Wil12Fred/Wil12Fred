# Repository standard — public repos of the Wil12Fred account

Owner's goal: every repo is polished, standardized and *proven* to work — a stranger
can understand it, build it, run it and see its tests pass in CI.

Clones live in `~/Projects/Personal/src/<repo>`. Default branch is `main` everywhere.

## 1. Files every repo has
- `README.md` — structure below.
- `LICENSE` — **MIT**. First line `MIT License`, then
  `Copyright (c) <year of first commit>-2026 Wilber Cutire` — add ` and contributors`
  when `git log --format=%an` shows other people. Standard MIT text, nothing else.
- `.gitignore` fitting the stack; nothing generated is tracked (build output, binaries,
  `node_modules`, venvs, `__pycache__`, IDE dirs, `.DS_Store`). Check with
  `git ls-files` — untrack with `git rm --cached`, never delete sources/assets.
- `.github/workflows/ci.yml`, workflow `name: CI` (one file; a monorepo keeps one
  workflow per folder named `<folder>.yml`, each `name: <folder>`). Triggers: `push`
  and `pull_request`. If a repo already has `build.yml`/other, rename/merge into `ci.yml`.
- No secrets: config from env vars, documented in `.env.example`.

## 2. README structure (English, in this order; omit a section only if truly N/A)
```
# <repo-name>

[![CI](https://github.com/Wil12Fred/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/Wil12Fred/<repo>/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<one or two sentences: what it is and why it is interesting>

<screenshot / sample output if there is one — docs/ folder>

## Features            (bullets, concrete)
## Requirements        (exact packages: Debian/Ubuntu apt names, and Arch names)
## Build
## Run                 (real command + real output captured from a real run)
## Tests               (how to run them, what they cover)
## Project layout      (short tree, only meaningful entries)
## Known limitations   (honest: bugs left, missing pieces, deprecated APIs)
## Background          (course/context and year; "a university course", never an institution name)
## License             (MIT — see LICENSE)
```
Monorepo root README: same header/badges(one per folder workflow is fine, or a list),
then a table of folders; each folder's README follows the template above (badge points
at `<folder>.yml`).

## 3. Build and test entry points (uniform per stack)
- C / C++: `Makefile` with `all`, `test`, `clean` (CMake is fine if already used; then
  document `cmake -B build && cmake --build build && ctest --test-dir build`).
- Python: `uv` project (`pyproject.toml` + `uv.lock`), `uv run pytest` (or the existing
  unittest runner via `uv run`).
- Node: `npm ci`, `npm run lint`, `npm run build`, `npm test`.
- JVM/Android: the Gradle/Maven wrapper (add `mvnw` if Maven has none).
- Free Pascal / Lazarus, MIPS, etc.: whatever the CI runner can install via apt.

## 4. "Probado" — what counts as tested
Every repo has automated tests that run in CI and are green **on GitHub**:
- CLI programs: golden tests — run the program on committed sample input
  (`tests/` or `examples/`) and compare with committed expected output. Programs with
  randomness: fix the seed if the code allows, otherwise assert invariants
  (exit code, format, bounds, convergence), not exact numbers.
- Libraries / data structures / algorithms: unit tests of real behaviour (insert/delete/
  search invariants, round trips like encrypt→decrypt, known answers).
- GUI programs: build in CI + a headless smoke run under `xvfb-run` with `timeout`
  (exit 124 = still running = pass) plus unit tests of the non-GUI logic where it is
  separable without rewriting the program.
- Web/back-end: the framework's test runner with real assertions on endpoints
  (status codes and bodies), using SQLite / in-memory / service containers in CI.
- A test must fail when the behaviour it names is broken: for each new test file,
  break the code once (copy the file aside first, restore from your copy, never
  `git checkout --`) and confirm it goes red. Report it.
- Things that cannot be verified locally (missing toolchain — **do not install anything
  locally**; project-local deps are fine) MUST be verified in GitHub Actions instead:
  push, then poll the run via the API until it concludes; fix and repeat until green.
  "BUILD NOT VERIFIED" is acceptable only when even CI cannot do it (e.g. a proprietary
  SDK, or source files that were never committed) — then say exactly why in README.

## 5. Code changes allowed
- Fix real bugs you find (with a test). Fix compiler warnings that indicate bugs.
- Do not rewrite programs, rename public APIs or add features. No mass reformatting.
- Keep identifiers/comments in their original language; docs are English.
- No company, employer or institution names anywhere (code, docs, metadata).

## 6. Git
- Small conventional commits in English (`docs:`, `test:`, `ci:`, `fix:`, `chore:`, `build:`).
- Identity: `git -c user.name="Wilber Cutire" -c user.email=<addr>` — the address Wilber
  used most in that repo's history, ignoring other people and `*.local` hostnames;
  fallback: the owner's main personal address. Never a work/employer address.
- Every commit message ends with:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- **Push to `origin main` is authorized** (needed to see CI). Never force-push, never
  rewrite history, never `git clean`, never touch other repos or branches.
- GitHub API: token via `$(secret-tool lookup service github account Wil12Fred)` —
  never print it. Useful: `GET /repos/Wil12Fred/<r>/actions/runs?head_sha=<sha>`,
  job logs at `/actions/jobs/<id>/logs` (use `curl -sL`; the redirect drops the auth
  header correctly).
- Also set the repo `description` via API if it does not match the README tagline
  (`PATCH /repos/Wil12Fred/<r>` with `{"description": ...}`). Do not change topics,
  visibility, name or settings.

## 7. Final report (per repo, concise)
- checklist: LICENSE / README sections / .gitignore clean / ci.yml / tests
- tests added: what each asserts + red-without-fix proof
- CI: run URL + conclusion on the final pushed sha
- bugs fixed; known limitations left
- commits (sha + subject)
