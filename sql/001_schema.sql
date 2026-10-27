-- =====================================================================
-- Schema do banco de competências.
--
-- Três decisões que moldam tudo aqui:
--
-- 1. IDENTIDADE VEM DO CANAL, NÃO DO DOCUMENTO.
--    O número de quem envia no WhatsApp é a âncora. Medido na amostra:
--    e-mail aparece em 22 de 30 currículos e o nome no corpo do documento
--    é lixo com frequência (a 1ª linha é "PROFESSIONAL SUMMARY" em um,
--    "ROLES" em outro). CPF não existe em nenhum. Por isso telefone_e164
--    é único e cpf é opcional.
--
-- 2. CADA FATO TEM CHAVE NATURAL.
--    chave_natural é calculada no Python e torna a gravação idempotente:
--    reprocessar vira UPDATE, não INSERT duplicado. Usa-se texto em vez de
--    UNIQUE sobre colunas nuláveis porque no Postgres NULL <> NULL e o
--    UNIQUE não deduplicaria.
--
-- 3. MERGE NUNCA APAGA.
--    Um documento só toca os escopos que ele traz. Se chega o PDF de um
--    certificado, as 30 skills e os 7 vínculos da pessoa continuam ali.
--    Remover fato é ação humana explícita (ver coluna removido_em).
-- =====================================================================

create table if not exists pessoa (
    id_pessoa       bigserial primary key,
    telefone_e164   text unique,
    cpf             text unique,
    chave_externa   text unique,
    nome            text,
    email           text,
    criado_em       timestamptz not null default now(),
    atualizado_em   timestamptz not null default now(),

    -- sem nenhum identificador a linha é inútil: não dá para reencontrar
    -- a pessoa no próximo documento
    constraint pessoa_tem_identificador
        check (telefone_e164 is not null or cpf is not null
               or chave_externa is not null or email is not null)
);

comment on column pessoa.telefone_e164 is
    'Número de quem enviou no WhatsApp, em E.164 (+5511999999999). Âncora da identidade.';
comment on column pessoa.cpf is
    'Opcional. Não vem nos currículos; é o campo de ligação com o cadastro da empresa.';
comment on column pessoa.chave_externa is
    'Identidade para documento que chegou sem telefone, como a carga inicial '
    'da pasta (ex.: "arquivo:Rao_Java.docx"). Quando a pessoa mandar algo '
    'pelo WhatsApp, basta preencher telefone_e164 na mesma linha.';


-- Cada arquivo recebido. O hash é a idempotência: no WhatsApp as pessoas
-- reenviam o mesmo arquivo, e reenvio tem que ser no-op.
create table if not exists documento (
    id_documento    bigserial primary key,
    id_pessoa       bigint references pessoa (id_pessoa) on delete set null,
    hash_sha256     char(64) not null unique,
    nome_arquivo    text not null,
    formato         text not null,
    tipo            text not null default 'INDEFINIDO',
    escopos         text[] not null default '{}',
    status          text not null default 'PENDENTE',
    motivo_revisao  text,
    recebido_em     timestamptz not null default now(),
    processado_em   timestamptz,

    constraint documento_tipo_valido
        check (tipo in ('CURRICULO', 'CERTIFICADO', 'INDEFINIDO')),
    constraint documento_status_valido
        check (status in ('PENDENTE', 'PROCESSADO', 'REVISAO', 'ERRO'))
);

create index if not exists documento_pessoa_idx on documento (id_pessoa);
create index if not exists documento_status_idx on documento (status)
    where status in ('PENDENTE', 'REVISAO');


-- ---------------------------------------------------------------------
-- FATOS
-- ---------------------------------------------------------------------

-- origem distingue os três graus de evidência:
--   HEDGE     = "good knowledge of X" solto no topo do currículo
--   MATRIZ    = listada na tabela "Technical Skills", sem nem uma frase
--   EVIDENCIA = citada dentro de um emprego datado (o grau mais forte)
-- A mesma skill pode existir nas três origens para a mesma pessoa, e é
-- justamente o cruzamento entre elas que interessa (ver vw_skill_sem_evidencia).
create table if not exists skill (
    id_skill            bigserial primary key,
    id_pessoa           bigint not null references pessoa (id_pessoa) on delete cascade,
    chave_natural       text not null,
    skill               text not null,
    categoria           text not null,
    origem              text not null,
    mencoes             integer not null default 1,
    termos_indice       text[] not null default '{}',
    organizacoes        text[] not null default '{}',
    rotulos_matriz      text[] not null default '{}',
    tem_indicio_entrega boolean not null default false,
    exemplo             text,
    id_documento_origem bigint references documento (id_documento) on delete set null,
    criado_em           timestamptz not null default now(),
    visto_em            timestamptz not null default now(),
    removido_em         timestamptz,

    constraint skill_origem_valida check (origem in ('HEDGE', 'MATRIZ', 'EVIDENCIA')),
    constraint skill_chave_unica unique (id_pessoa, chave_natural)
);

