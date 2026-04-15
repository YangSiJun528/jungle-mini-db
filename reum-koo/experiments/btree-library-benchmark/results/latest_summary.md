# B-tree Library Benchmark Summary

- record counts: `10000, 100000, 1000000, 2000000, 5000000, 8000000`
- seed: `20260415`
- libraries compared: `5`
- scenarios per dataset: `6`

## Overall Winner Count

| Library | Lookup wins | Insert wins |
| --- | --- | --- |
| `Kronuz/cpp-btree` | 13 | 17 |
| `frozenca/BTree` | 3 | 6 |
| `habedi/bptree` | 10 | 1 |
| `reum memory_bptree` | 10 | 12 |
| `tidwall/btree.c` | 0 | 0 |

## Ranked Results

### 10,000 records

#### dense sequential insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 22331796.91 | 24203288.26 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 29031115.55 | 24004820.17 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 16906170.75 | 22924843.19 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 20695021.61 | 19201523.83 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 19477382.86 | 15444993.43 |

#### dense random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 13561620.61 | 23287387.32 |
| 2 | `reum memory_bptree` | B+ tree | in-memory | 16343207.35 | 23039298.13 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 14267024.48 | 20865936.36 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 10741138.56 | 16214025.13 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 10537863.07 | 14574603.75 |

#### dense reverse insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 60316541.21 | 23515579.07 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 23677998.17 | 22924843.19 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 37499953.13 | 21195781.19 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 11535142.97 | 19938509.64 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 9909987.58 | 14602100.07 |

#### dense sequential insert + sequential get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 23152596.45 | 38740920.10 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 30234315.95 | 36079331.23 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 16874077.20 | 30785049.55 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 20652239.01 | 23663934.27 |
| 5 | `habedi/bptree` | B+ tree | in-memory | 20842408.47 | 19892263.50 |

#### dense random insert + hot-spot get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 16151827.18 | 44876656.51 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 13622419.23 | 42583452.92 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 14357501.79 | 40383644.62 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 10416666.67 | 16605558.21 |
| 5 | `habedi/bptree` | B+ tree | in-memory | 10421638.66 | 16574594.79 |

#### sparse random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 16475604.57 | 25054807.39 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 13998250.22 | 22820161.16 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 14453477.87 | 21971985.72 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 10033441.46 | 15177385.70 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 9014425.79 | 14665444.55 |

### 100,000 records

#### dense sequential insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 25964193.30 | 17512880.29 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 13896850.63 | 17035290.48 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 19719004.19 | 12391189.86 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 14713996.69 | 11866619.20 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 6631721.03 | 7943652.81 |

#### dense random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 10681335.70 | 17143960.23 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 11158846.18 | 16601067.55 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 12610009.72 | 14692020.00 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 8149793.20 | 10509445.36 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 7567731.19 | 9911375.45 |

#### dense reverse insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `frozenca/BTree` | B-tree | in-memory | 20609526.75 | 17805078.90 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 57092550.45 | 17244105.66 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 35269225.87 | 13617177.03 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 8526299.84 | 12689751.44 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 8162987.43 | 10631559.27 |

#### dense sequential insert + sequential get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 21033811.85 | 36719710.74 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 27250428.99 | 33032822.73 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 13985116.20 | 30905127.75 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 15345270.11 | 15591806.51 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 15127352.64 | 15534282.22 |

#### dense random insert + hot-spot get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `frozenca/BTree` | B-tree | in-memory | 11235113.05 | 32463579.92 |
| 2 | `reum memory_bptree` | B+ tree | in-memory | 12894145.00 | 31626803.72 |
| 3 | `Kronuz/cpp-btree` | B-tree | in-memory | 10931799.24 | 31560257.05 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 7464496.99 | 11812010.90 |
| 5 | `habedi/bptree` | B+ tree | in-memory | 7822456.52 | 11640653.49 |

#### sparse random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 10865922.77 | 17250179.88 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 11029564.64 | 17157808.95 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 11964226.96 | 14460968.83 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 7110268.24 | 9930321.91 |
| 5 | `habedi/bptree` | B+ tree | in-memory | 8163987.07 | 6574657.84 |

### 1,000,000 records

#### dense sequential insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 23519934.61 | 7368520.23 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 11521168.71 | 5978708.30 |
| 3 | `habedi/bptree` | B+ tree | in-memory | 11838773.57 | 5421898.23 |
| 4 | `reum memory_bptree` | B+ tree | in-memory | 17235077.22 | 4217495.54 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 11618388.27 | 3744937.90 |

