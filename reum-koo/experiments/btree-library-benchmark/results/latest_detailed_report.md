# Detailed B-tree Library Benchmark Report

## 1. Goal

이번 실험의 목표는 다섯 가지 B-tree/B+tree 구현을 같은 입력 조건과 같은 정답 검증 규칙 아래에서 비교하고,
데이터셋 크기와 입력 패턴이 바뀔 때 어떤 라이브러리가 강한지 확인하는 것이다.

## 2. Execution Context

- branch: `btree-library-benchmark`
- worktree: `/private/tmp/jungle-mini-db-btree-benchmark`
- benchmark root: `/private/tmp/jungle-mini-db-btree-benchmark/reum-koo/experiments/btree-library-benchmark`
- record counts: `10000, 100000, 1000000, 2000000, 5000000, 8000000`
- seed: `20260415`
- compared libraries: `Kronuz/cpp-btree, frozenca/BTree, habedi/bptree, reum memory_bptree, tidwall/btree.c`

## 3. Scenario Matrix

| Scenario ID | Meaning |
| --- | --- |
| `dense_seq_build_rand_get` | Dense integer keys. Insert in sorted order, then lookup in random order. |
| `dense_rand_build_rand_get` | Dense integer keys. Insert in random order, then lookup in random order. |
| `dense_rev_build_rand_get` | Dense integer keys. Insert in reverse-sorted order, then lookup in random order. |
| `dense_seq_build_seq_get` | Dense integer keys. Insert in sorted order, then lookup in sorted order. |
| `dense_rand_build_hot_get` | Dense integer keys. Insert in random order, then repeatedly lookup a hot 1% subset. |
| `sparse_rand_build_rand_get` | Sparse integer keys with gaps. Insert in random order, then lookup in random order. |

## 4. What Happened During The Work

1. 작업 트리에 로그 파일 변경이 남아 있어서, 원래 저장소를 건드리지 않기 위해 별도 worktree와 `btree-library-benchmark` 브랜치에서 실험을 진행했다.
2. 초기 벤치마크 러너는 단일 record count와 두 가지 시나리오만 지원했는데, 비교 해상도를 높이기 위해 세 가지 데이터셋 크기와 여섯 가지 시나리오를 도는 구조로 확장했다.
3. 처음 후보에는 프로젝트 내부의 디스크형 `thirdparty/bplustree`도 넣었지만, 100,000건 이상에서 assertion failure로 중단되어 최종 비교군에서 제외했다.
4. 비교군을 다섯 개로 유지하면서도 끝까지 안정적으로 돌리는 것이 중요하다고 판단해, 제외한 후보 대신 `frozenca/BTree`를 넣어 최종 세트를 완성했다.
5. 제외한 라이브러리의 산출물이 `build/`와 `results/runtime/`에 남아 결과 해석을 흐릴 수 있다는 점을 확인했고, 실행 스크립트가 매번 두 폴더를 재생성하도록 수정했다.
6. `cmake`가 설치되어 있지 않아, Apple clang의 `cc`와 `c++`를 직접 호출하는 방식으로 빌드 파이프라인을 구성했다.

## 5. High-Level Findings

- 가장 빠른 단일 lookup 성능은 `reum memory_bptree`가 `10,000`건의 `dense random insert + hot-spot get`에서 기록한 `44876656.51 ops/s`였다.
- 가장 빠른 단일 insert 성능은 `Kronuz/cpp-btree`가 `10,000`건의 `dense reverse insert + random get`에서 기록한 `60316541.21 ops/s`였다.
- lookup 1위 횟수는 `Kronuz/cpp-btree`가 `13`회로 가장 많았다.
- insert 1위 횟수는 `Kronuz/cpp-btree`가 `17`회로 가장 많았다.
- `habedi/bptree`는 random insert에서도 lookup 성능이 안정적이어서 B+ tree 계열 비교군 중 가장 꾸준한 편이었다.
- `reum memory_bptree`는 작은 dense dataset에서는 강했지만, `100,000`건 sparse random 시나리오에서 lookup이 크게 떨어져 데이터 분포 민감도가 눈에 띄었다.
- `sparse_rand_build_rand_get`와 `dense_rand_build_hot_get`를 같이 보니, 키 분포와 접근 지역성이 순위에 실제 영향을 준다는 점이 드러났다.