create index if not exists skill_pessoa_idx on skill (id_pessoa) where removido_em is null;
create index if not exists skill_nome_idx on skill (skill) where removido_em is null;
create index if not exists skill_categoria_idx on skill (categoria) where removido_em is null;


create table if not exists certificacao (
    id_certificacao     bigserial primary key,
    id_pessoa           bigint not null references pessoa (id_pessoa) on delete cascade,
    chave_natural       text not null,
    sigla               text not null,
    emissor             text,
    categoria           text,
    exige_renovacao     boolean not null default false,
    ano                 integer,
    texto_origem        text,
    id_documento_origem bigint references documento (id_documento) on delete set null,
    criado_em           timestamptz not null default now(),
    visto_em            timestamptz not null default now(),
    removido_em         timestamptz,

    constraint certificacao_chave_unica unique (id_pessoa, chave_natural)
);

create index if not exists certificacao_pessoa_idx on certificacao (id_pessoa)
    where removido_em is null;
-- sigla '?' = o documento fala de certificação mas a sigla não está no
-- dicionário. É fila de trabalho, não erro.
create index if not exists certificacao_nao_mapeada_idx on certificacao (id_pessoa)
    where sigla = '?';


-- chave natural = (organização normalizada, início). É isto que resolve o
-- caso do emprego em aberto: o currículo antigo diz "Jan 2024 – Till Date",
-- o novo diz "Jan 2024 – Jun 2026". Mesma chave, então o merge fecha o
-- vínculo em vez de criar um segundo.
create table if not exists experiencia (
    id_experiencia      bigserial primary key,
    id_pessoa           bigint not null references pessoa (id_pessoa) on delete cascade,
    chave_natural       text not null,
    organizacao         text,
    organizacao_chave   text,
    cargo               text,
    senioridade         text,
    inicio              date,
    fim                 date,
    em_aberto           boolean not null default false,
    meses               integer,
    texto_origem        text,
    id_documento_origem bigint references documento (id_documento) on delete set null,
    criado_em           timestamptz not null default now(),
    visto_em            timestamptz not null default now(),
    removido_em         timestamptz,

    constraint experiencia_chave_unica unique (id_pessoa, chave_natural),
    constraint experiencia_periodo_coerente check (fim is null or inicio is null or fim >= inicio)
);

create index if not exists experiencia_pessoa_idx on experiencia (id_pessoa)
    where removido_em is null;


-- Linha classificada como afirmação mas sem skill reconhecida. Não é erro:
-- parte é frase genérica sem skill nenhuma, parte é termo fora do
-- dicionário. É a fila de trabalho para ampliar o dicionário.
create table if not exists linha_nao_resolvida (
    id_linha        bigserial primary key,
    id_pessoa       bigint references pessoa (id_pessoa) on delete cascade,
    id_documento    bigint references documento (id_documento) on delete cascade,
    linha           integer not null,
    termo_indice    text,
    texto           text not null,
    resolvida_em    timestamptz,
    criado_em       timestamptz not null default now()
);

create index if not exists linha_nao_resolvida_aberta_idx on linha_nao_resolvida (id_documento)
    where resolvida_em is null;


-- Fila de revisão humana. Os motivos previstos:
--   SEM_TEXTO          documento é imagem/escaneado (aqui entraria o OCR)
--   CONFLITO_IDENTIDADE  o número já tem pessoa e o documento aponta outra
--   SIGLA_NAO_MAPEADA  fala de certificação mas a sigla é desconhecida
--   SEM_FATOS          nada extraído; pode não ser um currículo
--   FORMATO            extensão não suportada
create table if not exists revisao (
    id_revisao      bigserial primary key,
    id_documento    bigint references documento (id_documento) on delete cascade,
    id_pessoa       bigint references pessoa (id_pessoa) on delete set null,
    motivo          text not null,
    detalhe         text,
    resolvido_em    timestamptz,
    resolvido_por   text,
    criado_em       timestamptz not null default now()
);

