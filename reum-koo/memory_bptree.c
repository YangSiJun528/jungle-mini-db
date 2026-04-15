#include <stdlib.h>
#include <string.h>

#include "memory_bptree.h"

#define BPTREE_MAX_KEYS 15
#define BPTREE_MAX_CHILDREN (BPTREE_MAX_KEYS + 1)

typedef struct BPlusNode {
    int is_leaf;
    int key_count;
    int keys[BPTREE_MAX_KEYS];
    struct BPlusNode *children[BPTREE_MAX_CHILDREN];
    long values[BPTREE_MAX_KEYS];
    struct BPlusNode *next;
} BPlusNode;

struct MemoryBPlusTree {
    BPlusNode *root;
};

typedef struct {
    int status;
    int split;
    int promoted_key;
    BPlusNode *right_node;
} InsertResult;

static BPlusNode *create_node(int is_leaf);
static void destroy_node(BPlusNode *node);
static const BPlusNode *find_leaf(const BPlusNode *node, int key);
static int find_insert_index(const int *keys, int key_count, int key);
static int find_child_index(const BPlusNode *node, int key);
static InsertResult insert_recursive(BPlusNode *node, int key, long value);
static InsertResult insert_into_leaf(BPlusNode *leaf, int key, long value);
static InsertResult insert_into_internal(BPlusNode *node, int child_index, InsertResult child_result);

MemoryBPlusTree *memory_bptree_create(void) {
    MemoryBPlusTree *tree = calloc(1, sizeof(*tree));

    if (tree == NULL) {
        return NULL;
    }

    tree->root = create_node(1);
    if (tree->root == NULL) {
        free(tree);
        return NULL;
    }

    return tree;
}

void memory_bptree_destroy(MemoryBPlusTree *tree) {
    if (tree == NULL) {
        return;
    }

    destroy_node(tree->root);
    free(tree);
}

int memory_bptree_get(const MemoryBPlusTree *tree, int key, long *value) {
    const BPlusNode *leaf;
    int index;

    if (tree == NULL || tree->root == NULL) {
        return 0;
    }

    leaf = find_leaf(tree->root, key);
    if (leaf == NULL) {
        return 0;
    }

    index = find_insert_index(leaf->keys, leaf->key_count, key);
    if (index >= leaf->key_count || leaf->keys[index] != key) {
        return 0;
    }

    if (value != NULL) {
        *value = leaf->values[index];
    }
    return 1;
}

int memory_bptree_put(MemoryBPlusTree *tree, int key, long value) {
    InsertResult result;
    BPlusNode *new_root;

    if (tree == NULL || tree->root == NULL) {
        return -1;
    }

    result = insert_recursive(tree->root, key, value);
    if (result.status <= 0) {
        return result.status;
    }

    if (!result.split) {
        return 1;
    }

    new_root = create_node(0);
    if (new_root == NULL) {
        return -1;
    }

    new_root->keys[0] = result.promoted_key;
    new_root->children[0] = tree->root;
    new_root->children[1] = result.right_node;
    new_root->key_count = 1;
    tree->root = new_root;
    return 1;
}

static BPlusNode *create_node(int is_leaf) {
    BPlusNode *node = calloc(1, sizeof(*node));

    if (node == NULL) {
        return NULL;
    }

    node->is_leaf = is_leaf;
    return node;
}

static void destroy_node(BPlusNode *node) {
    if (node == NULL) {
        return;
    }

    if (!node->is_leaf) {
        for (int i = 0; i <= node->key_count; i++) {
            destroy_node(node->children[i]);
        }
    }

    free(node);
}

static const BPlusNode *find_leaf(const BPlusNode *node, int key) {
    const BPlusNode *current = node;

    while (current != NULL && !current->is_leaf) {
        current = current->children[find_child_index(current, key)];
    }

    return current;
}

static int find_insert_index(const int *keys, int key_count, int key) {
    int index = 0;

    while (index < key_count && keys[index] < key) {
        index++;
    }

    return index;
}

static int find_child_index(const BPlusNode *node, int key) {
    int index = 0;

    while (index < node->key_count && key >= node->keys[index]) {
        index++;
    }

    return index;
}

static InsertResult insert_recursive(BPlusNode *node, int key, long value) {
    InsertResult child_result;
    int child_index;

    if (node->is_leaf) {
        return insert_into_leaf(node, key, value);
    }

    child_index = find_child_index(node, key);
    child_result = insert_recursive(node->children[child_index], key, value);
    if (child_result.status <= 0 || !child_result.split) {
        return child_result;
    }

    return insert_into_internal(node, child_index, child_result);
}

