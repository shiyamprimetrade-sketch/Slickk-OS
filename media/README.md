# P0-017 — Graphics, audio and video benchmarking laboratory

**Implementation status:** Python 3 standard-library session-level validator and comparison engine. All bundled observations are **SYNTHETIC**, not phone measurements. No Android image, media codecs, HALs, network services, GPU or speaker have been modified.

## Contract and execution

From repository root:

```sh
python3 -m unittest discover -s media/tests -p 'test_*.py' -v
python3 media/tools/bench.py media/fixtures/synthetic_pairs.json
python3 media/tools/bench.py media/fixtures/synthetic_pairs.json --output /tmp/p017-report.json
python3 -m compileall -q media/tools media/tests
```

JSON root is `{"schema_version":"P0-017/1.0","observations":[...]}`. The fixture contains five *synthetic*, session-level pairs with intentionally different fabricated values; reported improvement is a numerical test of analyzer logic, **never device evidence**. Use `media/metrics.json` as the mandatory metric registry. Each metric has exact units, benefit direction, analysis aggregate, and minimum independent paired runs. Extending the catalog requires separate test coverage.

Records use the P0-007 provisional names: `variant` (`android`, `slickk-os`), `dataset_kind` (`synthetic`, `host`, `device`), `workload`, `metric`, `unit`, `value`, `iteration`, `session_id`, UTC timestamp, `evidence_ref`, `device_id` pseudonym, `device_model`, `device_type`, `os_build`, `app_version`, `test_version`, `network`, `brightness_pct`, `refresh_hz`, `start_temp_c`, `battery_soc_pct`, `profile_id`, `exposure_s`. P0-017 adds `sample_id`, artifact SHA-256, capture instrument, upstream source revision, AB/BA within-pair order (1 or 2), warmup runs, nonempty typed `conditions` (codec, resolution, bitrate, fixture, route, endpoint ID, sample rate, etc.), and explicit validity/error. A synthetic reference MUST begin `synthetic:`. A claimed device/host capture must carry a lowercase 64-digit SHA-256 and an evidence reference; these fields are **self-reported, not authenticated**.

`device` provenance is not proof of real hardware; `host` cannot be used to claim phone measurements. Do not insert per-frame or per-packet samples as if independent sessions: aggregate data **within each session**, then compare at least five independent pairs per metric. Include actual raw evidence off-repo, its digest, capture version, workload script and source/build revisions. The compare tool does not ingest Perfetto traces or PCAPs or verify whether a referenced artifact exists. Avoid raw personal identifiers. CSV is not implemented; JSON only.

**Invalid or incomparable inputs exit 2**, never create a comparison. Complete valid input exits 0; `--fail-on-regression` exits 3 when a regression is detected. Output includes sample n, P50 (median), linearly interpolated P95 (type 7), sample standard deviation, CV, percentage direction, and explicit status. `claim_allowed` is always false; improvements are only `IMPROVEMENT_CANDIDATE`, and non-inferiority and significance are NOT certified. For zero baseline no relative percentage is claimed. Default regression threshold is >5% deterioration, with any deterioration in count or percent metrics treated as regression on the selected aggregate. 5 repeats are a *pilot floor*, not a statistical power guarantee. P0-007 PR #5 remains a draft; final schema reconciliation pending.

## Capture matrix: scripted physical-device tests, not yet executed

| Subsystem and workload | Recorded session-level metric | Instrument; requirement / caveat |
|---|---|---|
| Graphics — fixed 60-second launcher scroll at 60 Hz and separately at 90/120 Hz if supported | `frame_time_ms` P95, `frame_jank_pct`, `frame_drop_pct`, `render_latency_ms` | Perfetto FrameTimeline Android 12+ (`android.surfaceflinger.frametimeline`); actual present/deadline/jank classifications, separate CPU vs compositor; raw trace + config; available refresh rates vary |
| Graphics — compositing with 1/4/8 layers, repeated fixed animations | same metrics plus optional energy `energy_mwh` | FrameTimeline + SurfaceFlinger composition + verified power rail measurements; tests must hold display mode/brightness/thermal constant |
| Video — fixed permission-cleared AVC/HEVC/AV1 files, resolution/bitrate/format/color/DRM mode separately pinned | `video_decode_fps`, `video_drop_pct`, `video_first_frame_ms`, `av_sync_error_ms` | MediaCodec/MediaPlayer counters and frame timestamps, display trace, wall-clock; codecs supported differ by device |
| Video — fixed encoder input with source/checksum and bitrate profile | `video_encode_fps`, `video_psnr_db`, `energy_mwh` | MediaCodec output plus reference quality tool/PSNR and verified energy; quality vs speed must be reported together |
| Audio — fixed PCM/encoded playback with precise output route (wired, speaker, BT separately) | `audio_latency_ms`, `audio_underrun_count`, `audio_dropout_pct` | AudioTrack/AudioFlinger stats; loopback calibrated hardware for acoustic latency; Bluetooth latency/codec/route pinned |
| Audio — simultaneous playback/record/notifications | same metrics and optional `energy_mwh` | AudioRecord / HAL trace; consent and microphone permissions required; preserve user audio privacy |

