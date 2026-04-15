#!/usr/bin/env python3
"""Benchmark SELECT performance with prebuilt fixed-row CSV datasets.

The benchmark prepares reusable datasets first, then measures SELECT only.
By default it covers 1M, 10M, and 100M rows:

    ./scripts/benchmark_bplus_tree_index.py --output benchmark-results/bplus-tree-index.json

Dataset files are stored under benchmark-datasets/ and are reused on later
runs. The active data/users.csv and index files are symlinks to the selected
dataset while each SELECT benchmark is running.
"""

import argparse
import json
import os
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path


FIXED_ROW_SIZE = 64
FIXED_ROW_DATA_SIZE = FIXED_ROW_SIZE - 1
FIXED_ROW_PADDING = "_"
DEFAULT_DATASETS = (1_000_000, 10_000_000, 100_000_000)
DEFAULT_SELECT_REPETITIONS = 1
DATASET_WRITE_BATCH = 100_000
MINI_DB_PROMPT = b"mini-db> "
PROGRESS_INTERVAL_SECONDS = 30

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DATASET_DIR = REPO_ROOT / "benchmark-datasets"
USERS_CSV = DATA_DIR / "users.csv"
USERS_INDEX = DATA_DIR / "users.idx"
USERS_INDEX_BOOT = DATA_DIR / "users.idx.boot"
DEFAULT_BUILD_DIR = REPO_ROOT / "cmake-build-debug"
DEFAULT_EXECUTABLE = DEFAULT_BUILD_DIR / "jungle_mini_db"


class DatasetResult:
    def __init__(
        self,
        records,
        select_repetitions,
        target_id,
        target_name,
        csv_path,
        index_path,
        csv_prepared,
        index_prepared,
        csv_prepare_seconds,
        index_prepare_seconds,
        indexed_startup_seconds,
        indexed_select_seconds,
        linear_select_seconds,
    ):
        self.records = records
        self.select_repetitions = select_repetitions
        self.target_id = target_id
        self.target_name = target_name
        self.csv_path = csv_path
        self.index_path = index_path
        self.csv_prepared = csv_prepared
        self.index_prepared = index_prepared
        self.csv_prepare_seconds = csv_prepare_seconds
        self.index_prepare_seconds = index_prepare_seconds
        self.indexed_startup_seconds = indexed_startup_seconds
        self.indexed_select_seconds = indexed_select_seconds
        self.linear_select_seconds = linear_select_seconds

    @property
    def indexed_avg_ms(self):
        return self.indexed_select_seconds * 1000 / self.select_repetitions

    @property
    def linear_avg_ms(self):
        return self.linear_select_seconds * 1000 / self.select_repetitions

    @property
    def speedup(self):
        if self.indexed_select_seconds == 0:
            return float("inf")
        return self.linear_select_seconds / self.indexed_select_seconds

    def to_dict(self):
        return {
            "records": self.records,
            "select_repetitions": self.select_repetitions,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "csv_path": str(self.csv_path),
            "index_path": str(self.index_path),
            "csv_prepared": self.csv_prepared,
            "index_prepared": self.index_prepared,
            "csv_prepare_seconds": self.csv_prepare_seconds,
            "index_prepare_seconds": self.index_prepare_seconds,
            "indexed_startup_seconds": self.indexed_startup_seconds,
            "indexed_select_seconds": self.indexed_select_seconds,
            "indexed_avg_ms": self.indexed_avg_ms,
            "linear_select_seconds": self.linear_select_seconds,
            "linear_avg_ms": self.linear_avg_ms,
            "linear_vs_indexed_speedup": self.speedup,
        }


