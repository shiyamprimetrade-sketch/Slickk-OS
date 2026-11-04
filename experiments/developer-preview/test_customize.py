import json
from pathlib import Path
import tempfile
import unittest
from customize import customize


class Contracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for directory in ('META', 'PRODUCT/etc', 'IMAGES'):
            (self.root / directory).mkdir(parents=True)
        (self.root / 'META/misc_info.txt').write_text('avb_enable=true\navb_product_hashtree_enable=true\nproduct_fs_type=erofs\navb_vbmeta_system=product system system_ext\n')
        (self.root / 'META/product_filesystem_config.txt').write_text('product 0 0 755 capabilities=0x0\n')
        for name in ('product.img', 'vbmeta_system.img', 'vbmeta.img', 'system.img'):
            (self.root / 'IMAGES' / name).write_bytes(b'original')
        self.apk = self.root / 'fixture.apk'
        self.apk.write_bytes(b'unit-test-only')

    def test_minimal_partition_change(self):
        result = customize(self.root, self.apk, 'test-revision')
        self.assertEqual(json.loads((self.root / 'PRODUCT/etc/slickk-os.json').read_text()), result)
        self.assertEqual((self.root / 'PRODUCT/app/SlickkHome/SlickkHome.apk').read_bytes(), self.apk.read_bytes())
        self.assertFalse((self.root / 'IMAGES/product.img').exists())
        self.assertFalse((self.root / 'IMAGES/vbmeta_system.img').exists())
        self.assertEqual((self.root / 'IMAGES/vbmeta.img').read_bytes(), b'original')
        self.assertEqual((self.root / 'IMAGES/system.img').read_bytes(), b'original')

    def test_disabled_avb_rejected_before_mutation(self):
        p = self.root / 'META/misc_info.txt'
        p.write_text(p.read_text().replace('avb_enable=true', 'avb_enable=false'))
        with self.assertRaises(ValueError):
            customize(self.root, self.apk, 'test')
        self.assertTrue((self.root / 'IMAGES/product.img').exists())

    def test_empty_apk_rejected(self):
        self.apk.write_bytes(b'')
        with self.assertRaises(ValueError):
            customize(self.root, self.apk, 'test')

    def test_existing_customization_not_overwritten(self):
        customize(self.root, self.apk, 'test')
        with self.assertRaises(ValueError):
            customize(self.root, self.apk, 'test')
