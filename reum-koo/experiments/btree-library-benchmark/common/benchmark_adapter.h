#ifndef BTREE_LIBRARY_BENCHMARK_ADAPTER_H
#define BTREE_LIBRARY_BENCHMARK_ADAPTER_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct BenchmarkLibraryOps {
    const char *id;
    const char *display_name;
    const char *family;
    const char *storage_mode;
    void *(*create)(const char *runtime_dir, const char *instance_name);
    void (*destroy)(void *tree_handle);
    int (*insert)(void *tree_handle, int key, int64_t value);
    int (*get)(void *tree_handle, int key, int64_t *out_value);
} BenchmarkLibraryOps;

const BenchmarkLibraryOps *const *btree_benchmark_get_libraries(size_t *count);

#ifdef __cplusplus
}
#endif

#endif
