#include <stdint.h>
#include <stdlib.h>

#include "../common/benchmark_adapter.h"
#include "../third_party/tidwall_btree_c/btree.h"

typedef struct {
    int key;
    int64_t value;
} TidwallEntry;

static int compare_entries(const void *a, const void *b, void *udata) {
    const TidwallEntry *left = (const TidwallEntry *) a;
    const TidwallEntry *right = (const TidwallEntry *) b;

    (void) udata;
    if (left->key < right->key) {
        return -1;
    }
    if (left->key > right->key) {
        return 1;
    }
    return 0;
}

static void *create_tree(const char *runtime_dir, const char *instance_name) {
    (void) runtime_dir;
    (void) instance_name;
    return btree_new(sizeof(TidwallEntry), 64, compare_entries, NULL);
}

static void destroy_tree(void *tree_handle) {
    btree_free((struct btree *) tree_handle);
}

static int insert_item(void *tree_handle, int key, int64_t value) {
    TidwallEntry entry;
    struct btree *tree = (struct btree *) tree_handle;

    entry.key = key;
    entry.value = value;
    btree_set(tree, &entry);
    return !btree_oom(tree);
}

static int get_item(void *tree_handle, int key, int64_t *out_value) {
    const TidwallEntry *entry;
    TidwallEntry query;

    query.key = key;
    query.value = 0;
    entry = (const TidwallEntry *) btree_get((const struct btree *) tree_handle, &query);
    if (entry == NULL) {
        return 0;
    }

    *out_value = entry->value;
    return 1;
}

static const BenchmarkLibraryOps OPS = {
        .id = "tidwall_btree_c",
        .display_name = "tidwall/btree.c",
        .family = "B-tree",
        .storage_mode = "in-memory",
        .create = create_tree,
        .destroy = destroy_tree,
        .insert = insert_item,
        .get = get_item,
};

const BenchmarkLibraryOps *btree_benchmark_tidwall_btree_c_ops(void) {
    return &OPS;
}
