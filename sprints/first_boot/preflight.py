#!/usr/bin/env python3
"""Read-only AOSP Linux build-host readiness report; not a boot test."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys

GIB = 1024 ** 3
COMMANDS = ('bash', 'curl', 'git', 'python3', 'repo')


def memory_total(path='/proc/meminfo'):
    try:
        for line in Path(path).read_text().splitlines():
            if line.startswith('MemTotal:'):
                fields = line.split()
                if len(fields) == 3 and fields[2] == 'kB':
                    return int(fields[1]) * 1024
    except (OSError, ValueError):
        return None
    return None


def assess(path, *, system=None, machine=None, memory=None, disk=None,
           commands=None, kvm=None):
    system = platform.system() if system is None else system
    machine = platform.machine() if machine is None else machine
    memory = memory_total() if memory is None else memory
    if disk is None:
        try:
            disk = shutil.disk_usage(path).free
        except OSError:
            pass
    if commands is None:
        commands = {c: shutil.which(c) is not None for c in COMMANDS}
    if kvm is None:
        kvm = os.path.exists('/dev/kvm') and os.access('/dev/kvm', os.R_OK | os.W_OK)
    checks = {
        'linux': system == 'Linux',
        'x86_64': machine in ('x86_64', 'amd64'),
        'ram_64_gib': memory is not None and memory >= 64 * GIB,
        'disk_400_gib': disk is not None and disk >= 400 * GIB,
    }
    checks.update({'tool_' + c: bool(commands.get(c)) for c in COMMANDS})
    ready = all(checks.values())
    return {
        'status': 'READ_ONLY_PREFLIGHT_NOT_OS_BUILD',
        'source': 'Google AOSP host requirements',
        'checks': checks,
        'build_ready': ready,
        'kvm_accessible': bool(kvm),
        'cuttlefish_boot_ready': ready and bool(kvm),
        'ram_gib': None if memory is None else round(memory / GIB, 2),
        'free_disk_gib': None if disk is None else round(disk / GIB, 2),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', default='.')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args(argv)
    path = Path(args.directory)
    if not path.is_dir():
        parser.error('Existing build-volume directory required')
    result = assess(path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if args.strict and not result['build_ready'] else 0


if __name__ == '__main__':
    sys.exit(main())
