#ifndef MEMORY_BPTREE_H
#define MEMORY_BPTREE_H

typedef struct MemoryBPlusTree MemoryBPlusTree;

MemoryBPlusTree *memory_bptree_create(void);
void memory_bptree_destroy(MemoryBPlusTree *tree);
int memory_bptree_get(const MemoryBPlusTree *tree, int key, long *value);
int memory_bptree_put(MemoryBPlusTree *tree, int key, long value);

#endif
