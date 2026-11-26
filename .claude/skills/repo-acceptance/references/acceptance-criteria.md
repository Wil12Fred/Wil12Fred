# Acceptance criteria

Each criterion is **PASS**, **WARN** (a human looks before publishing) or **FAIL**
(not accepted). `check_repo.py` automates the ones marked ⚙; the rest need judgement.

## Gates — any FAIL blocks acceptance

| ID | Criterion | PASS when | Checked by |
|---|---|---|---|
| G1 | No secrets | no key/token/password literals in the tree; history scanned; config from env + `.env.example` | ⚙ tree + history patterns, then read |
| G2 | No personal data | seeds, dumps, fixtures and screenshots hold fictitious people only | ⚙ ID-like numbers / e-mails / phones in data files → WARN, then read |
| G3 | No organization names | none of the denylist names in files, paths or commit messages | ⚙ against `~/.config/repo-acceptance/denylist.txt` |
| G4 | Redistributable | no "proprietary / confidential / not for distribution" files; vendored third-party code has a license that allows it | ⚙ markers, then read licenses |
| G5 | Owner's work | the owner authored or co-authored it | `git log --format=%an` + judgement |
| G6 | Licensed | `LICENSE` is MIT with `Copyright (c) <first-year>-<now> Wilber Cutire` (+ ` and contributors` when others are credited) | ⚙ |

## Standard

| ID | Criterion | PASS when | Checked by |
|---|---|---|---|
| S1 | README structure | sections in template order (see repo-standard.md) | ⚙ |
| S2 | README language | English; identifiers and code comments may stay as written | ⚙ heuristic |
| S3 | Badges | CI badge pointing at the repo's own workflow + MIT badge | ⚙ |
| S4 | Clean tree | nothing generated tracked: binaries, `node_modules`, venvs, build dirs, `.DS_Store`, IDE folders, editor swap files | ⚙ |
| S5 | `.gitignore` | exists and fits the stack | ⚙ exists |
| S6 | One build/test entry point | `make test`, `npm test`, `uv run pytest`, `./gradlew test`, `./mvnw verify` … documented in README | ⚙ presence, then run |
| S7 | Tests are real | each new test fails when the behaviour it names is broken (proof recorded) | human/agent, never trusted from a summary |
| S8 | No dead weight | no stale TODOs claiming bugs that are fixed; known limitations listed instead | read |

## Verification

| ID | Criterion | PASS when | Checked by |
|---|---|---|---|
| V1 | CI exists | `.github/workflows/ci.yml` (`name: CI`) or one `<folder>.yml` per monorepo folder | ⚙ |
| V2 | CI green on GitHub | every workflow run for `origin/main`'s SHA concluded `success` | ⚙ `--github` |
| V3 | CI actually tested | the job log shows the runner's pass line with a non-zero count | read the log |
| V4 | Headless | GUI tests run under `xvfb-run`; `make test` never opens a window | ⚙ grep for xvfb in GUI repos, then run |

## Publishing

| ID | Criterion | PASS when | Checked by |
|---|---|---|---|
| P1 | Name | kebab-case English describing the content | ⚙ |
| P2 | Default branch | `main` | ⚙ |
| P3 | Description | set, and matches the README tagline in substance | ⚙ `--github` (set) |
| P4 | Topics | 5–8 | ⚙ `--github` |
| P5 | Indexed | listed in the profile README under its area | ⚙ `--profile` |

## Verdict
- **Accepted**: no FAIL, every WARN read and resolved or explained.
- **Accepted, not pin-worthy**: accepted, but with open security issues or a
  BUILD-NOT-VERIFIED part (e.g. a proprietary SDK). Known limitations say so.
- **Rejected**: any gate FAIL. Fix, keep private, archive or delete — owner decides.
