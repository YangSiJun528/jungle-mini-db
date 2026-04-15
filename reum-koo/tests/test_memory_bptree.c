#include <assert.h>
#include <stdio.h>

#include "memory_bptree.h"

static void test_sequential_inserts_and_reads(void) {
    MemoryBPlusTree *tree = memory_bptree_create();

    assert(tree != NULL);
    for (int key = 1; key <= 256; key++) {
        assert(memory_bptree_put(tree, key, key * 64L) == 1);
    }

    for (int key = 1; key <= 256; key++) {
        long value = -1;

        assert(memory_bptree_get(tree, key, &value) == 1);
        assert(value == key * 64L);
    }

    memory_bptree_destroy(tree);
}

static void test_duplicate_and_missing_keys(void) {
    MemoryBPlusTree *tree = memory_bptree_create();
    long value = -1;

    assert(tree != NULL);
    assert(memory_bptree_put(tree, 42, 128L) == 1);
    assert(memory_bptree_put(tree, 42, 256L) == 0);
    assert(memory_bptree_get(tree, 99, &value) == 0);
    assert(memory_bptree_get(tree, 42, &value) == 1);
    assert(value == 128L);

    memory_bptree_destroy(tree);
}

static void test_out_of_order_inserts(void) {
    int keys[] = {50, 10, 70, 20, 60, 80, 30, 40, 90, 100, 15, 25, 35, 45};
    MemoryBPlusTree *tree = memory_bptree_create();

    assert(tree != NULL);
    for (size_t i = 0; i < sizeof(keys) / sizeof(keys[0]); i++) {
        assert(memory_bptree_put(tree, keys[i], keys[i] * 8L) == 1);
    }

    for (size_t i = 0; i < sizeof(keys) / sizeof(keys[0]); i++) {
        long value = -1;

        assert(memory_bptree_get(tree, keys[i], &value) == 1);
        assert(value == keys[i] * 8L);
    }

    memory_bptree_destroy(tree);
}

int main(void) {
    test_sequential_inserts_and_reads();
    test_duplicate_and_missing_keys();
    test_out_of_order_inserts();
    puts("memory_bptree tests passed");
    return 0;
}
