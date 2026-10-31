# P0-015 — Runtime/native profiling foundation (Chat 07)

Scope: read-only structured-observation analyzer, C++17 host benchmark and rollback-aware research register. This is not an ART patch, Android measurement, or binary-trace parser.

## Dependency checkpoint, 2026-10-31

- Foundation PR #1: open/draft/unmerged. Branch is based on planning/slickk-os-foundation and PR targets the same branch.
- P0-007 PR #5: implementation branch task/P0-007-benchmark-protocol exists, open/draft, not accepted. Its benchmarks/PROTOCOL.md and benchmarks/schema.json were inspected. Matched comparisons, type-7 P95, minimum five independent pairs and no-claims safeguards are adopted provisionally. No benchmark-owned paths were changed.
- P0-002 PR #3 initially supplied the project pin. **INDEPENDENTLY VERIFIED** with direct official Gitiles page retrieval on 2026-10-31: annotated platform/art tag android-17.0.0_r1, tag object fc31298bb626c4b5d53ae3b715c42a2daa802c08, peels to commit b753cf97923c3695338d21466fa14c57b480a59a. The page labels Android 17.0.0 release 1. Six selected files were retrieved at that exact commit with the blob identifiers below. This does NOT establish an actual Android build, checkout, October security patch or OS compatibility.

## Upstream evidence inspected

| Area | Role and status | Reference |
|---|---|---|
| ART AOT/JIT/interpreter | Official documentation: DEX interpretation, JIT, AOT compilation, runtime profile tradeoffs | https://source.android.com/docs/core/runtime/configure |
| ART JIT | Official documentation: JIT code profiling, interpreted/JIT/AOT method states | https://source.android.com/docs/core/runtime/jit-compiler |
| Managed GC | Official documentation: collectors and app performance impacts | https://source.android.com/docs/core/runtime |
| Heap trimming | Current upstream source describes lock/jank risk in Heap::RequestTrim; not a device benchmark | https://android.googlesource.com/platform/art/+/master/runtime/gc/heap.cc |
| Class linking | Public main source inspected; pinned revision not fetched | https://android.googlesource.com/platform/art/+/main/runtime/class_linker.cc |
| JNI | Official local/global reference and thread handling guidance | https://developer.android.com/ndk/guides/jni-tips |
| CPU/native profiling | Official Android simpleperf and Perfetto guidance | https://source.android.com/docs/core/tests/debug/eval_perf |

**VERIFIED pinned files** — official ART Gitiles pages returned HTTP 200, matching exact commit and displaying Git blob identifiers (2026-10-31). Roles and entrypoints were checked in retrieved source where specified. Links below use the exact commit, not floating main.

| Exact pinned path | Git blob SHA | Inspected symbol/role |
|---|---|---|
| runtime/runtime.cc | ea1052882a714e4d90407f080ff15e9fd92ae11a | Runtime startup/lifecycle source |
| runtime/class_linker.cc | 4b3c66770f82cfb8d34eca693e50f4827cb3dbf5 | FindClass and EnsureInitialized |
| runtime/jit/jit.cc | 94c2efc1eceff0b1af13fb6071b25013823891b7 | Jit::Create and CompileMethodInternal |
| runtime/gc/heap.cc | 817eb14f95168a19e3e021bcf06f542458c1a968 | TrimSpaces, RequestTrim and GetBytesAllocated |
| runtime/jni/jni_internal.cc | 15db66e10cefbd179a42c7edeb9f5c880700367e | GetPrimitiveArrayCritical, NewGlobalRef, DeleteLocalRef |
| runtime/thread.cc | c3a28d5815c0a0906f41426a7e0edcc3e4d44d1e | ART thread implementation |

Pinned source directory: https://android.googlesource.com/platform/art/+/b753cf97923c3695338d21466fa14c57b480a59a/
Pinned tag: https://android.googlesource.com/platform/art/+/refs/tags/android-17.0.0_r1

Individual paths append to the source directory above. Blob identity on Gitiles is independent source provenance, not evidence of downloaded compiled ART or measured performance. Full manifest/other project pins remain dependent on P0-002 integration.

## Data ingestion contract, v1.0

JSON top level must contain exactly schema_version="1.0" and observations=[rows]. CSV contains all per-row fields and a schema_version column. Each row requires:

| Column | Meaning |
|---|---|
| provenance | synthetic or producer-asserted measured (not authenticated by parser) |
| environment_kind | host, emulator or android_device |
| environment_id | anonymous, stable physical or virtual target label |
| build_id | tool/OS/app artifact version, constant within each variant |
| source_tool | exporter and version identifier |
| source_ref | evidence pointer; synthetic observations must use synthetic: prefix |
| experiment_id | unique experiment |
| protocol_id | exact experiment protocol |
| runtime_mode | native, interpreter, JIT, AOT or any explicitly described consistent condition |
| workload | scripted task |
| variant | baseline or candidate, not necessarily Android vs Slickk-OS |
| metric | duration_ns, initialization_ns, startup_ns, gc_pause_ns, jni_transition_ns, allocation_count or allocated_bytes |
| unit | time: ns/us/ms/s; count: count; bytes: bytes/KiB |
| sample_id | unique repeated trial, matched between variants |
| value | finite nonnegative numeric result, integral when allocation_count |

