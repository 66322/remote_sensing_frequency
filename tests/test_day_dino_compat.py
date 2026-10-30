import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import day_dino_compat as compat


class DinoCompatibilityTests(unittest.TestCase):
    def test_local_mirror_is_audited_and_original_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            original=root/'original'
            original.mkdir()
            source='def function(value: float | None = None):\n    return value\n'
            (original/'hubconf.py').write_text(source,encoding='utf-8')
            old=compat.MIRROR
            compat.MIRROR=root/'mirror'
            try:
                mirror,sha=compat.compatible_repo(original,force_py39=True)
                self.assertEqual(mirror,compat.MIRROR)
                self.assertEqual((original/'hubconf.py').read_text(encoding='utf-8'),source)
                self.assertTrue((mirror/'hubconf.py').read_text(encoding='utf-8').startswith(
                    'from __future__ import annotations\n'))
                self.assertEqual(sha,compat.compatible_repo(original,force_py39=True)[1])
                (mirror/'hubconf.py').write_text('modified',encoding='utf-8')
                with self.assertRaises(RuntimeError):
                    compat.compatible_repo(original,force_py39=True)
            finally:
                compat.MIRROR=old


if __name__=='__main__':
    unittest.main()
