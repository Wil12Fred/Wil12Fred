---
name: repo-acceptance
description: >
  Use when a repository is created, imported or made public under the Wil12Fred
  GitHub account, or when asked whether a repo is "acceptable", "ready to publish",
  "ready to pin" or "up to standard". Runs the acceptance gates (secrets, personal
  data, organization names, non-redistributable code, license), brings the repo to
  the shared standard (MIT license, README template, CI, tests that are proven to
  fail), verifies on GitHub Actions, then names, tags and indexes it in the profile
  README. Do not use for reviewing a single pull request, or for private repos the
  owner has marked as off-limits.
---

# Repo acceptance

A repository is **accepted** when a stranger can open it, understand what it is,
build it, run it, and watch its tests pass in CI — and when publishing it exposes
nothing that is not the owner's to publish.

Acceptance has two halves, in this order:

1. **Gates** — hard vetoes. A repo that fails one is not polished; it is fixed or
   kept private. Nothing else is worth doing first.
2. **Standard** — what every accepted repo looks like, so twenty repos read as one
   body of work.

The full checklist with pass/fail definitions is
[`references/acceptance-criteria.md`](references/acceptance-criteria.md). The
standard itself is [`references/repo-standard.md`](references/repo-standard.md).
How to run the work with agents — and the mistakes that already happened — is
[`references/ai-engineering.md`](references/ai-engineering.md).

## The flow

```
intake → gates → standard → verify on GitHub → publish → index → report
```

### 1. Intake
- Clone into `~/Projects/Personal/src/<repo>`. Read the whole repo before changing it.
- Run the checker once to get the baseline:
  `python3 .claude/skills/repo-acceptance/scripts/check_repo.py ~/Projects/Personal/src/<repo>`
  (from the `Wil12Fred` profile repo). It reports PASS / WARN / FAIL per criterion.
- Decide what the repo is: a standalone project, or small material that belongs in
  an existing monorepo (`ai-algorithms`, `university-coursework`, `coding-challenges`).
  A project with its own identity stays standalone; exercises go to a monorepo.

### 2. Gates (G1–G6) — stop and ask the owner when one fails
- **G1 Secrets**: no tokens, keys, passwords or connection strings in the tree *or
  in history*. Move to env vars + `.env.example`. A secret that was ever public must
  be **revoked** — removing it from git does not un-publish it. Tell the owner which.
- **G2 Personal data**: no real names + IDs (DNI/RUC), phones, addresses, real
  e-mails in seeds, fixtures, dumps or screenshots. Replace with obviously fictitious
  data (`10000001`, `Ana Torres`), then offer a history rewrite.
- **G3 Organization names**: no employer, client, interview company or institution
  names in names, READMEs, packages, comments, metadata or commit messages. Personal
  repos are general-purpose. The private denylist lives at
  `~/.config/repo-acceptance/denylist.txt` — never commit it.
- **G4 Redistributability**: no files marked "proprietary", "confidential", "not for
  distribution", no vendored SDKs whose license forbids redistribution. Remove them
  (and from history), document where to download them, read them from a path
  (`$SDK/include`). Academic use does not change the license.
- **G5 Ownership**: the owner wrote it, or co-authored it. Someone else's repo is not
  polished for the portfolio — archive or delete it (owner's decision).
- **G6 License**: MIT (owner's choice). Third-party pieces under other licenses are
  listed as excluded in the README's License section.

History rewrites: always `git bundle create <backup> --all` first, rewrite with
`git filter-branch` (no new tools installed), `--force-with-lease` against the SHA you
measured, then verify with a **fresh mirror clone from GitHub**, not your local clone.

### 3. Standard (S1–S8)
Files, README template, build/test entry points, CI, naming, metadata — see
`references/repo-standard.md`. The rule for tests: **each new test must be shown to
fail when the behaviour it names is broken.** A green test that cannot go red has
measured nothing.

### 4. Verify on GitHub (V1–V4)
- Push to `main` and poll the Actions API until **every** workflow on that SHA
  concluded `success`. Read the job log for the test runner's own pass line — a green
  workflow that ran zero tests is not a pass.
- Whatever cannot be built locally (missing toolchain) is verified in CI, where the
  runner can install it. Do not install toolchains locally without asking the owner.
- GUI programs run headless: `env -u DISPLAY -u WAYLAND_DISPLAY xvfb-run -a …`. Never
  open windows on the owner's desktop.

### 5. Publish (P1–P5)
- Name: kebab-case, English, says what it is (`software-rasterizer-fltk`, not
  `ComputacionGrafica`). Rename via API (`PATCH /repos/Wil12Fred/<old>` `{"name":…}`);
  GitHub redirects the old URL. Update the local remote and folder.
- Description = README tagline. Topics: 5–8, lowercase (`computer-graphics`, `cpp`,
  `university-project` …).
- Default branch `main` (`POST /repos/…/branches/master/rename`).

### 6. Index
Add the repo to the profile README (`Wil12Fred/README.md`) under the right area,
one line: **[name](url)**: what it is. Stack. Keep areas sorted by strength, not
alphabetically. Suggest pinning only repos that pass every criterion with no WARN.
Pinning has no API — the owner does it in the web UI.

### 7. Report
Per repo: gate results, what changed (commit SHAs), tests added with their
red-without-fix proof, CI run URL + conclusion on the final SHA, known limitations
left, and **decisions that belong to the owner** (deletions, history rewrites,
third-party material). Report three numbers when work is in flight — verified,
in progress, pending — never one blended percentage.

## Owner decisions — always ask, never assume
License choice · deleting or archiving a repo · rewriting published history ·
anything about third-party material · installing software on the machine · touching
repos marked off-limits (currently the private `AMPLIFY-SERVERLESS-SAM`,
`STS-GATEWAY`, `English`).