#### dense random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 4970082.17 | 6232663.77 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 6453368.51 | 6153211.90 |
| 3 | `Kronuz/cpp-btree` | B-tree | in-memory | 5733162.82 | 5915052.46 |
| 4 | `reum memory_bptree` | B+ tree | in-memory | 6328297.85 | 5522543.02 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 4164749.15 | 4294276.77 |

#### dense reverse insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 50740602.22 | 7217565.39 |
| 2 | `habedi/bptree` | B+ tree | in-memory | 7221726.55 | 6327195.10 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 19483207.91 | 5101078.92 |
| 4 | `reum memory_bptree` | B+ tree | in-memory | 31772382.65 | 4628622.48 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 6827476.50 | 3672370.67 |

#### dense sequential insert + sequential get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 24191329.22 | 28603266.46 |
| 2 | `reum memory_bptree` | B+ tree | in-memory | 18464151.85 | 25276993.51 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 11583358.19 | 22744136.99 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 11664743.69 | 12046662.70 |
| 5 | `habedi/bptree` | B+ tree | in-memory | 11993295.70 | 10694724.95 |

#### dense random insert + hot-spot get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 6413703.08 | 21524683.29 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 6890910.30 | 21198491.93 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 5830726.73 | 20413648.70 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 4508817.84 | 9692685.37 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 4481258.80 | 8906474.23 |

#### sparse random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 6558740.75 | 6416185.91 |
| 2 | `habedi/bptree` | B+ tree | in-memory | 5134924.43 | 6080988.13 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 6781873.75 | 6067671.22 |
| 4 | `reum memory_bptree` | B+ tree | in-memory | 5866402.92 | 5503448.60 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 3838052.74 | 4330951.85 |

### 2,000,000 records

#### dense sequential insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 9672212.77 | 4641140.26 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 23063772.38 | 4563909.42 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 9866706.96 | 3973706.32 |
| 4 | `reum memory_bptree` | B+ tree | in-memory | 15501377.48 | 3733754.96 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 10610790.25 | 2468006.03 |

#### dense random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 4203729.18 | 4710495.40 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 4693482.35 | 4407303.12 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 4577971.58 | 4039721.91 |
| 4 | `Kronuz/cpp-btree` | B-tree | in-memory | 4132133.58 | 3855417.35 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 2498095.07 | 3138285.00 |

#### dense reverse insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 47934042.76 | 4962912.06 |
| 2 | `habedi/bptree` | B+ tree | in-memory | 6807333.61 | 4322626.82 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 13740176.10 | 4236733.86 |
| 4 | `reum memory_bptree` | B+ tree | in-memory | 29792828.12 | 3394585.09 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 6477911.99 | 2742639.30 |

#### dense sequential insert + sequential get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 17829840.91 | 34073872.15 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 11244383.04 | 23032286.95 |
| 3 | `Kronuz/cpp-btree` | B-tree | in-memory | 16313075.06 | 19039217.49 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 11036037.97 | 11382008.15 |
| 5 | `habedi/bptree` | B+ tree | in-memory | 11197414.12 | 11345238.00 |

#### dense random insert + hot-spot get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 4697080.39 | 19517122.01 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 4349454.38 | 18784854.71 |
| 3 | `Kronuz/cpp-btree` | B-tree | in-memory | 3837017.25 | 16582458.87 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 3153572.48 | 9156338.75 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 3168957.32 | 6677637.47 |

#### sparse random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 3935144.23 | 4608029.94 |
| 2 | `habedi/bptree` | B+ tree | in-memory | 4068139.30 | 4180577.25 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 4652882.38 | 4005667.68 |
| 4 | `frozenca/BTree` | B-tree | in-memory | 4420023.40 | 3965211.22 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 2391506.92 | 3403455.87 |

### 5,000,000 records

#### dense sequential insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 9364599.44 | 3387528.42 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 18278274.90 | 3274672.49 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 10014176.73 | 3107015.88 |
| 4 | `reum memory_bptree` | B+ tree | in-memory | 16454346.15 | 2507035.58 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 9027052.26 | 2484091.52 |

#### dense random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 2941169.33 | 3658688.06 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 3301325.61 | 3085143.96 |
| 3 | `Kronuz/cpp-btree` | B-tree | in-memory | 2879684.62 | 3084303.10 |
| 4 | `reum memory_bptree` | B+ tree | in-memory | 3284913.34 | 2815746.23 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 2336263.19 | 2715950.55 |

