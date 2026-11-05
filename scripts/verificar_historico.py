#!/usr/bin/env python3
"""Reject changes/deletions to editions already present in the base commit."""
import argparse
import subprocess

def verify(base, cwd=None):
    if not base or set(base) == {'0'}:
        return
    changes = subprocess.check_output(['git','diff','--name-status','--no-renames',base,'HEAD','--','arquivo/','edicoes/'],cwd=cwd,text=True)
    for line in changes.splitlines():
        status, path = line.split('\t',1)
        historical = path.startswith('edicoes/') or path.startswith('arquivo/news4u-')
        if historical and status != 'A':
            raise ValueError('Histórico existente não pode ser alterado ou removido: '+path)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--base',required=True)
    args=p.parse_args()
    verify(args.base)
    print('Histórico preservado')
