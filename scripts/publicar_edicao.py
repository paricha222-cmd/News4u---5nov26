#!/usr/bin/env python3
"""Render ONE editorial source into the website, immutable archive and dot text.

No network, credentials or AI calls. This checks structure and consistency;
the editor must independently verify every fact and link before publishing.
"""
import argparse
import datetime as dt
import hashlib
import html
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

TZ = ZoneInfo('America/Sao_Paulo')
SECTIONS = ('Economia', 'Previdência', 'Esportes')
ROOT = Path(__file__).resolve().parent.parent

def public_url(url):
    if re.search(r'[\s()\[\]<>"\\]', url):
        raise ValueError('URL contém caracteres inseguros; use codificação percentual')
    u = urlsplit(url)
    if u.scheme != 'https' or not u.hostname or u.username or u.password:
        raise ValueError('Fonte precisa de link HTTPS público, sem credenciais')
    _ = u.port  # Reject malformed ports.
    host = u.hostname.lower()
    if host == 'localhost' or host.endswith(('.localhost','.local','.internal')) or '.' not in host:
        raise ValueError('Fonte não pode apontar para rede local')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError('Fonte não pode apontar para endereço IP privado')

def md_escape(value):
    return re.sub(r'([\\\[\]*_~`])', r'\\\1', value)

def validate(data):
    if data.get('schema_version') != 1:
        raise ValueError('schema_version deve ser 1')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-\d{4}-[a-z0-9-]+', data.get('id', '')):
        raise ValueError('ID inválido: use AAAA-MM-DD-HHMM-tipo')
    if data.get('timezone') != 'America/Sao_Paulo':
        raise ValueError('Fuso deve ser America/Sao_Paulo')
    cutoff = dt.datetime.fromisoformat(data['cutoff'])
    if cutoff.tzinfo is None or cutoff.utcoffset() != cutoff.astimezone(TZ).utcoffset():
        raise ValueError('Fechamento deve ter offset de Brasília')
    if not data['id'].startswith(cutoff.astimezone(TZ).strftime('%Y-%m-%d-%H%M-')):
        raise ValueError('ID e fechamento não correspondem')
    if not isinstance(data.get('title'), str) or not data['title'].strip():
        raise ValueError('Título obrigatório')
    if [s.get('name') for s in data.get('sections', [])] != list(SECTIONS):
        raise ValueError('Editorias obrigatórias: Economia, Previdência, Esportes')
    count = 0
    for section in data['sections']:
        if not section.get('stories') and not section.get('note'):
            raise ValueError('Editoria vazia precisa explicar a limitação')
        for story in section.get('stories', []):
            for field in ('headline', 'summary', 'source', 'url'):
                if not isinstance(story.get(field), str) or not story[field].strip():
                    raise ValueError(f'Campo obrigatório: {field}')
            public_url(story['url'])
            count += 1
    if not count:
        raise ValueError('Edição sem notícias')
    return cutoff.astimezone(TZ)

def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'

def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def build(data, root=ROOT, check=False):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.news4u-publish.lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Outra publicação está em andamento; confira antes de tentar novamente')
    try:
        return _build(data, root, check)
    finally:
        lock.rmdir()