## 6. Winner Count

| Library | Lookup wins | Insert wins |
| --- | --- | --- |
| `Kronuz/cpp-btree` | 13 | 17 |
| `frozenca/BTree` | 3 | 6 |
| `habedi/bptree` | 10 | 1 |
| `reum memory_bptree` | 10 | 12 |
| `tidwall/btree.c` | 0 | 0 |

## 7. Detailed Tables

### 10,000 records

| Library | Lookup wins at this size |
| --- | --- |
| `Kronuz/cpp-btree` | 2 |
| `frozenca/BTree` | 0 |
| `habedi/bptree` | 0 |
| `reum memory_bptree` | 4 |
| `tidwall/btree.c` | 0 |

#### dense sequential insert + random get

Dense integer keys. Insert in sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 0.000448 | 0.000413 | 22331796.91 | 24203288.26 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.000344 | 0.000417 | 29031115.55 | 24004820.17 |
| 3 | `frozenca/BTree` | B-tree | 0.000592 | 0.000436 | 16906170.75 | 22924843.19 |
| 4 | `habedi/bptree` | B+ tree | 0.000483 | 0.000521 | 20695021.61 | 19201523.83 |
| 5 | `tidwall/btree.c` | B-tree | 0.000513 | 0.000647 | 19477382.86 | 15444993.43 |

#### dense random insert + random get

Dense integer keys. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.000737 | 0.000429 | 13561620.61 | 23287387.32 |
| 2 | `reum memory_bptree` | B+ tree | 0.000612 | 0.000434 | 16343207.35 | 23039298.13 |
| 3 | `frozenca/BTree` | B-tree | 0.000701 | 0.000479 | 14267024.48 | 20865936.36 |
| 4 | `habedi/bptree` | B+ tree | 0.000931 | 0.000617 | 10741138.56 | 16214025.13 |
| 5 | `tidwall/btree.c` | B-tree | 0.000949 | 0.000686 | 10537863.07 | 14574603.75 |

#### dense reverse insert + random get

Dense integer keys. Insert in reverse-sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.000166 | 0.000425 | 60316541.21 | 23515579.07 |
| 2 | `frozenca/BTree` | B-tree | 0.000422 | 0.000436 | 23677998.17 | 22924843.19 |
| 3 | `reum memory_bptree` | B+ tree | 0.000267 | 0.000472 | 37499953.13 | 21195781.19 |
| 4 | `habedi/bptree` | B+ tree | 0.000867 | 0.000502 | 11535142.97 | 19938509.64 |
| 5 | `tidwall/btree.c` | B-tree | 0.001009 | 0.000685 | 9909987.58 | 14602100.07 |

#### dense sequential insert + sequential get

Dense integer keys. Insert in sorted order, then lookup in sorted order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 0.000432 | 0.000258 | 23152596.45 | 38740920.10 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.000331 | 0.000277 | 30234315.95 | 36079331.23 |
| 3 | `frozenca/BTree` | B-tree | 0.000593 | 0.000325 | 16874077.20 | 30785049.55 |
| 4 | `tidwall/btree.c` | B-tree | 0.000484 | 0.000423 | 20652239.01 | 23663934.27 |
| 5 | `habedi/bptree` | B+ tree | 0.000480 | 0.000503 | 20842408.47 | 19892263.50 |

#### dense random insert + hot-spot get

Dense integer keys. Insert in random order, then repeatedly lookup a hot 1% subset.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 0.000619 | 0.000223 | 16151827.18 | 44876656.51 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.000734 | 0.000235 | 13622419.23 | 42583452.92 |
| 3 | `frozenca/BTree` | B-tree | 0.000696 | 0.000248 | 14357501.79 | 40383644.62 |
| 4 | `tidwall/btree.c` | B-tree | 0.000960 | 0.000602 | 10416666.67 | 16605558.21 |
| 5 | `habedi/bptree` | B+ tree | 0.000960 | 0.000603 | 10421638.66 | 16574594.79 |

#### sparse random insert + random get

