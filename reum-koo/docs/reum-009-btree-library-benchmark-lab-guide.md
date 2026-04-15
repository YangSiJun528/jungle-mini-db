# reum-009 B-tree 라이브러리 벤치마크 실험 브랜치와 폴더 구조

## 이 문서의 역할

이 문서는

- 왜 새 브랜치를 만들었는지
- 왜 프로젝트를 라이브러리별로 통째로 복사하지 않았는지
- 비교 실험 폴더를 어떤 구조로 나눴는지
- 다섯 라이브러리를 어떤 기준으로 붙였는지

를 설명하는 **실험 구조 문서**다.

---

## 1. 왜 새 브랜치를 만들었나

이번 작업의 목표는 기존 미니 DB를 바로 바꾸는 것이 아니라,
**여러 B-tree/B+tree 구현을 비교 실험하는 별도 실험실**을 만드는 것이었다.

그래서 본 작업은 `btree-library-benchmark` 브랜치에서 진행했다.

이렇게 브랜치를 따로 나누는 이유는 단순하다.

- 기존 기능 브랜치와 실험 브랜치를 섞지 않기 위해
- 벤치마크용 외부 라이브러리와 결과 파일을 안전하게 다루기 위해
- 실험 구조가 실패해도 본 프로젝트 흐름을 더럽히지 않기 위해

즉, "제품 코드"와 "비교 실험 코드"를 분리한 셈이다.

---

## 2. 왜 라이브러리마다 전체 프로젝트를 복사하지 않았나

처음에는 이렇게 생각하기 쉽다.

> 라이브러리 A용 폴더 하나,  
> 라이브러리 B용 폴더 하나,  
> 각 폴더 안에 프로젝트 전체를 복사하면 되지 않을까?

가능은 하지만, 보통 금방 관리가 힘들어진다.

예를 들어:

- 같은 벤치마크 로직이 다섯 군데에 복사된다
- 버그를 고치면 다섯 군데를 같이 수정해야 한다
- 결과 형식이 조금씩 달라져 공정한 비교가 어려워진다
- README나 발표 자료에서 구조 설명이 길어진다

그래서 이번 실험은
**공통 실행기 + 라이브러리별 어댑터** 방식으로 설계했다.

---

## 3. 이번 실험 구조의 핵심 아이디어

핵심은 아주 단순하다.

> 시험 문제는 하나로 두고,  
> 각 라이브러리는 같은 문제를 푸는 엔진처럼 갈아 끼운다.

즉, 공통 벤치마크 실행기가

- 같은 키를 만들고
- 같은 순서로 삽입/조회하고
- 같은 방식으로 시간을 재고
- 같은 방식으로 정답을 검증한다

그리고 라이브러리별 어댑터는

- `create`
- `insert`
- `get`
- `destroy`

만 구현한다.

이 구조 덕분에 비교에서 바뀌는 것은
가능한 한 "라이브러리 자체"에 가깝게 유지된다.

---

## 4. 실제 폴더 구조

