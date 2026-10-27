# Como rodar e testar você mesmo

O código já está neste repositório, em `src/`. **Para testar um `.docx` você não
precisa instalar nada além do Python** — nem banco, nem biblioteca. O comando
`previa` mostra as linhas que *iriam* para o banco, sem gravar nada.

---

## 1. Abrir no VS Code

```powershell
cd C:\Users\guilh\elogroup26-saga
code .
```

Abra o terminal integrado com **Ctrl + '** (ou menu *Terminal → New Terminal*).

Confira se o Python responde:

```powershell
python --version
```

Se der erro, tente `py --version`. Use o que funcionar nos comandos abaixo.

---

## 2. Instalar o comando

```powershell
pip install -e .
```

É rápido porque o projeto não tem dependência obrigatória. Isso cria o comando
`curriculos`.

> **Se `curriculos` não for reconhecido depois disso**, não perca tempo:
> use `python -m curriculos.cli` no lugar de `curriculos` em todos os comandos.
> Funciona igual.
>
> **Se quiser rodar sem instalar nada:**
> ```powershell
> $env:PYTHONPATH="src"
> python -m curriculos.cli previa "data\curriculos_raw\Rao_Java.docx"
> ```

---

## 3. Testar com um arquivo qualquer

Pegue **qualquer currículo em .docx** — o seu, o de um amigo, um dos 228 da
pasta `data\curriculos_raw`, um baixado da internet. Aponte o comando para ele:

```powershell
curriculos previa "C:\Users\guilh\Downloads\meu_curriculo.docx"
```

Use aspas sempre: nome com espaço ou acento quebra sem elas.

A saída no terminal vem tabela por tabela — `pessoa`, `documento`,
`experiencia`, `certificacao`, as três origens de `skill`, a visão
`vw_skill_sem_evidencia` e a fila do dicionário.

### Para ver bonito

```powershell
curriculos previa "C:\Users\guilh\Downloads\meu_curriculo.docx" --html saida.html
```

Abra `saida.html` com **Ctrl + Shift + P → Simple Browser: Show** (abre dentro
do VS Code, ao lado do código), ou clique com o botão direito no arquivo →
*Reveal in File Explorer* e abra no navegador.

Prefere markdown? O VS Code pré-visualiza nativamente com **Ctrl + Shift + V**:

```powershell
curriculos previa "arquivo.docx" --md saida.md
```

### Para ver a pasta inteira de uma vez

```powershell
curriculos painel data\curriculos_raw --html data\previa\00_painel.html
```

Uma linha por documento, ordenado pela coluna que importa: competências
afirmadas e nunca comprovadas.

### Para simular a chegada pelo WhatsApp

```powershell
curriculos previa "arquivo.docx" --telefone +5531999998888
```

Repare na tabela `pessoa`: `chave_externa` some e `telefone_e164` aparece. É a
única diferença — a identidade passa a vir do canal.

---

## 4. O que esperar de cada tipo de arquivo

| Você testa com | O que acontece |
|---|---|
| `.docx` do Word | Funciona direto, sem instalar nada |
| `.pdf` com texto | Precisa de `pip install "curriculos[pdf]"` antes |
| `.pdf` escaneado ou foto | Diz `SemTextoExtraivel` — **é o comportamento certo**: iria para a fila de revisão, onde entraria o OCR |
| `.doc` antigo | Diz que é formato legado e sugere converter para `.docx` |
| Currículo em português | Os campos de data e seção funcionam; o dicionário de skills foi montado em inglês, então reconhece menos |

Esse último ponto é esperado e vale saber antes de uma demo ao vivo: o
dicionário saiu de 30 currículos em inglês. Tecnologias (Java, Python, AWS,
Docker) são reconhecidas em qualquer idioma porque o nome é o mesmo; termos
como "conhecimento sólido em" ainda não estão na lista de índices.

---

## 5. Se der errado

| Mensagem | O que fazer |
|---|---|
| `'curriculos' não é reconhecido` | Use `python -m curriculos.cli` no lugar |
| `No module named curriculos` | Rode `pip install -e .` na raiz do repositório, ou use `$env:PYTHONPATH="src"` |
| `para ler PDF: pip install...` | `pip install "curriculos[pdf]"` |
| `não é um .docx válido` | O arquivo está corrompido, ou é `.doc` renomeado para `.docx` |
| `nenhum texto extraível` | É imagem/escaneado — precisa de OCR, que ainda não está implementado |
| Caminho não encontrado | Faltou aspas, ou a barra está invertida. No Windows use `\` e aspas |

---

## 6. Rodar os testes

```powershell
pip install -e ".[dev]"
pytest
```

São 34 testes de extração, que rodam sem banco. Os 8 testes de merge precisam
de PostgreSQL e são pulados sozinhos se `DATABASE_URL_TESTE` não estiver
definida — por isso a saída mostra `34 passed, 8 skipped`. Isso é o esperado.

---

## 7. Com banco de dados (opcional)

Só se quiser ver a gravação de verdade e o merge incremental funcionando:

```powershell
docker compose up -d
pip install -e ".[db]"
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/competencias"
curriculos schema
curriculos carregar data\curriculos_raw
curriculos pessoa 1
```

Para ver a armadilha principal resolvida — um certificado que **não** apaga o
resto —, os testes de merge provam isso:

```powershell
$env:DATABASE_URL_TESTE="postgresql://postgres:postgres@localhost:5432/competencias_teste"
pytest tests/test_merge.py -v
```

---

## Já tem resultado gerado em `data/previa/`

| Arquivo | O que é |
|---|---|
| `00_painel.html` | os 30 currículos, uma linha cada |
| `Akhil_profile.html` | BA/Scrum Master — 4 certificações, 5 vínculos |
| `Rao_Java.html` | dev Java — 81 skills afirmadas, 19 sem evidência |
| `Rajendra-PMP-CSM.html` | PM certificado — 6 certificações, 0 sem evidência |

## Onde mexer

| Quero... | Arquivo |
|---|---|
| adicionar skill ao dicionário | `src/curriculos/dicionarios/skills.py` |
| adicionar certificação | `src/curriculos/dicionarios/certificacoes.py` |
| mudar os termos que indexam afirmação | `src/curriculos/dicionarios/hedge.py` |
| mudar como a zona CLAIM/EVIDENCIA é decidida | `src/curriculos/extracao/zonas.py` |
| mudar a aparência das páginas HTML | `src/curriculos/previa.py` (constante `_CSS`) |
| mudar o schema do banco | `sql/001_schema.sql` |
