import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('publisher', ROOT / 'scripts/publicar_edicao.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'assets').mkdir()
        (self.root / 'assets/logo-data.txt').write_text((ROOT / 'assets/logo-data.txt').read_text())
        self.data = json.loads((ROOT / 'edicoes/2026-11-05-1100-extra.json').read_text())
    def tearDown(self):
        self.tmp.cleanup()
    def test_roundtrip_and_hashes(self):
        m = p.build(self.data, self.root)
        p.build(self.data, self.root, check=True)
        self.assertEqual(p.digest((self.root/'index.html').read_text()), m['html_sha256'])
        self.assertEqual((self.root/'index.html').read_text(), (self.root/m['html_path']).read_text())
        md = (self.root/m['markdown_path']).read_text()
        for section in self.data['sections']:
            for story in section['stories']:
                for key in ['headline','summary','source','url']:
                    self.assertIn(story[key], md)
    def test_repeated_execution_is_idempotent(self):
        self.assertEqual(p.build(self.data,self.root), p.build(self.data,self.root))
    def test_cannot_overwrite_archive(self):
        p.build(self.data,self.root)
        self.data['sections'][0]['stories'][0]['summary'] += ' Outra versão.'
        with self.assertRaisesRegex(ValueError,'imutável'):
            p.build(self.data,self.root)
    def test_extra_preserves_both_same_day(self):
        old = p.build(self.data,self.root)
        self.data.update(id='2026-11-05-1130-extra', cutoff='2026-11-05T11:30:00-03:00')
        new = p.build(self.data,self.root)
        self.assertTrue((self.root/old['html_path']).exists())
        self.assertTrue((self.root/new['html_path']).exists())
        self.assertIn(old['html_path'].split('/')[-1], (self.root/'arquivo/index.html').read_text())
    def test_cannot_rewind_latest(self):
        old = copy.deepcopy(self.data)
        self.data.update(id='2026-11-05-1130-extra',cutoff='2026-11-05T11:30:00-03:00')
        p.build(self.data,self.root)
        with self.assertRaisesRegex(ValueError,'mais antiga'):
            p.build(old,self.root)
    def test_escape_untrusted_html(self):
        self.data['sections'][0]['stories'][0]['headline']='<script>alert(1)</script>'
        p.build(self.data,self.root)
        self.assertIn('&lt;script&gt;', (self.root/'index.html').read_text())
        self.assertNotIn('<script>alert', (self.root/'index.html').read_text())
    def test_reject_bad_urls(self):
        for url in ['javascript:alert(1)','http://example.com','https://name:secret@example.com']:
            self.data['sections'][0]['stories'][0]['url']=url
            with self.assertRaises(ValueError): p.validate(self.data)
    def test_reject_wrong_date_or_timezone(self):
        self.data['cutoff']='2026-11-04T11:00:00-03:00'
        with self.assertRaises(ValueError): p.validate(self.data)
        self.data['cutoff']='2026-11-05T11:00:00'
        with self.assertRaises(ValueError): p.validate(self.data)
    def test_missing_editorial_content_is_explicit(self):
        self.data['sections'][1]['stories']=[]
        with self.assertRaises(ValueError): p.validate(self.data)
        self.data['sections'][1]['note']='Nenhuma novidade verificada até o fechamento.'
        p.validate(self.data)
    def test_check_detects_partial_publication(self):
        p.build(self.data,self.root)
        (self.root/'index.html').write_text('stale')
        with self.assertRaisesRegex(ValueError,'divergente'):
            p.build(self.data,self.root,check=True)

if __name__=='__main__': unittest.main()