static InsertResult insert_into_leaf(BPlusNode *leaf, int key, long value) {
    InsertResult result = {1, 0, 0, NULL};
    int insert_index = find_insert_index(leaf->keys, leaf->key_count, key);

    if (insert_index < leaf->key_count && leaf->keys[insert_index] == key) {
        result.status = 0;
        return result;
    }

    if (leaf->key_count < BPTREE_MAX_KEYS) {
        memmove(&leaf->keys[insert_index + 1], &leaf->keys[insert_index],
                sizeof(leaf->keys[0]) * (leaf->key_count - insert_index));
        memmove(&leaf->values[insert_index + 1], &leaf->values[insert_index],
                sizeof(leaf->values[0]) * (leaf->key_count - insert_index));
        leaf->keys[insert_index] = key;
        leaf->values[insert_index] = value;
        leaf->key_count++;
        return result;
    }

    {
        int temp_keys[BPTREE_MAX_KEYS + 1];
        long temp_values[BPTREE_MAX_KEYS + 1];
        int total_keys = BPTREE_MAX_KEYS + 1;
        int left_count = total_keys / 2;
        int right_count = total_keys - left_count;
        BPlusNode *right = create_node(1);

        if (right == NULL) {
            result.status = -1;
            return result;
        }

        memcpy(temp_keys, leaf->keys, sizeof(leaf->keys));
        memcpy(temp_values, leaf->values, sizeof(leaf->values));

        memmove(&temp_keys[insert_index + 1], &temp_keys[insert_index],
                sizeof(temp_keys[0]) * (BPTREE_MAX_KEYS - insert_index));
        memmove(&temp_values[insert_index + 1], &temp_values[insert_index],
                sizeof(temp_values[0]) * (BPTREE_MAX_KEYS - insert_index));
        temp_keys[insert_index] = key;
        temp_values[insert_index] = value;

        memset(leaf->keys, 0, sizeof(leaf->keys));
        memset(leaf->values, 0, sizeof(leaf->values));
        memcpy(leaf->keys, temp_keys, sizeof(temp_keys[0]) * left_count);
        memcpy(leaf->values, temp_values, sizeof(temp_values[0]) * left_count);
        leaf->key_count = left_count;

        memcpy(right->keys, temp_keys + left_count, sizeof(temp_keys[0]) * right_count);
        memcpy(right->values, temp_values + left_count, sizeof(temp_values[0]) * right_count);
        right->key_count = right_count;
        right->next = leaf->next;
        leaf->next = right;

        result.split = 1;
        result.promoted_key = right->keys[0];
        result.right_node = right;
        return result;
    }
}

static InsertResult insert_into_internal(BPlusNode *node, int child_index, InsertResult child_result) {
    InsertResult result = {1, 0, 0, NULL};

    if (node->key_count < BPTREE_MAX_KEYS) {
        memmove(&node->keys[child_index + 1], &node->keys[child_index],
                sizeof(node->keys[0]) * (node->key_count - child_index));
        memmove(&node->children[child_index + 2], &node->children[child_index + 1],
                sizeof(node->children[0]) * (node->key_count - child_index));
        node->keys[child_index] = child_result.promoted_key;
        node->children[child_index + 1] = child_result.right_node;
        node->key_count++;
        return result;
    }

    {
        int temp_keys[BPTREE_MAX_KEYS + 1];
        BPlusNode *temp_children[BPTREE_MAX_CHILDREN + 1];
        int total_keys = BPTREE_MAX_KEYS + 1;
        int promote_index = total_keys / 2;
        int left_keys = promote_index;
        int right_keys = total_keys - promote_index - 1;
        BPlusNode *right = create_node(0);

        if (right == NULL) {
            result.status = -1;
            return result;
        }

        memcpy(temp_keys, node->keys, sizeof(node->keys));
        memcpy(temp_children, node->children, sizeof(node->children));

        memmove(&temp_keys[child_index + 1], &temp_keys[child_index],
                sizeof(temp_keys[0]) * (BPTREE_MAX_KEYS - child_index));
        temp_keys[child_index] = child_result.promoted_key;

        memmove(&temp_children[child_index + 2], &temp_children[child_index + 1],
                sizeof(temp_children[0]) * (BPTREE_MAX_CHILDREN - child_index - 1));
        temp_children[child_index + 1] = child_result.right_node;

        memset(node->keys, 0, sizeof(node->keys));
        memset(node->children, 0, sizeof(node->children));
        memcpy(node->keys, temp_keys, sizeof(temp_keys[0]) * left_keys);
        memcpy(node->children, temp_children, sizeof(temp_children[0]) * (left_keys + 1));
        node->key_count = left_keys;

        memcpy(right->keys, temp_keys + promote_index + 1, sizeof(temp_keys[0]) * right_keys);
        memcpy(right->children, temp_children + promote_index + 1,
               sizeof(temp_children[0]) * (right_keys + 1));
        right->key_count = right_keys;

        result.split = 1;
        result.promoted_key = temp_keys[promote_index];
        result.right_node = right;
        return result;
    }
}
