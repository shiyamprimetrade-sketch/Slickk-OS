# P0-015 native host microbenchmark — NOT Android performance evidence

Host-only C++17 comparison between std::memcpy and std::copy on identical, preallocated byte buffers. Each measured iteration reads and checksums all destination bytes. NOINLINE call wrappers and a volatile checksum sink make work observable instead of being eliminated. Checksum computation is shared substantial overhead: numbers measure copy AND checksum, not isolated memcpy throughput; the compiler may compile both copies identically. This is instrumentation validation, not proof of an optimization.

Reproduce at repository root (GNU c++ or compatible Clang):

    c++ -std=c++17 -O2 -Wall -Wextra -Wpedantic -Werror native/hotpath.cpp -o /tmp/slickk_hotpath
    /tmp/slickk_hotpath 7 4096 200 > /tmp/slickk_hotpath_obs.json
    python3 runtime/analyze.py /tmp/slickk_hotpath_obs.json > /tmp/slickk_hotpath_report.json
    /tmp/slickk_hotpath 4 4096 200  # expected exit 2 for insufficient samples

Arguments: samples 5..100, buffer size 1..65536 bytes, iterations per sample 1..10000. Two untimed warmups per variant precede AB/BA alternated paired batches. Reported ns per iteration use steady_clock. Each batch is a sample; multiple iterations within a batch are NOT statistically independent.

Output provenance=measured and environment_kind=host signifies local clock readings, not authenticated evidence. The environment_id is an unidentified host placeholder, build_id is a compile-flag label, and the evidence reference does not contain the actual raw-data digest. Before publishing performance claims, capture CPU architecture, host kernel, compiler full version, real flags, tool/source commit, SHA256 of raw results, thermal/frequency conditions and session metadata separately. No phone data, Android ART process, JNI call, battery energy, APK or NDK build was measured.

The tool makes no system modifications. To roll back, remove the test binary and temporary output files. Candidate changes must preserve output behavior, avoid undefined behavior, pass sanitizer/ABI/compatibility checks, and be reverted on >5% matched regression or any correctness, reliability, memory or security failure. Do not transplant host results into stock Android vs Slickk-OS benchmark claims.
