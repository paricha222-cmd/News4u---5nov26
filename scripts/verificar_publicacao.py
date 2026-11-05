#!/usr/bin/env python3
"""Verify the exact edition on the PUBLIC site, not only today's date."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

def verify(base, expected):
    if urlsplit(base).scheme != 'https':
        raise ValueError('HTTPS obrigatório')
    def get(path):
        # Cache-bypass query, public requests only. No secrets or sessions.
        url = base.rstrip('/') + '/' + path.lstrip('/') + '?edition_check=' + str(time.time_ns())
        with urlopen(Request(url, headers={'User-Agent':'News4U-Publication-Check/1.0', 'Cache-Control':'no-cache'}), timeout=30) as resp:
            return resp.read()
    actual = json.loads(get('latest.json'))
    if actual != expected:
        raise ValueError('Manifesto publicado difere da edição esperada')
    for path, key in [('index.html','html_sha256'), (actual['html_path'],'html_sha256'), (actual['markdown_path'],'markdown_sha256'), (actual['source_path'],'content_sha256')]:
        if hashlib.sha256(get(path)).hexdigest() != expected[key]:
            raise ValueError('Conteúdo publicado divergente: ' + path)
    if actual['html_path'].split('/')[-1].encode() not in get('arquivo/'):
        raise ValueError('Edição não aparece no arquivo público')
    return actual['id']

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='https://news4u-5nov26.onrender.com')
    p.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parent.parent / 'latest.json')
    args = p.parse_args()
    print('Publicação verificada:', verify(args.url, json.loads(args.manifest.read_text())))
