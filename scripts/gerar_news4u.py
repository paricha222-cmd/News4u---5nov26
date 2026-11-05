#!/usr/bin/env python3
"""News4U: RSS headlines, source links, dated archive. No fabricated summaries."""
import datetime as dt
import email.utils
import html
import os
import pathlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
today = dt.datetime.now(TZ).date()
root = pathlib.Path(__file__).resolve().parent.parent
sections = {
    "Economia": ["economia Brasil inflação juros mercado financeiro", "site:valor.globo.com economia"],
    "Previdência": ["PREVIC fundos de pensão EFPC RPPS previdência complementar", "site:gov.br/previc previdência"],
    "Esportes": ["Palmeiras Corinthians Santos São Paulo futebol hoje", "Fórmula 1 tênis Brasil esporte"],
}
def items_for(query):
    q = urllib.parse.quote(query + " when:2d")
    url = "https://news.google.com/rss/search?q=" + q + "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    req = urllib.request.Request(url, headers={"User-Agent": "News4U/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = resp.read()
    rss = ET.fromstring(data)
    for item in rss.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate") or ""
        source = item.find("source")
        publisher = source.text if source is not None and source.text else "Fonte"
        try:
            published = email.utils.parsedate_to_datetime(pub).astimezone(TZ).date()
        except Exception:
            continue
        if published != today or not link.startswith("https://"):
            continue
        yield (title, link, publisher)

def main():
    if (root / "latest.json").exists():
        raise SystemExit("Gerador RSS legado desativado: use scripts/publicar_edicao.py com a edição editorial única do dot. Nenhum arquivo foi alterado.")
    collected = {}
    for section, queries in sections.items():
        seen = set()
        stories = []
        for query in queries:
            try:
                for title, link, publisher in items_for(query):
                    key = title.lower().split(" - ")[0].strip()
                    if key in seen:
                        continue
                    seen.add(key)
                    stories.append((title, link, publisher))
                    if len(stories) >= 5:
                        break
            except Exception as exc:
                print(f"Feed unavailable: {query}: {exc}")
            if len(stories) >= 5:
                break
        collected[section] = stories
    total = sum(map(len, collected.values()))
    if total < 3:
        raise SystemExit("Not enough verified current-day headlines; previous edition preserved.")
    date_label = today.strftime("%d/%m/%Y")
    css = """body{margin:0;background:#f9f6ed;color:#243028;font-family:Georgia,serif}header,main,footer{max-width:970px;margin:auto;padding:24px}header{text-align:center;border-bottom:3px double #265747}.logo{font:bold 60px Georgia;color:#18564a;letter-spacing:-3px}.logo span{color:#a67835}h1{font-size:25px}h2{border-bottom:1px solid #aab2a5;padding-bottom:8px;color:#18564a}article{padding:16px 0;border-bottom:1px solid #ddd}article a{font-size:20px;color:#1f332c;text-decoration:none}article a:hover{text-decoration:underline}.source{font:13px Arial;color:#657068;margin-top:7px}.note{font:14px Arial;line-height:1.5;color:#59645c}footer{font:13px Arial;color:#59645c}nav a{color:#18564a;margin:0 10px}"""
    parts = ['<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>News4U | '+date_label+'</title><style>'+css+'</style></head><body>']
    parts.append('<header><div class="logo">News<span>4U</span></div><p>EDIÇÃO DIÁRIA • '+date_label+'</p><nav><a href="#economia">Economia</a><a href="#previdencia">Previdência</a><a href="#esportes">Esportes</a></nav></header><main><h1>Notícias de hoje</h1><p class="note">Seleção automática de manchetes publicadas nesta data. Clique para consultar a reportagem e conferir os detalhes na fonte original. A seleção não representa verificação editorial independente.</p>')
    for section, stories in collected.items():
        parts.append('<section id="'+{"Economia":"economia","Previdência":"previdencia","Esportes":"esportes"}[section]+'"><h2>'+section+'</h2>')
        if not stories:
            parts.append('<p class="note">Nenhuma manchete desta data encontrada nas fontes consultadas.</p>')
        for title, link, publisher in stories:
            parts.append('<article><a target="_blank" rel="noopener noreferrer" href="'+html.escape(link,quote=True)+'">'+html.escape(title)+'</a><div class="source">'+html.escape(publisher)+'</div></article>')
        parts.append('</section>')
    parts.append('</main><footer>News4U • Atualização automática • <a href="arquivo/">Arquivo de edições</a></footer></body></html>')
    output = "\n".join(parts)
    archive = root / "arquivo"
    archive.mkdir(exist_ok=True)
    filename = "news4u-"+today.isoformat()+".html"
    (archive / filename).write_text(output,encoding="utf-8")
    (root / "index.html").write_text(output,encoding="utf-8")
    archive_links = sorted(archive.glob("news4u-*.html"),reverse=True)
    archive_html = '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Arquivo News4U</title><body style="font:18px Georgia;background:#faf7ef;padding:35px"><h1>Arquivo News4U</h1><p><a href="../">Edição atual</a></p><ul>'+''.join('<li><a href="'+html.escape(p.name)+'">'+html.escape(p.stem)+'</a></li>' for p in archive_links)+'</ul></body></html>'
    (archive / "index.html").write_text(archive_html,encoding="utf-8")
    print(f"Published {total} headlines for {today}")

if __name__ == "__main__":
    main()