Sparse integer keys with gaps. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 0.000607 | 0.000399 | 16475604.57 | 25054807.39 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.000714 | 0.000438 | 13998250.22 | 22820161.16 |
| 3 | `frozenca/BTree` | B-tree | 0.000692 | 0.000455 | 14453477.87 | 21971985.72 |
| 4 | `habedi/bptree` | B+ tree | 0.000997 | 0.000659 | 10033441.46 | 15177385.70 |
| 5 | `tidwall/btree.c` | B-tree | 0.001109 | 0.000682 | 9014425.79 | 14665444.55 |

### 100,000 records

| Library | Lookup wins at this size |
| --- | --- |
| `Kronuz/cpp-btree` | 3 |
| `frozenca/BTree` | 2 |
| `habedi/bptree` | 0 |
| `reum memory_bptree` | 1 |
| `tidwall/btree.c` | 0 |

#### dense sequential insert + random get

Dense integer keys. Insert in sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.003851 | 0.005710 | 25964193.30 | 17512880.29 |
| 2 | `frozenca/BTree` | B-tree | 0.007196 | 0.005870 | 13896850.63 | 17035290.48 |
| 3 | `reum memory_bptree` | B+ tree | 0.005071 | 0.008070 | 19719004.19 | 12391189.86 |
| 4 | `habedi/bptree` | B+ tree | 0.006796 | 0.008427 | 14713996.69 | 11866619.20 |
| 5 | `tidwall/btree.c` | B-tree | 0.015079 | 0.012589 | 6631721.03 | 7943652.81 |

#### dense random insert + random get

Dense integer keys. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.009362 | 0.005833 | 10681335.70 | 17143960.23 |
| 2 | `frozenca/BTree` | B-tree | 0.008962 | 0.006024 | 11158846.18 | 16601067.55 |
| 3 | `reum memory_bptree` | B+ tree | 0.007930 | 0.006806 | 12610009.72 | 14692020.00 |
| 4 | `habedi/bptree` | B+ tree | 0.012270 | 0.009515 | 8149793.20 | 10509445.36 |
| 5 | `tidwall/btree.c` | B-tree | 0.013214 | 0.010089 | 7567731.19 | 9911375.45 |

#### dense reverse insert + random get

Dense integer keys. Insert in reverse-sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `frozenca/BTree` | B-tree | 0.004852 | 0.005616 | 20609526.75 | 17805078.90 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.001752 | 0.005799 | 57092550.45 | 17244105.66 |
| 3 | `reum memory_bptree` | B+ tree | 0.002835 | 0.007344 | 35269225.87 | 13617177.03 |
| 4 | `habedi/bptree` | B+ tree | 0.011728 | 0.007880 | 8526299.84 | 12689751.44 |
| 5 | `tidwall/btree.c` | B-tree | 0.012250 | 0.009406 | 8162987.43 | 10631559.27 |

#### dense sequential insert + sequential get

Dense integer keys. Insert in sorted order, then lookup in sorted order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 0.004754 | 0.002723 | 21033811.85 | 36719710.74 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.003670 | 0.003027 | 27250428.99 | 33032822.73 |
| 3 | `frozenca/BTree` | B-tree | 0.007150 | 0.003236 | 13985116.20 | 30905127.75 |
| 4 | `habedi/bptree` | B+ tree | 0.006517 | 0.006414 | 15345270.11 | 15591806.51 |
| 5 | `tidwall/btree.c` | B-tree | 0.006611 | 0.006437 | 15127352.64 | 15534282.22 |

#### dense random insert + hot-spot get

Dense integer keys. Insert in random order, then repeatedly lookup a hot 1% subset.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `frozenca/BTree` | B-tree | 0.008901 | 0.003080 | 11235113.05 | 32463579.92 |
| 2 | `reum memory_bptree` | B+ tree | 0.007755 | 0.003162 | 12894145.00 | 31626803.72 |
| 3 | `Kronuz/cpp-btree` | B-tree | 0.009148 | 0.003169 | 10931799.24 | 31560257.05 |
| 4 | `tidwall/btree.c` | B-tree | 0.013397 | 0.008466 | 7464496.99 | 11812010.90 |
| 5 | `habedi/bptree` | B+ tree | 0.012784 | 0.008591 | 7822456.52 | 11640653.49 |

#### sparse random insert + random get

