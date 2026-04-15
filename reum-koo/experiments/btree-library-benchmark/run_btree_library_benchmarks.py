#!/usr/bin/env python3
"""Build and run the multi-library B-tree benchmark."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REUM_ROOT = SCRIPT_DIR.parents[1]
WORKTREE_ROOT = SCRIPT_DIR.parents[2]
BUILD_DIR = SCRIPT_DIR / "build"
RESULTS_DIR = SCRIPT_DIR / "results"
RUNTIME_DIR = RESULTS_DIR / "runtime"
EXECUTABLE = BUILD_DIR / "btree_library_benchmark"
JSON_OUTPUT = RESULTS_DIR / "latest_results.json"
SUMMARY_OUTPUT = RESULTS_DIR / "latest_summary.md"
DETAILED_REPORT_OUTPUT = RESULTS_DIR / "latest_detailed_report.md"
INT32_MAX = 2_147_483_647
SPARSE_KEY_BASE = 11
SPARSE_KEY_STRIDE = 257
SPARSE_SAFE_RECORD_LIMIT = ((INT32_MAX - SPARSE_KEY_BASE) // SPARSE_KEY_STRIDE) + 1

SCENARIO_EXPLANATIONS = {
    "dense_seq_build_rand_get": "Dense integer keys. Insert in sorted order, then lookup in random order.",
    "dense_rand_build_rand_get": "Dense integer keys. Insert in random order, then lookup in random order.",
    "dense_rev_build_rand_get": "Dense integer keys. Insert in reverse-sorted order, then lookup in random order.",
    "dense_seq_build_seq_get": "Dense integer keys. Insert in sorted order, then lookup in sorted order.",
    "dense_rand_build_hot_get": "Dense integer keys. Insert in random order, then repeatedly lookup a hot 1% subset.",
    "sparse_rand_build_rand_get": "Sparse integer keys with gaps. Insert in random order, then lookup in random order.",
}

INCIDENT_LOG = [
    "작업 트리에 로그 파일 변경이 남아 있어서, 원래 저장소를 건드리지 않기 위해 별도 worktree와 `btree-library-benchmark` 브랜치에서 실험을 진행했다.",
    "초기 벤치마크 러너는 단일 record count와 두 가지 시나리오만 지원했는데, 비교 해상도를 높이기 위해 세 가지 데이터셋 크기와 여섯 가지 시나리오를 도는 구조로 확장했다.",
    "처음 후보에는 프로젝트 내부의 디스크형 `thirdparty/bplustree`도 넣어봤지만, 재검증 결과 assert보다는 큰 value를 쓰는 sparse 대용량 시나리오에서 lookup 값 손상이 먼저 관찰되어 최종 비교군에서 제외했다.",
    "비교군을 다섯 개로 유지하면서도 끝까지 안정적으로 돌리는 것이 중요하다고 판단해, 제외한 후보 대신 `frozenca/BTree`를 넣어 최종 세트를 완성했다.",
    "제외한 라이브러리의 산출물이 `build/`와 `results/runtime/`에 남아 결과 해석을 흐릴 수 있다는 점을 확인했고, 실행 스크립트가 매번 두 폴더를 재생성하도록 수정했다.",
    "`cmake`가 설치되어 있지 않아, Apple clang의 `cc`와 `c++`를 직접 호출하는 방식으로 빌드 파이프라인을 구성했다.",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, help="run a single dataset size")
    parser.add_argument(
        "--record-counts",
        default="10000,100000,1000000",
        help="comma-separated dataset sizes to run when --records is not supplied",
    )
    parser.add_argument("--seed", type=int, default=20260415, help="deterministic shuffle seed")
    parser.add_argument("--skip-build", action="store_true", help="reuse the existing executable")
    return parser.parse_args()


def normalize_record_counts(args: argparse.Namespace) -> list[int]:
    if args.records is not None:
        counts = [args.records]
    else:
        counts = [int(part.strip()) for part in args.record_counts.split(",") if part.strip()]

    if not counts:
        raise RuntimeError("at least one record count is required")
    if any(count <= 0 for count in counts):
        raise RuntimeError("record counts must all be positive integers")
    return counts


def run_command(command: list[str], *, cwd: Path) -> None:
    print("+", " ".join(command), file=sys.stderr)
    completed = subprocess.run(command, cwd=cwd, check=False, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with exit code {completed.returncode}: {' '.join(command)}")


def reset_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def build_executable() -> None:
    reset_output_dir(BUILD_DIR)

    include_flags = [
        "-I",
        str(SCRIPT_DIR),
        "-I",
        str(SCRIPT_DIR / "common"),
        "-I",
        str(REUM_ROOT),
        "-I",
        str(SCRIPT_DIR / "third_party" / "kronuz_cpp_btree"),
        "-I",
        str(SCRIPT_DIR / "third_party" / "frozenca_btree" / "include"),
    ]

    c_sources = {
        "memory_bptree": REUM_ROOT / "memory_bptree.c",
        "tidwall_btree_c": SCRIPT_DIR / "third_party" / "tidwall_btree_c" / "btree.c",
        "adapter_reum_memory_bptree": SCRIPT_DIR / "adapters" / "adapter_reum_memory_bptree.c",
        "adapter_habedi_bptree": SCRIPT_DIR / "adapters" / "adapter_habedi_bptree.c",
        "adapter_tidwall_btree_c": SCRIPT_DIR / "adapters" / "adapter_tidwall_btree_c.c",
    }
    cpp_sources = {
        "adapter_kronuz_cpp_btree": SCRIPT_DIR / "adapters" / "adapter_kronuz_cpp_btree.cpp",
        "adapter_frozenca_btree": SCRIPT_DIR / "adapters" / "adapter_frozenca_btree.cpp",
        "library_registry": SCRIPT_DIR / "adapters" / "library_registry.cpp",
        "benchmark_main": SCRIPT_DIR / "common" / "benchmark_main.cpp",
    }

    object_files = []
    for stem, source in c_sources.items():
        output = BUILD_DIR / f"{stem}.o"
        object_files.append(output)
        run_command(
            ["cc", "-O3", "-std=c11", "-c", str(source), "-o", str(output), *include_flags],
            cwd=SCRIPT_DIR,
        )

    for stem, source in cpp_sources.items():
        output = BUILD_DIR / f"{stem}.o"
        object_files.append(output)
        run_command(
            ["c++", "-O3", "-std=c++20", "-c", str(source), "-o", str(output), *include_flags],
            cwd=SCRIPT_DIR,
        )

    run_command(
        ["c++", "-O3", "-std=c++20", *[str(path) for path in object_files], "-o", str(EXECUTABLE)],
        cwd=SCRIPT_DIR,
    )


def parse_result_lines(output: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for line in output.splitlines():
        if not line.startswith("RESULT\t"):
            continue

        fields = line.split("\t")
        results.append(
            {
                "library_id": fields[1],
                "library_name": fields[2],
                "family": fields[3],
                "storage_mode": fields[4],
                "scenario_id": fields[5],
                "scenario_name": fields[6],
                "records": int(fields[7]),
                "insert_seconds": float(fields[8]),
                "lookup_seconds": float(fields[9]),
                "insert_ops_per_second": float(fields[10]),
                "lookup_ops_per_second": float(fields[11]),
            }
        )
    return results


def rank_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (row["lookup_ops_per_second"], row["insert_ops_per_second"]),
        reverse=True,
    )


def scenario_order(results: list[dict[str, object]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for row in results:
        scenario_id = str(row["scenario_id"])
        if scenario_id in seen:
            continue
        seen.add(scenario_id)
        ordered.append((scenario_id, str(row["scenario_name"])))
    return ordered


def group_results(results: list[dict[str, object]]) -> dict[int, dict[str, list[dict[str, object]]]]:
    grouped: dict[int, dict[str, list[dict[str, object]]]] = defaultdict(lambda: defaultdict(list))
    for row in results:
        grouped[int(row["records"])][str(row["scenario_id"])].append(row)
    return grouped


def format_ranking_table(rows: list[dict[str, object]], *, include_seconds: bool) -> list[str]:
    if include_seconds:
        lines = [
            "| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    else:
        lines = [
            "| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |",
            "| --- | --- | --- | --- | --- | --- |",
        ]

    for index, row in enumerate(rank_rows(rows), start=1):
        if include_seconds:
            lines.append(
                "| {rank} | `{name}` | {family} | {insert_sec:.6f} | {lookup_sec:.6f} | {insert:.2f} | {lookup:.2f} |".format(
                    rank=index,
                    name=row["library_name"],
                    family=row["family"],
                    insert_sec=row["insert_seconds"],
                    lookup_sec=row["lookup_seconds"],
                    insert=row["insert_ops_per_second"],
                    lookup=row["lookup_ops_per_second"],
                )
            )
        else:
            lines.append(
                "| {rank} | `{name}` | {family} | {storage} | {insert:.2f} | {lookup:.2f} |".format(
                    rank=index,
                    name=row["library_name"],
                    family=row["family"],
                    storage=row["storage_mode"],
                    insert=row["insert_ops_per_second"],
                    lookup=row["lookup_ops_per_second"],
                )
            )
    return lines


def build_winner_table(results: list[dict[str, object]]) -> list[str]:
    lookup_wins: dict[str, int] = defaultdict(int)
    insert_wins: dict[str, int] = defaultdict(int)

    for _, scenarios in group_results(results).items():
        for rows in scenarios.values():
            lookup_wins[str(max(rows, key=lambda row: row["lookup_ops_per_second"])["library_name"])] += 1
            insert_wins[str(max(rows, key=lambda row: row["insert_ops_per_second"])["library_name"])] += 1

    libraries = sorted({str(row["library_name"]) for row in results})
    lines = [
        "| Library | Lookup wins | Insert wins |",
        "| --- | --- | --- |",
    ]
    for library in libraries:
        lines.append(f"| `{library}` | {lookup_wins[library]} | {insert_wins[library]} |")
    return lines


def build_winner_timeline_table(
    grouped: dict[int, dict[str, list[dict[str, object]]]],
    ordered_scenarios: list[tuple[str, str]],
    record_counts: list[int],
) -> list[str]:
    lines = ["| Scenario | " + " | ".join(f"{count:,}" for count in record_counts) + " |", "| --- | " + " | ".join(["---"] * len(record_counts)) + " |"]

    for scenario_id, scenario_name in ordered_scenarios:
        winners = []
        for record_count in record_counts:
            rows = grouped[record_count][scenario_id]
            winner = max(rows, key=lambda row: row["lookup_ops_per_second"])
            winners.append(f"`{winner['library_name']}`")
        lines.append(f"| `{scenario_id}` | " + " | ".join(winners) + " |")
        lines.append(f"| {scenario_name} | " + " | ".join([" "] * len(record_counts)) + " |")

    return lines


def compute_win_counts(results: list[dict[str, object]]) -> tuple[dict[str, int], dict[str, int]]:
    lookup_wins: dict[str, int] = defaultdict(int)
    insert_wins: dict[str, int] = defaultdict(int)

    for _, scenarios in group_results(results).items():
        for rows in scenarios.values():
            lookup_wins[str(max(rows, key=lambda row: row["lookup_ops_per_second"])["library_name"])] += 1
            insert_wins[str(max(rows, key=lambda row: row["insert_ops_per_second"])["library_name"])] += 1

    return dict(lookup_wins), dict(insert_wins)


def describe_top_winners(win_counts: dict[str, int], metric_name: str) -> str:
    if not win_counts:
        return f"- {metric_name} 우승 횟수를 계산할 데이터가 없었다."

    top_count = max(win_counts.values())
    winners = sorted([library for library, count in win_counts.items() if count == top_count])
    if len(winners) == 1:
        return f"- {metric_name} 1위 횟수는 `{winners[0]}`가 `{top_count}`회로 가장 많았다."
    return f"- {metric_name} 1위 횟수는 `{', '.join(winners)}`가 공동 1위로 `{top_count}`회였다."


def write_summary(results: list[dict[str, object]], record_counts: list[int], seed: int) -> None:
    grouped = group_results(results)
    ordered_scenarios = scenario_order(results)

    lines = [
        "# B-tree Library Benchmark Summary",
        "",
        f"- record counts: `{', '.join(str(count) for count in record_counts)}`",
        f"- seed: `{seed}`",
        f"- libraries compared: `{len({row['library_name'] for row in results})}`",
        f"- scenarios per dataset: `{len(ordered_scenarios)}`",
        "",
        "## Overall Winner Count",
        "",
        *build_winner_table(results),
        "",
        "## Ranked Results",
        "",
    ]

    for record_count in record_counts:
        lines.append(f"### {record_count:,} records")
        lines.append("")

        for scenario_id, scenario_name in ordered_scenarios:
            lines.append(f"#### {scenario_name}")
            lines.append("")
            lines.extend(format_ranking_table(grouped[record_count][scenario_id], include_seconds=False))
            lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- All five benchmark targets in this run are configured as in-memory tree benchmarks behind a common insert/get adapter.",
            "- Each scenario validates correctness by checking `get(key) == key * 13 + 7` for every lookup.",
            "- The benchmark runner now recreates `build/` and `results/runtime/` every run so removed-library artifacts do not leak into new results.",
            "- Raw machine-readable results live in `latest_results.json`, and the longer narrative report lives in `latest_detailed_report.md`.",
            "",
        ]
    )

    SUMMARY_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def write_detailed_report(results: list[dict[str, object]], record_counts: list[int], seed: int) -> None:
    grouped = group_results(results)
    ordered_scenarios = scenario_order(results)
    libraries = sorted({str(row["library_name"]) for row in results})
    lookup_wins, insert_wins = compute_win_counts(results)

    fastest_lookup = max(results, key=lambda row: row["lookup_ops_per_second"])
    fastest_insert = max(results, key=lambda row: row["insert_ops_per_second"])

    lines = [
        "# Detailed B-tree Library Benchmark Report",
        "",
        "## 1. Goal",
        "",
        "이번 실험의 목표는 다섯 가지 B-tree/B+tree 구현을 같은 입력 조건과 같은 정답 검증 규칙 아래에서 비교하고,",
        "데이터셋 크기와 입력 패턴이 바뀔 때 어떤 라이브러리가 강한지 확인하는 것이다.",
        "",
        "## 2. Execution Context",
        "",
        f"- branch: `btree-library-benchmark`",
        f"- worktree: `{WORKTREE_ROOT}`",
        f"- benchmark root: `{SCRIPT_DIR}`",
        f"- record counts: `{', '.join(str(count) for count in record_counts)}`",
        f"- seed: `{seed}`",
        f"- compared libraries: `{', '.join(libraries)}`",
        "",
        "## 3. Scenario Matrix",
        "",
        "| Scenario ID | Meaning |",
        "| --- | --- |",
    ]

    for scenario_id, _ in ordered_scenarios:
        lines.append(f"| `{scenario_id}` | {SCENARIO_EXPLANATIONS.get(scenario_id, 'n/a')} |")

    lines.extend(
        [
            "",
            "## 4. What Happened During The Work",
            "",
        ]
    )
    for index, item in enumerate(INCIDENT_LOG, start=1):
        lines.append(f"{index}. {item}")

    lines.extend(
        [
            "",
            "## 5. High-Level Findings",
            "",
            "- 가장 빠른 단일 lookup 성능은 `{name}`가 `{records:,}`건의 `{scenario}`에서 기록한 `{lookup:.2f} ops/s`였다.".format(
                name=fastest_lookup["library_name"],
                records=int(fastest_lookup["records"]),
                scenario=fastest_lookup["scenario_name"],
                lookup=fastest_lookup["lookup_ops_per_second"],
            ),
            "- 가장 빠른 단일 insert 성능은 `{name}`가 `{records:,}`건의 `{scenario}`에서 기록한 `{insert:.2f} ops/s`였다.".format(
                name=fastest_insert["library_name"],
                records=int(fastest_insert["records"]),
                scenario=fastest_insert["scenario_name"],
                insert=fastest_insert["insert_ops_per_second"],
            ),
            describe_top_winners(lookup_wins, "lookup"),
            describe_top_winners(insert_wins, "insert"),
            "- `habedi/bptree`는 random insert에서도 lookup 성능이 안정적이어서 B+ tree 계열 비교군 중 가장 꾸준한 편이었다.",
            "- `reum memory_bptree`는 작은 dense dataset에서는 강했지만, `100,000`건 sparse random 시나리오에서 lookup이 크게 떨어져 데이터 분포 민감도가 눈에 띄었다.",
            "- `sparse_rand_build_rand_get`와 `dense_rand_build_hot_get`를 같이 보니, 키 분포와 접근 지역성이 순위에 실제 영향을 준다는 점이 드러났다.",
            "",
            "## 6. Winner Count",
            "",
            *build_winner_table(results),
            "",
            "## 7. Detailed Tables",
            "",
        ]
    )

    for record_count in record_counts:
        lines.append(f"### {record_count:,} records")
        lines.append("")

        record_lookup_wins: dict[str, int] = defaultdict(int)
        for scenario_id, _ in ordered_scenarios:
            winner = max(grouped[record_count][scenario_id], key=lambda row: row["lookup_ops_per_second"])
            record_lookup_wins[str(winner["library_name"])] += 1

        lines.append("| Library | Lookup wins at this size |")
        lines.append("| --- | --- |")
        for library in libraries:
            lines.append(f"| `{library}` | {record_lookup_wins[library]} |")
        lines.append("")

        for scenario_id, scenario_name in ordered_scenarios:
            lines.append(f"#### {scenario_name}")
            lines.append("")
            lines.append(SCENARIO_EXPLANATIONS.get(scenario_id, ""))
            lines.append("")
            lines.extend(format_ranking_table(grouped[record_count][scenario_id], include_seconds=True))
            lines.append("")

    lines.extend(
        [
            "## 8. Scale Notes",
            "",
            "- `1,000,000`건은 이번 실험의 기본 비교 기준 중 하나일 뿐, 이 벤치마크의 절대 최대값은 아니다.",
            "- 현재 러너는 `--records` 또는 `--record-counts` 인자로 더 큰 값도 받을 수 있다.",
            "- 다만 현재 구현은 key 타입으로 32-bit signed `int`를 쓰고, sparse 시나리오는 `key = index * 257 + 11` 공식을 쓰기 때문에, sparse 시나리오 기준 안전 상한은 대략 `{limit:,}`건 정도다.".format(limit=SPARSE_SAFE_RECORD_LIMIT),
            "- 실제로도 데이터셋 크기가 바뀌면 lookup 1위가 바뀌는 시나리오가 있었고, 그래서 결과를 한 구간만 보고 일반화하면 위험하다.",
            "",
            "### Lookup Winner Timeline",
            "",
            *build_winner_timeline_table(grouped, ordered_scenarios, record_counts),
            "",
            "## 9. Limits And Follow-Ups",
            "",
            "- 이번 실험은 point lookup과 unique-key insert만 비교했다. range scan, delete, duplicate key policy는 아직 범위 밖이다.",
            "- 라이브러리 내부 fanout, allocator, node layout은 서로 다르기 때문에 결과를 절대적인 우열로 보기보다는 현재 조건에서의 throughput 비교로 읽는 것이 맞다.",
            "- 다음 확장 후보는 delete benchmark, mixed read/write workload, range query, memory usage 측정이다.",
            "",
        ]
    )

    DETAILED_REPORT_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def run_benchmark_once(records: int, seed: int) -> list[dict[str, object]]:
    runtime_dir = RUNTIME_DIR / f"records_{records}"
    completed = subprocess.run(
        [
            str(EXECUTABLE),
            "--records",
            str(records),
            "--seed",
            str(seed),
            "--runtime-dir",
            str(runtime_dir),
        ],
        cwd=SCRIPT_DIR,
        text=True,
        check=False,
        capture_output=True,
    )
    sys.stderr.write(completed.stderr)
    sys.stdout.write(completed.stdout)

    if completed.returncode != 0:
        raise RuntimeError(f"benchmark executable failed with exit code {completed.returncode} for records={records}")

    return parse_result_lines(completed.stdout)


def main() -> int:
    args = parse_args()
    record_counts = normalize_record_counts(args)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    reset_output_dir(RUNTIME_DIR)

    if not args.skip_build:
        build_executable()

    all_results: list[dict[str, object]] = []
    for records in record_counts:
        all_results.extend(run_benchmark_once(records, args.seed))

    payload = {
        "record_counts": record_counts,
        "seed": args.seed,
        "libraries": sorted({row["library_name"] for row in all_results}),
        "scenario_ids": [scenario_id for scenario_id, _ in scenario_order(all_results)],
        "results": all_results,
    }
    JSON_OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_summary(all_results, record_counts, args.seed)
    write_detailed_report(all_results, record_counts, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
