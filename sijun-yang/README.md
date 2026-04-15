# Jungle Mini DB

C로 구현한 작은 SQL 처리기다. `users`, `posts` 테이블을 고정 길이 row 파일로 저장하고, `id` 조회는 B+Tree 인덱스를 통해 row 위치를 찾아 읽는다.

지원 SQL 예시:

```sql
select * from users;
select * from users where id = 101;
insert into users values (104,new-user);
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

## Benchmark

`docs/004-bplus-tree-index.md`의 대규모 데이터 성능 테스트 조건을 확인하는 스크립트가 있다.

- 기본 데이터셋은 1,000,000개, 10,000,000개, 100,000,000개 row다.
- INSERT SQL로 적재하지 않고, fixed-row CSV와 B+Tree index를 미리 만들어둔다.
- `id` 기준 SELECT는 미니 DB의 B+Tree 인덱스 경로를 사용한다.
- `name` 기준 SELECT는 fixed-row 데이터 파일을 선형 탐색한다.
- 미니 DB 시작 시 수행되는 index validation 시간과, 시작 이후 SELECT 실행 시간을 분리해서 출력한다.
- `indexed id SELECT after startup` 항목만 실제 B+Tree 조회 시간이다.

스크립트는 Python 3 표준 라이브러리만 사용한다. venv나 패키지 설치가 필요 없다.

먼저 데이터셋을 준비한다. 기본값은 100만, 1000만, 1억 row다.

```bash
./scripts/prepare_bplus_tree_datasets.sh
```

특정 크기만 준비하려면 `--datasets`를 넘긴다.

```bash
./scripts/prepare_bplus_tree_datasets.sh --datasets 1000000,10000000
```

준비된 데이터셋으로 SELECT만 측정한다.

```bash
./scripts/benchmark_bplus_tree_index.py --select-only
```

`--select-only`에서도 미니 DB 프로세스 시작 시 기존 B+Tree index와 CSV의 정합성 검증이 먼저 수행된다. 이 시간은 `mini DB startup/index validation`으로 따로 출력되며, B+Tree 조회 시간에는 포함하지 않는다.

결과를 JSON으로 저장:

```bash
./scripts/benchmark_bplus_tree_index.py --select-only --output benchmark-results/bplus-tree-index.json
```

빠른 동작 확인:

```bash
./scripts/benchmark_bplus_tree_index.py --datasets 1000 --select-repetitions 1
```

데이터셋은 `benchmark-datasets/` 아래에 저장된다. 기본적으로 벤치마크 실행 전 기존 `data/users.csv`, `data/users.idx`, `data/users.idx.boot`를 백업하고 실행 후 복원한다. 생성된 데이터셋, 인덱스 파일, 실행 결과는 git에서 제외된다.