create index if not exists revisao_aberta_idx on revisao (criado_em)
    where resolvido_em is null;


-- ---------------------------------------------------------------------
-- VISÕES
-- ---------------------------------------------------------------------

-- A pergunta que motiva o projeto: em que a pessoa diz ter competência
-- sem nunca ter mostrado onde usou.
-- Uma linha por (pessoa, skill), não por origem: a mesma skill pode estar
-- afirmada numa frase E listada na matriz, e isso é uma informação só.
drop view if exists vw_skill_sem_evidencia cascade;
create view vw_skill_sem_evidencia as
select
    a.id_pessoa,
    p.nome,
    p.telefone_e164,
    a.skill,
    min(a.categoria)                                    as categoria,
    string_agg(distinct a.origem, '+' order by a.origem) as origens,
    sum(a.mencoes)                                      as mencoes,
    -- subconsulta correlacionada em vez de array_agg sobre arrays: o
    -- array_agg exigiria que todos os arrays tivessem a mesma dimensão
    (select coalesce(array_agg(distinct t), '{}')
       from skill s2, unnest(s2.termos_indice) as t
      where s2.id_pessoa = a.id_pessoa
        and s2.skill = a.skill
        and s2.origem in ('HEDGE', 'MATRIZ')
        and s2.removido_em is null)                     as termos_indice,
    bool_or(a.tem_indicio_entrega)                      as tem_indicio_entrega,
    min(a.exemplo)                                      as exemplo
from skill a
join pessoa p on p.id_pessoa = a.id_pessoa
where a.origem in ('HEDGE', 'MATRIZ')
  and a.removido_em is null
  and not exists (
      select 1
      from skill e
      where e.id_pessoa = a.id_pessoa
        and e.skill = a.skill
        and e.origem = 'EVIDENCIA'
        and e.removido_em is null
  )
group by a.id_pessoa, p.nome, p.telefone_e164, a.skill;

comment on view vw_skill_sem_evidencia is
    'Skill afirmada (hedge ou matriz) que nunca aparece dentro de um emprego datado.';


-- O outro lado: competência amarrada a cliente e período.
drop view if exists vw_skill_comprovada cascade;
create view vw_skill_comprovada as
select
    s.id_pessoa,
    p.nome,
    s.skill,
    s.categoria,
    s.mencoes,
    s.organizacoes,
    s.exemplo
from skill s
join pessoa p on p.id_pessoa = s.id_pessoa
where s.origem = 'EVIDENCIA'
  and s.removido_em is null;


-- Panorama por pessoa, para ranquear candidato.
--
-- Feita com subconsultas em vez de LEFT JOIN de propósito: juntar skill,
-- certificação e experiência na mesma consulta multiplica as linhas, e
-- qualquer SUM sobre isso sai errado (um SUM(DISTINCT meses) esconderia
-- dois empregos de mesma duração).
drop view if exists vw_pessoa_resumo cascade;
create view vw_pessoa_resumo as
select
    p.id_pessoa,
    p.nome,
    p.telefone_e164,
    p.cpf,
    p.email,
    (select count(distinct s.skill) from skill s
      where s.id_pessoa = p.id_pessoa and s.removido_em is null
        and s.origem = 'EVIDENCIA')                     as skills_comprovadas,
    (select count(*) from vw_skill_sem_evidencia v
      where v.id_pessoa = p.id_pessoa)                  as skills_sem_evidencia,
    (select count(distinct s.skill) from skill s
      where s.id_pessoa = p.id_pessoa and s.removido_em is null
        and s.origem in ('HEDGE', 'MATRIZ'))            as skills_afirmadas,
    (select count(*) from certificacao c
      where c.id_pessoa = p.id_pessoa and c.removido_em is null
        and c.sigla <> '?')                             as certificacoes,
    (select count(*) from experiencia e
      where e.id_pessoa = p.id_pessoa and e.removido_em is null) as vinculos,
    (select sum(e.meses) from experiencia e
      where e.id_pessoa = p.id_pessoa and e.removido_em is null) as meses_somados,
    (select max(d.recebido_em) from documento d
      where d.id_pessoa = p.id_pessoa)                  as ultimo_documento
from pessoa p;
