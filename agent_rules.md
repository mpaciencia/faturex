# Regras e Contexto do Agente: Sistema de Gestão de Faturas

> **Âmbito:** Este documento é a fonte de verdade para qualquer agente de IA ou programador que trabalhe neste projeto. Todas as decisões de arquitetura, stack e comportamento estão aqui fixadas. Não deve ser necessário inferir nada — se algo não está aqui, não está decidido.

---

## 1. Contexto do Projeto

O objetivo é construir uma solução automatizada para digitalizar, extrair dados e categorizar faturas (despesas e receitas) de uma empresa individual de arquitetura (contribuinte singular). O sistema **não precisa de escalar** para múltiplos utilizadores — há um único utilizador autenticado. A prioridade é robustez dos dados fiscais portugueses, precisão absoluta dos valores e baixo custo de manutenção.

Os documentos chegam por duas vias:

1. **App Mobile:** O utilizador fotografa talões físicos. A app lê o QR Code da AT nativamente antes de tirar a foto.
2. **Email:** Faturas em PDF recebidas no Gmail são encaminhadas automaticamente ao backend via Google Apps Script.

O resultado final é um ficheiro `.xlsx` gerado a pedido, filtrado por intervalo de datas, com faturas organizadas por tipo (Despesa/Receita) e categoria, pronto para enviar ao contabilista.

---

## 2. Arquitetura e Tech Stack

| Camada | Tecnologia | Notas |
|---|---|---|
| App Mobile | React Native (Expo SDK 51+) | `expo-camera` com `BarcodeScanner` integrado (Vision Camera API) |
| Backend | Python 3.11+ com FastAPI | Uvicorn como servidor ASGI |
| Base de Dados | Supabase (PostgreSQL) | Dados estruturados das faturas |
| Storage | Supabase Storage | PDFs e fotos originais dos talões |
| Automação Email | Google Apps Script | Escuta Gmail e faz POST ao backend |
| IA (categorização) | Google Gemini API — modelo `gemini-2.0-flash` | **Apenas** para inferir a categoria; nunca para dados fiscais |
| Relatórios | `openpyxl` (Python) | Geração do `.xlsx`; `pandas` não é necessário |

### Estrutura de Diretórios do Backend

```
backend/
├── main.py                  # Entrada FastAPI, registo de routers, CORS
├── config.py                # Variáveis de ambiente (Pydantic BaseSettings)
├── routes/
│   ├── invoices.py          # POST /api/faturas/mobile e /api/faturas/email
│   └── reports.py           # GET /api/relatorios
├── services/
│   ├── supabase_client.py   # Wrapper de acesso ao Supabase (DB + Storage)
│   ├── qr_parser.py         # Parse da string QR Code AT → campos estruturados
│   ├── pdf_processor.py     # Extração do QR Code de PDFs com PyMuPDF + pyzbar
│   └── gemini_client.py     # Chamada à Gemini API para inferir categoria
├── models/
│   └── schemas.py           # Modelos Pydantic de entrada e saída
└── requirements.txt
```

---

## 3. Segurança e Autenticação

Todos os endpoints do backend são protegidos por **API Key estática** transmitida no header HTTP `X-API-Key`. A chave é definida como variável de ambiente (`API_KEY`) e validada por um middleware/dependency FastAPI em todas as rotas.

O Google Apps Script e a App Mobile incluem este header em todos os pedidos. Sem a chave correta, o backend responde `401 Unauthorized` sem processar nada.

Não se usa autenticação JWT nem Supabase Auth — o sistema tem um único utilizador e a API Key é suficiente para o contexto.

---

## 4. Base de Dados — Tabela `faturas`

