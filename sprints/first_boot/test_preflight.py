import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preflight

GIB = preflight.GIB
TOOLS = {tool: True for tool in preflight.COMMANDS + preflight.RUNTIME_COMMANDS}


class TestPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.images = Path(self.tmp.name)
        for name in ('boot.img', 'super.img'):
            (self.images / name).write_bytes(b'fixture-not-a-real-image')

    def probe(self, **changes):
        args = dict(system='Linux', machine='x86_64', memory=64 * GIB,
                    disk=400 * GIB, commands=TOOLS, kvm=True,
                    image_directory=self.images)
        args.update(changes)
        return preflight.assess(Path('.'), **args)

    def test_ready_is_not_boot_proof(self):
        r = self.probe()
        self.assertTrue(r['build_ready'])
        self.assertTrue(r['cuttlefish_boot_ready'])
        self.assertFalse(r['boot_verified'])
        self.assertTrue(r['remaining_boot_gates'])

    def test_disk(self):
        self.assertFalse(self.probe(disk=399 * GIB)['build_ready'])

    def test_ram(self):
        self.assertFalse(self.probe(memory=63 * GIB)['build_ready'])

    def test_os_and_arch(self):
        self.assertFalse(self.probe(system='Windows')['build_ready'])
        self.assertFalse(self.probe(machine='aarch64')['build_ready'])

    def test_missing_repo_only_blocks_build(self):
        r = self.probe(commands={**TOOLS, 'repo': False})
        self.assertFalse(r['build_ready'])
        self.assertTrue(r['prebuilt_runtime_prerequisites_ready'])

    def test_kvm_not_build_requirement(self):
        r = self.probe(kvm=False)
        self.assertTrue(r['build_ready'])
        self.assertFalse(r['cuttlefish_boot_ready'])

    def test_bad_meminfo(self):
        file = self.images / 'meminfo'
        file.write_text('MemTotal: 67108864 kB\n')
        self.assertEqual(preflight.memory_total(file), 64 * GIB)
        file.write_text('MemTotal: unknown kB\n')
        self.assertIsNone(preflight.memory_total(file))

    def test_effective_cgroup_cap(self):
        r = self.probe(memory=128 * GIB, memory_limit=8 * GIB)
        self.assertFalse(r['build_ready'])
        self.assertEqual(r['ram_gib'], 8)
        self.assertEqual(r['host_ram_gib'], 128)

    def test_low_resource_host_may_pass_prebuilt_prerequisites(self):
        r = self.probe(memory=8 * GIB, disk=30 * GIB)
        self.assertFalse(r['build_ready'])
        self.assertTrue(r['prebuilt_runtime_prerequisites_ready'])
        self.assertFalse(r['boot_verified'])

    def test_missing_runtime_tools(self):
        for tool in preflight.RUNTIME_COMMANDS:
            r = self.probe(commands={**TOOLS, tool: False})
            self.assertFalse(r['prebuilt_runtime_prerequisites_ready'])
            self.assertTrue(r['build_ready'])

    def test_no_supplied_images(self):
        self.assertFalse(self.probe(image_directory=None)['cuttlefish_boot_ready'])

    def test_empty_or_partial_images(self):
        (self.images / 'super.img').write_bytes(b'')
        self.assertFalse(self.probe()['cuttlefish_boot_ready'])
        (self.images / 'system.img').write_bytes(b'system-fixture')
        self.assertFalse(self.probe()['cuttlefish_boot_ready'])
        (self.images / 'vendor.img').write_bytes(b'vendor-fixture')
        self.assertTrue(self.probe()['cuttlefish_boot_ready'])

    def test_cgroup_minimum_visible_ancestor(self):
        (self.images / 'memory.max').write_text(str(16 * GIB))
        child = self.images / 'child'
        child.mkdir()
        (child / 'memory.max').write_text(str(8 * GIB))
        membership = self.images / 'membership'
        membership.write_text('0::/child\n')
        self.assertEqual(preflight.cgroup_memory_limit(self.images, membership), 8 * GIB)

    def test_cgroup_unlimited_and_v1(self):
        (self.images / 'memory.max').write_text('max')
        membership = self.images / 'membership'
        membership.write_text('5:memory:/\n')
        memory = self.images / 'memory'
        memory.mkdir()
        (memory / 'memory.limit_in_bytes').write_text(str(4 * GIB))
        self.assertEqual(preflight.cgroup_memory_limit(self.images, membership), 4 * GIB)
        (memory / 'memory.limit_in_bytes').write_text(str(2 ** 63 - 4096))
        self.assertIsNone(preflight.cgroup_memory_limit(self.images, membership))

    @mock.patch('preflight.os.open', side_effect=PermissionError('denied'))
    def test_kvm_denied(self, opened):
        self.assertFalse(preflight.probe_kvm()['accessible'])

    @mock.patch('preflight.os.close')
    @mock.patch('preflight.fcntl.ioctl', return_value=12)
    @mock.patch('preflight.os.open', return_value=51)
    def test_kvm_api_probe(self, opened, ioctl, closed):
        self.assertTrue(preflight.probe_kvm()['accessible'])
        ioctl.assert_called_once_with(51, preflight.KVM_GET_API_VERSION, 0)
        closed.assert_called_once_with(51)

    @mock.patch('preflight.os.close')
    @mock.patch('preflight.fcntl.ioctl', return_value=11)
    @mock.patch('preflight.os.open', return_value=51)
    def test_wrong_kvm_api(self, opened, ioctl, closed):
        self.assertFalse(preflight.probe_kvm()['accessible'])
        closed.assert_called_once_with(51)


class TestBuildEvidence(unittest.TestCase):
    def test_hashes_selected_product_only(self):
        import hashlib, json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product = root / 'product'; product.mkdir()
            for name in ('boot.img', 'super.img'):
                (product / name).write_bytes(b'fixture')
            (root / 'unrelated.img').write_bytes(b'other')
            rows = preflight.capture_images(product, root / 'evidence')
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['sha256'], hashlib.sha256(b'fixture').hexdigest())
            self.assertFalse(json.loads((root / 'evidence/images.json').read_text())['boot_verified'])

    def test_partial_empty_and_symlink_images_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'boot.img').write_bytes(b'fixture')
            with self.assertRaises(ValueError):
                preflight.capture_images(root, root / 'evidence')
            (root / 'super.img').write_bytes(b'fixture')
            (root / 'vendor.img').touch()
            with self.assertRaises(ValueError):
                preflight.capture_images(root, root / 'evidence')
            (root / 'vendor.img').unlink()
            (root / 'vendor.img').symlink_to(root / 'boot.img')
            with self.assertRaises(ValueError):
                preflight.capture_images(root, root / 'evidence')
            self.assertFalse((root / 'evidence/images.json').exists())

    def test_manifest_requires_resolved_unique_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'manifest.xml'
            project = '<project name="platform/a" revision="' + 'a' * 40 + '"/>'
            path.write_text('<manifest>' + project + '</manifest>')
            self.assertEqual(preflight.validate_locked_manifest(path), 1)
            for xml in ('<manifest/>', '<manifest>' + project * 2 + '</manifest>',
                        '<manifest><project name="a" revision="main"/></manifest>'):
                path.write_text(xml)
                with self.assertRaises(ValueError):
                    preflight.validate_locked_manifest(path)

if __name__ == '__main__':
    unittest.main()
