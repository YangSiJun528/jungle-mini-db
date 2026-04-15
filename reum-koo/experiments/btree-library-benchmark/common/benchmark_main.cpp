#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "benchmark_adapter.h"

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

struct ScenarioConfig {
    std::string id;
    std::string display_name;
    std::vector<int> insert_order;
    std::vector<int> lookup_order;
};

struct ScenarioResult {
    std::string scenario_id;
    std::string scenario_name;
    double insert_seconds;
    double lookup_seconds;
    double insert_ops_per_second;
    double lookup_ops_per_second;
};

struct BenchmarkOptions {
    std::size_t records = 100000;
    std::uint64_t seed = 20260415ULL;
    fs::path runtime_dir = "results/runtime";
};

static std::int64_t encode_value(int key) {
    return static_cast<std::int64_t>(key) * 13 + 7;
}

static std::vector<int> make_sequential_keys(std::size_t records) {
    std::vector<int> keys(records);
    std::iota(keys.begin(), keys.end(), 1);
    return keys;
}

static std::vector<int> make_shuffled_copy(const std::vector<int> &source, std::uint64_t seed) {
    std::vector<int> shuffled = source;
    std::mt19937_64 engine(seed);
    std::shuffle(shuffled.begin(), shuffled.end(), engine);
    return shuffled;
}

static std::vector<int> make_reversed_copy(const std::vector<int> &source) {
    std::vector<int> reversed = source;
    std::reverse(reversed.begin(), reversed.end());
    return reversed;
}

static std::vector<int> make_sparse_keys(std::size_t records) {
    constexpr int kStride = 257;

    std::vector<int> keys(records);
    for (std::size_t index = 0; index < records; ++index) {
        keys[index] = static_cast<int>(index) * kStride + 11;
    }
    return keys;
}

static std::vector<int> make_hot_lookup_order(const std::vector<int> &keys, std::uint64_t seed) {
    const std::size_t hot_size = std::max<std::size_t>(1, keys.size() / 100);
    std::vector<int> hot_keys(keys.begin(), keys.begin() + hot_size);
    std::vector<int> lookups;
    lookups.reserve(keys.size());

    for (std::size_t index = 0; index < keys.size(); ++index) {
        lookups.push_back(hot_keys[index % hot_keys.size()]);
    }

    std::mt19937_64 engine(seed);
    std::shuffle(lookups.begin(), lookups.end(), engine);
    return lookups;
}

static BenchmarkOptions parse_args(int argc, char **argv) {
    BenchmarkOptions options;

    for (int index = 1; index < argc; ++index) {
        std::string argument = argv[index];

        if (argument == "--records" && index + 1 < argc) {
            options.records = static_cast<std::size_t>(std::stoull(argv[++index]));
            continue;
        }
        if (argument == "--seed" && index + 1 < argc) {
            options.seed = std::stoull(argv[++index]);
            continue;
        }
        if (argument == "--runtime-dir" && index + 1 < argc) {
            options.runtime_dir = argv[++index];
            continue;
        }

        std::ostringstream message;
        message << "unknown or incomplete argument: " << argument;
        throw std::runtime_error(message.str());
    }

    if (options.records == 0) {
        throw std::runtime_error("--records must be at least 1");
    }

    return options;
}

static ScenarioResult run_scenario(const BenchmarkLibraryOps &library,
                                   const ScenarioConfig &scenario,
                                   const fs::path &runtime_root) {
    const std::string instance_name = std::string(library.id) + "_" + scenario.id;
    const fs::path library_runtime_dir = runtime_root / library.id;

    fs::create_directories(library_runtime_dir);

    void *tree = library.create(library_runtime_dir.string().c_str(), instance_name.c_str());
    if (tree == nullptr) {
        throw std::runtime_error("failed to create tree for " + std::string(library.id));
    }

    auto insert_started = Clock::now();
    for (int key: scenario.insert_order) {
        if (!library.insert(tree, key, encode_value(key))) {
            library.destroy(tree);
            throw std::runtime_error("insert failed for " + std::string(library.id) + " key " + std::to_string(key));
        }
    }
    auto insert_finished = Clock::now();

    auto lookup_started = Clock::now();
    for (int key: scenario.lookup_order) {
        std::int64_t value = 0;
        if (!library.get(tree, key, &value)) {
            library.destroy(tree);
            throw std::runtime_error("lookup failed for " + std::string(library.id) + " key " + std::to_string(key));
        }
        if (value != encode_value(key)) {
            library.destroy(tree);
            throw std::runtime_error("lookup returned wrong value for " + std::string(library.id));
        }
    }
    auto lookup_finished = Clock::now();

    library.destroy(tree);

    const std::chrono::duration<double> insert_elapsed = insert_finished - insert_started;
    const std::chrono::duration<double> lookup_elapsed = lookup_finished - lookup_started;

    ScenarioResult result{};
    result.scenario_id = scenario.id;
    result.scenario_name = scenario.display_name;
    result.insert_seconds = insert_elapsed.count();
    result.lookup_seconds = lookup_elapsed.count();
    result.insert_ops_per_second = static_cast<double>(scenario.insert_order.size()) / result.insert_seconds;
    result.lookup_ops_per_second = static_cast<double>(scenario.lookup_order.size()) / result.lookup_seconds;
    return result;
}

