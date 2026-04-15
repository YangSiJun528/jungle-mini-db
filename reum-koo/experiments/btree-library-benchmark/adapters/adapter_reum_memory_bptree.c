#include "../common/benchmark_adapter.h"
#include "../../memory_bptree.h"

static void *create_tree(const char *runtime_dir, const char *instance_name) {
    (void) runtime_dir;
    (void) instance_name;
    return memory_bptree_create();
}

static void destroy_tree(void *tree_handle) {
    memory_bptree_destroy((MemoryBPlusTree *) tree_handle);
}

static int insert_item(void *tree_handle, int key, int64_t value) {
    return memory_bptree_put((MemoryBPlusTree *) tree_handle, key, (long) value) == 1;
}

static int get_item(void *tree_handle, int key, int64_t *out_value) {
    long value = 0;
    int found = memory_bptree_get((const MemoryBPlusTree *) tree_handle, key, &value);

    if (!found) {
        return 0;
    }

    *out_value = (int64_t) value;
    return 1;
}

static const BenchmarkLibraryOps OPS = {
        .id = "reum_memory_bptree",
        .display_name = "reum memory_bptree",
        .family = "B+ tree",
        .storage_mode = "in-memory",
        .create = create_tree,
        .destroy = destroy_tree,
        .insert = insert_item,
        .get = get_item,
};

const BenchmarkLibraryOps *btree_benchmark_reum_memory_bptree_ops(void) {
    return &OPS;
}