#### dense reverse insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 6015116.59 | 3429505.53 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 46054315.83 | 3310081.12 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 18413230.64 | 3008959.18 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 5595964.12 | 2502181.96 |
| 5 | `reum memory_bptree` | B+ tree | in-memory | 29746227.61 | 2395499.77 |

#### dense sequential insert + sequential get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 16585659.54 | 26567463.76 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 22080079.60 | 21271266.61 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 7856201.14 | 17312909.51 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 9909519.49 | 9622644.01 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 9442937.51 | 9500819.04 |

#### dense random insert + hot-spot get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 3206729.00 | 15823638.18 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 2889645.59 | 15368624.12 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 2912934.64 | 14714844.73 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 2954110.12 | 7380265.80 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 2329503.63 | 7154481.05 |

#### sparse random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 2884663.92 | 3645581.88 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 2907981.58 | 3179894.92 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 3295493.38 | 3097797.15 |
| 4 | `Kronuz/cpp-btree` | B-tree | in-memory | 2862253.96 | 2978640.32 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 2334573.71 | 2493383.60 |

### 8,000,000 records

#### dense sequential insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 8232244.30 | 3134796.55 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 18460926.07 | 2998017.33 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 9855983.56 | 2760078.49 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 9038421.62 | 2328754.69 |
| 5 | `reum memory_bptree` | B+ tree | in-memory | 15680382.84 | 2165318.92 |

#### dense random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 2608327.44 | 3267164.63 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 2686703.54 | 2891396.57 |
| 3 | `Kronuz/cpp-btree` | B-tree | in-memory | 2510964.35 | 2684884.99 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 2146324.06 | 2635937.57 |
| 5 | `reum memory_bptree` | B+ tree | in-memory | 2268919.55 | 2476136.33 |

#### dense reverse insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `Kronuz/cpp-btree` | B-tree | in-memory | 41522410.46 | 2898200.70 |
| 2 | `frozenca/BTree` | B-tree | in-memory | 16014348.86 | 2772101.91 |
| 3 | `habedi/bptree` | B+ tree | in-memory | 4867952.11 | 2689572.37 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 5738969.60 | 2347998.50 |
| 5 | `reum memory_bptree` | B+ tree | in-memory | 23925871.69 | 2074009.54 |

#### dense sequential insert + sequential get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `reum memory_bptree` | B+ tree | in-memory | 15175922.14 | 29273634.26 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 19063304.65 | 23962980.17 |
| 3 | `frozenca/BTree` | B-tree | in-memory | 9682456.28 | 15028707.19 |
| 4 | `tidwall/btree.c` | B-tree | in-memory | 9372476.11 | 9198689.24 |
| 5 | `habedi/bptree` | B+ tree | in-memory | 9147127.97 | 8845493.15 |

#### dense random insert + hot-spot get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `frozenca/BTree` | B-tree | in-memory | 2298781.02 | 14564692.07 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 2120871.05 | 13283072.60 |
| 3 | `reum memory_bptree` | B+ tree | in-memory | 2433667.26 | 11577176.90 |
| 4 | `habedi/bptree` | B+ tree | in-memory | 2754984.74 | 7391122.41 |
| 5 | `tidwall/btree.c` | B-tree | in-memory | 1980335.37 | 5920808.63 |

#### sparse random insert + random get

| Rank | Library | Family | Storage | Insert ops/s | Lookup ops/s |
| --- | --- | --- | --- | --- | --- |
| 1 | `habedi/bptree` | B+ tree | in-memory | 2681382.39 | 3921851.15 |
| 2 | `Kronuz/cpp-btree` | B-tree | in-memory | 2604320.54 | 2697927.78 |
| 3 | `tidwall/btree.c` | B-tree | in-memory | 2096018.18 | 2505773.16 |
| 4 | `frozenca/BTree` | B-tree | in-memory | 1880038.76 | 2437378.11 |
| 5 | `reum memory_bptree` | B+ tree | in-memory | 2690540.69 | 2254780.31 |

## Notes

- All five benchmark targets in this run are configured as in-memory tree benchmarks behind a common insert/get adapter.
- Each scenario validates correctness by checking `get(key) == key * 13 + 7` for every lookup.
- The benchmark runner now recreates `build/` and `results/runtime/` every run so removed-library artifacts do not leak into new results.
- Raw machine-readable results live in `latest_results.json`, and the longer narrative report lives in `latest_detailed_report.md`.
