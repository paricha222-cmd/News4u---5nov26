import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request

ROOT=Path(__file__).resolve().parent.parent
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
live=module('verificar_publicacao')
history=module('verificar_historico')

class IntegrityTests(unittest.TestCase):
    def test_history_rejects_changes_and_deletion_but_allows_addition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def git(*args):
                return subprocess.check_output(['git',*args],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
            git('init'); git('config','user.email','test@example.com'); git('config','user.name','Test')
            (root/'arquivo').mkdir(); old=root/'arquivo/news4u-old.html';old.write_text('original')
            git('add','.');git('commit','-m','base');base=git('rev-parse','HEAD')
            (root/'arquivo/news4u-new.html').write_text('new');git('add','.');git('commit','-m','add')
            history.verify(base,root)
            old.write_text('changed');git('add','.');git('commit','-m','bad change')
            with self.assertRaises(ValueError):history.verify(base,root)
            old.unlink();git('add','.');git('commit','-m','bad deletion')
            with self.assertRaises(ValueError):history.verify(base,root)
    def test_cross_host_and_insecure_redirects_are_rejected(self):
        handler=live.SameSiteRedirects();req=Request('https://news.example/latest.json')
        for url in ['http://news.example/latest.json','https://other.example/latest.json']:
            with self.assertRaises(ValueError):handler.redirect_request(req,None,302,'Found',{},url)
    def test_public_verifier_accepts_exact_files_and_detects_mismatch(self):
        expected=json.loads((ROOT/'latest.json').read_text())
        paths=['latest.json','index.html',expected['html_path'],expected['markdown_path'],expected['source_path']]
        mapping={p:(ROOT/p).read_bytes() for p in paths}
        mapping['arquivo/']=(ROOT/'arquivo/index.html').read_bytes()
        class Response:
            def __init__(self,data):self.data=data
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return self.data
        class Opener:
            def open(self,request,timeout):
                path=live.urlsplit(request.full_url).path.lstrip('/')
                return Response(mapping[path])
        with patch.object(live,'build_opener',return_value=Opener()):
            self.assertEqual(live.verify('https://news.example',expected),expected['id'])
            mapping['index.html']=b'stale'
            with self.assertRaisesRegex(ValueError,'divergente'):live.verify('https://news.example',expected)

if __name__=='__main__':unittest.main()
