#!/usr/bin/env python3
"""Check a repository against the acceptance criteria (references/acceptance-criteria.md).

usage: check_repo.py <repo-dir> [--github] [--profile <profile-README>] [--json]

Stdlib only. Prints one row per criterion (PASS / WARN / FAIL) and exits 1 if any
criterion FAILs. --github also asks the GitHub API (CI on origin/main, description,
topics, default branch); the token comes from $GITHUB_TOKEN or the keyring
(`secret-tool lookup service github account Wil12Fred`) and is never printed.

The organization denylist is private and lives outside every repo:
~/.config/repo-acceptance/denylist.txt (one term per line, '#' comments), or the
path in $REPO_ACCEPTANCE_DENYLIST.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

OWNER = "Wil12Fred"
LICENSE_HOLDER = "Wilber Cutire"
DENYLIST = pathlib.Path(os.environ.get("REPO_ACCEPTANCE_DENYLIST",
                                    pathlib.Path.home() / ".config/repo-acceptance/denylist.txt"))
MAX_BYTES = 1_000_000

README_SECTIONS = ["Features", "Requirements", "Build", "Run", "Tests",
                   "Project layout", "Known limitations", "Background", "License"]
README_REQUIRED = ["Build", "Tests", "License"]

STRONG_SECRETS = re.compile(
    r"AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|xox[abpr]-[0-9A-Za-z-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|AIza[0-9A-Za-z_-]{35}")
GENERIC_SECRET = re.compile(
    r"""(?i)\b(password|passwd|pwd|secret|secret_key|api[_-]?key|token)\b\s*[:=]\s*["']([^"'\s]{6,})["']""")
PLACEHOLDER = re.compile(r"(?i)change[-_ ]?me|example|placeholder|xxx+|\$\{|<[^>]+>|dummy|fake|test|dev-only|insecure|your[-_]")
PROPRIETARY = re.compile(r"(?i)proprietary and confidential|not for (re)?distribution|confidential and proprietary")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ID_NUMBER = re.compile(r"(?<![\d.])\d{8}(?:\d{3})?(?![\d.])")
PHONE = re.compile(r"(?<!\d)(?:\+?51[ -]?)?9\d{2}[ -]?\d{3}[ -]?\d{3}(?!\d)")
DATA_SUFFIXES = {".sql", ".csv", ".tsv", ".json", ".txt"}
SAFE_EMAIL = re.compile(r"(?i)example\.|noreply|no-reply|localhost|users\.noreply\.github\.com|@anthropic\.com$")
JUNK = re.compile(
    r"(^|/)(node_modules|__pycache__|\.venv|venv|\.idea|\.vscode|target|\.gradle|xcuserdata)/"
    r"|\.(o|exe|dll|so|dylib|class|pyc|apk|aab|ipa|swp|swo)$|(^|/)\.DS_Store$|(^|/)a\.out$")
MAYBE_VENDORED = re.compile(r"(^|/)(build|dist|out)/")
LOCKFILE = re.compile(r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|uv\.lock|poetry\.lock|Cargo\.lock|composer\.lock|Gemfile\.lock)$")
TESTY = re.compile(r"(?i)(^|/)(tests?|spec|e2e|fixtures?|__tests__)/|(^|/)tests?(_[^/]*)?\.[a-z]+$|[._-](test|spec)\.[a-z]+$")
SPANISH = set("el la los las de del que y en un una para por con como es son se no al lo más este esta "
              "estos sus su pero también donde cuando programa archivo".split())
GUI_HINT = re.compile(r"glut|GLUT|fltk|FL/Fl|QApplication|QtWidgets|SFML|tkinter|pygame")


def looks_fake(value: str) -> bool:
    """Low-entropy or obviously illustrative values are documentation, not secrets."""
    body = re.sub(r"^[A-Za-z]{2,5}[-_]", "", value)
    return len(set(body)) < 8 or bool(re.search(r"(?i)123456|abcdef|example|fake|dummy|x{6,}|a{6,}|0{6,}", value))


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, cid: str, status: str, detail: str) -> None:
        self.rows.append((cid, status, detail))

    def failed(self) -> bool:
        return any(s == "FAIL" for _, s, _ in self.rows)


def git(repo: pathlib.Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout


def ignored_paths(repo: pathlib.Path) -> list[str]:
    """Globs from .repo-acceptance-ignore: files that hold patterns on purpose (the checker itself)."""
    p = repo / ".repo-acceptance-ignore"
    if not p.exists():
        return []
    return [l.split("#")[0].strip() for l in p.read_text().splitlines() if l.split("#")[0].strip()]


def tracked_text_files(repo: pathlib.Path) -> list[tuple[str, str]]:
    out = []
    skip = ignored_paths(repo)
    for rel in git(repo, "ls-files", "-z").split("\0"):
        if not rel or any(fnmatch.fnmatch(rel, g) for g in skip):
            continue
        p = repo / rel
        try:
            if not p.is_file() or p.stat().st_size > MAX_BYTES:
                continue
            b = p.read_bytes()
        except OSError:
            continue
        if b"\0" in b[:8000]:
            continue
        out.append((rel, b.decode("utf-8", "replace")))
    return out


def repo_name(repo: pathlib.Path) -> str:
    url = git(repo, "remote", "get-url", "origin").strip()
    m = re.search(r"[/:]([^/:]+?)(?:\.git)?$", url)
    return m.group(1) if m else repo.name


def check_secrets(repo, files, rep):
    strong = [rel for rel, t in files if any(not looks_fake(m.group(0)) for m in STRONG_SECRETS.finditer(t))]
    generic = []
    for rel, t in files:
        for m in GENERIC_SECRET.finditer(t):
            if not PLACEHOLDER.search(m.group(2)) and not rel.endswith((".example", ".md")) and not TESTY.search(rel):
                generic.append(rel)
                break
    hist_hits, cur = set(), None
    for line in git(repo, "log", "--all", "-p", "--no-color", "-G", STRONG_SECRETS.pattern, "--format=@@%h").splitlines():
        if line.startswith("@@") and re.fullmatch(r"@@[0-9a-f]{7,12}", line):
            cur = line[2:]
        elif line.startswith("+") and cur and any(not looks_fake(m.group(0)) for m in STRONG_SECRETS.finditer(line)):
            hist_hits.add(cur)
    hist_hits = sorted(hist_hits)
    if strong or hist_hits:
        rep.add("G1", "FAIL", f"strong secret patterns in {strong[:5]} history commits {hist_hits[:5]} — revoke, then remove")
    elif generic:
        rep.add("G1", "WARN", f"possible hard-coded credentials in {generic[:5]}")
    else:
        rep.add("G1", "PASS", "no secret patterns in tree or history")


def check_personal_data(files, rep):
    hits = []
    for rel, t in files:
        if pathlib.Path(rel).suffix.lower() not in DATA_SUFFIXES or LOCKFILE.search(rel) or rel.startswith(".github/"):
            continue
        ids = {n for n in ID_NUMBER.findall(t) if not re.fullmatch(r"(\d)\1{7,}|[12]0{6,}\d{1,4}|19\d{6}|20\d{6}", n)}
        mails = {e for e in EMAIL.findall(t) if not SAFE_EMAIL.search(e)}
        phones = set(PHONE.findall(t))
        if ids or mails or phones:
            hits.append(f"{rel} (ids={len(ids)} emails={len(mails)} phones={len(phones)})")
    rep.add("G2", "WARN" if hits else "PASS",
            ("read these and make the people fictitious: " + "; ".join(hits[:6])) if hits else "no ID-like data in data files")


def check_denylist(repo, files, rep):
    if not DENYLIST.exists():
        rep.add("G3", "WARN", f"denylist missing: create {DENYLIST}")
        return
    terms = [t.strip() for t in DENYLIST.read_text().splitlines() if t.strip() and not t.startswith("#")]
    pat = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(t) for t in terms) + r")(?![A-Za-z0-9])", re.I) if terms else None
    if not pat:
        rep.add("G3", "WARN", "denylist is empty")
        return
    where = [rel for rel, t in files if pat.search(t) or pat.search(rel)]
    authors = sorted({m.group(1).lower() for m in pat.finditer(git(repo, "log", "--all", "--format=%an %ae %cn %ce"))})
    messages = sorted({m.group(1).lower() for m in pat.finditer(git(repo, "log", "--all", "--format=%s %b"))})
    if where or authors or messages:
        parts = []
        if where:
            parts.append(f"files {where[:6]}")
        if authors:
            parts.append(f"author/committer identities ({', '.join(authors)})")
        if messages:
            parts.append(f"commit messages ({', '.join(messages)})")
        rep.add("G3", "FAIL", "organization names in " + "; ".join(parts) + " — history fixes need the owner's OK")
    else:
        rep.add("G3", "PASS", f"none of {len(terms)} denylisted names in files, paths or history metadata")


def check_proprietary(files, rep):
    hits = [rel for rel, t in files if PROPRIETARY.search(t)]
    rep.add("G4", "FAIL" if hits else "PASS",
            f"non-redistributable markers in {hits[:6]}" if hits else "no proprietary/not-for-distribution markers")


def check_license(repo, rep):
    p = repo / "LICENSE"
    if not p.exists():
        rep.add("G6", "FAIL", "no LICENSE file")
        return
    t = p.read_text(errors="replace")
    ok = t.startswith("MIT License") and re.search(r"Copyright \(c\) \d{4}(-\d{4})? " + re.escape(LICENSE_HOLDER), t)
    rep.add("G6", "PASS" if ok else "FAIL", "MIT, owner named" if ok else "LICENSE is not the standard MIT text with the owner's copyright")


def readme_sections(text: str) -> list[str]:
    no_code = re.sub(r"```.*?```", "", text, flags=re.S)
    return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+?)\s*$", no_code, re.M)]


def check_readme(repo, rep, monorepo: bool):
    p = repo / "README.md"
    if not p.exists():
        rep.add("S1", "FAIL", "no README.md")
        return
    text = p.read_text(errors="replace")
    secs = readme_sections(text)
    known = [s for s in secs if s in README_SECTIONS]
    order_ok = known == sorted(known, key=README_SECTIONS.index)
    missing = [s for s in README_REQUIRED if s not in secs]
    if missing and monorepo:
        rep.add("S1", "WARN", f"monorepo root README lacks {missing} (folders must carry them)")
    elif missing or not order_ok:
        rep.add("S1", "FAIL", f"missing {missing}" if missing else f"sections out of order: {known}")
    else:
        rep.add("S1", "PASS", f"{len(known)} standard sections in order")
    prose = re.sub(r"```.*?```|`[^`]*`|\[[^\]]*\]\([^)]*\)", " ", text, flags=re.S).lower()
    words = re.findall(r"[a-záéíóúñ]+", prose)
    ratio = sum(w in SPANISH for w in words) / max(len(words), 1)
    rep.add("S2", "WARN" if ratio > 0.06 else "PASS", f"Spanish-word ratio {ratio:.2%} (English expected)")
    badges = "actions/workflows/" in text and "License" in text and "shields.io" in text
    rep.add("S3", "PASS" if badges else "FAIL", "CI + MIT badges" if badges else "CI and/or license badge missing")


def check_tree(repo, rep):
    tracked = git(repo, "ls-files").splitlines()
    junk = [f for f in tracked if JUNK.search(f)]
    vendored = sorted({f[:m.end()] for f in tracked if (m := MAYBE_VENDORED.search(f))})
    if junk:
        rep.add("S4", "FAIL", f"tracked generated files: {junk[:6]}")
    elif vendored:
        rep.add("S4", "WARN", f"build/dist/out folders tracked (fine only if vendored and needed): {vendored[:4]}")
    else:
        rep.add("S4", "PASS", "nothing generated is tracked")
    ignores = [f for f in tracked if f == ".gitignore" or f.endswith("/.gitignore")]
    rep.add("S5", "PASS" if ignores else "FAIL", f".gitignore present ({len(ignores)})" if ignores else "no .gitignore")
    names = ("Makefile", "package.json", "pyproject.toml", "build.gradle", "gradlew", "mvnw", "pom.xml", "CMakeLists.txt")
    entry = sorted({pathlib.Path(f).name for f in tracked if pathlib.Path(f).name in names and f.count("/") <= 2}
                   | {"*.lpi" for f in tracked if f.endswith(".lpi")})
    rep.add("S6", "PASS" if entry else "WARN", f"entry points: {entry}" if entry else "no recognised build/test entry point")


def check_ci_files(repo, rep, files) -> list[str]:
    wf = sorted(p.name for p in (repo / ".github/workflows").glob("*.y*ml")) if (repo / ".github/workflows").is_dir() else []
    ok = "ci.yml" in wf or len(wf) > 1
    rep.add("V1", "PASS" if ok else "FAIL", f"workflows: {wf}" if wf else "no workflows")
    gui = any(GUI_HINT.search(t) for rel, t in files if rel.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".pyw")))
    if gui:
        uses_xvfb = any("xvfb" in t for rel, t in files if not rel.endswith(".md"))
        rep.add("V4", "PASS" if uses_xvfb else "WARN", "GUI code; tests use xvfb" if uses_xvfb else "GUI code but no xvfb-run in tests/CI")
    return wf


def check_naming(repo, rep):
    name = repo_name(repo)
    ok = name == OWNER or re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) is not None
    rep.add("P1", "PASS" if ok else "FAIL", f"name '{name}'" + ("" if ok else " is not kebab-case"))
    head = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip() or git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    rep.add("P2", "PASS" if head.endswith("main") else "FAIL", f"default branch {head or '?'}")
    return name


def token() -> str:
    t = os.environ.get("GITHUB_TOKEN", "")
    if not t:
        t = subprocess.run(["secret-tool", "lookup", "service", "github", "account", OWNER],
                           capture_output=True, text=True).stdout.strip()
    return t


def api(path: str, tok: str):
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def check_github(repo, name, rep):
    tok = token()
    if not tok:
        rep.add("V2", "WARN", "no GitHub token: set GITHUB_TOKEN")
        return
    git(repo, "fetch", "-q", "origin")
    info = api(f"/repos/{OWNER}/{name}", tok)
    sha = git(repo, "rev-parse", f"origin/{info['default_branch']}").strip()
    runs = [r for r in api(f"/repos/{OWNER}/{name}/actions/runs?head_sha={sha}&per_page=50", tok)["workflow_runs"]
            if r["event"] == "push"]
    if not runs:
        rep.add("V2", "FAIL", f"no CI run for {sha[:7]}")
    elif any(r["status"] != "completed" for r in runs):
        rep.add("V2", "WARN", f"CI still running on {sha[:7]}")
    else:
        bad = [r["name"] for r in runs if r["conclusion"] != "success"]
        rep.add("V2", "FAIL" if bad else "PASS", f"red on {sha[:7]}: {bad}" if bad else f"{len(runs)} workflow(s) green on {sha[:7]}")
    rep.add("P2", "PASS" if info["default_branch"] == "main" else "FAIL", f"GitHub default branch {info['default_branch']}")
    rep.add("P3", "PASS" if info.get("description") else "FAIL", "description set" if info.get("description") else "no description")
    n = len(info.get("topics", []))
    rep.add("P4", "PASS" if 5 <= n <= 8 else "WARN", f"{n} topics")
    if info.get("private"):
        rep.add("P0", "WARN", "repository is private")


def check_profile(name, profile: pathlib.Path, rep):
    if name == OWNER:
        return
    if not profile.exists():
        rep.add("P5", "WARN", f"profile README not found at {profile}")
        return
    ok = f"github.com/{OWNER}/{name})" in profile.read_text()
    rep.add("P5", "PASS" if ok else "FAIL", "listed in the profile README" if ok else "not indexed in the profile README")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", type=pathlib.Path)
    ap.add_argument("--github", action="store_true", help="also query the GitHub API")
    ap.add_argument("--profile", type=pathlib.Path,
                    default=pathlib.Path(__file__).resolve().parents[4] / "README.md",
                    help="profile README used for P5 (default: this repo's README)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()
    if not (repo / ".git").exists():
        print(f"not a git repository: {repo}", file=sys.stderr)
        return 2
    rep = Report()
    files = tracked_text_files(repo)
    check_secrets(repo, files, rep)
    check_personal_data(files, rep)
    check_denylist(repo, files, rep)
    check_proprietary(files, rep)
    check_license(repo, rep)
    wf = check_ci_files(repo, rep, files)
    if repo_name(repo) == OWNER:
        rep.add("S1", "PASS", "profile repo: README is the profile page, template does not apply")
    else:
        check_readme(repo, rep, monorepo=len(wf) > 1)
    check_tree(repo, rep)
    name = check_naming(repo, rep)
    if a.github:
        rep.rows = [r for r in rep.rows if r[0] != "P2"]
        check_github(repo, name, rep)
    check_profile(name, a.profile, rep)
    order = ["G1", "G2", "G3", "G4", "G6", "S1", "S2", "S3", "S4", "S5", "S6", "V1", "V2", "V4", "P0", "P1", "P2", "P3", "P4", "P5"]
    rep.rows.sort(key=lambda r: order.index(r[0]) if r[0] in order else 99)
    if a.json:
        print(json.dumps({"repo": name, "rows": rep.rows, "failed": rep.failed()}, ensure_ascii=False))
    else:
        print(f"{name}")
        for cid, st, detail in rep.rows:
            print(f"  {cid:3} {st:4}  {detail}")
        fails = sum(s == "FAIL" for _, s, _ in rep.rows)
        warns = sum(s == "WARN" for _, s, _ in rep.rows)
        print(f"  => {'REJECTED' if fails else 'ACCEPTED' if not warns else 'ACCEPTED with warnings'} ({fails} fail, {warns} warn)")
    return 1 if rep.failed() else 0


if __name__ == "__main__":
    sys.exit(main())
