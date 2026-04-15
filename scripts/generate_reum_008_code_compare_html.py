#!/usr/bin/env python3
"""Generate a side-by-side HTML guide for the original vs current mini DB code."""

from __future__ import annotations

import difflib
import html
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "docs" / "reum-008-initial-vs-current-code-flow-compare.html"
BASE_REF = "HEAD"


IMPORTANT_FUNCTIONS = {
    "main.c": {
        "prepare_database": "boot",
        "run_repl": "boot",
        "find_table": "contract",
    },
    "parser.c": {
        "parse_select": "parse",
        "build_select_plan": "parse",
        "build_insert_plan": "parse",
    },
    "executor.c": {
        "execute_select": "execute",
        "execute_select_by_id": "execute",
        "execute_select_by_column_linear": "execute",
        "execute_insert": "execute",
        "encode_fixed_row": "storage",
        "encode_fixed_row_values": "storage",
    },
    "db_index.c": {
        "db_index_open_table": "index",
        "db_index_get": "index",
        "db_index_put": "index",
        "db_index_next_id": "index",
        "rebuild_index_from_data_file": "index",
        "validate_index_against_data": "index",
        "update_next_id": "index",
    },
    "memory_bptree.c": {
        "memory_bptree_get": "tree",
        "memory_bptree_put": "tree",
        "insert_recursive": "tree",
        "insert_into_leaf": "tree",
        "insert_into_internal": "tree",
    },
    "memory_bptree.h": {
        "memory_bptree_create": "tree",
        "memory_bptree_get": "tree",
        "memory_bptree_put": "tree",
    },
    "thirdparty/bplustree.h": {
        "bplus_tree_get": "tree-old",
        "bplus_tree_put": "tree-old",
        "bplus_tree_init": "tree-old",
        "bplus_tree_deinit": "tree-old",
    },
    "CMakeLists.txt": {
        "add_executable": "build",
        "add_test": "build",
    },
    "tests/test_memory_bptree.c": {
        "test_sequential_inserts_and_reads": "test",
        "test_duplicate_and_missing_keys": "test",
        "test_out_of_order_inserts": "test",
    },
    "tests/test_mini_db_requirements.py": {
        "build_binary": "test",
        "main": "test",
    },
}


INLINE_REVIEW_NOTES = {
    ("old", "mini_db.h"): [
        ("const char *index_file_path;", "리뷰 포인트: 테이블 메타데이터 계약 자체가 디스크 인덱스 파일을 전제로 하고 있다."),
    ],
    ("new", "mini_db.h"): [
        ("SELECT_CONDITION_COLUMN_EQUALS", "리뷰 포인트: `WHERE id = ?` 전용 조건에서 일반 컬럼 equality 조건으로 확장되었다."),
        ("char column_name[MAX_TABLE_NAME_SIZE];", "리뷰 포인트: 어떤 컬럼을 비교할지 실행기까지 전달하기 위한 필드다."),
        ("int db_index_next_id(", "리뷰 포인트: 자동 ID 정책이 인덱스 계층과 연결되면서 새로운 공개 계약이 추가되었다."),
    ],
    ("old", "parser.c"): [
        ('condition.type = SELECT_CONDITION_ID_EQUALS;', "리뷰 포인트: 초기 SELECT 파서는 `where id = ...` 경로 하나에 강하게 묶여 있다."),
        ('expect_text(&parser, "id");', "리뷰 포인트: 컬럼 이름을 일반적으로 읽지 않고 `id` 키워드를 하드코딩해서 기대한다."),
    ],
    ("new", "parser.c"): [
        ("read_name(&parser, column_name", "리뷰 포인트: 현재 파서는 먼저 컬럼 이름을 읽고 나서 `id` 인지 아닌지 분기한다."),
        ('strcmp(column_name, "id") == 0', "리뷰 포인트: `id` 인 경우만 인덱스 경로로 보내고, 아니면 선형 탐색 조건으로 저장한다."),
        ("condition.type = SELECT_CONDITION_COLUMN_EQUALS;", "리뷰 포인트: 비-id 조건도 계획 객체로 표현할 수 있게 됐다."),
        ("plan.value_count != table->column_count - 1", "리뷰 포인트: INSERT에서 id 생략 입력을 허용하기 위해 값 개수 검증 규칙을 완화했다."),
    ],
    ("old", "executor.c"): [
        ("if (!parse_id_value(plan->values[0], &id))", "리뷰 포인트: 첫 번째 값이 항상 id라고 가정한다. 자동 ID가 없던 구조다."),
        ("found = db_index_get(plan->table_name, id, &location);", "리뷰 포인트: INSERT 전 중복 id 검사도 인덱스 조회를 통해 처리한다."),
        ("if (!encode_fixed_row(plan, fixed_row))", "리뷰 포인트: Plan 안의 원본 values를 그대로 fixed row로 직렬화한다."),
    ],
    ("new", "executor.c"): [
        ("if (plan->condition.type == SELECT_CONDITION_COLUMN_EQUALS)", "리뷰 포인트: 현재 실행기는 비-id 조건을 별도 선형 탐색 함수로 보낸다."),
        ("static void execute_select_by_column_linear", "리뷰 포인트: 새로 추가된 함수다. 같은 SQL 실행기 안에서 비-id 선형 탐색을 수행한다."),
        ("plan->value_count == table->column_count - 1", "리뷰 포인트: 값 하나가 모자라면 자동 ID INSERT 로 해석한다."),
        ("db_index_next_id(plan->table_name, &id)", "리뷰 포인트: 자동으로 부여할 다음 id를 인덱스 계층에서 받아온다."),
        ('snprintf(insert_values[0], sizeof(insert_values[0]), "%d", id);', "리뷰 포인트: 실제 저장 직전에는 결국 `id` 를 포함한 완전한 row 값 배열로 정규화한다."),
        ("extract_column_value(logical_row, column_index", "리뷰 포인트: 비-id 조건은 fixed row를 복원한 뒤 필요한 컬럼만 잘라 비교한다."),
    ],
    ("old", "db_index.c"): [
        ("if (!index_files_exist(table))", "리뷰 포인트: 초기 버전은 `.idx` 와 `.boot` 파일 존재 여부를 인덱스 상태의 출발점으로 본다."),
        ("validate_result = validate_index_against_data", "리뷰 포인트: 디스크 인덱스가 CSV와 어긋나면 다시 복구하는 검증 단계가 있다."),
        ("stored_offset = encode_offset_for_index(location.offset);", "리뷰 포인트: 외부 라이브러리 제약 때문에 offset을 그대로 저장하지 못하고 +1 인코딩을 한다."),
        ("return bplus_tree_put(handle->tree, id, stored_offset) == 0 ? 1 : -1;", "리뷰 포인트: 인덱스 삽입 책임은 thirdparty 라이브러리에 위임된다."),
    ],
    ("new", "db_index.c"): [
        ("handle->tree = memory_bptree_create();", "리뷰 포인트: 부팅 시마다 빈 메모리 트리를 새로 만들고 시작한다."),
        ("handle->next_id = 1;", "리뷰 포인트: 자동 ID를 위해 가장 큰 id 다음 값을 별도 상태로 유지한다."),
        ("if (!memory_bptree_get(handle->tree, id, &offset))", "리뷰 포인트: 현재 인덱스 조회는 메모리 B+ 트리에서 직접 offset을 꺼낸다."),
        ("if (memory_bptree_put(handle->tree, id, location.offset) != 1)", "리뷰 포인트: CSV append 후 메모리 인덱스도 같은 트랜잭션 흐름 안에서 갱신한다."),
        ("int db_index_next_id(const char *table_name, int *next_id)", "리뷰 포인트: 자동 ID 공급 함수가 새로 생기면서 INSERT 흐름이 바뀌었다."),
        ("if (memory_bptree_put(handle->tree, id, offset) != 1)", "리뷰 포인트: 시작 시 CSV 전체를 순회하면서 `id -> offset` 을 메모리 트리에 다시 적재한다."),
        ("static int update_next_id", "리뷰 포인트: 현재 구조에서 자동 ID 정책의 핵심은 가장 큰 id 다음 값을 유지하는 것이다."),
    ],
    ("old", "thirdparty/bplustree.h"): [
        ("struct bplus_tree {", "리뷰 포인트: 외부 구현은 파일 디스크립터와 free block 목록까지 포함하는 디스크 지향 구조다."),
        ("struct bplus_tree *bplus_tree_init", "리뷰 포인트: 시작 함수부터 파일 이름과 block size를 요구한다."),
    ],
    ("new", "memory_bptree.h"): [
        ("MemoryBPlusTree *memory_bptree_create", "리뷰 포인트: 현재 공개 API는 메모리 트리 생성/조회/삽입에 집중한 훨씬 단순한 형태다."),
    ],
    ("new", "memory_bptree.c"): [
        ("result = insert_recursive(tree->root, key, value);", "리뷰 포인트: 삽입은 재귀적으로 내려가며 split 결과를 부모에게 올리는 방식으로 구현했다."),
        ("int left_count = total_keys / 2;", "리뷰 포인트: 리프 split 시 왼쪽과 오른쪽 키 개수를 계산해 반으로 나눈다."),
        ("result.promoted_key = right->keys[0];", "리뷰 포인트: 리프 split 후 부모에 올리는 separator key는 오른쪽 새 리프의 첫 key다."),
        ("int promote_index = total_keys / 2;", "리뷰 포인트: 내부 노드는 가운데 key를 올리고 좌우 자식 배열을 다시 배치한다."),
    ],
    ("old", "CMakeLists.txt"): [
        ("add_executable(", "리뷰 포인트: 초기 빌드는 실행 파일 하나만 만들고 테스트 타깃이 없다."),
    ],
    ("new", "CMakeLists.txt"): [
        ("enable_testing()", "리뷰 포인트: 현재 빌드 설정은 CTest를 켜고 테스트 러너를 포함한다."),
        ("add_test(NAME memory_bptree_tests", "리뷰 포인트: 트리 자체를 빠르게 검증할 수 있는 단위 테스트가 추가됐다."),
        ("NAME mini_db_requirements", "리뷰 포인트: 요구사항 관점의 기능 테스트도 자동화됐다."),
    ],
    ("new", "tests/test_memory_bptree.c"): [
        ("assert(memory_bptree_put(tree, 42, 256L) == 0);", "리뷰 포인트: 같은 key를 두 번 넣을 때 중복 삽입을 거부하는지 확인한다."),
        ("test_out_of_order_inserts", "리뷰 포인트: 키가 정렬되어 들어오지 않아도 탐색 결과가 맞는지 확인하는 케이스다."),
    ],
    ("new", "tests/test_mini_db_requirements.py"): [
        ('"insert into users values (alice);"', "리뷰 포인트: 자동 ID INSERT 지원 여부를 직접 검증하는 입력이다."),
        ('"select * from users where name = carol;"', "리뷰 포인트: 비-id 조건도 같은 SQL 실행기 안에서 동작하는지 본다."),
        ("restart_output = run_db(", "리뷰 포인트: 프로그램 재시작 후에도 next_id와 재구축이 올바른지 확인한다."),
    ],
}


