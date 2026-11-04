#!/usr/bin/env python3
"""Read-only AOSP host/prerequisite audit. Never launches a VM or proves boot."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import re
import xml.etree.ElementTree as ET

GIB = 1024 ** 3
COMMANDS = ('bash', 'curl', 'git', 'python3', 'repo')
RUNTIME_COMMANDS = ('adb', 'launch_cvd')
KVM_GET_API_VERSION = 0xAE00
KVM_API_VERSION = 12


def memory_total(path='/proc/meminfo'):
    try:
        for line in Path(path).read_text().splitlines():
            fields = line.split()
            if fields and fields[0] == 'MemTotal:' and len(fields) == 3 and fields[2] == 'kB':
                return int(fields[1]) * 1024
    except (OSError, ValueError):
        return None
    return None


def cgroup_memory_limit(root='/sys/fs/cgroup', membership='/proc/self/cgroup'):
    """Read visible v1/v2 current-cgroup and ancestor limits, never modify them."""
    root = Path(root)
    locations = {root, root / 'memory'}
    try:
        for line in Path(membership).read_text().splitlines():
            _, controllers, relative = line.split(':', 2)
            if controllers and 'memory' not in controllers.split(','):
                continue
            relative = Path(relative.lstrip('/'))
            if '..' in relative.parts:
                continue
            base = root if not controllers else root / 'memory'
            current = base / relative
            while current == base or base in current.parents:
                locations.add(current)
                if current == base:
                    break
                current = current.parent
    except (OSError, ValueError):
        pass
    limits = []
    for location in locations:
        for name in ('memory.max', 'memory.limit_in_bytes'):
            try:
                value = int((location / name).read_text().strip())
                if 0 < value < 2 ** 60:  # Ignore v1 unlimited sentinels.
                    limits.append(value)
            except (OSError, ValueError):
                pass
    return min(limits) if limits else None


def probe_kvm(path='/dev/kvm'):
    result = {'accessible': False, 'api_version': None, 'error': None}
    try:
        fd = os.open(path, os.O_RDWR | os.O_CLOEXEC)
        try:
            result['api_version'] = fcntl.ioctl(fd, KVM_GET_API_VERSION, 0)
            result['accessible'] = result['api_version'] == KVM_API_VERSION
            if not result['accessible']:
                result['error'] = 'Unexpected KVM API version'
        finally:
            os.close(fd)
    except OSError as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    return result


def image_evidence(directory):
    """Recognize a minimal nonempty image payload, not a complete/versioned build."""
    if directory is None:
        return {'directory': None, 'present': False, 'files': []}
    directory = Path(directory)
    files = []
    for name in ('boot.img', 'super.img', 'system.img', 'vendor.img'):
        path = directory / name
        try:
            if path.is_file() and path.stat().st_size > 0:
                with path.open('rb') as stream:
                    if stream.read(1):
                        files.append(name)
        except OSError:
            pass
    present = ('boot.img' in files and
               ('super.img' in files or {'system.img', 'vendor.img'} <= set(files)))
    return {'directory': str(directory), 'present': present, 'files': files}


def assess(path, *, system=None, machine=None, memory=None, disk=None,
           commands=None, kvm=None, memory_limit=None, image_directory=None):
    system = platform.system() if system is None else system
    machine = platform.machine() if machine is None else machine
    # Explicit memory injection is for unit fixtures; never mix them with host caps.
    if memory is None:
        memory = memory_total()
        if memory_limit is None:
            memory_limit = cgroup_memory_limit()
    available_caps = [x for x in (memory, memory_limit) if x is not None]
    effective_memory = min(available_caps) if available_caps else None
    if disk is None:
        try:
            disk = shutil.disk_usage(path).free
        except OSError:
            pass
    if commands is None:
        commands = {c: shutil.which(c) is not None for c in COMMANDS + RUNTIME_COMMANDS}
    kvm_result = (probe_kvm() if kvm is None else
                  {'accessible': bool(kvm), 'api_version': None,
                   'error': None, 'injected_test_value': True})
    images = image_evidence(image_directory)
    checks = {
        'linux': system == 'Linux',
        'x86_64': machine in ('x86_64', 'amd64'),
        'ram_64_gib': effective_memory is not None and effective_memory >= 64 * GIB,
        'disk_400_gib': disk is not None and disk >= 400 * GIB,
    }
    checks.update({'tool_' + c: bool(commands.get(c)) for c in COMMANDS})
    prebuilt_checks = {
        'linux': checks['linux'], 'x86_64': checks['x86_64'],
        'kvm_api_usable': kvm_result['accessible'],
        'tool_adb': bool(commands.get('adb')),
        'tool_launch_cvd': bool(commands.get('launch_cvd')),
        'supplied_image_payload': images['present'],
    }
    prebuilt_ready = all(prebuilt_checks.values())
    gib = lambda value: None if value is None else round(value / GIB, 2)
    return {
        'status': 'READ_ONLY_PREFLIGHT_NOT_OS_BUILD_OR_BOOT',
        'source': 'Google AOSP source-build policy plus local runtime prerequisite checks',
        'checks': checks, 'build_ready': all(checks.values()),
        'prebuilt_checks': prebuilt_checks,
        'prebuilt_runtime_prerequisites_ready': prebuilt_ready,
        'kvm_accessible': kvm_result['accessible'], 'kvm_probe': kvm_result,
        # Legacy alias, now means prerequisites only; never verified boot.
        'cuttlefish_boot_ready': prebuilt_ready, 'boot_verified': False,
        'ram_gib': gib(effective_memory), 'host_ram_gib': gib(memory),
        'cgroup_limit_gib': gib(memory_limit), 'free_disk_gib': gib(disk),
        'image_evidence': images,
        'remaining_boot_gates': [
            'Host package and images must come from the same verified official build',
            'Complete target image set, host dependencies and image-specific resources unverified',
            'Actual launch, adb connection, boot_completed=1, fingerprint, logs and hashes required',
        ],
    }


def validate_locked_manifest(path):
    root = ET.parse(path).getroot()
    projects = root.findall('project')
    if root.tag != 'manifest' or not projects:
        raise ValueError('Empty or invalid locked manifest')
    paths = set()
    for project in projects:
        name = project.get('path') or project.get('name')
        if not name or name in paths or not re.fullmatch(r'[0-9a-f]{40}', project.get('revision', '')):
            raise ValueError('Manifest contains unresolved/duplicate project: ' + str(name))
        paths.add(name)
    return len(projects)


def capture_images(directory, evidence):
    directory = Path(directory).resolve()
    evidence = Path(evidence)
    if not image_evidence(directory)['present']:
        raise ValueError('Missing nonempty boot and system payload in selected PRODUCT_OUT')
    rows = []
    for path in sorted(directory.glob('*.img')):
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError('Invalid/empty/symlink image: ' + path.name)
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        rows.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest})
    if not rows:
        raise ValueError('No images to hash')
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'image-sha256.txt').write_text(''.join(r['sha256'] + '  ' + r['path'] + '\n' for r in rows))
    (evidence / 'images.json').write_text(json.dumps({'images': rows, 'boot_verified': False}, indent=2) + '\n')
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', default='.')
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--mode', choices=('build', 'prebuilt'), default='build')
    parser.add_argument('--image-directory')
    parser.add_argument('--capture-images')
    parser.add_argument('--evidence-directory')
    parser.add_argument('--validate-manifest')
    args = parser.parse_args(argv)
    if args.capture_images or args.validate_manifest:
        try:
            if args.validate_manifest:
                print(json.dumps({'locked_projects': validate_locked_manifest(args.validate_manifest)}))
            if args.capture_images:
                if not args.evidence_directory:
                    raise ValueError('--evidence-directory required')
                print(json.dumps({'hashed_images': len(capture_images(args.capture_images, args.evidence_directory)), 'boot_verified': False}))
            return 0
        except (OSError, ValueError, ET.ParseError) as exc:
            print('FAIL: ' + str(exc), file=sys.stderr)
            return 3
    path = Path(args.directory)
    if not path.is_dir():
        parser.error('Existing build-volume directory required')
    result = assess(path, image_directory=args.image_directory)
    print(json.dumps(result, indent=2, sort_keys=True))
    ready = result['build_ready'] if args.mode == 'build' else result['prebuilt_runtime_prerequisites_ready']
    return 2 if args.strict and not ready else 0


if __name__ == '__main__':
    sys.exit(main())