Sparse integer keys with gaps. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.009203 | 0.005797 | 10865922.77 | 17250179.88 |
| 2 | `frozenca/BTree` | B-tree | 0.009067 | 0.005828 | 11029564.64 | 17157808.95 |
| 3 | `reum memory_bptree` | B+ tree | 0.008358 | 0.006915 | 11964226.96 | 14460968.83 |
| 4 | `tidwall/btree.c` | B-tree | 0.014064 | 0.010070 | 7110268.24 | 9930321.91 |
| 5 | `habedi/bptree` | B+ tree | 0.012249 | 0.015210 | 8163987.07 | 6574657.84 |

### 1,000,000 records

| Library | Lookup wins at this size |
| --- | --- |
| `Kronuz/cpp-btree` | 5 |
| `frozenca/BTree` | 0 |
| `habedi/bptree` | 1 |
| `reum memory_bptree` | 0 |
| `tidwall/btree.c` | 0 |

#### dense sequential insert + random get

Dense integer keys. Insert in sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.042517 | 0.135712 | 23519934.61 | 7368520.23 |
| 2 | `frozenca/BTree` | B-tree | 0.086797 | 0.167260 | 11521168.71 | 5978708.30 |
| 3 | `habedi/bptree` | B+ tree | 0.084468 | 0.184437 | 11838773.57 | 5421898.23 |
| 4 | `reum memory_bptree` | B+ tree | 0.058021 | 0.237108 | 17235077.22 | 4217495.54 |
| 5 | `tidwall/btree.c` | B-tree | 0.086070 | 0.267027 | 11618388.27 | 3744937.90 |

#### dense random insert + random get

Dense integer keys. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 0.201204 | 0.160445 | 4970082.17 | 6232663.77 |
| 2 | `frozenca/BTree` | B-tree | 0.154958 | 0.162517 | 6453368.51 | 6153211.90 |
| 3 | `Kronuz/cpp-btree` | B-tree | 0.174424 | 0.169060 | 5733162.82 | 5915052.46 |
| 4 | `reum memory_bptree` | B+ tree | 0.158020 | 0.181076 | 6328297.85 | 5522543.02 |
| 5 | `tidwall/btree.c` | B-tree | 0.240111 | 0.232868 | 4164749.15 | 4294276.77 |

#### dense reverse insert + random get

Dense integer keys. Insert in reverse-sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.019708 | 0.138551 | 50740602.22 | 7217565.39 |
| 2 | `habedi/bptree` | B+ tree | 0.138471 | 0.158048 | 7221726.55 | 6327195.10 |
| 3 | `frozenca/BTree` | B-tree | 0.051326 | 0.196037 | 19483207.91 | 5101078.92 |
| 4 | `reum memory_bptree` | B+ tree | 0.031474 | 0.216047 | 31772382.65 | 4628622.48 |
| 5 | `tidwall/btree.c` | B-tree | 0.146467 | 0.272304 | 6827476.50 | 3672370.67 |

#### dense sequential insert + sequential get

Dense integer keys. Insert in sorted order, then lookup in sorted order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.041337 | 0.034961 | 24191329.22 | 28603266.46 |
| 2 | `reum memory_bptree` | B+ tree | 0.054159 | 0.039562 | 18464151.85 | 25276993.51 |
| 3 | `frozenca/BTree` | B-tree | 0.086331 | 0.043967 | 11583358.19 | 22744136.99 |
| 4 | `tidwall/btree.c` | B-tree | 0.085728 | 0.083011 | 11664743.69 | 12046662.70 |
| 5 | `habedi/bptree` | B+ tree | 0.083380 | 0.093504 | 11993295.70 | 10694724.95 |

#### dense random insert + hot-spot get

Dense integer keys. Insert in random order, then repeatedly lookup a hot 1% subset.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.155916 | 0.046458 | 6413703.08 | 21524683.29 |
| 2 | `frozenca/BTree` | B-tree | 0.145119 | 0.047173 | 6890910.30 | 21198491.93 |
| 3 | `reum memory_bptree` | B+ tree | 0.171505 | 0.048987 | 5830726.73 | 20413648.70 |
| 4 | `habedi/bptree` | B+ tree | 0.221788 | 0.103171 | 4508817.84 | 9692685.37 |
| 5 | `tidwall/btree.c` | B-tree | 0.223152 | 0.112278 | 4481258.80 | 8906474.23 |

#### sparse random insert + random get