REQUIREMENT_ALIGNMENT_ROWS = (
    ("인덱스 저장 위치", "`users.idx`, `posts.idx` 같은 디스크 파일", "실행 중 메모리에만 존재하는 B+ 트리", "과제 요구사항의 메모리 기반 방식에 맞추기 위해"),
    ("인덱스 구현 방식", "외부 `thirdparty/bplustree.c` 래핑", "직접 구현한 `memory_bptree.c` 사용", "핵심 로직을 코드 수준에서 설명 가능하게 만들기 위해"),
    ("프로그램 시작 시 동작", "기존 인덱스 파일을 열고 검증", "CSV를 스캔해 메모리 인덱스를 재구축", "CSV를 기준 데이터로 두고 단순화하기 위해"),
    ("INSERT 입력 형식", "`insert into users values (104,name);`", "`insert into users values (name);` 기본 지원", "자동 ID 부여 요구사항 충족"),
    ("비-id WHERE 처리", "사실상 미지원", "SQL 실행기 안에서 선형 탐색", "인덱스 조회와 선형 탐색 비교를 같은 시스템 안에서 보여주기 위해"),
    ("성능 비교 방식", "id는 DB 경로, 비-id는 Python이 CSV 직접 스캔", "둘 다 mini DB SQL 경로 사용", "비교 경로를 공정하게 맞추기 위해"),
    ("테스트", "설명 위주", "단위 테스트 + 기능 테스트", "검증 가능한 결과물로 만들기 위해"),
)


INDEX_LIFECYCLE_ROWS = (
    ("프로그램 시작", "인덱스 파일 존재 여부 확인", "CSV 파일 존재 여부 확인"),
    ("초기화", "인덱스 파일 열기", "메모리 B+ 트리 생성"),
    ("준비 과정", "인덱스 파일 검증 또는 복구", "CSV 스캔 후 `id -> offset` 적재"),
    ("프로그램 종료", "인덱스 파일은 그대로 유지", "메모리 인덱스 해제"),
)


QUERY_PATH_ROWS = (
    ("`select * from users where id = 101;`", "인덱스 조회", "인덱스 조회", "유지"),
    ("`select * from users where name = alice;`", "사실상 미지원", "SQL 실행기 안에서 선형 탐색", "같은 SQL 시스템 안에서 비교 가능"),
    ("`insert into users values (alice);`", "실패", "자동 ID 부여 후 저장", "요구사항 충족"),
)


TEST_LAYER_ROWS = (
    ("단위 테스트", "`tests/test_memory_bptree.c`", "B+ 트리 insert/get, 중복 키, 순서 섞인 입력"),
    ("기능 테스트", "`tests/test_mini_db_requirements.py`", "자동 ID, `WHERE id`, `WHERE name`, 재시작 후 재구축"),
)


@dataclass(frozen=True)
class SourceSpec:
    path: str | None
    mode: str = "file"
    names: tuple[str, ...] = ()
    label: str | None = None


@dataclass(frozen=True)
class Card:
    title: str
    note: str
    old: SourceSpec
    new: SourceSpec
    review_points: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Section:
    anchor: str
    title: str
    summary: str
    bullets: tuple[str, ...]
    cards: tuple[Card, ...]


