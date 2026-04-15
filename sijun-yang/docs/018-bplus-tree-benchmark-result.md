# B+Tree 인덱스 벤치마크 실행 결과

이 문서는 `scripts/prepare_bplus_tree_datasets.sh`와 `scripts/benchmark_bplus_tree_index.py`로 실행한 B+Tree 인덱스 조회 벤치마크 결과를 정리한다.

결과 원본은 `benchmark-results/bplus-tree-index.json`에 저장된 값을 기준으로 한다.

## 1. 실행 목적

이번 벤치마크의 목적은 `users` 테이블에서 `id` 조건 조회가 B+Tree 인덱스를 사용할 때, fixed-row CSV를 선형 탐색하는 방식과 어느 정도 차이가 나는지 확인하는 것이다.

비교 대상은 두 가지다.

| 항목 | 의미 |
|---|---|
| `indexed id SELECT after startup` | 미니 DB 프로세스가 뜨고 인덱스 준비가 끝난 뒤, `select * from users where id = ...;`를 실행한 시간 |
| `linear name scan` | Python 스크립트가 fixed-row CSV를 처음부터 읽으면서 `name` 값을 찾은 시간 |

중요한 점은 `mini DB startup/index validation`은 실제 SELECT 시간에 포함하지 않는다는 것이다. 이 값은 미니 DB가 시작할 때 기존 B+Tree index와 CSV 데이터의 정합성을 확인하는 시간이다.

## 2. 실행 명령

실행 위치는 `sijun-yang/` 디렉터리다.

먼저 100만, 1000만, 1억 row 데이터셋을 준비했다.

```bash
./scripts/prepare_bplus_tree_datasets.sh
```

그 다음 이미 준비된 CSV와 B+Tree index를 재사용해서 SELECT 측정만 수행했다.

```bash
./scripts/benchmark_bplus_tree_index.py --select-only --output benchmark-results/bplus-tree-index.json
```

## 3. 데이터셋 준비 결과

준비된 데이터셋은 `benchmark-datasets/` 아래에 저장된다.

| row 수 | CSV 파일 | B+Tree index 파일 |
|---:|---|---|
| 1,000,000 | `benchmark-datasets/users-1000000.csv` | `benchmark-datasets/users-1000000.idx` |
| 10,000,000 | `benchmark-datasets/users-10000000.csv` | `benchmark-datasets/users-10000000.idx` |
| 100,000,000 | `benchmark-datasets/users-100000000.csv` | `benchmark-datasets/users-100000000.idx` |

측정 실행에서는 세 데이터셋 모두 이미 준비되어 있었다.

| row 수 | CSV prepared this run | index prepared this run |
|---:|---|---|
| 1,000,000 | `false` | `false` |
| 10,000,000 | `false` | `false` |
| 100,000,000 | `false` | `false` |

따라서 아래 측정값은 INSERT 적재 시간이나 인덱스 생성 시간을 포함하지 않는다.

## 4. 측정 결과 요약

| row 수 | 조회 대상 | 시작/검증 시간 | B+Tree id 조회 | 선형 name scan | 선형/B+Tree 비율 |
|---:|---|---:|---:|---:|---:|
| 1,000,000 | `id=1000000` / `user-1000000` | 1.685s | 0.078ms | 694.552ms | 8,909.31x |
| 10,000,000 | `id=10000000` / `user-10000000` | 21.408s | 0.086ms | 6,975.519ms | 80,914.05x |
| 100,000,000 | `id=100000000` / `user-100000000` | 371.123s | 0.115ms | 68,955.078ms | 599,828.44x |

## 5. 결과 해석

B+Tree id 조회 시간은 데이터가 100만 row에서 1억 row로 커져도 0.078ms에서 0.115ms 수준으로만 증가했다.

반면 선형 scan은 row 수가 커지는 만큼 거의 선형으로 증가했다.

| row 수 | 선형 scan 시간 |
|---:|---:|
| 1,000,000 | 0.695s |
| 10,000,000 | 6.976s |
| 100,000,000 | 68.955s |

이 차이는 접근 방식의 차이에서 나온다.

`id` 조회는 B+Tree에서 `id -> row offset`을 찾은 뒤, CSV 파일의 해당 byte offset으로 이동해서 row 하나만 읽는다.

```text
select * from users where id = 100000000;
-> B+Tree에서 id 검색
-> row offset 획득
-> fseek으로 해당 위치 이동
-> fixed row 하나 읽기
```

선형 scan은 찾는 값이 마지막 row에 있을 때 파일 전체를 앞에서부터 읽어야 한다.

```text
name = user-100000000 찾기
-> 1번 row 읽기
-> 2번 row 읽기
-> ...
-> 100,000,000번 row 읽기
```

이번 벤치마크의 target은 각 데이터셋의 마지막 row다. 따라서 선형 scan에는 가장 불리하고, B+Tree 조회에는 일반적인 단건 검색에 가까운 조건이다.

## 6. 시작/검증 시간이 큰 이유

`mini DB startup/index validation`은 실제 SELECT 시간이 아니다.

현재 미니 DB는 프로세스 시작 시 `db_index_open_table()`에서 기존 index 파일과 CSV 파일의 정합성을 확인한다. 이 과정은 CSV 전체를 읽으면서 각 row의 id가 B+Tree index에 올바르게 들어 있는지 검사한다.

그래서 이 시간은 데이터 크기에 따라 크게 증가한다.

| row 수 | 시작/검증 시간 |
|---:|---:|
| 1,000,000 | 1.685s |
| 10,000,000 | 21.408s |
| 100,000,000 | 371.123s |

1억 row 측정에서 다음 메시지가 반복된 이유도 이 검증 단계가 길었기 때문이다.

```text
waiting for mini DB startup/index validation after 30s
waiting for mini DB startup/index validation after 60s
...
waiting for mini DB startup/index validation after 360s
```

즉 1억 row에서 오래 걸린 부분은 B+Tree SELECT가 아니라, SELECT를 받기 전에 실행되는 index validation이다.

## 7. 결론

이번 결과에서 확인한 핵심은 다음과 같다.

- B+Tree id 조회는 1억 row에서도 단건 조회 시간이 0.115ms 수준이다.
- 선형 scan은 1억 row에서 68.955초가 걸렸다.
- 데이터가 커질수록 선형 scan은 row 수에 비례해 느려진다.
- B+Tree 조회 자체는 데이터 크기가 커져도 단건 조회 시간이 매우 작게 유지된다.
- 현재 구현의 가장 큰 병목은 SELECT가 아니라 프로세스 시작 시 수행하는 전체 index validation이다.

따라서 이 벤치마크는 B+Tree 인덱스가 단건 id 조회에는 매우 유리하다는 점을 보여준다. 동시에 운영 관점에서는 매 시작마다 전체 CSV를 검증하는 정책을 그대로 둘 경우, 대용량 데이터셋에서는 시작 시간이 큰 비용이 된다는 점도 보여준다.
