// SPDX-License-Identifier: Apache-2.0
// P0-015 host-only comparison. Not an Android/ART benchmark.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

static volatile std::uint64_t observable = 0;

NOINLINE void memcpy_copy(unsigned char* to, const unsigned char* from, std::size_t n) {
    std::memcpy(to, from, n);
}
NOINLINE void stl_copy(unsigned char* to, const unsigned char* from, std::size_t n) {
    std::copy(from, from + n, to);
}

using Clock = std::chrono::steady_clock;
using Fn = void (*)(unsigned char*, const unsigned char*, std::size_t);

static double measure(Fn fn, std::vector<unsigned char>& dest,
                      const std::vector<unsigned char>& source, int iterations) {
    std::uint64_t digest = 0;
    auto start = Clock::now();
    for (int n = 0; n < iterations; ++n) {
        fn(dest.data(), source.data(), source.size());
        // Observe every byte, not just time. The same checksum is done for both variants.
        for (unsigned char b : dest) {
            digest = (digest * 131U) ^ b;
        }
    }
    auto finish = Clock::now();
    observable = digest;
    return static_cast<double>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(finish - start).count())
        / iterations;
}

static int positive(const char* text, int maximum) {
    std::size_t end = 0;
    std::string value(text);
    int number = std::stoi(value, &end);
    if (end != value.size() || number < 1 || number > maximum) {
        throw std::invalid_argument("positive integer out of bounds");
    }
    return number;
}

int main(int argc, char** argv) {
    // Fixed names only, no user-supplied labels inside JSON; no personal device identifiers.
    if (argc != 4) {
        std::cerr << "usage: hotpath <samples:5..100> <bytes:1..65536> <iterations:1..10000>\n";
        return 2;
    }
    try {
        int samples = positive(argv[1], 100);
        int size = positive(argv[2], 65536);
        int iterations = positive(argv[3], 10000);
        if (samples < 5) throw std::invalid_argument("at least five samples required");
        std::vector<unsigned char> source(size), dest(size);
        for (int i = 0; i < size; ++i) source[i] = static_cast<unsigned char>((i * 73 + 29) % 251);
        for (int i = 0; i < 2; ++i) {
            measure(memcpy_copy, dest, source, iterations);
            measure(stl_copy, dest, source, iterations);
        }
        std::cout << "{\"schema_version\":\"1.0\",\"observations\":[\n";
        bool first = true;
        for (int sample = 1; sample <= samples; ++sample) {
            // Alternating AB/BA limits, but cannot eliminate, ordering bias.
            double a = 0, b = 0;
            if (sample % 2) {
                a = measure(memcpy_copy, dest, source, iterations);
                b = measure(stl_copy, dest, source, iterations);
            } else {
                b = measure(stl_copy, dest, source, iterations);
                a = measure(memcpy_copy, dest, source, iterations);
            }
            for (int variant = 0; variant < 2; ++variant) {
                if (!first) std::cout << ",\n";
                first = false;
                std::cout << "{\"provenance\":\"measured\","
                          << "\"environment_kind\":\"host\","
                          << "\"environment_id\":\"unidentified_host\","
                          << "\"build_id\":\"cpp17_O2\","
                          << "\"source_tool\":\"cpp17_hotpath_v1\","
                          << "\"source_ref\":\"local:steady_clock_no_trace\","
                          << "\"experiment_id\":\"host_copy_" << size << "B_" << iterations << "ops\","
                          << "\"protocol_id\":\"hotpath_v1\","
                          << "\"runtime_mode\":\"native_host_only\","
                          << "\"workload\":\"copy_and_checksum\","
                          << "\"variant\":\"" << (variant ? "candidate" : "baseline") << "\","
                          << "\"metric\":\"duration_ns\",\"unit\":\"ns\","
                          << "\"sample_id\":\"pair_" << sample << "\","
                          << "\"value\":" << (variant ? b : a) << "}";
            }
        }
        std::cout << "\n]}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "invalid benchmark arguments: " << error.what() << "\n";
        return 2;
    }
}
