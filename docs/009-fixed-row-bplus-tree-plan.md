# 고정 길이 CSV + B+Tree 인덱스 적용 계획

## Summary

- 현재 C11 기반 미니 DB 구조는 유지하고, `begeekmyfriend/bplustree`의 C 구현을 `third_party/`에 vendoring한다.
- 라이브러리 타입과 API는 `db_index.c/.h` wrapper 뒤에 숨긴다. 실행기와 파서는 `bplus_tree_*` API를 직접 호출하지 않는다.
- 물리적 row는 항상 `64 bytes`로 저장한다. 이 크기는 줄바꿈 `\n`까지 포함한다.
- 각 CSV row의 마지막 필드는 내부 padding 컬럼으로 사용한다. 사용자 입력/출력에서는 숨기고, 파일에만 저장한다.
- B+Tree key는 첫 번째 컬럼 `id`이고, leaf value는 CSV 파일 byte offset이다.
- `begeekmyfriend/bplustree`는 `data == 0`을 delete로 처리하므로, wrapper는 실제 offset 대신 `offset + 1`을 저장하고 읽을 때 `stored_offset - 1`로 복원한다.

## Key Changes

- `mini_db.h`에 `ROW_SIZE = 64`, padding 관련 상수, `WHERE id` 조건을 담을 select plan 필드, `RowLocation` 타입을 추가한다.
- `parser.c`는 기존 `select * from table;`를 유지하고, `select * from table where id = 101;`를 추가 지원한다.
- `executor.c`는 CSV 줄 단위 읽기/쓰기 대신 64-byte fixed row 단위로 처리한다.
- B+Tree wrapper 모듈을 새로 추가해 라이브러리 타입을 외부로 노출하지 않는다.
- `CMakeLists.txt`는 `third_party/bplustree/bplustree.c`와 새 wrapper 소스 파일을 빌드 대상에 포함한다.
- `data/users.csv`, `data/posts.csv`는 기존 데이터를 64-byte row 형식으로 한 번 변환한다. 런타임 자동 마이그레이션 코드는 추가하지 않는다.

## Library Integration Plan

- upstream 기준은 `begeekmyfriend/bplustree`의 `disk-io` 브랜치다.
- vendoring 대상은 최소 `lib/bplustree.c`, `lib/bplustree.h`, `LICENSE`다.
- wrapper는 테이블별 B+Tree 인스턴스를 관리한다. 예를 들어 `users`와 `posts`는 서로 다른 index 파일 또는 서로 다른 tree 핸들을 가진다.
- wrapper 공개 API는 다음처럼 작게 유지한다.

```c
int db_index_init_all(void);
void db_index_shutdown_all(void);
int db_index_rebuild_table(const TableMetadata *table);
int db_index_put(const char *table_name, int id, long row_offset);
int db_index_get(const char *table_name, int id, long *row_offset);
```

- `db_index_rebuild_table()`은 프로그램 시작 시 CSV를 64-byte row 단위로 스캔하면서 첫 번째 컬럼 `id`와 현재 byte offset을 B+Tree에 등록한다.
- INSERT는 파일 append 전 `ftell(file)`로 새 row offset을 얻고, row 쓰기가 성공한 뒤 `db_index_put()`으로 `id -> offset`을 등록한다.
- `WHERE id = ?` SELECT는 `db_index_get()`으로 offset을 찾고, `fseek(table_path, offset, SEEK_SET)` 후 정확히 한 row만 읽는다.
- 전체 SELECT는 인덱스를 사용하지 않고 기존처럼 파일 전체를 순차 스캔한다.

## Data Format And Behavior

- row encoding은 `logical_value1,logical_value2,` 뒤에 `_` padding을 채워 총 63 bytes를 만들고 마지막 1 byte는 `\n`으로 둔다.
- SELECT 출력은 기존처럼 논리 컬럼만 보여준다. padding 컬럼은 컬럼명에도 출력하지 않고 row 출력에서도 제외한다.
- `select * from users where id = 101;`는 B+Tree에서 `id -> byte offset`을 찾고, `fseek(table_path, offset, SEEK_SET)` 후 정확히 64 bytes만 읽는다.
- `select * from users;`는 파일 크기 기준으로 `0, 64, 128...` offset을 순차 스캔한다.
- INSERT는 먼저 id 중복 여부를 B+Tree로 확인한 뒤 파일 끝에 fixed row를 append한다. 중복 id이면 파일을 쓰지 않고 에러를 출력한다.
- logical row가 padding 포함 64 bytes에 들어가지 않으면 INSERT를 거부하고 `row size를 초과했습니다`를 출력한다.

## Begeekmyfriend Integration Notes

- `bplustree.h`의 `key_t`는 `int`다. 따라서 이번 인덱스 key는 정수형 `id`로 제한한다.
- value 타입은 `long`이므로 CSV byte offset 저장에 맞다.
- `bplus_tree_put(tree, key, 0)`은 delete 의미다. 실제 offset `0`을 저장할 수 없으므로 wrapper에서 `offset + 1` 규칙을 반드시 적용한다.
- disk-io 구현은 `pread`, `pwrite`, `open`, `fsync` 등 POSIX API를 사용한다. 현재 macOS/Linux 개발 환경에서는 맞지만, Windows 빌드는 별도 대응이 필요하다.
- 구현 내부에 `_block_size`, `_max_order`, `_max_entries` 전역 상태가 있으므로 모든 테이블 인덱스는 같은 block size로 초기화한다.
- upstream `bplus_tree_init()`은 설정 로그를 `printf`로 출력한다. REPL 출력이 지저분해지지 않도록 vendoring 후 해당 출력은 제거하거나 debug macro로 감싼다.
- index 파일과 CSV 파일의 sync 문제가 생길 수 있으므로, 첫 구현에서는 프로그램 시작 시 CSV에서 인덱스를 재구축하는 방식을 기본으로 둔다.

## Test Plan

- `cmake --build cmake-build-debug`로 기존 빌드가 유지되는지 확인한다.
- `select * from users;`가 padding 없이 기존 논리 컬럼과 row만 출력하는지 확인한다.
- `select * from users where id = 101;`가 B+Tree 경로로 단일 row를 출력하는지 확인한다.
- 없는 id 검색은 에러가 아니라 컬럼명만 출력하는 빈 결과로 처리한다.
- INSERT 후 `data/*.csv` 파일 크기가 항상 `64`의 배수인지 확인한다.
- INSERT한 id를 즉시 `WHERE id`로 조회해 index 갱신과 offset 접근이 맞는지 확인한다.
- 중복 id INSERT, 64 bytes 초과 row INSERT, 잘못된 `where` 문법을 각각 거부하는지 확인한다.
- 첫 번째 row처럼 byte offset이 `0`인 레코드도 `WHERE id`로 조회되는지 확인한다. 이 테스트는 `offset + 1` wrapper 규칙을 검증한다.
- 프로그램을 재시작한 뒤 기존 CSV 데이터가 다시 인덱싱되고 `WHERE id` 조회가 동작하는지 확인한다.

## Assumptions

- `row_size = 64 bytes`는 줄바꿈까지 포함한 실제 파일 레코드 간격이다.
- B+Tree index는 `begeekmyfriend/bplustree`의 disk-io 구현을 사용하더라도, 첫 구현에서는 CSV를 기준 데이터로 보고 프로그램 시작 시 재구축한다.
- 기존처럼 `id`는 INSERT 입력에 포함된다. 자동 id 발급은 이번 최소 변경 범위에 포함하지 않는다.
- padding 문자는 `_`로 고정한다.
- `id`는 32-bit signed integer 범위 안에 들어온다고 가정한다.
