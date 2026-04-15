# Jungle Mini DB

C로 구현한 작은 SQL 처리기다. `users`, `posts` 테이블을 고정 길이 row 파일로 저장하고, 프로그램 시작 시 CSV를 스캔해 메모리 기반 B+Tree 인덱스를 재구축한다. `where id = ...` 조회는 인덱스를 사용하고, 다른 컬럼 조건 조회는 같은 SQL 실행기 안에서 선형 탐색으로 처리한다.

지원 SQL 예시:

```sql
select * from users;
select * from users where id = 101;
select * from users where name = new-user;
insert into users values (new-user);
insert into users values (104,seed-user);
```

## Build

```bash
cmake -S . -B cmake-build-debug
cmake --build cmake-build-debug
```

## Run

```bash
./cmake-build-debug/jungle_mini_db
```

종료:

```text
.exit
```

## Tests

단위 테스트:

```bash
cc -std=c11 tests/test_memory_bptree.c memory_bptree.c -I. -o /tmp/memory_bptree_tests
/tmp/memory_bptree_tests
```

기능 테스트:

```bash
python3 tests/test_mini_db_requirements.py
```

## Benchmark

`docs/004-bplus-tree-index.md`의 대규모 데이터 성능 테스트 조건을 확인하는 스크립트가 있다.

- 기본값으로 1,000,000개 레코드를 `INSERT` SQL로 적재한다.
- `id` 기준 SELECT는 미니 DB의 B+Tree 인덱스 경로를 사용한다.
- `name` 기준 SELECT는 미니 DB 실행기의 선형 탐색 경로를 사용한다.
- 두 SELECT 방식의 실행 시간을 비교한다.

스크립트는 Python 3 표준 라이브러리만 사용한다. venv나 패키지 설치가 필요 없다.

```bash
./scripts/benchmark_bplus_tree_index.py
```

결과를 JSON으로 저장:

```bash
./scripts/benchmark_bplus_tree_index.py --output benchmark-results/bplus-tree-index.json
```

빠른 동작 확인:

```bash
./scripts/benchmark_bplus_tree_index.py --records 1000 --select-repetitions 5 --load-mode generate --skip-build
```

기본적으로 벤치마크 실행 전 기존 `data/users.csv`와 남아 있는 `data/users.idx*` 파일을 백업하고 실행 후 복원한다. 과거 디스크 인덱스 실험에서 생성된 `data/users.idx*` 파일이 있어도 현재 구현은 사용하지 않는다.