Sparse integer keys with gaps. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.152468 | 0.155856 | 6558740.75 | 6416185.91 |
| 2 | `habedi/bptree` | B+ tree | 0.194745 | 0.164447 | 5134924.43 | 6080988.13 |
| 3 | `frozenca/BTree` | B-tree | 0.147452 | 0.164808 | 6781873.75 | 6067671.22 |
| 4 | `reum memory_bptree` | B+ tree | 0.170462 | 0.181704 | 5866402.92 | 5503448.60 |
| 5 | `tidwall/btree.c` | B-tree | 0.260549 | 0.230896 | 3838052.74 | 4330951.85 |

### 2,000,000 records

| Library | Lookup wins at this size |
| --- | --- |
| `Kronuz/cpp-btree` | 2 |
| `frozenca/BTree` | 0 |
| `habedi/bptree` | 2 |
| `reum memory_bptree` | 2 |
| `tidwall/btree.c` | 0 |

#### dense sequential insert + random get

Dense integer keys. Insert in sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 0.206778 | 0.430929 | 9672212.77 | 4641140.26 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.086716 | 0.438221 | 23063772.38 | 4563909.42 |
| 3 | `frozenca/BTree` | B-tree | 0.202702 | 0.503308 | 9866706.96 | 3973706.32 |
| 4 | `reum memory_bptree` | B+ tree | 0.129021 | 0.535654 | 15501377.48 | 3733754.96 |
| 5 | `tidwall/btree.c` | B-tree | 0.188487 | 0.810371 | 10610790.25 | 2468006.03 |

#### dense random insert + random get

Dense integer keys. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 0.475768 | 0.424584 | 4203729.18 | 4710495.40 |
| 2 | `frozenca/BTree` | B-tree | 0.426123 | 0.453792 | 4693482.35 | 4407303.12 |
| 3 | `reum memory_bptree` | B+ tree | 0.436875 | 0.495084 | 4577971.58 | 4039721.91 |
| 4 | `Kronuz/cpp-btree` | B-tree | 0.484011 | 0.518751 | 4132133.58 | 3855417.35 |
| 5 | `tidwall/btree.c` | B-tree | 0.800610 | 0.637291 | 2498095.07 | 3138285.00 |

#### dense reverse insert + random get

Dense integer keys. Insert in reverse-sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.041724 | 0.402989 | 47934042.76 | 4962912.06 |
| 2 | `habedi/bptree` | B+ tree | 0.293801 | 0.462682 | 6807333.61 | 4322626.82 |
| 3 | `frozenca/BTree` | B-tree | 0.145559 | 0.472062 | 13740176.10 | 4236733.86 |
| 4 | `reum memory_bptree` | B+ tree | 0.067130 | 0.589174 | 29792828.12 | 3394585.09 |
| 5 | `tidwall/btree.c` | B-tree | 0.308741 | 0.729225 | 6477911.99 | 2742639.30 |

#### dense sequential insert + sequential get

Dense integer keys. Insert in sorted order, then lookup in sorted order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 0.112171 | 0.058696 | 17829840.91 | 34073872.15 |
| 2 | `frozenca/BTree` | B-tree | 0.177867 | 0.086835 | 11244383.04 | 23032286.95 |
| 3 | `Kronuz/cpp-btree` | B-tree | 0.122601 | 0.105046 | 16313075.06 | 19039217.49 |
| 4 | `tidwall/btree.c` | B-tree | 0.181224 | 0.175716 | 11036037.97 | 11382008.15 |
| 5 | `habedi/bptree` | B+ tree | 0.178613 | 0.176285 | 11197414.12 | 11345238.00 |

#### dense random insert + hot-spot get

Dense integer keys. Insert in random order, then repeatedly lookup a hot 1% subset.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 0.425796 | 0.102474 | 4697080.39 | 19517122.01 |
| 2 | `frozenca/BTree` | B-tree | 0.459828 | 0.106469 | 4349454.38 | 18784854.71 |
| 3 | `Kronuz/cpp-btree` | B-tree | 0.521238 | 0.120609 | 3837017.25 | 16582458.87 |
| 4 | `habedi/bptree` | B+ tree | 0.634201 | 0.218428 | 3153572.48 | 9156338.75 |
| 5 | `tidwall/btree.c` | B-tree | 0.631122 | 0.299507 | 3168957.32 | 6677637.47 |