int main(int argc, char **argv) {
    try {
        const BenchmarkOptions options = parse_args(argc, argv);
        const std::vector<int> dense_sequential_keys = make_sequential_keys(options.records);
        const std::vector<int> dense_random_keys = make_shuffled_copy(dense_sequential_keys, options.seed);
        const std::vector<int> dense_reverse_keys = make_reversed_copy(dense_sequential_keys);
        const std::vector<int> dense_random_lookups =
                make_shuffled_copy(dense_sequential_keys, options.seed ^ 0xBAD5EEDULL);
        const std::vector<int> dense_hot_lookups =
                make_hot_lookup_order(dense_sequential_keys, options.seed ^ 0xC001D00DULL);

        const std::vector<int> sparse_keys = make_sparse_keys(options.records);
        const std::vector<int> sparse_random_keys = make_shuffled_copy(sparse_keys, options.seed ^ 0x51515151ULL);
        const std::vector<int> sparse_random_lookups =
                make_shuffled_copy(sparse_keys, options.seed ^ 0xA5A5A5A5ULL);

        const std::vector<ScenarioConfig> scenarios = {
                {"dense_seq_build_rand_get",
                 "dense sequential insert + random get",
                 dense_sequential_keys,
                 dense_random_lookups},
                {"dense_rand_build_rand_get",
                 "dense random insert + random get",
                 dense_random_keys,
                 dense_random_lookups},
                {"dense_rev_build_rand_get",
                 "dense reverse insert + random get",
                 dense_reverse_keys,
                 dense_random_lookups},
                {"dense_seq_build_seq_get",
                 "dense sequential insert + sequential get",
                 dense_sequential_keys,
                 dense_sequential_keys},
                {"dense_rand_build_hot_get",
                 "dense random insert + hot-spot get",
                 dense_random_keys,
                 dense_hot_lookups},
                {"sparse_rand_build_rand_get",
                 "sparse random insert + random get",
                 sparse_random_keys,
                 sparse_random_lookups},
        };

        fs::create_directories(options.runtime_dir);

        std::size_t library_count = 0;
        const BenchmarkLibraryOps *const *libraries = btree_benchmark_get_libraries(&library_count);

        std::cerr << "records=" << options.records << ", libraries=" << library_count << '\n';
        for (std::size_t library_index = 0; library_index < library_count; ++library_index) {
            const BenchmarkLibraryOps &library = *libraries[library_index];
            std::cerr << "running " << library.id << " (" << library.display_name << ")" << '\n';

            for (const ScenarioConfig &scenario: scenarios) {
                const ScenarioResult result = run_scenario(library, scenario, options.runtime_dir);
                std::cout << "RESULT"
                          << '\t' << library.id
                          << '\t' << library.display_name
                          << '\t' << library.family
                          << '\t' << library.storage_mode
                          << '\t' << result.scenario_id
                          << '\t' << result.scenario_name
                          << '\t' << options.records
                          << '\t' << std::fixed << std::setprecision(9) << result.insert_seconds
                          << '\t' << result.lookup_seconds
                          << '\t' << result.insert_ops_per_second
                          << '\t' << result.lookup_ops_per_second
                          << '\n';
            }
        }
    } catch (const std::exception &error) {
        std::cerr << "benchmark failed: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
