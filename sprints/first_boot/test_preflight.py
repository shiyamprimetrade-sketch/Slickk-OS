import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight

GIB = preflight.GIB
TOOLS = {tool: True for tool in preflight.COMMANDS}


class TestPreflight(unittest.TestCase):
    def probe(self, **changes):
        args = dict(system='Linux', machine='x86_64', memory=64 * GIB,
                    disk=400 * GIB, commands=TOOLS, kvm=True)
        args.update(changes)
        return preflight.assess(Path('.'), **args)

    def test_ready(self):
        r = self.probe()
        self.assertTrue(r['build_ready'])
        self.assertTrue(r['cuttlefish_boot_ready'])

    def test_disk(self):
        self.assertFalse(self.probe(disk=399 * GIB)['build_ready'])

    def test_ram(self):
        self.assertFalse(self.probe(memory=63 * GIB)['build_ready'])

    def test_os_and_arch(self):
        self.assertFalse(self.probe(system='Windows')['build_ready'])
        self.assertFalse(self.probe(machine='aarch64')['build_ready'])

    def test_missing_repo(self):
        self.assertFalse(self.probe(commands={**TOOLS, 'repo': False})['build_ready'])

    def test_kvm_not_build_requirement(self):
        r = self.probe(kvm=False)
        self.assertTrue(r['build_ready'])
        self.assertFalse(r['cuttlefish_boot_ready'])

    def test_bad_meminfo(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            file = Path(directory) / 'meminfo'
            file.write_text('MemTotal: 67108864 kB\n')
            self.assertEqual(preflight.memory_total(file), 64 * GIB)
            file.write_text('MemTotal: unknown kB\n')
            self.assertIsNone(preflight.memory_total(file))
