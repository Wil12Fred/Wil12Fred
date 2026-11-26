"""Tests for check_repo.py: each planted defect must turn its criterion red.

Run: python3 -m unittest discover -s .claude/skills/repo-acceptance/tests
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_repo.py"
# Built at runtime so this file never contains a literal that looks like a real token
# or a non-distribution notice (GitHub push protection and the checker itself would flag it).
FAKE_TOKEN = "gh" + "p_" + "Zq8Lm2Rt5Vx9Kp3Wn7Bc4Hd6Jf1Gs0Ty8Ua2Qe"
MARKER = "proprietary and " + "confidential"

MIT = """MIT License

Copyright (c) 2020-2026 Wilber Cutire

Permission is hereby granted, free of charge, to any person obtaining a copy...
"""
README = """# good-repo

[![CI](https://github.com/Wil12Fred/good-repo/actions/workflows/ci.yml/badge.svg)](x) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A small program that sorts numbers and prints them, used to test the checker.

## Features
- sorts numbers
## Build
Run make in the repository root.
## Tests
Run make test, which compares the output with a golden file.
## License
MIT, see the LICENSE file.
"""


class CheckRepoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.deny = root / "denylist.txt"
        self.deny.write_text("# private\nacmecorp\n")
        self.profile = root / "PROFILE.md"
        self.profile.write_text("- **[good-repo](https://github.com/Wil12Fred/good-repo)**: test\n")
        self.repo = root / "good-repo"
        self.repo.mkdir()
        self.write({
            "LICENSE": MIT, "README.md": README, ".gitignore": "build/\n",
            "Makefile": "all:\n\ttrue\ntest:\n\ttrue\n", "main.c": "int main(void){return 0;}\n",
            ".github/workflows/ci.yml": "name: CI\non: [push]\njobs: {}\n",
        })
        self.git("init", "-q", "-b", "main")
        self.git("remote", "add", "origin", "git@github.com:Wil12Fred/good-repo.git")
        self.commit("initial")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, files):
        for rel, text in files.items():
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def commit(self, msg, author="Wilber Cutire <owner@example.org>"):
        self.git("add", "-A")
        name, mail = author[:-1].split(" <")
        self.git("-c", f"user.name={name}", "-c", f"user.email={mail}", "-c", "commit.gpgsign=false",
                 "commit", "-q", "-m", msg)

    def run_checker(self):
        env = dict(os.environ, REPO_ACCEPTANCE_DENYLIST=str(self.deny))
        r = subprocess.run([sys.executable, str(SCRIPT), str(self.repo), "--json", "--profile", str(self.profile)],
                           capture_output=True, text=True, env=env)
        out = json.loads(r.stdout)
        return r.returncode, {cid: (st, detail) for cid, st, detail in out["rows"]}

    def assertStatus(self, rows, cid, status):
        self.assertIn(cid, rows)
        self.assertEqual(rows[cid][0], status, f"{cid}: {rows[cid]}")

    def test_clean_repo_is_accepted(self):
        code, rows = self.run_checker()
        self.assertEqual(code, 0, rows)
        for cid in ("G1", "G2", "G3", "G4", "G6", "S1", "S3", "S4", "S5", "V1", "P1", "P2", "P5"):
            self.assertStatus(rows, cid, "PASS")

    def test_real_looking_token_fails_g1(self):
        self.write({"config.py": f'TOKEN = "{FAKE_TOKEN}"\n'})
        self.commit("add config")
        code, rows = self.run_checker()
        self.assertEqual(code, 1)
        self.assertStatus(rows, "G1", "FAIL")

    def test_token_removed_still_fails_from_history(self):
        self.write({"config.py": f'TOKEN = "{FAKE_TOKEN}"\n'})
        self.commit("add config")
        (self.repo / "config.py").unlink()
        self.commit("remove config")
        _, rows = self.run_checker()
        self.assertStatus(rows, "G1", "FAIL")

    def test_illustrative_token_is_not_a_secret(self):
        self.write({"docs.py": '"""redact("xoxb-" + "a" * 40) -> "xoxb-aaaaaaaaaaaaaaaaaaaa""""\n'})
        self.commit("docs")
        _, rows = self.run_checker()
        self.assertStatus(rows, "G1", "PASS")

    def test_denylisted_name_in_file_fails_g3(self):
        self.write({"main.c": "/* written at AcmeCorp */ int main(void){return 0;}\n"})
        self.commit("comment")
        _, rows = self.run_checker()
        self.assertStatus(rows, "G3", "FAIL")

    def test_denylisted_name_in_author_email_fails_g3(self):
        self.write({"x.txt": "x\n"})
        self.commit("x", author="Wilber Cutire <w@acmecorp.com>")
        _, rows = self.run_checker()
        self.assertStatus(rows, "G3", "FAIL")
        self.assertIn("author", rows["G3"][1])

    def test_denylist_matches_whole_words_only(self):
        self.write({"package-lock.json": '{"integrity": "sha512-xxACMECORPyy"}\n'})
        self.commit("lock")
        _, rows = self.run_checker()
        self.assertStatus(rows, "G3", "PASS")

    def test_proprietary_header_fails_g4(self):
        self.write({"sdk/vendor.h": f"/* Vendor {MARKER}. */\n"})
        self.commit("sdk")
        _, rows = self.run_checker()
        self.assertStatus(rows, "G4", "FAIL")

    def test_real_looking_ids_in_seed_warn_g2(self):
        self.write({"seed.sql": "INSERT INTO people VALUES (1,'Juan Perez',47281936);\n"})
        self.commit("seed")
        _, rows = self.run_checker()
        self.assertStatus(rows, "G2", "WARN")

    def test_fictitious_ids_pass_g2(self):
        self.write({"seed.sql": "INSERT INTO people VALUES (1,'Ana Torres',10000001);\n"})
        self.commit("seed")
        _, rows = self.run_checker()
        self.assertStatus(rows, "G2", "PASS")

    def test_missing_license_fails_g6(self):
        (self.repo / "LICENSE").unlink()
        self.commit("drop license")
        _, rows = self.run_checker()
        self.assertStatus(rows, "G6", "FAIL")

    def test_sections_out_of_order_fail_s1(self):
        self.write({"README.md": README.replace("## Build\nRun make in the repository root.\n", "")
                    + "## Build\nlater\n"})
        self.commit("reorder")
        _, rows = self.run_checker()
        self.assertStatus(rows, "S1", "FAIL")

    def test_spanish_readme_warns_s2(self):
        self.write({"README.md": README + "\nEste programa es para el curso y la tarea de los alumnos, que se "
                    "compila con make y se ejecuta en la terminal con los datos de la carpeta.\n" * 3})
        self.commit("es")
        _, rows = self.run_checker()
        self.assertStatus(rows, "S2", "WARN")

    def test_tracked_binary_fails_s4(self):
        (self.repo / "main.o").write_bytes(b"\x7fELF\0\0")
        self.commit("oops")
        _, rows = self.run_checker()
        self.assertStatus(rows, "S4", "FAIL")

    def test_no_workflow_fails_v1(self):
        (self.repo / ".github/workflows/ci.yml").unlink()
        self.commit("no ci")
        _, rows = self.run_checker()
        self.assertStatus(rows, "V1", "FAIL")

    def test_camel_case_name_fails_p1(self):
        self.git("remote", "set-url", "origin", "git@github.com:Wil12Fred/GoodRepo.git")
        _, rows = self.run_checker()
        self.assertStatus(rows, "P1", "FAIL")

    def test_not_indexed_fails_p5(self):
        self.profile.write_text("nothing here\n")
        _, rows = self.run_checker()
        self.assertStatus(rows, "P5", "FAIL")

    def test_gui_without_xvfb_warns_v4(self):
        self.write({"view.c": "#include <GL/glut.h>\nint main(void){return 0;}\n"})
        self.commit("gui")
        _, rows = self.run_checker()
        self.assertStatus(rows, "V4", "WARN")


if __name__ == "__main__":
    unittest.main()