class DataBackup:
    def __init__(self, paths):
        self._snapshots = {}
        for path in paths:
            if path.is_symlink():
                self._snapshots[path] = ("symlink", os.readlink(path))
            elif path.exists():
                self._snapshots[path] = ("file", path.read_bytes())
            else:
                self._snapshots[path] = ("missing", None)

    def restore(self):
        for path, (kind, content) in self._snapshots.items():
            unlink_if_exists(path)
            if kind == "missing":
                continue

            path.parent.mkdir(parents=True, exist_ok=True)
            if kind == "symlink":
                os.symlink(content, path)
            else:
                path.write_bytes(content)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare fixed-row CSV datasets, then measure SELECT performance only."
    )
    parser.add_argument(
        "--datasets",
        default=",".join(str(value) for value in DEFAULT_DATASETS),
        help="comma-separated row counts; default: 1000000,10000000,100000000",
    )
    parser.add_argument(
        "--select-repetitions",
        type=int,
        default=DEFAULT_SELECT_REPETITIONS,
        help="number of repeated SELECT measurements per dataset; default: %d" % DEFAULT_SELECT_REPETITIONS,
    )
    parser.add_argument(
        "--target-id",
        type=int,
        default=None,
        help="id to select; default: the last id in each dataset",
    )
    parser.add_argument(
        "--executable",
        type=Path,
        default=DEFAULT_EXECUTABLE,
        help="mini DB executable path; default: %s" % DEFAULT_EXECUTABLE,
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="skip cmake build before running the benchmark",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="create missing CSV/index datasets, then exit without measuring SELECT",
    )
    parser.add_argument(
        "--select-only",
        action="store_true",
        help="do not generate missing datasets; fail if a CSV or index is missing",
    )
    parser.add_argument(
        "--keep-active-data",
        action="store_true",
        help="leave data/users.csv and index symlinks pointing at the last benchmarked dataset",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="optional JSON output path for benchmark results",
    )
    return parser.parse_args()


def parse_dataset_counts(text):
    values = []
    for item in text.split(","):
        item = item.strip().replace("_", "")
        if not item:
            continue
        value = int(item)
        if value < 1:
            raise ValueError("dataset sizes must be at least 1")
        values.append(value)

    if not values:
        raise ValueError("--datasets must include at least one row count")

    return values


def validate_args(args, datasets):
    if args.select_repetitions < 1:
        raise ValueError("--select-repetitions must be at least 1")
    if args.target_id is not None and args.target_id < 1:
        raise ValueError("--target-id must be at least 1")
    if args.prepare_only and args.select_only:
        raise ValueError("--prepare-only and --select-only cannot be used together")
    for records in datasets:
        if args.target_id is not None and args.target_id > records:
            raise ValueError("--target-id must be within every selected dataset")


def dataset_paths(records):
    stem = "users-%d" % records
    return {
        "csv": DATASET_DIR / (stem + ".csv"),
        "idx": DATASET_DIR / (stem + ".idx"),
        "boot": DATASET_DIR / (stem + ".idx.boot"),
    }


def read_cmake_cache_value(cache_path, key):
    if not cache_path.exists():
        return None

    prefix = key + ":"
    for line in cache_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1]

    return None


def cmake_cache_is_stale(build_dir):
    cache_path = build_dir / "CMakeCache.txt"
    if not cache_path.exists():
        return False

    cache_source = read_cmake_cache_value(cache_path, "CMAKE_HOME_DIRECTORY")
    cache_build = read_cmake_cache_value(cache_path, "CMAKE_CACHEFILE_DIR")

    try:
        source_mismatch = cache_source is not None and Path(cache_source).resolve() != REPO_ROOT
        build_mismatch = cache_build is not None and Path(cache_build).resolve() != build_dir.resolve()
    except OSError:
        return True

    return source_mismatch or build_mismatch


def run_cmake(args, description):
    completed = subprocess.run(
        args,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "%s failed with exit code %d:\nstdout:\n%s\nstderr:\n%s"
            % (description, completed.returncode, completed.stdout, completed.stderr)
        )


