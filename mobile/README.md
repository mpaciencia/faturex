# FatureX Mobile

MVP do fluxo core da app móvel:

- ler QR Code da AT com a câmara
- tirar foto do talão ou escolher da galeria
- selecionar `Despesa` ou `Receita`
- enviar `multipart/form-data` para o backend FastAPI

## Configuração

Criar um ficheiro `.env` com:

```env
EXPO_PUBLIC_FATUREX_API_BASE_URL=http://192.168.1.10:8000
EXPO_PUBLIC_FATUREX_API_KEY=coloca_a_tua_api_key_aqui
```

## Arranque

```bash
npm install
npx expo start --tunnel
```

Ou, se preferires a rede local:

```bash
npx expo start --lan
```