```text
reum-koo/
└─ experiments/
   └─ btree-library-benchmark/
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

---

## 5. 각 폴더는 무슨 역할을 하나

### `common/`

공통 벤치마크 로직이 들어 있다.

- 라이브러리 공통 인터페이스 정의
- 시나리오 실행
- 시간 측정
- 결과 출력

즉, "시험 감독관" 역할이다.

### `adapters/`

각 라이브러리를 공통 인터페이스에 맞게 감싼 코드다.

예를 들어 어떤 라이브러리는:

- `put/get`를 쓰고
- 어떤 라이브러리는 `insert/find`를 쓰고
- 어떤 라이브러리는 C API이고
- 어떤 라이브러리는 C++ 템플릿이다

이 차이를 어댑터가 흡수한다.

즉, "번역기" 역할이다.

### `third_party/`

외부에서 가져온 라이브러리 소스가 들어 있다.

즉, "비교 대상 원본" 보관소다.

### `results/`

벤치마크 실행 결과가 저장된다.

- `latest_results.json`: 원시 수치
- `latest_summary.md`: 읽기 쉬운 표
- `latest_detailed_report.md`: 실험 중간 이슈까지 포함한 긴 보고서
- `runtime/`: 실행 중 생기는 임시 파일

즉, "실험 결과 보관함"이다.

---

## 6. 이번에 실제로 붙인 다섯 라이브러리

| 이름 | 계열 | 언어/형태 | 메모 |
| --- | --- | --- | --- |
| `reum memory_bptree` | B+ tree | 프로젝트 내부 C 구현 | 현재 프로젝트의 기준선 |
| `habedi/bptree` | B+ tree | single-header C | 제네릭 ordered map 스타일 |
| `tidwall/btree.c` | B-tree | C | 단일 C 라이브러리 |
| `Kronuz/cpp-btree` | B-tree | header-only C++ | Google 계열 cpp-btree 계보 |
| `frozenca/BTree` | B-tree | header-only C++ | 현대 C++ 스타일 구현 |

---

## 7. 벤치마크 시나리오는 왜 이렇게 정했나

현재는 여섯 가지 데이터셋 크기와 여섯 시나리오를 조합해서 돈다.

### 데이터셋 크기

- `10,000`
- `100,000`
- `1,000,000`
- `2,000,000`
- `5,000,000`
- `8,000,000`

### `dense_seq_build_rand_get`

- dense 키를 순차 삽입
- 랜덤 조회

### `dense_rand_build_rand_get`

- dense 키를 랜덤 삽입
- 랜덤 조회

### `dense_rev_build_rand_get`

- dense 키를 역순 삽입
- 랜덤 조회

### `dense_seq_build_seq_get`

- dense 키를 순차 삽입
- 순차 조회

### `dense_rand_build_hot_get`

- dense 키를 랜덤 삽입
- 상위 1% hot subset 반복 조회

### `sparse_rand_build_rand_get`

- sparse 키를 랜덤 삽입
- 랜덤 조회

왜 이렇게 늘렸냐면,
트리 자료구조는 입력 순서뿐 아니라 키 분포와 접근 지역성에도 성능 영향을 받기 때문이다.

---

## 8. 이번 결과는 어디까지 공정한가

이번 실험은 꽤 공정하게 만들려 했지만,
완전히 똑같은 조건은 아니다.

예를 들어:

- B-tree와 B+tree는 구조가 다르다
- C와 C++ 구현은 메모리 관리 스타일이 다르다
- 노드 fanout, 내부 정책, 최적화 정도가 서로 다르다

그래도 비교 의미가 있는 이유는,
최소한 아래 조건은 같게 맞췄기 때문이다.

- 같은 키 개수
- 같은 입력 순서
- 같은 조회 순서
- 같은 정답 검증
- 같은 실행 환경

즉, "같은 시험 문제를 주고 누가 더 빨리 푸는가"에 가까운 비교다.

---

## 9. 최신 측정에서 보인 큰 흐름

- lookup 우승 횟수는 `Kronuz/cpp-btree`와 `reum memory_bptree`가 공동 1위였다.
- insert 우승 횟수는 `Kronuz/cpp-btree`가 가장 많았다.
- 작은 dense dataset에서는 `reum memory_bptree`가 강한 구간이 있었지만, `2,000,000`건 이상으로 올라가면 `Kronuz/cpp-btree`와 `habedi/bptree`가 더 자주 앞섰다.
- `dense_rand_build_hot_get` 같은 hot-spot lookup에서는 `frozenca/BTree`도 상당히 강했다.
- `sparse_rand_build_rand_get`는 키 분포 차이가 크게 드러나는 시나리오였고, 라이브러리별 민감도 차이를 관찰하기 좋았다.

정확한 수치는 아래 파일에 저장된다.

- `results/latest_results.json`
- `results/latest_summary.md`
- `results/latest_detailed_report.md`

---

## 10. 실험 중 제외한 구현도 있다

처음에는 현재 프로젝트에 포함된 디스크형 `thirdparty/bplustree`도 넣어봤다.

초기 메모에는 큰 데이터셋에서 assertion으로 중단된다고 적었지만,
재검증 결과 현재 환경에서는 그 assert를 재현하지 못했다.

대신 `1,000,000`건 sparse 시나리오에서
큰 value를 넣었을 때 lookup 값 손상이 먼저 관찰됐다.

즉 이 구현을 제외한 이유는
"몇 건 이상은 절대 못 넣는다"보다는
"현재 비교 규칙에서 결과를 끝까지 안정적으로 검증하기 어렵다"에 더 가깝다.

이 판단은 중요하다.

왜냐하면 벤치마크는
"억지로 다 넣는 것"보다
"끝까지 안정적으로 돌고 재현 가능한 비교 세트"를 만드는 쪽이 더 가치 있기 때문이다.

---

## 11. 실행 스크립트가 자동으로 정리하는 것

`run_btree_library_benchmarks.py`는 실행할 때마다

- `build/`
- `results/runtime/`

를 새로 만들어,
예전 실험의 object 파일이나 임시 산출물이 다음 결과에 섞이지 않게 한다.

이건 비교 실험에서 꽤 중요하다.

왜냐하면 이전에 제외한 라이브러리의 잔재가 남아 있으면
"지금 돌린 다섯 개 결과"와 "예전에 실패한 실험 흔적"이 섞여 보일 수 있기 때문이다.

---

## 12. 이 구조를 나중에 어떻게 확장할 수 있나

새 라이브러리를 추가하고 싶다면 보통 아래 순서면 된다.

1. `third_party/`에 소스를 넣는다
2. `adapters/`에 새 어댑터를 만든다
3. `library_registry.cpp`에 등록한다
4. 벤치마크를 다시 돌린다

즉, 전체 프로젝트를 복사할 필요 없이
"어댑터 한 장"만 추가하면 비교 대상을 늘릴 수 있다.

---

## 13. 한 줄 요약

이번 실험 구조의 핵심은 이 문장 하나로 정리된다.

> 라이브러리마다 프로젝트 전체를 복사하지 않고,  
> 공통 벤치마크 실행기 위에 라이브러리별 어댑터를 얹는 방식으로  
> 다섯 가지 구현을 같은 규칙으로 비교했다.