Source boundaries: apps use Android SDK `Choreographer`, FrameMetrics, MediaCodec, AudioTrack and AudioRecord where allowed. SurfaceFlinger, RenderThread/HWUI, Codec2 and AudioFlinger can require privileged tracing, system build access or vendor HAL evidence. An ordinary APK cannot replace SurfaceFlinger/HWC or request protected buffers. Metrics gathered with restricted tools must be labeled as such, not promised for every device.

## Architecture and inspected upstream references

- **SurfaceFlinger / BufferQueue / HWC:** https://source.android.com/docs/core/graphics/architecture and https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager . App HWUI/RenderThread produces buffers; SurfaceFlinger composites, with HWC device-composition as possible offload. VSync, scheduler deadlines, GPU fences and gralloc affect jank, input latency and power. **Verified inspected source listing, moving `main`:** https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/services/surfaceflinger/ (listed tree `0452dbf98aab6372eb1b44f6a6f1b2b4830fd41e` when consulted); not a pinned Android release. FrameTimeline: https://perfetto.dev/docs/data-sources/frametimeline .
- **AudioFlinger / FAST mixer / AudioTrack / AudioRecord / HAL:** https://source.android.com/docs/core/audio/latency/design and https://source.android.com/docs/core/audio/terminology . **Inspected `main` directory listing:** https://android.googlesource.com/platform/frameworks/av/+/refs/heads/main/services/audioflinger/ (`931d1904290fe8b0c69e320044a585e77e9a3f4a` at inspection). Audio output route, buffer policy and scheduling affect underruns; latency optimizations are hypotheses until loopback measurements.
- **MediaCodec / Codec2:** https://developer.android.com/reference/android/media/MediaCodec and https://developer.android.com/reference/android/media/MediaPlayer.MetricsConstants . Available metrics include codec instance and playback-frame counts; capability support and metrics are API/device dependent. No codec implementation or hardware acceleration was tested here.

## No-regression gates and rollback

1. **Visual/UX:** no clipping, flicker, input lag, hidden accessibility controls or increased reproducible jank; test screen reader, animations, scaling, refresh modes.
2. **Audio/video:** no audio dropouts, desynchronization, codec incompatibility, damaged colors, reduced PSNR/VMAF at matched quality, DRM/protected playback regression or camera/recording failure.
3. **Compatibility:** pinned priority apps and SDK/JNI/Binder behavior pass, relevant CTS/VTS run if/when a platform image exists; do not claim passing without running.
4. **Energy/thermal:** same device, battery/charging condition, background activity, environment; block clear sustained drain or throttling regressions.
5. **Security/privacy:** no unintended permission changes, microphone/camera capture, raw identifiers, packet payload logging or bypasses to protected surfaces.
6. **Stability:** crash/ANR, system_server, codec processes and display restarts cannot worsen; retain evidence for slow cases.

If any critical correctness/security/accessibility failure occurs, **disable the experimental flag/revert patch**, restore baseline and repeat the affected tests. A performance uplift alone never overrides critical no-regression gates. This P0 task adds tooling only; rollback is closing the draft PR or reverting its isolated commit.

## Testable research hypotheses (NOT conclusions)

- SurfaceFlinger jank correlated with GPU/client composition may be reduced by workload-specific composition hints; test CPU/GPU composition and total energy **without violating HWC/vendor contracts**.
- Audio mixer scheduling or buffer strategy may reduce underruns for a fixed supported output route; test both end-to-end latency and distortion/energy.
- Hardware video codec paths may reduce CPU consumption but affect format support, quality and power; perform supported-hardware vs fallback A/B under matched visual quality rather than assuming an outcome.