def build_project():
    if cmake_cache_is_stale(DEFAULT_BUILD_DIR):
        print_progress("  removing stale CMake build directory: %s" % DEFAULT_BUILD_DIR)
        shutil.rmtree(DEFAULT_BUILD_DIR)

    if not (DEFAULT_BUILD_DIR / "CMakeCache.txt").exists():
        run_cmake(
            ["cmake", "-S", str(REPO_ROOT), "-B", str(DEFAULT_BUILD_DIR)],
            "cmake configure",
        )

    run_cmake(["cmake", "--build", str(DEFAULT_BUILD_DIR)], "cmake build")


def print_progress(message):
    print(message, file=sys.stderr, flush=True)


def unlink_if_exists(path):
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def replace_with_symlink(path, target):
    unlink_if_exists(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(str(target), path)


def fixed_user_name(record_id):
    return "user-%07d" % record_id


def encode_fixed_row(record_id):
    logical_row = "%d,%s," % (record_id, fixed_user_name(record_id))
    if len(logical_row) > FIXED_ROW_DATA_SIZE:
        raise ValueError("record %d is too large for fixed row storage" % record_id)

    padded = logical_row + (FIXED_ROW_PADDING * (FIXED_ROW_DATA_SIZE - len(logical_row))) + "\n"
    return padded.encode("ascii")


def expected_csv_size(records):
    return records * FIXED_ROW_SIZE


def csv_is_ready(csv_path, records):
    return csv_path.exists() and csv_path.stat().st_size == expected_csv_size(records)


def generate_dataset_csv(records, csv_path):
    if csv_is_ready(csv_path, records):
        return False, 0.0

    started = time.perf_counter()
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = csv_path.with_suffix(csv_path.suffix + ".tmp")
    unlink_if_exists(temp_path)

    with temp_path.open("wb") as file:
        for start_id in range(1, records + 1, DATASET_WRITE_BATCH):
            end_id = min(start_id + DATASET_WRITE_BATCH - 1, records)
            file.write(b"".join(encode_fixed_row(record_id) for record_id in range(start_id, end_id + 1)))
            if records >= 1_000_000 and (end_id % 1_000_000 == 0 or end_id == records):
                print_progress("  generated {:,}/{:,} rows".format(end_id, records))

    temp_path.replace(csv_path)
    return True, time.perf_counter() - started


def link_active_dataset(paths):
    replace_with_symlink(USERS_CSV, paths["csv"].resolve())
    replace_with_symlink(USERS_INDEX, paths["idx"].resolve())
    replace_with_symlink(USERS_INDEX_BOOT, paths["boot"].resolve())


def prepare_dataset_index(executable, records, paths, select_only):
    if paths["idx"].exists() and paths["boot"].exists():
        return False, 0.0
    if select_only:
        raise FileNotFoundError("missing prebuilt index for {:,} rows".format(records))

    started = time.perf_counter()
    replace_with_symlink(USERS_CSV, paths["csv"].resolve())
    unlink_if_exists(USERS_INDEX)
    unlink_if_exists(USERS_INDEX_BOOT)

    print_progress("  building B+Tree index for {:,} prebuilt rows".format(records))
    run_mini_db_batch(
        executable,
        ".exit\n",
        "B+Tree index build for {:,} rows".format(records),
    )

    if not USERS_INDEX.exists() or not USERS_INDEX_BOOT.exists():
        raise RuntimeError("index build did not create users.idx and users.idx.boot")

    unlink_if_exists(paths["idx"])
    unlink_if_exists(paths["boot"])
    USERS_INDEX.replace(paths["idx"])
    USERS_INDEX_BOOT.replace(paths["boot"])
    return True, time.perf_counter() - started


def run_mini_db_batch(executable, commands, progress_label=None):
    process = subprocess.Popen(
        [str(executable)],
        cwd=REPO_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    try:
        assert process.stdin is not None
        process.stdin.write(commands.encode("ascii"))
        process.stdin.close()

        started = time.perf_counter()
        next_progress = started + PROGRESS_INTERVAL_SECONDS
        while process.poll() is None:
            now = time.perf_counter()
            if progress_label is not None and now >= next_progress:
                print_progress(
                    "  %s still running after %.0fs" % (progress_label, now - started)
                )
                next_progress += PROGRESS_INTERVAL_SECONDS
            time.sleep(1)

        assert process.stderr is not None
        stderr = process.stderr.read().decode("utf-8", errors="replace")
    except Exception:
        process.kill()
        process.wait()
        raise

    if process.returncode != 0:
        raise RuntimeError(
            "mini DB command batch failed with exit code %d:\n%s" % (process.returncode, stderr)
        )


def measure_indexed_select(executable, target_id, repetitions):
    process = subprocess.Popen(
        [str(executable)],
        cwd=REPO_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        startup_started = time.perf_counter()
        read_until_prompt(process, "mini DB startup/index validation")
        startup_seconds = time.perf_counter() - startup_started

        query_started = time.perf_counter()
        for _ in range(repetitions):
            write_mini_db_command(process, "select * from users where id = %d;\n" % target_id)
            read_until_prompt(process, "indexed SELECT")
        select_seconds = time.perf_counter() - query_started

        write_mini_db_command(process, ".exit\n")
        returncode = process.wait()
        assert process.stderr is not None
        stderr = process.stderr.read().decode("utf-8", errors="replace")
    except Exception:
        process.kill()
        process.wait()
        raise

    if returncode != 0:
        raise RuntimeError(
            "mini DB SELECT session failed with exit code %d:\n%s" % (returncode, stderr)
        )

    return startup_seconds, select_seconds


def write_mini_db_command(process, command):
    assert process.stdin is not None
    process.stdin.write(command.encode("ascii"))
    process.stdin.flush()


def read_until_prompt(process, progress_label):
    assert process.stdout is not None
    assert process.stderr is not None

    output = bytearray()
    started = time.perf_counter()
    next_progress = started + PROGRESS_INTERVAL_SECONDS
    stdout_fd = process.stdout.fileno()

    while True:
        ready, _, _ = select.select([stdout_fd], [], [], 1)
        if ready:
            chunk = os.read(stdout_fd, 4096)
            if chunk == b"":
                stderr = process.stderr.read().decode("utf-8", errors="replace")
                raise RuntimeError("mini DB exited before prompt was ready:\n%s" % stderr)
            output.extend(chunk)
            if MINI_DB_PROMPT in output:
                return bytes(output)

        returncode = process.poll()
        if returncode is not None:
            stderr = process.stderr.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                "mini DB exited with code %d before prompt was ready:\n%s" % (returncode, stderr)
            )

        now = time.perf_counter()
        if now >= next_progress:
            print_progress("  waiting for %s after %.0fs" % (progress_label, now - started))
            next_progress += PROGRESS_INTERVAL_SECONDS


def decode_fixed_row(raw_row):
    if len(raw_row) != FIXED_ROW_SIZE or raw_row[-1:] != b"\n":
        raise ValueError("invalid fixed row")

    return raw_row[:FIXED_ROW_DATA_SIZE].decode("ascii").rstrip(FIXED_ROW_PADDING).rstrip(",")


def linear_select_by_name(target_name):
    with USERS_CSV.open("rb") as file:
        while True:
            raw_row = file.read(FIXED_ROW_SIZE)
            if raw_row == b"":
                break
            logical_row = decode_fixed_row(raw_row)
            columns = logical_row.split(",")
            if len(columns) >= 2 and columns[1] == target_name:
                return logical_row

    raise LookupError("name not found by linear scan: %s" % target_name)


def measure_linear_select(target_name, repetitions):
    started = time.perf_counter()
    for _ in range(repetitions):
        linear_select_by_name(target_name)
    return time.perf_counter() - started


def write_output(path, results):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": "prebuilt_csv_select_only",
        "datasets": [result.to_dict() for result in results],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_result(result):
    print("B+Tree index benchmark")
    print("- records: {:,}".format(result.records))
    print("- dataset CSV: %s" % result.csv_path)
    print("- index file: %s" % result.index_path)
    print("- csv prepared this run: %s" % result.csv_prepared)
    print("- index prepared this run: %s" % result.index_prepared)
    print("- target: id=%d, name=%s" % (result.target_id, result.target_name))
    print("- select repetitions: {:,}".format(result.select_repetitions))
    print("- csv prepare time: %.3fs" % result.csv_prepare_seconds)
    print("- index prepare time: %.3fs" % result.index_prepare_seconds)
    print("- mini DB startup/index validation: %.6fs" % result.indexed_startup_seconds)
    print(
        "- indexed id SELECT after startup: "
        "%.6fs total, %.3fms/query" % (result.indexed_select_seconds, result.indexed_avg_ms)
    )
    print(
        "- linear name scan: "
        "%.6fs total, %.3fms/query" % (result.linear_select_seconds, result.linear_avg_ms)
    )
    print("- linear/indexed query elapsed ratio: %.2fx" % result.speedup)
    print()


def run_dataset(executable, records, args):
    paths = dataset_paths(records)
    if args.select_only and not csv_is_ready(paths["csv"], records):
        raise FileNotFoundError("missing prebuilt CSV for {:,} rows".format(records))

    print_progress("[dataset {:,}] preparing CSV".format(records))
    csv_prepared, csv_seconds = generate_dataset_csv(records, paths["csv"])
    print_progress("[dataset {:,}] preparing index".format(records))
    index_prepared, index_seconds = prepare_dataset_index(executable, records, paths, args.select_only)

    link_active_dataset(paths)

    target_id = args.target_id if args.target_id is not None else records
    target_name = fixed_user_name(target_id)

    if args.prepare_only:
        return DatasetResult(
            records,
            args.select_repetitions,
            target_id,
            target_name,
            paths["csv"],
            paths["idx"],
            csv_prepared,
            index_prepared,
            csv_seconds,
            index_seconds,
            0.0,
            0.0,
            0.0,
        )

    print_progress("[dataset {:,}] measuring SELECT only".format(records))
    indexed_startup_seconds, indexed_seconds = measure_indexed_select(
        executable,
        target_id,
        args.select_repetitions,
    )
    linear_seconds = measure_linear_select(target_name, args.select_repetitions)

    return DatasetResult(
        records,
        args.select_repetitions,
        target_id,
        target_name,
        paths["csv"],
        paths["idx"],
        csv_prepared,
        index_prepared,
        csv_seconds,
        index_seconds,
        indexed_startup_seconds,
        indexed_seconds,
        linear_seconds,
    )


def main():
    args = parse_args()
    try:
        datasets = parse_dataset_counts(args.datasets)
        validate_args(args, datasets)
    except ValueError as error:
        print("error: %s" % error, file=sys.stderr)
        return 2

    executable = args.executable.resolve()
    backup = DataBackup([USERS_CSV, USERS_INDEX, USERS_INDEX_BOOT])

    try:
        if not args.skip_build:
            print_progress("[1/2] building mini DB")
            build_project()
            print_progress("[1/2] build complete")
        if not executable.exists():
            raise FileNotFoundError("mini DB executable not found: %s" % executable)

        results = []
        for records in datasets:
            result = run_dataset(executable, records, args)
            results.append(result)
            if not args.prepare_only:
                print_result(result)

        if args.prepare_only:
            for result in results:
                print(
                    "prepared {:,} rows: csv={}, index={}".format(
                        result.records, result.csv_path, result.index_path
                    )
                )

        if args.output is not None:
            write_output(args.output, results)
            print_progress("wrote JSON result: %s" % args.output)

        return 0
    except Exception as error:
        print("error: %s" % error, file=sys.stderr)
        return 1
    finally:
        if not args.keep_active_data:
            backup.restore()


if __name__ == "__main__":
    raise SystemExit(main())