def _build(data, root, check):
    cutoff = validate(data)
    edition_id = data['id']
    base = 'news4u-' + edition_id
    archive_path = 'arquivo/' + base + '.html'
    markdown_path = 'arquivo/' + base + '.md'
    source_path = 'edicoes/' + edition_id + '.json'
    canonical = json_text(data)
    content_hash = digest(canonical)
    label = cutoff.strftime('%d/%m/%Y • %Hh%M de Brasília')
    esc = html.escape
    logo = (root / 'assets/logo-data.txt').read_text().strip()
    if not logo.startswith('data:image/webp;base64,'):
        raise ValueError('Logo original News4U ausente')
    css = '''*{box-sizing:border-box}body{margin:0;background:#e2e7e2;color:#243329;font-family:Georgia,serif}a{color:#18564a;text-underline-offset:3px}.toolbar{max-width:1120px;margin:20px auto;display:flex;justify-content:space-between;gap:12px;padding:0 18px;font:14px Arial}.paper{max-width:1120px;margin:0 auto 40px;background:#faf7ef;padding:40px;box-shadow:0 8px 35px #23332216}header{text-align:center;border-bottom:4px double #18564a;padding-bottom:24px}.logo{width:340px;max-width:90%;height:auto}.kicker{font:12px Arial;letter-spacing:2px;text-transform:uppercase;color:#657266}h1{font-size:30px;margin:18px 0 10px}.date{font:14px Arial;color:#59665b}.intro{max-width:720px;margin:18px auto 0;font:14px/1.6 Arial;color:#59665b}.sections{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px;padding-top:12px}.section+ .section{border-left:1px solid #cdd2c7;padding-left:28px}h2{font-size:24px;color:#18564a;border-bottom:2px solid #b39158;padding-bottom:10px}article{border-bottom:1px solid #d8dbd1;padding:0 0 20px;margin-bottom:20px;break-inside:avoid}h3{font-size:21px;line-height:1.2;margin:0 0 12px}p{font-size:16px;line-height:1.5}.source{font:12px/1.5 Arial}.note{font:14px/1.5 Arial;color:#59665b}footer{padding-top:20px;border-top:3px double #18564a;font:12px/1.6 Arial;color:#59665b}button{border:1px solid #18564a;background:#faf7ef;color:#18564a;border-radius:4px;padding:9px 14px;cursor:pointer}@media(max-width:800px){.paper{padding:25px 20px}.sections{display:block}.section+ .section{border-left:0;padding-left:0}.toolbar{flex-wrap:wrap}.logo{width:280px}h1{font-size:25px}}@media print{body{background:white}.toolbar{display:none}.paper{margin:0;box-shadow:none;padding:0;max-width:none}.sections{display:block}.section{break-before:page}.section:first-child{break-before:auto}.section+ .section{border-left:0;padding-left:0}.source a{color:#18564a}footer{margin-top:20px}}'''
    parts = [f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="news4u-edition-id" content="{edition_id}"><meta name="news4u-content-sha256" content="{content_hash}"><title>News4U | {esc(data["title"])} | {cutoff:%d/%m/%Y}</title><style>{css}</style></head><body>',
             '<div class="toolbar"><a href="/arquivo/">Arquivo de edições</a><button type="button" onclick="window.print()">Imprimir / Salvar em PDF</button></div><main class="paper">',
             f'<header><img class="logo" src="{logo}" alt="Logo News4U"><div class="kicker">Economia · Previdência · Esportes</div><h1>{esc(data["title"])}</h1><div class="date">Fechamento: {label}</div><p class="intro">A mesma edição no site e no dot. Notícias com fontes e links diretos; datas anteriores são identificadas nas referências. Consulte as fontes para a íntegra e eventuais atualizações.</p></header><div class="sections">']
    md = [f'📰 **NEWS4U | {md_escape(data["title"])}**', f'Fechamento: {label}', '']
    for section in data['sections']:
        parts.append(f'<section class="section"><h2>{esc(section["name"])}</h2>')
        md += [f'**{section["name"]}**', '']
        for story in section.get('stories', []):
            parts.append(f'<article><h3>{esc(story["headline"])}</h3><p>{esc(story["summary"])}</p><div class="source"><a href="{esc(story["url"],quote=True)}" target="_blank" rel="noopener noreferrer">{esc(story["source"])}</a></div></article>')
            md += [f'• **{md_escape(story["headline"])}** {md_escape(story["summary"])} [{md_escape(story["source"])}]({story["url"]})', '']
        if section.get('note'):
            parts.append(f'<p class="note">{esc(section["note"])}</p>')
            md += [md_escape(section['note']), '']
        parts.append('</section>')
    parts.append('</div>')
    for note in data.get('notes', []):
        parts.append(f'<p class="note">{esc(note)}</p>')
        md += [md_escape(note), '']
    parts.append(f'<footer>News4U · Edição {edition_id}<br><a href="/{archive_path}">Link permanente desta edição</a> · <a href="/arquivo/">Todas as edições</a></footer></main></body></html>\n')
    page = '\n'.join(parts)
    markdown = '\n'.join(md).rstrip() + '\n'
    manifest = {'schema_version': 1, 'id': edition_id, 'title': data['title'], 'cutoff': data['cutoff'], 'timezone': data['timezone'], 'source_path': source_path, 'html_path': archive_path, 'markdown_path': markdown_path, 'content_sha256': content_hash, 'html_sha256': digest(page), 'markdown_sha256': digest(markdown)}
    # Archive identity is immutable. A correction must receive a NEW ID.
    outputs = {source_path: canonical, archive_path: page, markdown_path: markdown}
    for path, value in outputs.items():
        p = root / path
        # A new JSON draft can use any formatting before its archive exists.
        if path == source_path and not (root / archive_path).exists():
            if p.exists() and json.loads(p.read_text()) != data:
                raise ValueError('Rascunho de origem difere dos dados fornecidos')
            continue
        if p.exists() and p.read_text() != value:
            raise ValueError(f'Edição imutável já existe com conteúdo diferente: {path}')
    # Never promote an older edition over a newer published cutoff.
    existing = root / 'latest.json'
    if existing.exists():
        old = json.loads(existing.read_text())
        if dt.datetime.fromisoformat(old['cutoff']) > cutoff:
            raise ValueError('Não é permitido substituir a edição atual por uma mais antiga')
    outputs.update({'index.html': page, 'latest.json': json_text(manifest)})
    entries = {p.name for p in (root / 'arquivo').glob('news4u-*.html')} if (root / 'arquivo').exists() else set()
    entries.add(base + '.html')
    rows = []
    for name in sorted(entries, reverse=True):
        title = name.removeprefix('news4u-').removesuffix('.html')
        if name == 'news4u-2026-11-05.html':
            title += ' · seleção RSS anterior (10h05)'
        elif 'original' in name:
            title += ' · edição original preservada'
        rows.append(f'<li><a href="{esc(name)}">{esc(title)}</a></li>')
    outputs['arquivo/index.html'] = '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Arquivo News4U</title><style>body{max-width:900px;margin:40px auto;padding:24px;background:#faf7ef;color:#243329;font:18px/1.7 Georgia}a{color:#18564a}li{margin:12px 0}</style></head><body><h1>Arquivo News4U</h1><p>Edições preservadas por data e horário de Brasília.</p><p><a href="/">Edição atual</a></p><ul>' + ''.join(rows) + '</ul></body></html>\n'
    for path, value in outputs.items():
        p = root / path
        if check:
            if not p.exists() or p.read_text() != value:
                raise ValueError(f'Arquivo ausente ou divergente: {path}')
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=p.parent, prefix='.news4u-', suffix='.tmp', delete=False) as temp:
                temp.write(value)
                tmp_name = temp.name
            os.replace(tmp_name, p)
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json_text(build(json.loads(args.source.read_text()), args.root, args.check)), end='')
