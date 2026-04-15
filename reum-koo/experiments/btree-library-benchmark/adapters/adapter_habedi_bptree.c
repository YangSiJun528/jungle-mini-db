#include <stdbool.h>
#include <stdint.h>

#define BPTREE_NUMERIC_TYPE int
#define BPTREE_VALUE_TYPE int64_t
#define BPTREE_IMPLEMENTATION
#include "../third_party/habedi_bptree/include/bptree.h"

#include "../common/benchmark_adapter.h"

static void *create_tree(const char *runtime_dir, const char *instance_name) {
    (void) runtime_dir;
    (void) instance_name;
    return bptree_create(31, NULL, false);
}

static void destroy_tree(void *tree_handle) {
    bptree_free((bptree *) tree_handle);
}

static int insert_item(void *tree_handle, int key, int64_t value) {
    return bptree_put((bptree *) tree_handle, &key, value) == BPTREE_OK;
}

static int get_item(void *tree_handle, int key, int64_t *out_value) {
    return bptree_get((const bptree *) tree_handle, &key, out_value) == BPTREE_OK;
}

static const BenchmarkLibraryOps OPS = {
        .id = "habedi_bptree",
        .display_name = "habedi/bptree",
        .family = "B+ tree",
        .storage_mode = "in-memory",
        .create = create_tree,
        .destroy = destroy_tree,
        .insert = insert_item,
        .get = get_item,
};

const BenchmarkLibraryOps *btree_benchmark_habedi_bptree_ops(void) {
    return &OPS;
}
