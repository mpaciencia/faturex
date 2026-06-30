# Resolução de Problemas Bloqueantes para Produção (Go/No-Go) e Melhorias

Este plano detalha as correções necessárias para endereçar os cinco problemas bloqueantes identificados no código do backend e frontend, juntamente com melhorias recomendadas para segurança, tratamento de erros, performance e prontidão para produção.

---

## User Review Required

> [!IMPORTANT]
> **Decisão sobre Isolamento de Dados e RLS:**
> Como o backend usa a *service role key* para interagir com o Supabase, as políticas de RLS (Row Level Security) na base de dados e no Storage não são avaliadas pelo Supabase. O isolamento de dados baseia-se exclusivamente nos filtros explicitados em Python (`.eq("user_id", user_id)`). Esta decisão arquitetural foi explicitamente documentada no código e em `agent_rules.md` para evitar falsas sensações de segurança em futuras extensões do sistema.

> [!NOTE]
> **Ajuste de CORS configurável:**
> Em vez de fixar estaticamente um único domínio no código, introduzimos a variável `ALLOWED_ORIGINS` no `config.py` (lida a partir de `.env`). O valor padrão local será mantido para desenvolvimento e, em produção, será configurado com o domínio real do Vercel (ex: `https://faturex.vercel.app`). Como o Vercel gera também URLs de preview por branch/PR (`https://faturex-git-<branch>-<org>.vercel.app`), adiciona-se `ALLOWED_ORIGIN_REGEX` para cobrir esses domínios sem reabrir o CORS por completo.

---

## Open Questions

Não existem questões em aberto. Todas as correções propostas seguem as boas práticas habituais e os requisitos delineados.

---

## Proposed Changes

### Componente: Configuração & Segurança (Backend)

#### [MODIFY] [config.py](file:///c:/Projetos%20Pessoais/faturex/backend/config.py)
- Adicionar a propriedade `ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"` à classe `Settings` para permitir a configuração dinâmica das origens fixas do CORS.
- Adicionar a propriedade opcional `ALLOWED_ORIGIN_REGEX: str = ""` para cobrir os domínios de preview gerados automaticamente pelo Vercel a cada branch/PR (ex: `^https://faturex-git-.*\.vercel\.app$`), evitando ter de atualizar `ALLOWED_ORIGINS` manualmente em cada deploy de preview.

#### [MODIFY] [main.py](file:///c:/Projetos%20Pessoais/faturex/backend/main.py)
- Atualizar o middleware de CORS para restringir origens usando a lista configurada em `settings.ALLOWED_ORIGINS` (em vez de `*`) e, se definido, `settings.ALLOWED_ORIGIN_REGEX` via `allow_origin_regex`. Habilitar `allow_credentials=True` e limitar os métodos e cabeçalhos permitidos (`Authorization`, `Content-Type`).
- Remover o endpoint de debug exposto `/api/test-error` (linhas 54-67).
- Nota: o backend corre no Render free tier, que tem cold starts (~30-60s após inatividade) semelhantes ao caso já documentado para o F1 do Azure App Service — mantém-se a decisão de aceitar este comportamento dado tratar-se de um sistema de utilizador único.

#### [MODIFY] [requirements.txt](file:///c:/Projetos%20Pessoais/faturex/backend/requirements.txt)
- Remover a dependência morta `google-generativeai==0.8.4` para otimizar o tempo de build e reduzir a superfície de vulnerabilidades.

---

### Componente: Serviços do Backend & Segurança (Sanitização)

#### [MODIFY] [invoices.py](file:///c:/Projetos%20Pessoais/faturex/backend/routes/invoices.py)
- Sanitizar o parâmetro `atcud` na função `_build_storage_path` contra path traversal usando um regex whitelist (`^[A-Za-z0-9\-]+$`). Caso não valide, lança um `HTTPException(status_code=400)`.
- Tornar assíncrona a consulta do nome do emissor em `criar_fatura_mobile` e `criar_fatura_email` usando `await asyncio.to_thread(get_nome_emissor, ...)` para evitar bloquear o event loop do Uvicorn com chamadas síncronas de rede (`urllib.request.urlopen`).

#### [MODIFY] [qr_parser.py](file:///c:/Projetos%20Pessoais/faturex/backend/services/qr_parser.py)
- Validar o campo `H` (ATCUD) no backend usando o mesmo regex whitelist (`^[A-Za-z0-9\-]+$`) dentro de `parse_qr_string`, levantando `QRParseError` adequado em caso de insucesso.

