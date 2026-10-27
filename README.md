# Banco de competências

Recebe currículos e certificados, extrai competência, certificação e
experiência, e grava num PostgreSQL de forma **incremental**: cada documento
atualiza só a parte que ele traz.

Pensado para o fluxo de WhatsApp — a pessoa manda um documento, o banco se
atualiza — mas a camada de WhatsApp não faz parte deste pacote (ver
[Onde o WhatsApp entra](#onde-o-whatsapp-entra)).

> **Este repositório não contém currículo de ninguém.** Os números citados
> abaixo vieram de uma base real de 228 currículos que não é redistribuída
> aqui; o exemplo embutido é sintético.

## Experimente em um minuto

Não precisa de banco de dados nem de nenhuma dependência: para ler `.docx`
basta o Python.

```bash
pip install -e .
python exemplos/gerar_exemplo.py
curriculos previa exemplos/exemplo_curriculo.docx --html saida.html
```

Abra `saida.html`. Ou aponte o comando para qualquer currículo `.docx` seu.

```
$ curriculos extrair "data/curriculos_raw/Akhil.profile.docx"
arquivo .......... Akhil.profile.docx
tipo ............. CURRICULO
escopos .......... CERTIFICACAO, EXPERIENCIA, SKILL_COMPROVADA, SKILL_MATRIZ, SKILL_SC
anos declarados .. 8.0
skill_sc.......... 48
skill_matriz...... 35
skill_comprovada.. 182
sem_evidencia..... 26

EXPERIÊNCIA
  2016-03-01 -> atual  JPMorgan Chase    Sr. Business Systems Analyst/ Scrum Master
  2015-04-01 -> 2016-02-01  Global Payments   Sr. Business Analyst/Scrum Master
  ...
AFIRMADA SEM EVIDÊNCIA (26)
  SDLC          METODOLOGIA  via understanding of
  Banking       DOMINIO      via understanding of
  TFS           FERRAMENTA   via hands on
```

---

## A ideia

Três graus de evidência para a mesma competência, e o valor está em separá-los:

| origem | o que é | exemplo |
|---|---|---|
| `HEDGE` | afirmação solta no topo do currículo | *"Good knowledge of Spring MVC"* |
| `MATRIZ` | item da tabela "Technical Skills" | `Languages \| Java, C++, SQL` |
| `EVIDENCIA` | citada dentro de um emprego datado | *"Developed pipelines using Spark"* sob `Client: Banco Alfa, Jan 2024–atual` |

A separação não vem da palavra, vem da **posição no documento**. O extrator
acha a *âncora* — a primeira entrada de emprego — e tudo acima dela é
afirmação. Isso é mais robusto que procurar o cabeçalho "Summary": na amostra
de 30 currículos, 6 não têm cabeçalho de resumo nenhum e um chama o resumo de
`Responsibility:`.

Daí sai a pergunta que o banco responde em uma consulta:

```sql
select skill, categoria, mencoes, termos_indice
  from vw_skill_sem_evidencia
 where id_pessoa = 7;
```

> *em que essa pessoa diz ter competência sem nunca ter mostrado onde usou*

Rodando nos 30 currículos da amostra, as mais afirmadas sem evidência são
justamente as tecnologias de enchimento de lista:

```
13/30 Analitico   9/30 SQL Server   8/30 UDDI   7/30 C++   7/30 JAXB
 7/30 JAX-RPC     7/30 Cucumber     6/30 DTD    5/30 RMI   5/30 Mockito
```

---

## Instalação

```bash
docker compose up -d                 # PostgreSQL 16 em localhost:5432
pip install -e ".[dev]"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/competencias"
curriculos schema
```

## Uso

```bash
# conferir sem gravar
curriculos extrair caminho/do/arquivo.docx

# gravar um documento recebido (telefone = identidade do remetente)
curriculos ingerir certificado.pdf --telefone +5511999998888

# carga inicial de uma pasta (sem telefone: identidade vira arquivo:<nome>)
curriculos carregar data/curriculos_raw -v

# filas de trabalho
curriculos revisoes      # o que precisa de olho humano
curriculos pendencias    # termos que faltam no dicionário

# o que o banco sabe de alguém
curriculos pessoa 7
```

Carga medida: **30 currículos em 2,1s**, extração e gravação incluídas
(~70 ms por documento). Extrapolando, os 228 da pasta levam ~16s.

---

## As quatro regras do merge

Elas existem porque "atualizar só uma parte" é a parte perigosa do fluxo.

**1. Reenvio é no-op.** O SHA-256 do arquivo é `unique` em `documento`. No
WhatsApp as pessoas mandam o mesmo arquivo três vezes.

**2. Merge por escopo.** O documento declara quais escopos traz e só esses são
tocados. Um PDF de certificado não menciona skill nenhuma — num
"substitui tudo" ele apagaria as 30 skills e os 7 vínculos da pessoa. Existe
teste para isso: `test_certificado_nao_apaga_skills_nem_vinculos`.

**3. Upsert por chave natural.** Cada fato carrega a sua:

| fato | chave natural |
|---|---|
| skill | `(pessoa, skill, origem)` |
| certificação | `(pessoa, sigla)` |
| experiência | `(pessoa, organização normalizada, início)` |

A da experiência é a que resolve o emprego em aberto: o currículo antigo diz
`Jan 2024 – Till Date`, o novo diz `Jan 2024 – Jun 2026`. Mesma chave, então o
vínculo é **fechado**, não duplicado. A normalização de empresa faz
`Cognizant Inc.` e `Cognizant` caírem na mesma chave.

**4. Nunca apagar.** Fato que a pessoa parou de mencionar fica, com o
`visto_em` antigo. Gente poda currículo para caber numa página; isso não quer
dizer que desaprendeu. Remover é ação humana, pela coluna `removido_em`.

---

## Identidade: não existe CPF nos currículos

Procurei nos 30: **nenhum tem CPF** — são currículos americanos e indianos.
Cobertura dos identificadores que existem:

| identificador | cobertura | serve de chave? |
|---|---|---|
| telefone do remetente (WhatsApp) | 100% quando vem pelo canal | **sim, é a âncora** |
| nome do arquivo | 100% na carga de pasta | sim, via `chave_externa` |
| e-mail no documento | 22/30 (73%) | não |
| nome no corpo do documento | não confiável | não |

O nome no corpo é pior do que parece: a primeira linha é `PROFESSIONAL SUMMARY`
em um currículo, `ROLES` em outro, `right9525Amar` em outro (resíduo de campo
do Word).

Então `pessoa` tem `telefone_e164` único como âncora, `cpf` como campo de
ligação com o cadastro da empresa (vem `null`), e `chave_externa` para
documento que chegou sem telefone. Quando a pessoa mandar algo pelo WhatsApp
depois, basta preencher `telefone_e164` na linha que já existe.

**Um risco que precisa de regra:** recrutador encaminhando currículos do
próprio número faria todos os candidatos colapsarem numa pessoa só. Quando o
número já tem pessoa e o e-mail do documento é outro, isso não vira merge —
vira item em `revisao` com motivo `CONFLITO_IDENTIDADE`.

---

## Estrutura

```
src/curriculos/
  leitura/          docx (parágrafos + tabelas em ordem), pdf, gancho de OCR
  dicionarios/      skills (409 canônicas), certificações (39 siglas),
                    hedge (termos-índice), seções (cabeçalhos, meses)
  normalizacao.py   varredor de n-gramas — uma função para os três campos
  extracao/
    zonas.py        âncora, seções, CLAIM × EVIDENCIA, datas, anos
    campos.py       skill afirmada / comprovada / matriz, certificação, experiência
  dominio.py        os fatos e suas chaves naturais
  persistencia/     conexão e o merge por escopo
  cli.py
sql/001_schema.sql  schema, constraints e as 3 visões
tests/              42 testes
```

### Por que n-gramas e não regex

O varredor precisa do **casamento mais longo**. Com regex, `sql` casaria
dentro de `pl/sql` e `spring` dentro de `spring boot`. Varrendo n-gramas de 3,
2 e 1 palavra, parando no primeiro acerto e **pulando as palavras
consumidas**, o termo mais específico sempre ganha. Custo: ~3 consultas-hash
por palavra, independente do tamanho do dicionário.

Esse "pulando as palavras consumidas" foi bug: sem ele, `PL/SQL` gerava
`PL/SQL` **e** `SQL`, e `Amazon Web Services` gerava `AWS` mais um
`Web Services` fantasma. Tem teste.

### Dois cuidados que vieram de falso positivo real

- Termo de uma letra (`R`, `C`) casa com qualquer letra solta. Por isso `R`
  não está no dicionário, e a normalização **preserva `+` e `#`** — sem isso
  `C++` e `C#` viram `c`.
- `Apache` casava sozinho dentro de "Apache Kafka". Agora
  `Apache HTTP Server` só casa com `apache http`/`httpd`, e cada projeto
  Apache tem a sua variante.

---

## Testes

```bash
pytest                                     # 34 testes de extração
DATABASE_URL_TESTE=postgresql://postgres:postgres@localhost:5432/competencias_teste pytest
                                           # + 8 testes de merge no banco
```

Os testes de banco são os que importam de verdade: não é se o extrator acha
"Spring Boot", é se mandar um certificado no WhatsApp **não apaga** o resto da
vida profissional da pessoa.

Quase todo teste de extração é uma regressão de caso que deu errado com
documento real: os 11 formatos de data que convivem na base, o
`Bachelor ... Aug 2008-May 2012` que se passava por emprego, o `8+` que não
era lido, o `Rest API Identity Credentials` que virava certificação.

---

## As duas filas de trabalho

O sistema não finge precisão que não tem. Ele separa o que não resolveu:

**`linha_nao_resolvida`** — linha que virou afirmação mas não rendeu skill.
Metade é frase genérica sem skill nenhuma (*"Ability to work under tight
deadlines"*), metade é termo fora do dicionário. `curriculos pendencias`
ordena por frequência, e é assim que o dicionário cresce: na carga dos 30, a
fila apontou Google App Engine, Drools e Session Beans, que entraram.

**`revisao`** — precisa de olho humano. Motivos: `SEM_TEXTO` (imagem, onde
entraria o OCR), `CONFLITO_IDENTIDADE`, `SIGLA_NAO_MAPEADA`, `SEM_FATOS`,
`FORMATO`.

Na carga dos 30: 25 processados, 5 em revisão, 36 linhas na fila do dicionário.

---

## Onde o WhatsApp entra

Não está implementado, por decisão de escopo. Quando entrar, o webhook faz
exatamente o que a CLI faz:

```python
arquivo   = ler_arquivo(caminho_da_midia_baixada)
resultado = extrair(arquivo)
ingestao  = ingerir(conexao, resultado, telefone=telefone_do_remetente)
```

Nada no pacote precisa mudar. O que falta montar é em volta:

- **Provedor.** Meta Cloud API (oficial, exige app verificado e HTTPS
  público) ou um BSP (Zenvia, 360dialog, Twilio — onboarding mais rápido,
  custo por mensagem).
- **Download da mídia.** O webhook entrega um `media_id`; o arquivo vem numa
  segunda chamada autenticada.
- **Resposta à pessoa.** Confirmar o que entrou ("2 certificações, 1 emprego
  atualizado") fecha o ciclo e evita reenvio. Atenção à janela de 24h: fora
  dela só template aprovado.
- **Fila.** Processar no webhook deixa a requisição pendurada. Uma fila
  (`documento.status = 'PENDENTE'` já serve de tabela de trabalho) separa
  recebimento de processamento.

## O gancho de OCR

`leitura/pdf.py::ler_com_ocr` existe e levanta `NotImplementedError` com o
caminho de implementação documentado. Hoje, documento sem texto extraível é
registrado e vai para `revisao` com motivo `SEM_TEXTO` — nada é perdido
silenciosamente.

Quando implementar, três pontos que este domínio exige: certificado
fotografado em ângulo derruba muito a precisão e o resultado tem que entrar
com confiança baixa, não direto no banco; sigla de certificação é curta e OCR
troca letra fácil (CSM/C5M, ITIL/IT1L), então vale casar contra o dicionário
de siglas com distância de edição 1; e `pytesseract` + `pdf2image` precisam de
`tesseract-ocr` e `poppler` no sistema.

---

## LGPD

O banco guarda currículo e telefone — dado pessoal, e o currículo costuma
trazer dado sensível por tabela (nome, contato, histórico). Três coisas que
valem antes de ir para produção:

- **Base legal e consentimento.** O opt-in no WhatsApp é um registro de
  consentimento razoável, mas precisa ser explícito sobre a finalidade.
  Vale guardar quando e como foi dado.
- **Retenção.** Hoje nada expira. Defina prazo e um job de expurgo —
  `visto_em` em cada fato já dá a base para isso.
- **Direito de eliminação.** `removido_em` cobre a remoção lógica; a
  eliminação de verdade precisa de rotina que apague `documento`,
  `pessoa` e os fatos em cascata.

## O que ainda falta

- Rodar nos 198 currículos restantes. O dicionário saiu de 30 documentos de
  perfil Java/BA/PM; em outros perfis vão faltar termos, e a fila
  `linha_nao_resolvida` é onde eles aparecem.
- Resolução de organização entre pessoas (hoje `Cognizant` é texto, não
  entidade). Uma tabela `organizacao` permitiria "quem já trabalhou no cliente X".
- O currículo diz `Client:`, que é o cliente, não necessariamente o
  empregador. A coluna se chama `organizacao` por isso — não confunda com
  vínculo empregatício formal.