```sql
CREATE TABLE faturas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    atcud           TEXT UNIQUE NOT NULL,        -- Código único AT; garante idempotência
    raw_qr_string   TEXT NOT NULL,               -- String original do QR (para auditoria/debug)
    tipo            TEXT NOT NULL CHECK (tipo IN ('Despesa', 'Receita')),
    nif_emissor     TEXT NOT NULL,               -- Extraído do QR
    data_fatura     DATE NOT NULL,               -- Extraído do QR
    valor_total     NUMERIC(10, 2) NOT NULL,     -- Extraído do QR (€)
    imposto_total   NUMERIC(10, 2) NOT NULL,     -- Extraído do QR (IVA em €)
    categoria       TEXT NOT NULL,               -- Inferido pelo Gemini
    url_documento   TEXT NOT NULL,               -- URL público/privado no Supabase Storage
    origem          TEXT NOT NULL CHECK (origem IN ('Mobile', 'Email')),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Decisões explícitas:**

- `atcud` tem constraint `UNIQUE` — impede inserção de faturas duplicadas independentemente da via de entrada.
- Usa-se `NUMERIC(10, 2)` e nunca `FLOAT` para valores monetários, evitando erros de arredondamento em casa decimal.
- `raw_qr_string` guarda a string bruta para permitir reprocessamento sem precisar do documento original.

---

## 5. Parse do QR Code AT (Formato Português)

O QR Code das faturas portuguesas segue o formato definido pela AT (Portaria n.º 195/2020). A string tem campos separados por `*`, com chaves fixas e ordem obrigatória.

Campos a extrair obrigatoriamente:

| Campo QR | Significado | Campo DB |
|---|---|---|
| `A:` | NIF do emissor | `nif_emissor` |
| `F:` | Data da fatura (YYYYMMDD) | `data_fatura` |
| `H:` | ATCUD | `atcud` |
| `O:` | Total com impostos | `valor_total` |
| `N:` | Total de impostos (IVA) | `imposto_total` |

> **Nota:** `I1:` indica o espaço fiscal (`PT`, `PT-AC`, `PT-MA`), não o valor de IVA. Os valores de IVA por taxa estão em pares de campos (`I3:`/`I4:`, `I5:`/`I6:`, `I7:`/`I8:`), mas não são necessários para o registo base.

O serviço `qr_parser.py` é responsável por este parse. Se algum campo obrigatório estiver ausente ou malformado, lança uma exceção interna que o router transforma em `400 Bad Request` com mensagem descritiva.

---

## 6. Fluxos de Trabalho

### Fluxo A — App Mobile (Talão Físico)

1. O utilizador abre a app e aponta a câmara ao QR Code da fatura.
2. A app lê e faz parse do QR Code **antes** de tirar a foto — valida que os campos obrigatórios existem no cliente.
3. A app captura a foto do talão.
4. A app envia um pedido `POST /api/faturas/mobile` como `multipart/form-data` com:
   - Campo `qr_data`: JSON com os campos extraídos do QR.
   - Campo `tipo`: `"Despesa"` ou `"Receita"` (selecionado pelo utilizador).
   - Campo `file`: imagem JPEG/PNG do talão.
5. O backend valida o payload com Pydantic, verifica se `atcud` já existe na DB (retorna `409 Conflict` se sim), guarda a imagem no Supabase Storage, chama o Gemini com a imagem para obter a `categoria`, e insere o registo na tabela `faturas`.
6. Responde `201 Created` com o `id` e `categoria` atribuída.

### Fluxo B — Gmail / Google Apps Script (PDF por Email)

1. O Google Apps Script corre periodicamente (trigger de tempo) e deteta emails com a label `"Faturas"` ou com anexos PDF não processados.
2. O script envia um pedido `POST /api/faturas/email` com `multipart/form-data`:
   - Campo `tipo`: `"Despesa"` ou `"Receita"` (definido pela sub-label do email ou por defeito `"Despesa"`).
   - Campo `file`: PDF binário.
3. O backend recebe o PDF, usa **PyMuPDF (`fitz`)** para renderizar a primeira página como imagem PNG em memória, e usa **`pyzbar`** para decodificar o QR Code da imagem renderizada.
4. Faz parse da string QR com `qr_parser.py`. Se ilegível, responde `400 Bad Request` — o script marca o email como falhado e não tenta reenviar automaticamente (evita spam de erros).
5. Verifica idempotência via `atcud`. Se já existir, responde `409 Conflict` — o script marca como duplicado.
6. Envia a imagem PNG da primeira página ao Gemini para inferir a `categoria`.
7. Guarda o PDF original no Supabase Storage e insere o registo na DB.
8. Responde `201 Created`.

### Fluxo C — Geração de Relatório Excel

1. O utilizador seleciona `data_inicio` e `data_fim` na app e solicita o relatório.
2. A app envia `GET /api/relatorios?data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD`.
3. O backend faz query ao Supabase filtrando `data_fatura` no intervalo (inclusive nos dois extremos).
4. Constrói um ficheiro `.xlsx` com `openpyxl` com a seguinte estrutura:
   - Folha **"Despesas"**: todas as faturas do tipo `Despesa`, agrupadas por `categoria`, com subtotal por categoria e total geral no fim.
   - Folha **"Receitas"**: idem para `Receita`.
   - Colunas: `Data`, `NIF Emissor`, `Categoria`, `IVA (€)`, `Total (€)`.
5. O backend devolve o ficheiro diretamente no response HTTP com `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` e header `Content-Disposition: attachment; filename="relatorio_YYYYMMDD_YYYYMMDD.xlsx"`.
6. A app faz download do ficheiro binário e disponibiliza-o para partilha/email via `expo-sharing`.

---

## 7. Integração com Gemini API

- Modelo: `gemini-2.0-flash`
- O Gemini é invocado **exclusivamente** para inferir a `categoria`. Nunca para extrair dados fiscais.
- O prompt enviado é sempre estruturado para forçar uma resposta em JSON com um único campo:

```
Analisa esta imagem de uma fatura/talão de uma empresa de arquitetura portuguesa.
Responde APENAS com um objeto JSON válido, sem texto adicional, sem markdown:
{"categoria": "<categoria>"}