#### sparse random insert + random get

Sparse integer keys with gaps. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.508241 | 0.434025 | 3935144.23 | 4608029.94 |
| 2 | `habedi/bptree` | B+ tree | 0.491625 | 0.478403 | 4068139.30 | 4180577.25 |
| 3 | `reum memory_bptree` | B+ tree | 0.429841 | 0.499293 | 4652882.38 | 4005667.68 |
| 4 | `frozenca/BTree` | B-tree | 0.452486 | 0.504387 | 4420023.40 | 3965211.22 |
| 5 | `tidwall/btree.c` | B-tree | 0.836293 | 0.587638 | 2391506.92 | 3403455.87 |

### 5,000,000 records

| Library | Lookup wins at this size |
| --- | --- |
| `Kronuz/cpp-btree` | 0 |
| `frozenca/BTree` | 0 |
| `habedi/bptree` | 4 |
| `reum memory_bptree` | 2 |
| `tidwall/btree.c` | 0 |

#### dense sequential insert + random get

Dense integer keys. Insert in sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 0.533926 | 1.476002 | 9364599.44 | 3387528.42 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.273549 | 1.526870 | 18278274.90 | 3274672.49 |
| 3 | `frozenca/BTree` | B-tree | 0.499292 | 1.609261 | 10014176.73 | 3107015.88 |
| 4 | `reum memory_bptree` | B+ tree | 0.303871 | 1.994387 | 16454346.15 | 2507035.58 |
| 5 | `tidwall/btree.c` | B-tree | 0.553891 | 2.012808 | 9027052.26 | 2484091.52 |

#### dense random insert + random get

Dense integer keys. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 1.700004 | 1.366610 | 2941169.33 | 3658688.06 |
| 2 | `frozenca/BTree` | B-tree | 1.514543 | 1.620670 | 3301325.61 | 3085143.96 |
| 3 | `Kronuz/cpp-btree` | B-tree | 1.736301 | 1.621112 | 2879684.62 | 3084303.10 |
| 4 | `reum memory_bptree` | B+ tree | 1.522110 | 1.775728 | 3284913.34 | 2815746.23 |
| 5 | `tidwall/btree.c` | B-tree | 2.140170 | 1.840976 | 2336263.19 | 2715950.55 |

#### dense reverse insert + random get

Dense integer keys. Insert in reverse-sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 0.831239 | 1.457936 | 6015116.59 | 3429505.53 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.108567 | 1.510537 | 46054315.83 | 3310081.12 |
| 3 | `frozenca/BTree` | B-tree | 0.271544 | 1.661704 | 18413230.64 | 3008959.18 |
| 4 | `tidwall/btree.c` | B-tree | 0.893501 | 1.998256 | 5595964.12 | 2502181.96 |
| 5 | `reum memory_bptree` | B+ tree | 0.168089 | 2.087247 | 29746227.61 | 2395499.77 |

#### dense sequential insert + sequential get

Dense integer keys. Insert in sorted order, then lookup in sorted order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 0.301465 | 0.188200 | 16585659.54 | 26567463.76 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.226448 | 0.235059 | 22080079.60 | 21271266.61 |
| 3 | `frozenca/BTree` | B-tree | 0.636440 | 0.288802 | 7856201.14 | 17312909.51 |
| 4 | `habedi/bptree` | B+ tree | 0.504565 | 0.519608 | 9909519.49 | 9622644.01 |
| 5 | `tidwall/btree.c` | B-tree | 0.529496 | 0.526270 | 9442937.51 | 9500819.04 |

#### dense random insert + hot-spot get

Dense integer keys. Insert in random order, then repeatedly lookup a hot 1% subset.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 1.559221 | 0.315983 | 3206729.00 | 15823638.18 |
| 2 | `Kronuz/cpp-btree` | B-tree | 1.730316 | 0.325338 | 2889645.59 | 15368624.12 |
| 3 | `frozenca/BTree` | B-tree | 1.716482 | 0.339793 | 2912934.64 | 14714844.73 |
| 4 | `habedi/bptree` | B+ tree | 1.692557 | 0.677482 | 2954110.12 | 7380265.80 |
| 5 | `tidwall/btree.c` | B-tree | 2.146380 | 0.698863 | 2329503.63 | 7154481.05 |