FLOW_SECTIONS: tuple[Section, ...] = (
    Section(
        anchor="overview",
        title="1. 시작과 메타데이터 준비",
        summary="프로그램이 켜질 때 어떤 메타데이터를 들고 시작하고, 인덱스를 어떻게 준비하는지가 바뀌었다.",
        bullets=(
            "초기 버전은 `TableMetadata` 가 CSV 경로와 인덱스 파일 경로를 같이 들고 있었다.",
            "현재 버전은 인덱스 파일 경로를 없애고, 시작할 때 CSV를 스캔해 메모리 B+ 트리를 다시 만든다.",
            "같은 REPL 구조를 유지하면서도 부팅 시 인덱스 준비 단계의 의미가 완전히 달라졌다.",
        ),
        cards=(
            Card(
                title="공유 계약: `mini_db.h`",
                note="조회 조건 타입과 테이블 메타데이터 구조가 바뀐 지점을 먼저 보면 전체 흐름이 빨리 잡힌다.",
                old=SourceSpec("mini_db.h", "file"),
                new=SourceSpec("mini_db.h", "file"),
                review_points=(
                    "타입 정의는 모든 흐름의 공통 계약이다.",
                    "`index_file_path` 제거와 `SELECT_CONDITION_COLUMN_EQUALS` 추가가 큰 방향 전환을 잘 보여준다.",
                ),
            ),
            Card(
                title="부팅 진입점: `main.c`",
                note="메인 루프는 거의 유지됐지만, 메타데이터 배열에서 `index_file_path` 가 사라졌다.",
                old=SourceSpec("main.c", "file"),
                new=SourceSpec("main.c", "file"),
                review_points=(
                    "REPL 구조는 유지하고 인덱스 준비 의미만 바꾼 점이 중요하다.",
                    "겉보기 변화보다 메타데이터 구조 변화에 주목하면 읽기 쉽다.",
                ),
            ),
            Card(
                title="인덱스 부팅 경로: `db_index_open_table()`",
                note="처음 코드는 인덱스 파일을 열고 검증하는 쪽, 지금 코드는 메모리 트리를 만들고 CSV에서 재구축하는 쪽으로 바뀌었다.",
                old=SourceSpec("db_index.c", "functions", ("db_index_open_table",)),
                new=SourceSpec("db_index.c", "functions", ("db_index_open_table",)),
                review_points=(
                    "왼쪽은 디스크 인덱스 상태 검증이 핵심이다.",
                    "오른쪽은 메모리 트리 생성 후 CSV 재구축이 핵심이다.",
                ),
            ),
        ),
    ),
    Section(
        anchor="select",
        title="2. SELECT 파싱과 조회 분기",
        summary="처음 코드는 `WHERE id = ...` 만 이해했지만, 지금 코드는 컬럼 기반 equality 조건을 더 받아서 실행기에서 선형 탐색으로 분기한다.",
        bullets=(
            "파서가 이제 `condition.column_name` 과 `comparison_value` 를 담는다.",
            "실행기는 `id` 인덱스 경로와 비-id 선형 탐색 경로를 따로 가진다.",
            "같은 SQL 처리기 안에서 인덱스 조회와 선형 탐색을 모두 보여주도록 구조가 커졌다.",
        ),
        cards=(
            Card(
                title="SELECT 파서: `parse_select()`",
                note="`id` 전용 파서에서 컬럼 일반화 파서로 확장된 부분이다.",
                old=SourceSpec("parser.c", "functions", ("parse_select",)),
                new=SourceSpec("parser.c", "functions", ("parse_select",)),
                review_points=(
                    "지금 코드는 컬럼 이름을 먼저 읽고 `id` 인지 확인한다.",
                    "parser를 완전히 다시 만들지 않고 최소한으로 확장한 구현이다.",
                ),
            ),
            Card(
                title="계획 검증: `build_select_plan()`",
                note="현재 코드는 테이블 컬럼 존재 여부까지 확인해 잘못된 `WHERE` 를 막는다.",
                old=SourceSpec("parser.c", "functions", ("build_select_plan",)),
                new=SourceSpec("parser.c", "functions", ("build_select_plan",)),
                review_points=(
                    "실행기까지 가기 전에 오류를 막는 방어 로직이 늘었다.",
                ),
            ),
            Card(
                title="SELECT 실행 분기",
                note="현재 버전에 새로 들어온 `execute_select_by_column_linear()` 때문에 `SELECT` 경로가 두 갈래가 되었다.",
                old=SourceSpec("executor.c", "functions", ("execute_select", "execute_select_by_id")),
                new=SourceSpec("executor.c", "functions", ("execute_select", "execute_select_by_id", "execute_select_by_column_linear")),
                review_points=(
                    "이 카드가 요구사항의 핵심이다: `WHERE id` 는 인덱스, 다른 컬럼은 선형 탐색.",
                    "새 함수 하나가 들어오면서 벤치마크와 설명 가능성이 크게 좋아졌다.",
                ),
            ),
        ),
    ),
    Section(
        anchor="insert",
        title="3. INSERT와 자동 ID",
        summary="가장 눈에 띄는 사용자 경험 차이는 INSERT다. 예전에는 id를 직접 넣어야 했고, 지금은 자동 ID도 허용한다.",
        bullets=(
            "초기 버전은 `plan->values[0]` 을 무조건 id로 해석했다.",
            "현재 버전은 `column_count - 1` 개 값이 들어오면 `db_index_next_id()` 로 자동 id를 받아 채운다.",
            "자동 ID 때문에 실행기와 인덱스 계층 사이에 `next_id` 상태가 생겼다.",
        ),
        cards=(
            Card(
                title="INSERT 계획 만들기: `build_insert_plan()`",
                note="값 개수 검증 규칙이 바뀐 부분이다. 현재 코드는 `id` 생략 INSERT 를 허용한다.",
                old=SourceSpec("parser.c", "functions", ("build_insert_plan",)),
                new=SourceSpec("parser.c", "functions", ("build_insert_plan",)),
                review_points=(
                    "이 함수는 작지만 자동 ID 지원 여부를 결정하는 문턱이다.",
                ),
            ),
            Card(
                title="INSERT 실행: `execute_insert()`",
                note="현재 버전은 명시적 id 입력과 자동 id 입력 두 경우를 모두 처리한다.",
                old=SourceSpec("executor.c", "functions", ("execute_insert", "encode_fixed_row")),
                new=SourceSpec("executor.c", "functions", ("execute_insert", "encode_fixed_row_values")),
                review_points=(
                    "왼쪽은 입력값 첫 칸이 항상 id다.",
                    "오른쪽은 입력을 정규화해서 결국 `id` 가 포함된 값 배열로 바꾼 뒤 저장한다.",
                ),
            ),
            Card(
                title="자동 ID 상태 관리",
                note="처음 코드에는 없던 `db_index_next_id()` 와 `update_next_id()` 가 현재 구조의 핵심 연결부다.",
                old=SourceSpec("db_index.c", "functions", ("db_index_put",)),
                new=SourceSpec("db_index.c", "functions", ("db_index_put", "db_index_next_id", "update_next_id")),
                review_points=(
                    "자동 ID는 executor 혼자 해결하지 않고 인덱스 계층과 상태를 공유한다.",
                ),
            ),
        ),
    ),
    Section(
        anchor="index",
        title="4. 인덱스 엔진과 재구축 전략",
        summary="처음 코드는 외부 디스크 B+ 트리 라이브러리를 감싸는 래퍼였고, 지금 코드는 프로젝트 안에서 메모리 B+ 트리를 직접 구현한다.",
        bullets=(
            "초기 버전은 `.idx`, `.boot` 파일을 열고 검증/복구하는 흐름이 있었다.",
            "현재 버전은 메모리 트리를 생성한 뒤 CSV를 순차 스캔해서 `id -> offset` 을 다시 채운다.",
            "트리 구현 책임이 외부 라이브러리에서 `memory_bptree.c` 로 프로젝트 내부에 들어왔다.",
        ),
        cards=(
            Card(
                title="재구축 전략: `rebuild_index_from_data_file()`",
                note="두 버전 모두 CSV를 읽지만 목적이 다르다. 처음 코드는 디스크 인덱스 파일을 복구하고, 지금 코드는 메모리 트리를 채운다.",
                old=SourceSpec("db_index.c", "functions", ("rebuild_index_from_data_file", "validate_index_against_data")),
                new=SourceSpec("db_index.c", "functions", ("rebuild_index_from_data_file",)),
                review_points=(
                    "이 카드만 잘 읽어도 `디스크 기반 → 메모리 재구축` 변화가 보인다.",
                ),
            ),
            Card(
                title="트리 공개 API",
                note="왼쪽은 외부 `thirdparty` API, 오른쪽은 프로젝트 안에서 정의한 단순 메모리 API다.",
                old=SourceSpec("thirdparty/bplustree.h", "file"),
                new=SourceSpec("memory_bptree.h", "file"),
                review_points=(
                    "공개 인터페이스가 단순해질수록 내부 구현을 설명하기 쉬워진다.",
                ),
            ),
            Card(
                title="트리 핵심 삽입 로직",
                note="현재 버전은 `insert_recursive()` 와 split 함수들을 직접 구현한다. 초기 버전은 이 책임을 외부 라이브러리에 맡겼다.",
                old=SourceSpec("thirdparty/bplustree.c", "placeholder", label="초기 버전은 외부 라이브러리 전체 구현을 사용했습니다. 아래 전체 파일 부록에서 원본 코드를 그대로 볼 수 있습니다."),
                new=SourceSpec("memory_bptree.c", "functions", ("memory_bptree_put", "insert_recursive", "insert_into_leaf", "insert_into_internal")),
                review_points=(
                    "현재 구현은 split 결과를 재귀 반환으로 부모에게 올리는 스타일이다.",
                    "리프 split과 내부 split에서 어떤 key를 올리는지 주석 행을 꼭 확인해보면 좋다.",
                ),
            ),
        ),
    ),
    Section(
        anchor="build-test",
        title="5. 빌드와 테스트 구조",
        summary="현재 코드는 구현만 있는 상태를 넘어서, 트리 단위 테스트와 요구사항 기능 테스트까지 빌드에 연결한다.",
        bullets=(
            "초기 CMake는 실행 파일 하나만 만들었다.",
            "현재 CMake는 테스트 바이너리와 Python 기능 테스트를 등록한다.",
            "새 메모리 B+ 트리 구현에 맞춘 단위 테스트가 추가되었다.",
        ),
        cards=(
            Card(
                title="빌드 설정: `CMakeLists.txt`",
                note="소스 목록과 테스트 타깃이 어떻게 늘어났는지 보면 현재 구조의 책임 분리가 보인다.",
                old=SourceSpec("CMakeLists.txt", "file"),
                new=SourceSpec("CMakeLists.txt", "file"),
                review_points=(
                    "테스트가 빌드 스크립트 안으로 들어왔다는 점이 현재 구조의 성숙도를 보여준다.",
                ),
            ),
            Card(
                title="메모리 B+ 트리 단위 테스트",
                note="새 트리 구현 자체를 바로 검증하는 작은 C 테스트다. 초기 버전에는 대응 파일이 없었다.",
                old=SourceSpec(None, "placeholder", label="초기 버전에는 메모리 B+ 트리 전용 단위 테스트가 없었습니다."),
                new=SourceSpec("tests/test_memory_bptree.c", "file"),
                review_points=(
                    "자료구조 레벨에서 중복 key, 정렬되지 않은 입력까지 따로 검사한다.",
                ),
            ),
            Card(
                title="요구사항 기능 테스트",
                note="자동 ID, 재시작 후 next_id, `WHERE id`, `WHERE name` 경로를 한 번에 확인하는 테스트다.",
                old=SourceSpec(None, "placeholder", label="초기 버전에는 현재 요구사항 기준의 기능 테스트 파일이 없었습니다."),
                new=SourceSpec("tests/test_mini_db_requirements.py", "file"),
                review_points=(
                    "이 테스트는 코드보다 요구사항을 기준으로 읽으면 더 잘 이해된다.",
                ),
            ),
        ),
    ),
)


