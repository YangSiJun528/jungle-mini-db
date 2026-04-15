#include <cstdint>
#include <new>

#include "../common/benchmark_adapter.h"
#include "../third_party/frozenca_btree/include/fc/btree.h"

struct FrozencaWrapper {
    frozenca::BTreeMap<int, std::int64_t> tree;
};

static void *create_tree(const char *runtime_dir, const char *instance_name) {
    (void) runtime_dir;
    (void) instance_name;
    try {
        return new FrozencaWrapper();
    } catch (const std::bad_alloc &) {
        return nullptr;
    }
}

static void destroy_tree(void *tree_handle) {
    delete static_cast<FrozencaWrapper *>(tree_handle);
}

static int insert_item(void *tree_handle, int key, std::int64_t value) {
    FrozencaWrapper *wrapper = static_cast<FrozencaWrapper *>(tree_handle);
    const auto size_before = wrapper->tree.size();
    wrapper->tree[key] = value;
    return wrapper->tree.size() == size_before + 1 ? 1 : 0;
}

static int get_item(void *tree_handle, int key, std::int64_t *out_value) {
    FrozencaWrapper *wrapper = static_cast<FrozencaWrapper *>(tree_handle);
    auto iter = wrapper->tree.find(key);

    if (iter == wrapper->tree.end()) {
        return 0;
    }

    *out_value = iter->second;
    return 1;
}

static const BenchmarkLibraryOps OPS = {
        "frozenca_btree",
        "frozenca/BTree",
        "B-tree",
        "in-memory",
        create_tree,
        destroy_tree,
        insert_item,
        get_item,
};

extern "C" const BenchmarkLibraryOps *btree_benchmark_frozenca_btree_ops(void) {
    return &OPS;
}