#### sparse random insert + random get

Sparse integer keys with gaps. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 1.733304 | 1.371523 | 2884663.92 | 3645581.88 |
| 2 | `frozenca/BTree` | B-tree | 1.719406 | 1.572379 | 2907981.58 | 3179894.92 |
| 3 | `reum memory_bptree` | B+ tree | 1.517224 | 1.614050 | 3295493.38 | 3097797.15 |
| 4 | `Kronuz/cpp-btree` | B-tree | 1.746875 | 1.678618 | 2862253.96 | 2978640.32 |
| 5 | `tidwall/btree.c` | B-tree | 2.141719 | 2.005307 | 2334573.71 | 2493383.60 |

### 8,000,000 records

| Library | Lookup wins at this size |
| --- | --- |
| `Kronuz/cpp-btree` | 1 |
| `frozenca/BTree` | 1 |
| `habedi/bptree` | 3 |
| `reum memory_bptree` | 1 |
| `tidwall/btree.c` | 0 |

#### dense sequential insert + random get

Dense integer keys. Insert in sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 0.971788 | 2.552000 | 8232244.30 | 3134796.55 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.433348 | 2.668430 | 18460926.07 | 2998017.33 |
| 3 | `frozenca/BTree` | B-tree | 0.811690 | 2.898468 | 9855983.56 | 2760078.49 |
| 4 | `tidwall/btree.c` | B-tree | 0.885110 | 3.435312 | 9038421.62 | 2328754.69 |
| 5 | `reum memory_bptree` | B+ tree | 0.510192 | 3.694606 | 15680382.84 | 2165318.92 |

#### dense random insert + random get

Dense integer keys. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 3.067100 | 2.448606 | 2608327.44 | 3267164.63 |
| 2 | `frozenca/BTree` | B-tree | 2.977627 | 2.766829 | 2686703.54 | 2891396.57 |
| 3 | `Kronuz/cpp-btree` | B-tree | 3.186027 | 2.979643 | 2510964.35 | 2684884.99 |
| 4 | `tidwall/btree.c` | B-tree | 3.727303 | 3.034973 | 2146324.06 | 2635937.57 |
| 5 | `reum memory_bptree` | B+ tree | 3.525907 | 3.230840 | 2268919.55 | 2476136.33 |

#### dense reverse insert + random get

Dense integer keys. Insert in reverse-sorted order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | 0.192667 | 2.760333 | 41522410.46 | 2898200.70 |
| 2 | `frozenca/BTree` | B-tree | 0.499552 | 2.885897 | 16014348.86 | 2772101.91 |
| 3 | `habedi/bptree` | B+ tree | 1.643402 | 2.974451 | 4867952.11 | 2689572.37 |
| 4 | `tidwall/btree.c` | B-tree | 1.393978 | 3.407157 | 5738969.60 | 2347998.50 |
| 5 | `reum memory_bptree` | B+ tree | 0.334366 | 3.857263 | 23925871.69 | 2074009.54 |

#### dense sequential insert + sequential get

Dense integer keys. Insert in sorted order, then lookup in sorted order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | 0.527151 | 0.273283 | 15175922.14 | 29273634.26 |
| 2 | `Kronuz/cpp-btree` | B-tree | 0.419654 | 0.333848 | 19063304.65 | 23962980.17 |
| 3 | `frozenca/BTree` | B-tree | 0.826237 | 0.532315 | 9682456.28 | 15028707.19 |
| 4 | `tidwall/btree.c` | B-tree | 0.853563 | 0.869689 | 9372476.11 | 9198689.24 |
| 5 | `habedi/bptree` | B+ tree | 0.874591 | 0.904415 | 9147127.97 | 8845493.15 |

#### dense random insert + hot-spot get

Dense integer keys. Insert in random order, then repeatedly lookup a hot 1% subset.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `frozenca/BTree` | B-tree | 3.480105 | 0.549274 | 2298781.02 | 14564692.07 |
| 2 | `Kronuz/cpp-btree` | B-tree | 3.772035 | 0.602270 | 2120871.05 | 13283072.60 |
| 3 | `reum memory_bptree` | B+ tree | 3.287220 | 0.691015 | 2433667.26 | 11577176.90 |
| 4 | `habedi/bptree` | B+ tree | 2.903827 | 1.082380 | 2754984.74 | 7391122.41 |
| 5 | `tidwall/btree.c` | B-tree | 4.039720 | 1.351167 | 1980335.37 | 5920808.63 |