#### [MODIFY] [supabase_client.py](file:///c:/Projetos%20Pessoais/faturex/backend/services/supabase_client.py)
- Documentar explicitamente nas notas da inicialização do cliente que o uso da `SUPABASE_KEY` (service role key) ignora o RLS, sendo o isolamento assegurado inteiramente pela aplicação Python.
- Robustecer a função `storage_path_from_public_url` para validar e tratar URLs malformados de forma segura, capturando eventuais erros de indexação e retornando um `ValueError` explícito em vez de um `IndexError` genérico (500).

---

### Componente: Processamento de PDF & Geração de Relatórios

#### [MODIFY] [pdf_processor.py](file:///c:/Projetos%20Pessoais/faturex/backend/services/pdf_processor.py)
- Eliminar o carregamento/renderização duplicados da página 0.
- Modificar o fluxo de extração para retornar o `png_bytes` correspondente à página onde o QR Code foi efetivamente detetado (em vez de retornar sempre a página 0), garantindo que a IA categorize a fatura baseando-se no conteúdo relevante da página correta.

#### [MODIFY] [reports.py](file:///c:/Projetos%20Pessoais/faturex/backend/routes/reports.py)
- Corrigir o bug do arquivo ZIP: usar a variável `nome_arquivo` gerada na chamada a `archive.writestr` em vez de passar o `storage_path` completo (evitando a exposição da estrutura interna do bucket/user_id no ZIP).
- Implementar a nomenclatura de ficheiro conforme especificado no README: `{nome_emissor}_{data_fatura}.{ext}` (ou `NIF{nif_emissor}_{data_fatura}.{ext}` caso o nome do emissor seja nulo), sanitizando caracteres inválidos.
- Tornar a criação do ZIP tolerante a falhas individuais: se o download de um documento falhar ou o URL estiver ausente, registar o erro, continuar a processar os restantes e criar um ficheiro `_erros.txt` no final do ZIP com o log das falhas.

---

### Componente: Frontend (Validação de QR Code)

#### [MODIFY] [qrValidation.ts](file:///c:/Projetos%20Pessoais/faturex/frontend/src/utils/qrValidation.ts)
- Adicionar validação de whitelist ao ATCUD no frontend usando a expressão regular `/^[A-Za-z0-9\-]+$/`, disparando um `QrValidationError` amigável caso falhe.

---

### Componente: Testes & CI (Backend)

#### [MODIFY] [test_logging_flow.py](file:///c:/Projetos%20Pessoais/faturex/backend/tests/test_logging_flow.py)
- Corrigir a chamada à função `insert_fatura` nos testes (`test_supabase_insert_success_logs` e `test_supabase_connection_error_logs_exception`) de modo a incluir o argumento `user_id` obrigatório.

#### [MODIFY] [test_qr_parser.py](file:///c:/Projetos%20Pessoais/faturex/backend/tests/test_qr_parser.py)
- Remover a dependência física do ficheiro ausente `fatura2.pdf` na raiz do repositório.
- Substituir o teste `test_extracts_qr_from_second_pdf_page` por um teste mockado robusto que simula a abertura do PDF multipágina, a deteção do QR na segunda página, e a validação do retorno dos bytes da página certa.

---

### Componente: Documentação

#### [MODIFY] [agent_rules.md](file:///c:/Projetos%20Pessoais/faturex/agent_rules.md)
- Atualizar a secção de segurança (Secção 3) para documentar a validação baseada em tokens JWT e explicitar o isolamento de dados no backend em virtude do bypass de RLS pela service role key.

---

## Verification Plan

### Automated Tests
Para validar que as modificações não quebram a CI e que as correções funcionam como planeado:
- Executar a suite de testes unitários do Python a partir da pasta `backend`:
  ```bash
  python -m unittest discover -s tests -p "test_*.py"
  ```

### Manual Verification
- Iniciar o servidor de desenvolvimento FastAPI:
  ```bash
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```
- Executar testes manuais para verificar:
  1. Que pedidos com ATCUD contendo caracteres de path traversal (ex: `../../`) são rejeitados com `400 Bad Request`.
  2. Que a exportação do ZIP contém ficheiros com o nome limpo no formato `{nome_emissor}_{data_fatura}.{ext}`.
  3. Que o CORS está restrito às origens definidas (o domínio de produção Vercel e, se aplicável, URLs de preview que cumpram o `ALLOWED_ORIGIN_REGEX`) — pedidos a partir de outras origens devem falhar no preflight.
  4. Que o endpoint `/api/test-error` já não está acessível (retorna 404).