Categorias possíveis: Material de Escritório, Deslocações e Transportes,
Alimentação e Representação, Telecomunicações, Software e Serviços Digitais,
Equipamento e Ferramentas, Obras e Materiais de Construção, Serviços Externos,
Publicidade e Marketing, Outros.

Se não conseguires determinar a categoria, usa "Outros".
```

- O backend faz parse do JSON da resposta e valida que `categoria` é uma das strings permitidas. Se não for, usa `"Outros"` em vez de falhar.

---

## 8. Regras Estritas de Implementação

**Prioridade absoluta ao QR Code:** Os campos `nif_emissor`, `data_fatura`, `valor_total` e `imposto_total` provêm **sempre e exclusivamente** do QR Code da AT. O Gemini nunca é consultado para estes valores.

**Idempotência:** Antes de qualquer inserção, verificar se o `atcud` já existe. Se sim, `409 Conflict` — nunca inserir duplicados.

**Sem dados sujos:** Se o QR Code for ilegível ou incompleto, o pedido é rejeitado com `400 Bad Request` e uma mensagem que identifica qual campo falhou. Não se insere nada parcialmente.

**Tipagem forte:** Todos os modelos de entrada e saída são definidos como classes Pydantic em `models/schemas.py`. Não se aceita `dict` raw em nenhum router.

**Valores monetários:** Usar sempre `Decimal` (Python) e `NUMERIC(10,2)` (PostgreSQL). Nunca `float`.

**Storage:** O ficheiro é guardado no Supabase Storage com path `{origem}/{ano}/{mes}/{atcud}.{ext}` (ex: `email/2025/06/ABCD1234-1.pdf`). A `url_documento` guardada na DB é a URL pública ou signed URL consoante o bucket ser público ou privado.

**Variáveis de ambiente obrigatórias** (nunca hardcoded no código):

```
API_KEY
SUPABASE_URL
SUPABASE_KEY
GEMINI_API_KEY
```

**Modularidade:** Cada ficheiro em `services/` tem uma única responsabilidade. Os routers em `routes/` apenas orquestram — não contêm lógica de negócio diretamente.
