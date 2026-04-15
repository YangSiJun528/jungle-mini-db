#!/usr/bin/env python3
"""Functional checks for auto-id INSERT and B+Tree-backed id lookup."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def build_binary(repo_root: Path, project_root: Path, output_path: Path) -> None:
    sources = [
        "main.c",
        "parser.c",
        "executor.c",
        "db_index.c",
        "memory_bptree.c",
    ]
    command = [
        "cc",
        "-std=c11",
        f'-DPROJECT_ROOT_DIR="{project_root}"',
        *sources,
        "-o",
        str(output_path),
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "failed to build test binary\nstdout:\n%s\nstderr:\n%s"
            % (completed.stdout, completed.stderr)
        )


def run_db(binary_path: Path, commands: str) -> str:
    completed = subprocess.run(
        [str(binary_path)],
        input=commands,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "mini DB returned %d\nstdout:\n%s\nstderr:\n%s"
            % (completed.returncode, completed.stdout, completed.stderr)
        )
    return completed.stdout


def assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError("expected %r in output:\n%s" % (expected, text))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    with tempfile.TemporaryDirectory(prefix="mini-db-test-") as temp_dir_name:
        project_root = Path(temp_dir_name)
        data_dir = project_root / "data"
        binary_path = project_root / "jungle_mini_db_test"

        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "users.csv").write_text("", encoding="ascii")
        (data_dir / "posts.csv").write_text("", encoding="ascii")

        build_binary(repo_root, project_root, binary_path)

        output = run_db(
            binary_path,
            "\n".join(
                [
                    "insert into users values (alice);",
                    "insert into users values (5,bob);",
                    "insert into users values (carol);",
                    "select * from users where id = 1;",
                    "select * from users where id = 5;",
                    "select * from users where id = 6;",
                    "select * from users where name = carol;",
                    ".exit",
                    "",
                ]
            ),
        )
        assert_contains(output, "1,alice")
        assert_contains(output, "5,bob")
        assert_contains(output, "6,carol")

        restart_output = run_db(
            binary_path,
            "\n".join(
                [
                    "insert into users values (dave);",
                    "select * from users where id = 7;",
                    "select * from users where name = dave;",
                    ".exit",
                    "",
                ]
            ),
        )
        assert_contains(restart_output, "7,dave")

    print("mini_db requirement tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
