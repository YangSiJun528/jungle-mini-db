#include "../common/benchmark_adapter.h"

extern "C" const BenchmarkLibraryOps *btree_benchmark_reum_memory_bptree_ops(void);
extern "C" const BenchmarkLibraryOps *btree_benchmark_habedi_bptree_ops(void);
extern "C" const BenchmarkLibraryOps *btree_benchmark_tidwall_btree_c_ops(void);
extern "C" const BenchmarkLibraryOps *btree_benchmark_kronuz_cpp_btree_ops(void);
extern "C" const BenchmarkLibraryOps *btree_benchmark_frozenca_btree_ops(void);

extern "C" const BenchmarkLibraryOps *const *btree_benchmark_get_libraries(size_t *count) {
    static const BenchmarkLibraryOps *LIBRARIES[] = {
            btree_benchmark_reum_memory_bptree_ops(),
            btree_benchmark_habedi_bptree_ops(),
            btree_benchmark_tidwall_btree_c_ops(),
            btree_benchmark_kronuz_cpp_btree_ops(),
            btree_benchmark_frozenca_btree_ops(),
    };

    *count = sizeof(LIBRARIES) / sizeof(LIBRARIES[0]);
    return LIBRARIES;
}
