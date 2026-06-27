# FatureX

Sistema automatizado de digitalização, extração e categorização de faturas para uma empresa individual de arquitetura (contribuinte singular português).

## Funcionalidades

- **App Mobile** — Fotografar talões físicos, ler QR Code da AT, introduzir observações livres e categorizar automaticamente via IA
- **Automação Email** — PDFs recebidos por Gmail são processados automaticamente via Google Apps Script
- **Consulta NIF.pt** — Obtenção automatizada do nome da empresa emissora a partir do NIF extraído
- **Relatórios Excel** — Geração de `.xlsx` organizado por Despesas/Receitas, agrupado por categoria, com subtotais e observações
- **Arquivo ZIP** — Exportação compactada das faturas originais (fotos/PDFs) de um dado período num único ficheiro ZIP

## Tech Stack

| Camada | Tecnologia |
|---|---|
| App Mobile | React Native (Expo SDK 54+) |
| Backend | Python 3.11+ / FastAPI |
| Base de Dados | Supabase (PostgreSQL) |
| Storage | Supabase Storage |
| Automação Email | Google Apps Script |
| IA (categorização) | Groq API (`meta-llama/llama-4-scout-17b-16e-instruct`) |
| Consultas NIF | API NIF.pt |
| Relatórios | `openpyxl` |

## Estrutura do Backend

```
backend/
├── main.py                  # Entrada FastAPI, routers, CORS
├── config.py                # Variáveis de ambiente (Pydantic BaseSettings)
├── routes/
│   ├── invoices.py          # POST /api/faturas/mobile e /email
│   └── reports.py           # GET /api/relatorios/excel e /zip
├── services/
│   ├── supabase_client.py   # Wrapper Supabase (DB + Storage)
│   ├── qr_parser.py         # Parse QR Code AT → campos estruturados
│   ├── pdf_processor.py     # Extração QR de PDFs (PyMuPDF + pyzbar)
│   ├── gemini_client.py     # Chamada Groq API para categorização
│   └── nif_service.py       # Consulta de nome de empresa na API NIF.pt
├── models/
│   └── schemas.py           # Modelos Pydantic
└── requirements.txt
```

## Setup

### Pré-requisitos

- Python 3.11+
- Conta Supabase (com tabela `faturas` e bucket `documentos` configurados)
- API Key do Groq
- API Key do NIF.pt

### Instalação

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

### Variáveis de Ambiente

Criar ficheiro `.env` na pasta `backend/`:

```env
API_KEY=<chave-api-do-backend>
SUPABASE_URL=<url-do-projeto-supabase>
SUPABASE_KEY=<chave-do-supabase>
GROQ_API_KEY=<chave-api-groq>
NIF_API_KEY=<chave-api-nif-pt>
```

### Execução

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/faturas/mobile` | Criar fatura (fluxo mobile) |
| `POST` | `/api/faturas/email` | Criar fatura (fluxo email/PDF) |
| `GET` | `/api/relatorios/excel` | Gerar relatório Excel (.xlsx) |
| `GET` | `/api/relatorios/zip` | Gerar arquivo ZIP com faturas originais |

Todos os endpoints (exceto `/`) requerem header `X-API-Key`.

## Licença

Projeto privado — uso pessoal.
