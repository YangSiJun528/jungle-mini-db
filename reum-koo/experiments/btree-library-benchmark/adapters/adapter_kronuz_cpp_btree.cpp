#include <cstdint>
#include <new>

#include "../common/benchmark_adapter.h"
#include "../third_party/kronuz_cpp_btree/btree/map.h"

struct KronuzWrapper {
    btree::map<int, std::int64_t> tree;
};

static void *create_tree(const char *runtime_dir, const char *instance_name) {
    (void) runtime_dir;
    (void) instance_name;
    try {
        return new KronuzWrapper();
    } catch (const std::bad_alloc &) {
        return nullptr;
    }
}

static void destroy_tree(void *tree_handle) {
    delete static_cast<KronuzWrapper *>(tree_handle);
}

static int insert_item(void *tree_handle, int key, std::int64_t value) {
    KronuzWrapper *wrapper = static_cast<KronuzWrapper *>(tree_handle);
    return wrapper->tree.emplace(key, value).second ? 1 : 0;
}

static int get_item(void *tree_handle, int key, std::int64_t *out_value) {
    KronuzWrapper *wrapper = static_cast<KronuzWrapper *>(tree_handle);
    auto it = wrapper->tree.find(key);

    if (it == wrapper->tree.end()) {
        return 0;
    }

    *out_value = it->second;
    return 1;
}

static const BenchmarkLibraryOps OPS = {
        "kronuz_cpp_btree",
        "Kronuz/cpp-btree",
        "B-tree",
        "in-memory",
        create_tree,
        destroy_tree,
        insert_item,
        get_item,
};

extern "C" const BenchmarkLibraryOps *btree_benchmark_kronuz_cpp_btree_ops(void) {
    return &OPS;
}