FULL_FILE_PAIRS = (
    ("mini_db.h", "mini_db.h", "mini_db.h"),
    ("main.c", "main.c", "main.c"),
    ("parser.c", "parser.c", "parser.c"),
    ("executor.c", "executor.c", "executor.c"),
    ("db_index.c", "db_index.c", "db_index.c"),
    ("thirdparty/bplustree.h", "memory_bptree.h", "트리 API 헤더"),
    ("thirdparty/bplustree.c", "memory_bptree.c", "트리 구현 파일"),
    ("CMakeLists.txt", "CMakeLists.txt", "CMakeLists.txt"),
    (None, "tests/test_memory_bptree.c", "tests/test_memory_bptree.c"),
    (None, "tests/test_mini_db_requirements.py", "tests/test_mini_db_requirements.py"),
)


def run_git_show(path: str) -> str | None:
    completed = subprocess.run(
        ["git", "show", f"{BASE_REF}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def read_current(path: str) -> str | None:
    file_path = ROOT / path
    if not file_path.exists():
        return None
    return file_path.read_text(encoding="utf-8")


def line_starts(text: str) -> list[int]:
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    return starts


def line_number_for_offset(starts: list[int], offset: int) -> int:
    low = 0
    high = len(starts)
    while low + 1 < high:
        mid = (low + high) // 2
        if starts[mid] <= offset:
            low = mid
        else:
            high = mid
    return low + 1


def find_function_block(text: str, func_name: str) -> tuple[str, int]:
    pattern = re.compile(rf"(^|\n)([^\n]*\b{re.escape(func_name)}\s*\([^;]*\)\s*\{{)", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"function {func_name!r} not found")

    starts = line_starts(text)
    start_offset = match.start(2)
    start_line = line_number_for_offset(starts, start_offset)

    index = match.end(2) - 1
    brace_depth = 0
    end_index = index
    while end_index < len(text):
        char = text[end_index]
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth == 0:
                end_index += 1
                while end_index < len(text) and text[end_index] != "\n":
                    end_index += 1
                if end_index < len(text):
                    end_index += 1
                break
        end_index += 1

    return text[start_offset:end_index], start_line


def build_source(spec: SourceSpec, *, use_old: bool) -> tuple[str, int, str]:
    if spec.mode == "placeholder":
        return spec.label or "코드가 없습니다.", 1, spec.label or ""

    if spec.path is None:
        return spec.label or "코드가 없습니다.", 1, spec.label or ""

    text = run_git_show(spec.path) if use_old else read_current(spec.path)
    if text is None:
        return spec.label or "코드가 없습니다.", 1, spec.label or ""

    if spec.mode == "file":
        return text, 1, spec.path

    if spec.mode != "functions":
        raise ValueError(f"unsupported mode: {spec.mode}")

    parts: list[str] = []
    first_line = None
    for index, name in enumerate(spec.names):
        block, start_line = find_function_block(text, name)
        if first_line is None:
            first_line = start_line
        if index > 0:
            parts.append("\n/* ===== next function ===== */\n\n")
        parts.append(block.rstrip())
        parts.append("\n")
    return "".join(parts).rstrip() + "\n", first_line or 1, spec.path


def line_kind_lists(old_lines: list[str], new_lines: list[str]) -> tuple[list[str], list[str]]:
    old_kinds = ["" for _ in old_lines]
    new_kinds = ["" for _ in new_lines]
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in {"replace", "delete"}:
            for index in range(i1, i2):
                old_kinds[index] = "changed" if tag == "replace" else "removed"
        if tag in {"replace", "insert"}:
            for index in range(j1, j2):
                new_kinds[index] = "changed" if tag == "replace" else "added"
    return old_kinds, new_kinds


def detect_function_category(path: str, line: str) -> str | None:
    names = IMPORTANT_FUNCTIONS.get(path, {})
    for name, category in names.items():
        if name in line and "(" in line:
            return category
    return None


def inline_notes_for_line(side_key: str, path: str, line: str) -> list[str]:
    notes = []
    for needle, note in INLINE_REVIEW_NOTES.get((side_key, path), []):
        if needle in line:
            notes.append(note)
    return notes


def review_list_html(points: tuple[str, ...]) -> str:
    if not points:
        return ""
    items = "\n".join(f"<li>{html.escape(point)}</li>" for point in points)
    return f"""
    <div class="review-points">
      <strong>리뷰 힌트</strong>
      <ul>{items}</ul>
    </div>
    """


def render_code_panel(
    text: str,
    path: str,
    start_line: int,
    kinds: list[str],
    side_label: str,
    side_key: str,
) -> str:
    rows: list[str] = []
    emitted_notes: set[str] = set()
    lines = text.splitlines()
    if not lines:
        lines = [""]
        kinds = [""]

    for index, line in enumerate(lines, start=start_line):
        local_index = index - start_line
        diff_class = kinds[local_index] if local_index < len(kinds) else ""
        func_category = detect_function_category(path, line)
        classes = ["code-row"]
        if diff_class:
            classes.append(f"diff-{diff_class}")
        if func_category:
            classes.append("important")
            classes.append(f"important-{func_category}")

        rows.append(
            "<tr class='{classes}'><td class='gutter'>{line_no}</td><td class='code'>{code}</td></tr>".format(
                classes=" ".join(classes),
                line_no=index,
                code=html.escape(line).replace(" ", "&nbsp;").replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;"),
            )
        )

        for note in inline_notes_for_line(side_key, path, line):
            if note in emitted_notes:
                continue
            emitted_notes.add(note)
            rows.append(
                "<tr class='comment-row'><td class='gutter note-gutter'>//</td><td class='code-comment'>{}</td></tr>".format(
                    html.escape(note)
                )
            )

    return """
    <div class="panel-header panel-{side_key}">
      <span class="panel-side side-{side_key}">{side}</span>
      <span class="panel-path">{path}</span>
    </div>
    <div class="code-wrap">
      <table class="code-table"><tbody>
        {rows}
      </tbody></table>
    </div>
    """.format(side=html.escape(side_label), side_key=side_key, path=html.escape(path), rows="\n".join(rows))


def render_compare_block(card: Card) -> str:
    old_text, old_start, old_path = build_source(card.old, use_old=True)
    new_text, new_start, new_path = build_source(card.new, use_old=False)
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    old_kinds, new_kinds = line_kind_lists(old_lines, new_lines)

    return """
    <article class="compare-card">
      <div class="compare-meta">
        <h3>{title}</h3>
        <p>{note}</p>
        {review_points}
      </div>
      <div class="compare-grid">
        <section class="code-panel">
          {old_panel}
        </section>
        <section class="code-panel">
          {new_panel}
        </section>
      </div>
    </article>
    """.format(
        title=html.escape(card.title),
        note=html.escape(card.note),
        review_points=review_list_html(card.review_points),
        old_panel=render_code_panel(old_text, old_path, old_start, old_kinds, "처음 코드", "old"),
        new_panel=render_code_panel(new_text, new_path, new_start, new_kinds, "지금 코드", "new"),
    )


def architecture_table() -> str:
    rows = [
        ("인덱스 백엔드", "외부 `thirdparty/bplustree` 디스크 B+ 트리", "프로젝트 내부 `memory_bptree` 메모리 B+ 트리"),
        ("테이블 메타데이터", "`csv_file_path` + `index_file_path`", "`csv_file_path` 만 유지"),
        ("부팅 시 인덱스 준비", "기존 `.idx` / `.boot` 파일을 열고 검증 또는 복구", "CSV를 스캔해 매번 메모리 트리 재구축"),
        ("INSERT", "명시적 `id` 필수", "`id` 명시 입력 또는 자동 ID 허용"),
        ("SELECT 지원 범위", "전체 조회 + `WHERE id = ?`", "전체 조회 + `WHERE id = ?` + 다른 컬럼 equality 선형 탐색"),
        ("인덱스 상태", "디스크 파일이 truth source 에 가까움", "CSV가 truth source, 인덱스는 실행 중 재구축"),
        ("테스트", "실행 파일만 빌드", "단위 테스트 + 기능 테스트 추가"),
    ]
    rendered = []
    for title, old_value, new_value in rows:
        rendered.append(
            "<tr><th>{}</th><td>{}</td><td>{}</td></tr>".format(
                html.escape(title),
                html.escape(old_value),
                html.escape(new_value),
            )
        )
    return "\n".join(rendered)


def render_table(headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> str:
    head_html = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        body_rows.append("<tr>{}</tr>".format("".join(f"<td>{html.escape(cell)}</td>" for cell in row)))
    return """
    <table class="glass-table">
      <thead><tr>{head}</tr></thead>
      <tbody>{body}</tbody>
    </table>
    """.format(head=head_html, body="".join(body_rows))


def render_glass_details(
    anchor: str,
    title: str,
    summary: str,
    content: str,
    *,
    open_by_default: bool = True,
    kind: str = "section",
) -> str:
    open_attr = " open" if open_by_default else ""
    return """
    <details id="{anchor}" class="glass-section {kind}"{open_attr}>
      <summary class="glass-summary">
        <span class="summary-left">
          <span class="summary-tag">{kind_label}</span>
          <span class="summary-title">{title}</span>
          <span class="summary-sub">{summary}</span>
        </span>
        <span class="summary-toggle">펴기 / 접기</span>
      </summary>
      <div class="section-content">
        {content}
      </div>
    </details>
    """.format(
        anchor=html.escape(anchor),
        kind=html.escape(kind),
        open_attr=open_attr,
        kind_label="Flow" if kind == "flow" else "Guide",
        title=html.escape(title),
        summary=html.escape(summary),
        content=content,
    )


def render_chain_card(title: str, nodes: tuple[str, ...], *, note: str = "") -> str:
    parts = []
    for index, node in enumerate(nodes):
        if index > 0:
            parts.append("<span class='diagram-arrow'>→</span>")
        parts.append(f"<span class='diagram-node'>{html.escape(node)}</span>")
    note_html = f"<p class='diagram-note'>{html.escape(note)}</p>" if note else ""
    return """
    <div class="diagram-card">
      <h4>{title}</h4>
      <div class="diagram-chain">{parts}</div>
      {note}
    </div>
    """.format(title=html.escape(title), parts="".join(parts), note=note_html)


def render_vertical_card(title: str, nodes: tuple[str, ...], *, note: str = "") -> str:
    parts = []
    for index, node in enumerate(nodes):
        if index > 0:
            parts.append("<span class='diagram-arrow vertical'>↓</span>")
        parts.append(f"<span class='diagram-node wide'>{html.escape(node)}</span>")
    note_html = f"<p class='diagram-note'>{html.escape(note)}</p>" if note else ""
    return """
    <div class="diagram-card">
      <h4>{title}</h4>
      <div class="diagram-stack">{parts}</div>
      {note}
    </div>
    """.format(title=html.escape(title), parts="".join(parts), note=note_html)


def render_shift_card(title: str, pairs: tuple[tuple[str, str], ...]) -> str:
    rows = []
    for old_text, new_text in pairs:
        rows.append(
            "<div class='shift-row'><span class='diagram-node old'>{}</span><span class='diagram-arrow'>→</span><span class='diagram-node new'>{}</span></div>".format(
                html.escape(old_text),
                html.escape(new_text),
            )
        )
    return """
    <div class="diagram-card">
      <h4>{title}</h4>
      <div class="diagram-shift">
        {rows}
      </div>
    </div>
    """.format(title=html.escape(title), rows="".join(rows))


def render_branch_card(title: str, start: tuple[str, ...], decision: str, yes_nodes: tuple[str, ...], no_nodes: tuple[str, ...]) -> str:
    start_html = []
    for index, node in enumerate(start):
        if index > 0:
            start_html.append("<span class='diagram-arrow vertical'>↓</span>")
        start_html.append(f"<span class='diagram-node wide'>{html.escape(node)}</span>")

    def lane(label: str, nodes: tuple[str, ...]) -> str:
        parts = [f"<div class='branch-label'>{html.escape(label)}</div>"]
        for index, node in enumerate(nodes):
            if index > 0:
                parts.append("<span class='diagram-arrow vertical'>↓</span>")
            parts.append(f"<span class='diagram-node wide'>{html.escape(node)}</span>")
        return "<div class='branch-lane'>{}</div>".format("".join(parts))

    return """
    <div class="diagram-card">
      <h4>{title}</h4>
      <div class="diagram-branch">
        <div class="diagram-stack">{start}</div>
        <span class="diagram-arrow vertical">↓</span>
        <span class="diagram-node decision">{decision}</span>
        <div class="branch-grid">
          {yes_lane}
          {no_lane}
        </div>
      </div>
    </div>
    """.format(
        title=html.escape(title),
        start="".join(start_html),
        decision=html.escape(decision),
        yes_lane=lane("예", yes_nodes),
        no_lane=lane("아니오", no_nodes),
    )


def render_requirements_alignment() -> str:
    content = """
    <div class="content-stack">
      <p class="lead">`reum-001`의 핵심을 008 안으로 가져온 요약 섹션이다. 이 HTML 안에서 코드 비교를 읽기 전에 “왜 바뀌었는지”를 먼저 잡을 수 있도록 정리했다.</p>
      <div class="chip-row">
        <span class="glass-chip">메모리 기반 요구사항 정렬</span>
        <span class="glass-chip">자동 ID 부여</span>
        <span class="glass-chip">인덱스 vs 선형 탐색 비교</span>
        <span class="glass-chip">테스트 추가</span>
      </div>
      <div class="diagram-grid two">
        {shift_diagram}
        {lifecycle_diagram}
      </div>
      <div class="content-grid two">
        <div class="glass-card">
          <h3>요약 비교표</h3>
          {summary_table}
        </div>
        <div class="glass-card">
          <h3>인덱스 라이프사이클</h3>
          {lifecycle_table}
        </div>
      </div>
      <div class="content-grid two">
        <div class="glass-card">
          <h3>조회/삽입 경로 변화</h3>
          {query_table}
        </div>
        <div class="glass-card">
          <h3>테스트 계층</h3>
          {test_table}
          <ul class="tight-list">
            <li>현재 구조는 설명 문서만이 아니라 실행 가능한 검증 코드도 가진다.</li>
            <li>그래서 008 안에 `reum-001` 요약을 흡수하는 것이 오히려 자연스럽다.</li>
          </ul>
        </div>
      </div>
    </div>
    """.format(
        shift_diagram=render_shift_card(
            "변화 방향 요약",
            (
                ("디스크 인덱스", "메모리 B+ 트리"),
                ("수동 ID 입력", "자동 ID 기본 지원"),
                ("id 전용 WHERE", "id 인덱스 + 비-id 선형 탐색"),
                ("설명 중심", "테스트 포함 결과물"),
            ),
        ),
        lifecycle_diagram=render_vertical_card(
            "현재 인덱스 준비 흐름",
            (
                "프로그램 시작",
                "CSV 파일 확인",
                "메모리 B+ 트리 생성",
                "CSV 순차 스캔",
                "id 추출",
                "id -> offset 적재",
                "next_id 갱신",
            ),
            note="지금 구조에서는 CSV가 기준 데이터이고 인덱스는 실행 시 재구축된다.",
        ),
        summary_table=render_table(("비교 항목", "이전 구현", "현재 구현", "왜 바꿨는가"), REQUIREMENT_ALIGNMENT_ROWS),
        lifecycle_table=render_table(("단계", "이전 구현", "현재 구현"), INDEX_LIFECYCLE_ROWS),
        query_table=render_table(("질의/기능", "이전 구현", "현재 구현", "의미"), QUERY_PATH_ROWS),
        test_table=render_table(("테스트 종류", "파일", "검증 대상"), TEST_LAYER_ROWS),
    )
    return render_glass_details(
        "requirements",
        "요구사항 정렬 요약",
        "왜 바뀌었는지 먼저 보는 섹션",
        content,
        open_by_default=True,
    )


def render_structure_overview() -> str:
    content = """
    <div class="content-stack">
      <div class="diagram-grid two">
        {old_diagram}
        {new_diagram}
      </div>
      <div class="content-grid two">
        <div class="glass-card old-rail">
          <h3>처음 코드 구조</h3>
          <p>SQL → parser → executor → db_index → `thirdparty/bplustree` → `.idx` / `.boot` 파일</p>
          <ul class="tight-list">
            <li>테이블 메타데이터에 인덱스 파일 경로가 있었다.</li>
            <li>`WHERE id = ?` 만 인덱스를 사용했다.</li>
            <li>INSERT는 사용자가 id를 직접 넣어야 했다.</li>
          </ul>
        </div>
        <div class="glass-card new-rail">
          <h3>지금 코드 구조</h3>
          <p>SQL → parser → executor → db_index → `memory_bptree` → 시작 시 CSV 스캔으로 메모리 인덱스 재구축</p>
          <ul class="tight-list">
            <li>메타데이터에서 인덱스 파일 경로를 제거했다.</li>
            <li>`WHERE id = ?` 는 인덱스, 다른 컬럼은 선형 탐색으로 분기한다.</li>
            <li>INSERT는 자동 ID 또는 명시적 ID 둘 다 처리한다.</li>
          </ul>
        </div>
      </div>
      <div class="glass-card">
        <h3>구조 비교표</h3>
        <table class="glass-table">
          <thead>
            <tr>
              <th>항목</th>
              <th>처음 코드</th>
              <th>지금 코드</th>
            </tr>
          </thead>
          <tbody>
            {architecture_rows}
          </tbody>
        </table>
      </div>
    </div>
    """.format(
        old_diagram=render_chain_card(
            "이전 구조 그림",
            ("SQL 입력", "parser.c", "executor.c", "db_index.c", "thirdparty/bplustree", "users.idx / .boot"),
            note="인덱스 파일이 구조의 한가운데에 있다.",
        ),
        new_diagram=render_chain_card(
            "현재 구조 그림",
            ("SQL 입력", "parser.c", "executor.c", "db_index.c", "memory_bptree.c", "CSV 스캔 재구축"),
            note="CSV가 기준 데이터이고 메모리 인덱스는 시작 시 다시 채운다.",
        ),
        architecture_rows=architecture_table(),
    )
    return render_glass_details(
        "structure",
        "구조 차이 한눈에 보기",
        "초기 구조와 현재 구조를 먼저 요약해서 보는 섹션",
        content,
        open_by_default=True,
    )


def render_section_visual(anchor: str) -> str:
    if anchor == "select":
        return """
        <div class="diagram-grid one">
          {}
        </div>
        """.format(
            render_branch_card(
                "SELECT 분기 그림",
                ("SELECT 입력", "parser가 WHERE 해석"),
                "조건 컬럼이 id인가?",
                ("B+ 트리 검색", "offset으로 row 1개 읽기", "결과 출력"),
                ("CSV 전체 선형 탐색", "컬럼 값 비교", "결과 출력"),
            )
        )

    if anchor == "insert":
        return """
        <div class="diagram-grid one">
          {}
        </div>
        """.format(
            render_vertical_card(
                "현재 자동 ID INSERT 흐름",
                (
                    "INSERT 입력",
                    "parser가 values 해석",
                    "db_index_next_id()",
                    "fixed row 생성",
                    "CSV append",
                    "memory_bptree_put()",
                    "next_id 갱신 완료",
                ),
                note="자동 ID는 executor와 index 계층이 함께 만든다.",
            )
        )

    if anchor == "index":
        return """
        <div class="diagram-grid two">
          {old}
          {new}
        </div>
        """.format(
            old=render_vertical_card(
                "이전 인덱스 흐름",
                (
                    "인덱스 파일 확인",
                    "디스크 트리 열기",
                    "CSV와 검증",
                    "문제 있으면 복구",
                ),
            ),
            new=render_vertical_card(
                "현재 인덱스 흐름",
                (
                    "메모리 트리 생성",
                    "CSV 순차 스캔",
                    "id -> offset 삽입",
                    "실행 중 조회에 사용",
                ),
            ),
        )

    if anchor == "build-test":
        return """
        <div class="diagram-grid one">
          {}
        </div>
        """.format(
            render_branch_card(
                "테스트 범위 그림",
                ("테스트",),
                "무엇을 검증하나?",
                ("단위 테스트", "memory_bptree insert/get", "중복 key / 순서 섞인 입력"),
                ("기능 테스트", "자동 ID", "WHERE id / WHERE name / 재시작"),
            )
        )

    return ""


def render_section(section: Section) -> str:
    bullet_html = "\n".join(f"<li>{html.escape(item)}</li>" for item in section.bullets)
    cards_html = "\n".join(render_compare_block(card) for card in section.cards)
    content = """
    <div class="content-stack">
      {visual}
      <div class="glass-card">
        <h3>핵심 읽기 포인트</h3>
        <ul>{bullets}</ul>
      </div>
      {cards}
    </div>
    """.format(visual=render_section_visual(section.anchor), bullets=bullet_html, cards=cards_html)
    return render_glass_details(
        section.anchor,
        section.title,
        section.summary,
        content,
        open_by_default=True,
        kind="flow",
    )


def render_full_pair(old_path: str | None, new_path: str | None, title: str) -> str:
    old_spec = SourceSpec(old_path, "file", label="처음 코드에는 이 파일이 없습니다.") if old_path else SourceSpec(None, "placeholder", label="처음 코드에는 이 파일이 없습니다.")
    new_spec = SourceSpec(new_path, "file", label="지금 코드에는 이 파일이 없습니다.") if new_path else SourceSpec(None, "placeholder", label="지금 코드에는 이 파일이 없습니다.")
    card = Card(title=title, note="전체 파일 비교 보기", old=old_spec, new=new_spec)
    return """
    <details class="appendix-item glass-subsection">
      <summary>{title}</summary>
      {content}
    </details>
    """.format(
        title=html.escape(title),
        content=render_compare_block(card),
    )


def build_html() -> str:
    toc_items = [
        ("requirements", "요구사항 정렬 요약"),
        ("structure", "구조 차이 한눈에 보기"),
        *[(section.anchor, section.title) for section in FLOW_SECTIONS],
        ("appendix", "전체 파일 부록"),
    ]
    toc = "\n".join(f"<li><a href='#{html.escape(anchor)}'>{html.escape(title)}</a></li>" for anchor, title in toc_items)
    flow_sections = "\n".join(render_section(section) for section in FLOW_SECTIONS)
    full_pairs = "\n".join(render_full_pair(old_path, new_path, title) for old_path, new_path, title in FULL_FILE_PAIRS)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>reum-008 처음 코드 vs 지금 코드 흐름 비교</title>
  <style>
    :root {{
      --bg-top: #e8eef4;
      --bg-mid: #cdd8e3;
      --bg-bottom: #d7cabc;
      --glass: rgba(255, 255, 255, 0.22);
      --glass-strong: rgba(255, 255, 255, 0.38);
      --glass-soft: rgba(255, 255, 255, 0.16);
      --line: rgba(255, 255, 255, 0.46);
      --line-soft: rgba(255, 255, 255, 0.26);
      --ink: #18212c;
      --muted: rgba(24, 33, 44, 0.70);
      --shadow: 0 24px 60px rgba(28, 39, 54, 0.15);
      --code-bg: rgba(248, 250, 252, 0.48);
      --gutter: rgba(248, 250, 252, 0.70);
      --add: rgba(85, 128, 110, 0.16);
      --remove: rgba(173, 122, 87, 0.17);
      --change: rgba(184, 160, 91, 0.18);
      --comment: rgba(86, 104, 120, 0.08);
      --accent-old: #a56f50;
      --accent-new: #2f6d70;
      --accent-parse: #58728b;
      --accent-execute: #8e6e4f;
      --accent-index: #2f7a72;
      --accent-tree: #625b82;
      --accent-tree-old: #8b6a8b;
      --accent-test: #8a5566;
      --accent-build: #5f6d88;
      --accent-storage: #92744f;
      --accent-contract: #5a6877;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
      line-height: 1.6;
      background:
        radial-gradient(circle at 12% 12%, rgba(255,255,255,0.64), transparent 24rem),
        radial-gradient(circle at 84% 16%, rgba(47,109,112,0.14), transparent 20rem),
        radial-gradient(circle at 18% 82%, rgba(165,111,80,0.12), transparent 18rem),
        radial-gradient(circle at 78% 76%, rgba(98,91,130,0.10), transparent 16rem),
        linear-gradient(135deg, var(--bg-top), var(--bg-mid) 52%, var(--bg-bottom));
      min-height: 100vh;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(120deg, rgba(255,255,255,0.32), transparent 30%, rgba(255,255,255,0.16) 52%, transparent 70%),
        radial-gradient(circle at top, rgba(255,255,255,0.16), transparent 38%);
      mix-blend-mode: screen;
      opacity: 0.75;
    }}
    a {{ color: inherit; }}
    .page {{
      width: min(1500px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 64px;
    }}
    .hero, .legend, .glass-section {{
      background: linear-gradient(180deg, rgba(255,255,255,0.22), rgba(255,255,255,0.12));
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(24px) saturate(150%);
      -webkit-backdrop-filter: blur(24px) saturate(150%);
      margin-bottom: 20px;
      position: relative;
      overflow: hidden;
    }}
    .hero::before, .legend::before, .glass-section::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(135deg, rgba(255,255,255,0.28), transparent 40%, rgba(255,255,255,0.12) 70%, transparent);
      pointer-events: none;
    }}
    .hero, .legend {{
      padding: 26px;
    }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: clamp(2rem, 2vw, 2.8rem);
      line-height: 1.15;
      letter-spacing: -0.04em;
    }}
    .hero p {{
      margin: 0 0 10px;
      color: var(--muted);
      max-width: 920px;
    }}
    .meta-grid, .content-grid.two {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }}
    .meta-card, .glass-card {{
      background: var(--glass-strong);
      border: 1px solid var(--line-soft);
      border-radius: 22px;
      padding: 16px 18px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }}
    .meta-card strong {{
      display: block;
      margin-bottom: 4px;
      font-size: 0.92rem;
      color: var(--muted);
    }}
    .meta-card span {{
      font-weight: 800;
    }}
    .toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .glass-button {{
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.24);
      color: var(--ink);
      border-radius: 999px;
      padding: 10px 14px;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
      transition: transform 160ms ease, background 160ms ease, border-color 160ms ease;
    }}
    .glass-button:hover {{
      transform: translateY(-1px);
      background: rgba(255,255,255,0.34);
      border-color: rgba(255,255,255,0.54);
    }}
    .toc {{
      margin: 18px 0 0;
      padding: 0;
      list-style: none;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
    }}
    .toc a {{
      display: block;
      text-decoration: none;
      padding: 12px 14px;
      border-radius: 18px;
      background: rgba(255,255,255,0.22);
      border: 1px solid var(--line-soft);
      font-weight: 700;
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      transition: transform 160ms ease, background 160ms ease;
    }}
    .toc a:hover {{
      transform: translateY(-1px);
      background: rgba(255,255,255,0.30);
    }}
    .legend h2 {{
      margin: 0 0 12px;
    }}
    .legend-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
    }}
    .legend-chip, .glass-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin: 6px 8px 0 0;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.24);
      border: 1px solid var(--line-soft);
      font-size: 0.92rem;
      font-weight: 700;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }}
    .legend-dot {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      display: inline-block;
    }}
    .dot-added {{ background: #5f8f77; }}
    .dot-removed {{ background: #b17a57; }}
    .dot-changed {{ background: #b09a57; }}
    .dot-important {{ background: #3f566d; }}
    details.glass-section > summary {{
      list-style: none;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      padding: 22px 24px;
      position: relative;
      z-index: 1;
    }}
    details.glass-section > summary::-webkit-details-marker {{
      display: none;
    }}
    .summary-left {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }}
    .summary-tag {{
      display: inline-block;
      font-size: 0.76rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(45, 78, 104, 0.88);
    }}
    .summary-title {{
      font-size: clamp(1.2rem, 1.4vw, 1.55rem);
      font-weight: 800;
      letter-spacing: -0.02em;
    }}
    .summary-sub {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .summary-toggle {{
      flex: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 0.9rem;
      font-weight: 700;
      color: var(--muted);
      padding-top: 2px;
    }}
    .summary-toggle::before {{
      content: "▾";
      transition: transform 180ms ease;
    }}
    details.glass-section:not([open]) .summary-toggle::before {{
      transform: rotate(-90deg);
    }}
    .section-content {{
      padding: 0 24px 24px;
      position: relative;
      z-index: 1;
    }}
    .lead {{
      margin: 0;
      color: var(--muted);
    }}
    .content-stack {{
      display: grid;
      gap: 16px;
    }}
    .diagram-grid {{
      display: grid;
      gap: 14px;
    }}
    .diagram-grid.two {{
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    }}
    .diagram-grid.one {{
      grid-template-columns: 1fr;
    }}
    .diagram-card {{
      background: rgba(255,255,255,0.20);
      border: 1px solid var(--line-soft);
      border-radius: 22px;
      padding: 16px 18px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.32);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
    }}
    .diagram-card h4 {{
      margin: 0 0 12px;
      font-size: 1rem;
    }}
    .diagram-note {{
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .diagram-chain {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }}
    .diagram-stack {{
      display: grid;
      justify-items: center;
      gap: 8px;
    }}
    .diagram-node {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: 10px 14px;
      border-radius: 16px;
      border: 1px solid rgba(24,33,44,0.08);
      background: linear-gradient(180deg, rgba(255,255,255,0.48), rgba(255,255,255,0.34));
      font-weight: 700;
      text-align: center;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.40);
    }}
    .diagram-node.wide {{
      width: min(100%, 360px);
    }}
    .diagram-node.decision {{
      border-style: dashed;
      background: linear-gradient(180deg, rgba(90,114,139,0.14), rgba(255,255,255,0.28));
    }}
    .diagram-node.old,
    .diagram-node.new {{
      min-width: 140px;
    }}
    .diagram-node.old {{
      border-color: rgba(165,111,80,0.24);
      background: linear-gradient(180deg, rgba(165,111,80,0.16), rgba(255,255,255,0.36));
    }}
    .diagram-node.new {{
      border-color: rgba(47,109,112,0.24);
      background: linear-gradient(180deg, rgba(47,109,112,0.16), rgba(255,255,255,0.36));
    }}
    .diagram-arrow {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 22px;
      font-size: 1rem;
      font-weight: 800;
      color: rgba(24,33,44,0.52);
    }}
    .diagram-arrow.vertical {{
      min-width: auto;
      line-height: 1;
    }}
    .diagram-shift {{
      display: grid;
      gap: 10px;
    }}
    .shift-row {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }}
    .diagram-branch {{
      display: grid;
      justify-items: center;
      gap: 8px;
    }}
    .branch-grid {{
      width: 100%;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .branch-lane {{
      display: grid;
      justify-items: center;
      gap: 8px;
      padding: 10px;
      border-radius: 18px;
      border: 1px solid var(--line-soft);
      background: rgba(255,255,255,0.16);
    }}
    .branch-label {{
      font-size: 0.84rem;
      font-weight: 800;
      color: var(--muted);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .old-rail {{
      border-left: 5px solid var(--accent-old);
      background: linear-gradient(135deg, rgba(165,111,80,0.14), rgba(255,255,255,0.16));
    }}
    .new-rail {{
      border-left: 5px solid var(--accent-new);
      background: linear-gradient(135deg, rgba(47,109,112,0.14), rgba(255,255,255,0.16));
    }}
    .glass-card h3 {{
      margin: 0 0 10px;
      font-size: 1.02rem;
    }}
    .glass-card p {{
      margin: 0 0 10px;
    }}
    .glass-table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border-radius: 18px;
      background: rgba(255,255,255,0.16);
    }}
    .glass-table th, .glass-table td {{
      border: 1px solid var(--line-soft);
      padding: 12px 14px;
      text-align: left;
      vertical-align: top;
    }}
    .glass-table thead th {{
      background: rgba(255,255,255,0.24);
    }}
    .tight-list {{
      margin: 0;
      padding-left: 20px;
    }}
    .compare-card {{
      border: 1px solid var(--line-soft);
      border-radius: 24px;
      padding: 18px;
      background: rgba(255,255,255,0.16);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.32);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }}
    .compare-meta {{
      margin-bottom: 14px;
    }}
    .compare-meta h3 {{
      margin: 0 0 6px;
      font-size: 1.12rem;
    }}
    .compare-meta p {{
      margin: 0;
      color: var(--muted);
    }}
    .review-points {{
      margin-top: 12px;
      padding: 12px 14px;
      border-radius: 18px;
      background: rgba(255,255,255,0.22);
      border: 1px solid var(--line-soft);
    }}
    .review-points strong {{
      display: block;
      margin-bottom: 6px;
    }}
    .review-points ul {{
      margin: 0;
      padding-left: 20px;
    }}
    .compare-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .code-panel {{
      border: 1px solid var(--line-soft);
      border-radius: 20px;
      overflow: hidden;
      min-width: 0;
      background: rgba(255,255,255,0.14);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line-soft);
      background: rgba(255,255,255,0.22);
      font-size: 0.92rem;
    }}
    .panel-header.panel-old {{
      background: linear-gradient(135deg, rgba(165,111,80,0.18), rgba(255,255,255,0.24));
    }}
    .panel-header.panel-new {{
      background: linear-gradient(135deg, rgba(47,109,112,0.18), rgba(255,255,255,0.24));
    }}
    .panel-side {{
      font-weight: 800;
      color: var(--muted);
    }}
    .panel-side.side-old {{
      color: var(--accent-old);
    }}
    .panel-side.side-new {{
      color: var(--accent-new);
    }}
    .panel-path {{
      color: var(--muted);
      word-break: break-all;
      text-align: right;
    }}
    .code-wrap {{
      max-height: 760px;
      overflow: auto;
      background: var(--code-bg);
    }}
    .code-table {{
      width: 100%;
      border-collapse: collapse;
      font-family: "SFMono-Regular", "JetBrains Mono", "Consolas", monospace;
      font-size: 12.5px;
      line-height: 1.48;
    }}
    .gutter {{
      position: sticky;
      left: 0;
      width: 60px;
      min-width: 60px;
      padding: 0 10px;
      text-align: right;
      vertical-align: top;
      color: rgba(24,33,44,0.48);
      background: var(--gutter);
      border-right: 1px solid var(--line-soft);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
    }}
    .note-gutter {{
      font-weight: 800;
      color: rgba(24,33,44,0.40);
    }}
    .code {{
      padding: 0 14px;
      white-space: pre;
      vertical-align: top;
    }}
    .code-comment {{
      padding: 10px 14px;
      color: rgba(24,33,44,0.78);
      background: var(--comment);
      font-size: 0.9rem;
      border-left: 4px solid rgba(90,114,139,0.18);
    }}
    .comment-row td {{
      border-top: 1px solid rgba(255,255,255,0.12);
    }}
    .code-row.diff-added td {{ background: var(--add); }}
    .code-row.diff-removed td {{ background: var(--remove); }}
    .code-row.diff-changed td {{ background: var(--change); }}
    .code-row.important-boot td.code {{ border-left: 4px solid var(--accent-old); }}
    .code-row.important-contract td.code {{ border-left: 4px solid var(--accent-contract); }}
    .code-row.important-parse td.code {{ border-left: 4px solid var(--accent-parse); }}
    .code-row.important-execute td.code {{ border-left: 4px solid var(--accent-execute); }}
    .code-row.important-index td.code {{ border-left: 4px solid var(--accent-index); }}
    .code-row.important-tree td.code {{ border-left: 4px solid var(--accent-tree); }}
    .code-row.important-tree-old td.code {{ border-left: 4px solid var(--accent-tree-old); }}
    .code-row.important-test td.code {{ border-left: 4px solid var(--accent-test); }}
    .code-row.important-build td.code {{ border-left: 4px solid var(--accent-build); }}
    .code-row.important-storage td.code {{ border-left: 4px solid var(--accent-storage); }}
    .appendix-shell {{
      display: grid;
      gap: 14px;
    }}
    .appendix-item {{
      border: 1px solid var(--line-soft);
      border-radius: 20px;
      background: rgba(255,255,255,0.16);
      overflow: hidden;
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
    }}
    .appendix-item > summary {{
      cursor: pointer;
      padding: 14px 16px;
      font-weight: 800;
      list-style: none;
      background: rgba(255,255,255,0.22);
    }}
    .appendix-item > summary::-webkit-details-marker {{
      display: none;
    }}
    .appendix-item[open] > summary {{
      border-bottom: 1px solid var(--line-soft);
    }}
    .appendix-item > .compare-card {{
      margin: 0;
      border: 0;
      border-radius: 0;
      background: transparent;
      box-shadow: none;
    }}
    @media (max-width: 1024px) {{
      .compare-grid {{
        grid-template-columns: 1fr;
      }}
    }}
    @media (max-width: 768px) {{
      .page {{
        width: min(100vw - 18px, 1500px);
        padding-top: 16px;
      }}
      .hero, .legend {{
        padding: 18px;
      }}
      details.glass-section > summary,
      .section-content {{
        padding-left: 18px;
        padding-right: 18px;
      }}
      .summary-toggle {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>reum-008 처음 코드 vs 지금 코드 흐름 비교</h1>
      <p>`HEAD` 기준 처음 코드와 현재 작업 트리를 2단 구조로 나란히 보여주는 비교용 HTML입니다. 이번 버전은 코드만 비교하는 문서가 아니라, 요구사항 정렬 요약과 리뷰 주석까지 함께 읽을 수 있는 설명형 비교 문서로 다듬었습니다.</p>
      <p>`reum-001`의 핵심 내용은 그대로 중복 복붙하지 않고, “왜 바뀌었는지”를 먼저 읽을 수 있는 요약 섹션으로 흡수했습니다. 이 방식이 008의 역할과 더 잘 맞습니다.</p>
      <div class="meta-grid">
        <div class="meta-card"><strong>처음 코드 기준</strong><span>{html.escape(BASE_REF)} 커밋 상태</span></div>
        <div class="meta-card"><strong>지금 코드 기준</strong><span>현재 작업 트리</span></div>
        <div class="meta-card"><strong>비교 방식</strong><span>흐름 카드 + 전체 파일 부록</span></div>
        <div class="meta-card"><strong>리뷰 편의</strong><span>섹션 접기/펼치기 + 코드 주석 행</span></div>
      </div>
      <div class="toolbar">
        <button class="glass-button" data-action="expand-all">모두 펼치기</button>
        <button class="glass-button" data-action="collapse-all">모두 접기</button>
        <button class="glass-button" data-action="expand-flow">흐름 섹션만 펼치기</button>
      </div>
      <ul class="toc">
        {toc}
      </ul>
    </section>

    <section class="legend">
      <h2>범례</h2>
      <div class="legend-grid">
        <div class="glass-card">
          <p>차이 강조</p>
          <span class="legend-chip"><span class="legend-dot dot-added"></span>현재 코드에 새로 생긴 줄</span>
          <span class="legend-chip"><span class="legend-dot dot-removed"></span>처음 코드에만 있던 줄</span>
          <span class="legend-chip"><span class="legend-dot dot-changed"></span>양쪽에서 바뀐 줄</span>
        </div>
        <div class="glass-card">
          <p>리뷰 표시</p>
          <span class="legend-chip"><span class="legend-dot dot-important"></span>중요 함수 줄은 색 막대로 표시</span>
          <span class="legend-chip"><span class="legend-dot dot-important"></span>`//` 줄은 HTML 안에 추가한 리뷰 주석</span>
        </div>
      </div>
    </section>

    {render_requirements_alignment()}
    {render_structure_overview()}
    {flow_sections}

    {render_glass_details(
        "appendix",
        "전체 파일 부록",
        "흐름 카드 아래에서 실제 파일 전체를 2단 비교로 펼쳐 볼 수 있는 섹션",
        f"<div class='appendix-shell'>{full_pairs}</div>",
        open_by_default=False,
    )}
  </main>

  <script>
    const topSections = Array.from(document.querySelectorAll('details.glass-section'));
    const flowSections = Array.from(document.querySelectorAll('details.flow'));

    document.querySelector('[data-action=\"expand-all\"]').addEventListener('click', () => {{
      topSections.forEach(section => section.open = true);
    }});

    document.querySelector('[data-action=\"collapse-all\"]').addEventListener('click', () => {{
      topSections.forEach(section => section.open = false);
    }});

    document.querySelector('[data-action=\"expand-flow\"]').addEventListener('click', () => {{
      topSections.forEach(section => {{
        section.open = flowSections.includes(section);
      }});
    }});
  </script>
</body>
</html>
"""


def main() -> int:
    OUTPUT_PATH.write_text(build_html(), encoding="utf-8")
    print(f"generated {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
