# Publicação editorial única do News4U

O arquivo JSON em `edicoes/` é a única fonte de cada edição. HTML do site,
arquivo permanente e texto entregue pelo dot são gerados desse mesmo conteúdo.
O renderizador valida estrutura e consistência, mas **não verifica fatos**:
antes de publicar, o editor deve consultar as fontes e conferir cada afirmação.

## Preparar e validar

1. Atualizar o checkout da branch `main` de `paricha222-cmd/News4u---5nov26`.
2. Usar `edicoes/2026-11-05-1100-extra.json` como exemplo do esquema.
   Criar novo ID `AAAA-MM-DD-HHMM-tipo`, com fechamento de Brasília e fontes
   HTTPS diretas. Preservar a manchete, resumo, fonte e URL que serão enviados
   no dot. As três editorias são Economia, Previdência e Esportes.
3. Executar `python scripts/publicar_edicao.py edicoes/ID.json`.
4. Executar `python -m unittest discover -s tests -v` e repetir o comando
   do passo 3 com `--check`. Revisar a apresentação em desktop e celular.
5. Fazer **um único commit atômico** contendo a fonte, `index.html`,
   `latest.json`, `arquivo/index.html`, HTML e Markdown da nova edição.
   Preservar todos os arquivos anteriores. Nunca fazer force-push.

## Publicar e confirmar

Os plugins GitHub e Render já conectados podem fazer publicação e consulta.
Não são necessários novos tokens, API keys, deploy hooks ou segredos no repo.

Serviço Render: `srv-dbm7ebh5efls73cnipo0`.
Workspace autorizado: `tea-db398n7avr4c73a6kje0`.
Site: https://news4u-5nov26.onrender.com.

Depois do commit, conferir o deploy correspondente no Render. Não iniciar
deploy duplicado quando o automático já estiver pendente ou rodando.
Se não houver deploy, investigar o vínculo do repositório; não afirmar que o
site foi atualizado só porque o GitHub recebeu o commit.

Executar `python scripts/verificar_publicacao.py` para comparar o manifesto
e os hashes da página atual, arquivo permanente, texto e JSON em URLs públicas.
Só depois de essa verificação passar, enviar no dot o texto do caminho
`markdown_path` informado em `latest.json`, com o link permanente `html_path`.
Não gerar uma segunda versão independente para a mensagem. Se a publicação
falhar, informar a limitação sem anunciar sincronização ou sucesso.

## Histórico e correções

Edições com o mesmo ID são imutáveis. Reexecutar a mesma edição é seguro;
alterar uma edição já arquivada causa erro. Para corrigir conteúdo, usar novo
horário e ID e identificar a correção em `notes`. Edições extras coexistem com
as edições regulares. Um fechamento mais antigo nunca substitui a página atual.

A edição original da manhã de 05/11 e a antiga seleção RSS foram preservadas
no arquivo como registros históricos; não são a fonte da edição atual.

GitHub Actions valida os arquivos, mas a pesquisa e a geração editorial são
feitas pela automação do dot. Não configurar outro gerador que sobrescreva a
mesma página independentemente.