Time is converted to ns, KiB to bytes; input with mismatched units is rejected. Missing optional metrics are not imputed. A JSON or CSV observation must be a derived scalar; NO raw Perfetto, simpleperf or ART binary file import is supported. Trace exporters must preserve original raw data, versions, timestamps, aggregation, clock units, hashes, permission/PII review and process selection. A CPU sample count is not a JNI transition latency.

Analysis partitions experiment/workload/metric, checks matched provenance/environment/tool/protocol/runtime context and requires 5 common paired sample identifiers. A variant with changing build IDs is rejected as incomparable. Report includes median, interpolated type-7 P95, mean, sample SD, CV, min/max, matched counts, and P95 latency or median allocation endpoint. Delta = (candidate - baseline)/baseline * 100; >5% is REGRESSION, <-5% is IMPROVEMENT_CANDIDATE (not verified superiority). Zero baseline prevents relative calculation. Reports always use claim_allowed=false. Five independent pairs is a pilot minimum, NOT a power analysis. CV above 20% calls for more repetitions. Lack of real trace/device verification remains explicit.

## Reproduction

    python3 -m compileall -q runtime
    python3 -m unittest discover -s runtime/tests -v
    python3 runtime/analyze.py runtime/fixtures/synthetic_pairs.json
    python3 runtime/analyze.py runtime/fixtures/synthetic_pairs.json --fail-on-regression

The last command is an intentional synthetic regression negative control: expected exit code 3. Malformed or inconsistent data returns exit 2. See native/README.md for C++17 compilation and host run instructions.

## Finite plan and criteria

1. Repository: inspect main, planning, dependencies and existing P0-015. Complete on live branch/PR evidence.
2. Upstream: inspect official ART/JNI sources/docs and record verified vs provisional pins. Complete on source provenance.
3. Analyzer: implement strict Python JSON/CSV reader, stats and regression reporting. Complete on tests.
4. Microbenchmark: compile C++17 with observable workload and feed into analyzer. Complete on actual host execution.
5. Testing: synthetic valid, malformed, incompatible context, missing and unpaired observations. Complete on recorded exit codes.
6. Optimization: register hypotheses with experiments, ABI/security gates and rollback conditions.
7. GitHub: publish task branch, draft PR, exact commit/readback, CI status. Merge/acceptance is independent.

## Reversible optimization hypotheses (not proven bottlenecks)

| Component | Evidence and hypothesis | Required experiment | Compatibility, security and rollback |
|---|---|---|---|
| ART JNI, runtime/jni/jni_internal.cc | HYPOTHESIS: repeated small JNI copies may cost time; JNI semantics documented, hotspot unmeasured | JNI Java/native test app: safe copies vs safe scoped buffers, matched P95 and allocation profile | CheckJNI, references, pinning and exceptions must pass; revert on any semantic mismatch, >5% P95 regression or memory issue |
| ART GC, runtime/gc/heap.cc | SOURCE OBSERVATION: upstream source documents heap trimming lock/jank concern; not measured on Slickk | Perfetto GC pauses, memory, frame timeline under fixed pressure on emulator, matched policy | No OOM, ANR, memory or power regression. Revert on failures or >5% matched P95 |
| ART JIT, runtime/jit/jit.cc | HYPOTHESIS: compilation scheduling balances startup, runtime CPU and storage | Identical cold/warm workloads under controlled AOT/JIT settings; track dexopt CPU and cache | Preserve DEX/ABI, patch/update security; revert on app compatibility, energy, startup or storage loss |
| ART linking, runtime/class_linker.cc | HYPOTHESIS: class-link/init costs dominate some startup | Stage-level class loading measurements, cold/warm pairs and correct class resolution | Preserve verifier and resolution order; rollback for semantic or startup regression |
| Native copy, native/hotpath.cpp | HOST CONTROL ONLY: no confirmed Android inefficiency | Paired copy+checksum on matched host CPU sizes and toolchains; use external allocation profiling | Preserve output identity and safe aliasing; sanitizer/ABI tests; revert on integrity failures or regression |
| JNI thread attachment, runtime/thread.cc | HYPOTHESIS: avoidable repeated attachment in app native callbacks | App test with fixed threads, attachment counts and callback P95 | JNIEnv thread ownership, reference lifecycle and exception handling must pass; rollback on leak/deadlock/crash |

No runtime code or firmware was changed. Proposed patches require matched measurements, CTS/CheckJNI/ABI gates, security review and revert plan before release.
