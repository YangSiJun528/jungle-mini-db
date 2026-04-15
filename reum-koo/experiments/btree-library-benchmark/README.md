# B-tree Library Benchmark Lab

이 폴더는 여러 B-tree/B+tree 구현을 **같은 입력**, **같은 검증 규칙**, **같은 측정 방식**으로 비교하기 위한 실험실이다.

핵심 목표는 두 가지다.

- 다섯 가지 구현을 같은 insert/get 인터페이스로 감싸서 비교하기
- 결과를 JSON과 Markdown으로 남겨 재현 가능하게 만들기

## 현재 비교 대상 5개

| ID | 구현 | 계열 | 저장 방식 |
| --- | --- | --- | --- |
| `reum_memory_bptree` | 현재 프로젝트의 `memory_bptree.c` | B+ tree | in-memory |
| `habedi_bptree` | `habedi/bptree` | B+ tree | in-memory |
| `tidwall_btree_c` | `tidwall/btree.c` | B-tree | in-memory |
| `kronuz_cpp_btree` | `Kronuz/cpp-btree` | B-tree | in-memory |
| `frozenca_btree` | `frozenca/BTree` | B-tree | in-memory |

## 폴더 구조

```text
btree-library-benchmark/
├─ README.md
├─ .gitignore
├─ run_btree_library_benchmarks.py
├─ common/
│  ├─ benchmark_adapter.h
│  └─ benchmark_main.cpp
├─ adapters/
│  ├─ adapter_reum_memory_bptree.c
│  ├─ adapter_habedi_bptree.c
│  ├─ adapter_tidwall_btree_c.c
│  ├─ adapter_kronuz_cpp_btree.cpp
│  ├─ adapter_frozenca_btree.cpp
│  └─ library_registry.cpp
├─ third_party/
│  ├─ habedi_bptree/
│  ├─ tidwall_btree_c/
│  ├─ kronuz_cpp_btree/
│  └─ frozenca_btree/
├─ results/
│  ├─ latest_results.json
│  ├─ latest_summary.md
│  └─ runtime/
└─ docs/
```

## 설계 방식

전체 프로젝트를 라이브러리마다 통째로 복사하지 않고,
**공통 실행기 + 라이브러리별 어댑터** 구조로 만들었다.

즉, 비교의 핵심은 아래와 같다.

1. 공통 실행기는 키 생성, 셔플, 시간 측정, 정답 검증을 담당한다
2. 각 라이브러리 어댑터는 `create`, `insert`, `get`, `destroy`만 구현한다
3. 결과는 동일한 형식으로 출력되어 바로 비교할 수 있다

이 구조가 좋은 이유는,
"시험 문제는 같고 엔진만 다르다"는 상태를 유지하기 쉽기 때문이다.

## 현재 벤치마크 시나리오

이번 버전은 **6개의 데이터셋 크기**와 **6개의 시나리오**를 함께 돈다.

### 데이터셋 크기

- `10,000`
- `100,000`
- `1,000,000`
- `2,000,000`
- `5,000,000`
- `8,000,000`

### 시나리오

1. `dense_seq_build_rand_get`
Dense 키를 순차 삽입하고 랜덤 조회한다.

2. `dense_rand_build_rand_get`
Dense 키를 랜덤 삽입하고 랜덤 조회한다.

3. `dense_rev_build_rand_get`
Dense 키를 역순 삽입하고 랜덤 조회한다.

4. `dense_seq_build_seq_get`
Dense 키를 순차 삽입하고 순차 조회한다.

5. `dense_rand_build_hot_get`
Dense 키를 랜덤 삽입하고, 상위 1% hot subset을 반복 조회한다.

6. `sparse_rand_build_rand_get`
간격이 큰 sparse 키를 랜덤 삽입하고 랜덤 조회한다.

이 조합을 둔 이유는,
삽입 순서, 키 분포, 접근 지역성이 순위에 어떤 영향을 주는지 분리해서 보기 위해서다.

## 실행 방법

기본 실행:

```bash
python3 reum-koo/experiments/btree-library-benchmark/run_btree_library_benchmarks.py
```

단일 크기만 보고 싶을 때:

```bash
python3 reum-koo/experiments/btree-library-benchmark/run_btree_library_benchmarks.py --records 1000000
```

이미 빌드한 뒤 다시 실행:

```bash
python3 reum-koo/experiments/btree-library-benchmark/run_btree_library_benchmarks.py --skip-build
```

## 결과 파일

| 파일 | 역할 |
| --- | --- |
| `results/latest_results.json` | 기계가 읽기 좋은 원시 결과 |
| `results/latest_summary.md` | 사람이 읽기 좋은 요약 표 |
| `results/latest_detailed_report.md` | 실험 중간 이슈까지 포함한 상세 보고서 |
| `results/runtime/` | 실행 중 생기는 임시 산출물 |

실행 스크립트는 매번 `build/`와 `results/runtime/`를 다시 만들어,
이전 실험의 찌꺼기가 다음 결과에 섞이지 않게 한다.

## 최신 측정 하이라이트

- 전체 lookup 우승 횟수는 `Kronuz/cpp-btree`가 `13`회로 가장 많았다.
- 전체 insert 우승 횟수도 `Kronuz/cpp-btree`가 `17`회로 가장 많았다.
- `habedi/bptree`와 `reum memory_bptree`도 lookup 우승을 각각 `10`회씩 가져가면서, 큰 구간에서 시나리오별 강점이 분명히 갈렸다.
- `dense_rand_build_hot_get`에서는 데이터가 커진 뒤에도 `Kronuz/cpp-btree`, `frozenca/BTree`, `reum memory_bptree`가 서로 근접하게 경쟁했다.
- `sparse_rand_build_rand_get`와 `dense_rand_build_rand_get`는 데이터셋 크기를 키울수록 winner가 실제로 바뀌는 대표 시나리오였다.
- 기본 비교 구간의 끝이 `1,000,000`일 뿐 최대치는 아니며, 이번 실험은 `8,000,000`건까지 확장해 재측정했다.

정확한 수치는 아래 파일에서 보는 것이 가장 좋다.

- `results/latest_summary.md`
- `results/latest_detailed_report.md`
- `../../docs/reum-010-btree-library-benchmark-compare.html`

## 참고 메모

- 처음에는 현재 프로젝트에 있던 디스크형 `thirdparty/bplustree`도 후보에 넣어봤다.
- 하지만 큰 데이터셋에서 assertion으로 중단되어, 최종 비교 세트에서는 제외했다.
- 따라서 현재 결과는 모두 **in-memory** 구현 다섯 개 기준이다.