#### sparse random insert + random get

Sparse integer keys with gaps. Insert in random order, then lookup in random order.

| Rank | Library | Family | Insert sec | Lookup sec | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | 2.983536 | 2.039853 | 2681382.39 | 3921851.15 |
| 2 | `Kronuz/cpp-btree` | B-tree | 3.071819 | 2.965239 | 2604320.54 | 2697927.78 |
| 3 | `tidwall/btree.c` | B-tree | 3.816761 | 3.192627 | 2096018.18 | 2505773.16 |
| 4 | `frozenca/BTree` | B-tree | 4.255231 | 3.282215 | 1880038.76 | 2437378.11 |
| 5 | `reum memory_bptree` | B+ tree | 2.973380 | 3.548017 | 2690540.69 | 2254780.31 |

## 8. Scale Notes

- `1,000,000`건은 이번 실험의 기본 비교 기준 중 하나일 뿐, 이 벤치마크의 절대 최대값은 아니다.
- 현재 러너는 `--records` 또는 `--record-counts` 인자로 더 큰 값도 받을 수 있다.
- 다만 현재 구현은 key 타입으로 32-bit signed `int`를 쓰고, sparse 시나리오는 `key = index * 257 + 11` 공식을 쓰기 때문에, sparse 시나리오 기준 안전 상한은 대략 `8,355,968`건 정도다.
- 실제로도 데이터셋 크기가 바뀌면 lookup 1위가 바뀌는 시나리오가 있었고, 그래서 결과를 한 구간만 보고 일반화하면 위험하다.

### Lookup Winner Timeline

| Scenario | 10,000 | 100,000 | 1,000,000 | 2,000,000 | 5,000,000 | 8,000,000 |
| --- | --- | --- | --- | --- | --- | --- |
| `dense_seq_build_rand_get` | `reum memory_bptree` | `Kronuz/cpp-btree` | `Kronuz/cpp-btree` | `habedi/bptree` | `habedi/bptree` | `habedi/bptree` |
| dense sequential insert + random get |   |   |   |   |   |   |
| `dense_rand_build_rand_get` | `Kronuz/cpp-btree` | `Kronuz/cpp-btree` | `habedi/bptree` | `habedi/bptree` | `habedi/bptree` | `habedi/bptree` |
| dense random insert + random get |   |   |   |   |   |   |
| `dense_rev_build_rand_get` | `Kronuz/cpp-btree` | `frozenca/BTree` | `Kronuz/cpp-btree` | `Kronuz/cpp-btree` | `habedi/bptree` | `Kronuz/cpp-btree` |
| dense reverse insert + random get |   |   |   |   |   |   |
| `dense_seq_build_seq_get` | `reum memory_bptree` | `reum memory_bptree` | `Kronuz/cpp-btree` | `reum memory_bptree` | `reum memory_bptree` | `reum memory_bptree` |
| dense sequential insert + sequential get |   |   |   |   |   |   |
| `dense_rand_build_hot_get` | `reum memory_bptree` | `frozenca/BTree` | `Kronuz/cpp-btree` | `reum memory_bptree` | `reum memory_bptree` | `frozenca/BTree` |
| dense random insert + hot-spot get |   |   |   |   |   |   |
| `sparse_rand_build_rand_get` | `reum memory_bptree` | `Kronuz/cpp-btree` | `Kronuz/cpp-btree` | `Kronuz/cpp-btree` | `habedi/bptree` | `habedi/bptree` |
| sparse random insert + random get |   |   |   |   |   |   |

## 9. Limits And Follow-Ups

- 이번 실험은 point lookup과 unique-key insert만 비교했다. range scan, delete, duplicate key policy는 아직 범위 밖이다.
- 라이브러리 내부 fanout, allocator, node layout은 서로 다르기 때문에 결과를 절대적인 우열로 보기보다는 현재 조건에서의 throughput 비교로 읽는 것이 맞다.
- 다음 확장 후보는 delete benchmark, mixed read/write workload, range query, memory usage 측정이다.
