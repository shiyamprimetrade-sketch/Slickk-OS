"""Stage minimal product additions in an extracted, pinned target-files tree."""
import hashlib
import json
from pathlib import Path
import shutil
import sys


def customize(root, apk, revision):
    root, apk = Path(root), Path(apk)
    meta = root / 'META/misc_info.txt'
    values = dict(line.split('=', 1) for line in meta.read_text().splitlines() if '=' in line)
    required = {'avb_enable': 'true', 'avb_product_hashtree_enable': 'true',
                'product_fs_type': 'erofs', 'avb_vbmeta_system': 'product system system_ext'}
    for key, value in required.items():
        if values.get(key) != value:
            raise ValueError('Unsupported target metadata: ' + key)
    if not apk.is_file() or apk.stat().st_size == 0:
        raise ValueError('Missing APK')
    product = root / 'PRODUCT'
    for relative in ('app/SlickkHome', 'etc/slickk-os.json'):
        if (product / relative).exists():
            raise ValueError('Refusing to overwrite customization')
    target = product / 'app/SlickkHome/SlickkHome.apk'
    target.parent.mkdir(parents=True)
    shutil.copyfile(apk, target)
    identity = {'name': 'Slickk-OS Developer Preview 0.1', 'upstream_build': '16644040',
                'source_revision': revision, 'signing': 'PUBLIC_DEVELOPMENT_TEST_KEYS',
                'apk_sha256': hashlib.sha256(apk.read_bytes()).hexdigest()}
    (product / 'etc/slickk-os.json').write_text(json.dumps(identity, sort_keys=True, indent=2) + '\n')
    config = root / 'META/product_filesystem_config.txt'
    with config.open('a') as stream:
        for path, mode in [('product/app/SlickkHome', '755'),
                           ('product/app/SlickkHome/SlickkHome.apk', '644'),
                           ('product/etc/slickk-os.json', '644')]:
            stream.write(f'{path} 0 0 {mode} capabilities=0x0\n')
    # Only these dependent images are invalidated. Top-level vbmeta retains its chain key.
    for name in ('product.img', 'vbmeta_system.img'):
        (root / 'IMAGES' / name).unlink()
    return identity


if __name__ == '__main__':
    print(json.dumps(customize(*sys.argv[1:]), indent=2))
