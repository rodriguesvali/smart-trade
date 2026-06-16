# Backend Build - MVP Pipeline de Treinamento

## Status

Build backend em andamento para o MVP resetado do pipeline de treinamento. A fatia atual adiciona treinamento com candles reais via CCXT, mantendo o dataset sintético apenas como modo explícito de desenvolvimento/teste.

## Escopo Implementado

- Backend FastAPI com Swagger/OpenAPI em `/docs`.
- Catálogo de estratégias com uma estratégia registrada: `RSI Sentiment XGBoost`.
- Endpoint para listar estratégias.
- Endpoint para abrir detalhes da estratégia.
- Endpoint para iniciar treinamento.
- `timeframe` tratado como parâmetro de treinamento, com default `M5`, e não como metadado fixo da estratégia.
- `exchange_id`, `data_mode` e `sentiment_required` tratados como parâmetros/configuração de treinamento.
- Adapter público CCXT para coleta de candles OHLCV reais da exchange configurada.
- Feature engineering real com pandas/NumPy para RSI/IFR e operadores de sentimento vindos da CCXT quando `sentiment_required=true`.
- Provider CCXT de sentimento para Open Interest, Long/Short Ratio e Taker Buy/Sell Ratio do mercado perpétuo correspondente.
- Geração de um novo modelo treinado por execução.
- Persistência de execução, modelo, métricas, resultados de validação e eventos de auditoria via SQLAlchemy.
- Treinamento XGBoost determinístico sobre dataset sintético de desenvolvimento, com features RSI/IFR, Open Interest RoC, Long/Short Ratio e Taker Buy/Sell Ratio.
- Treinamento XGBoost com dataset real salvo junto ao artefato do modelo em `.dataset.npz`, permitindo validação reprodutível do mesmo modelo.
- Artefato XGBoost salvo em formato nativo `.json`.
- Resposta de modelo expõe `dataset_metadata` com modo, exchange, símbolo, timeframe, fonte, período e janelas cronológicas.
- Endpoint explícito para executar validação do modelo pelo Swagger.
- Scorecard de validação com métricas de ML e métricas operacionais simuladas.
- Endpoints de aprovação/rejeição incluídos como continuação natural do ciclo, com rejeição exigindo comentário.
- Endpoint `GET /api/audit-events`.

## Arquitetura Hexagonal + DDD

Após revisão arquitetural, o backend foi reorganizado para separar domínio, aplicação, adapters e infraestrutura:

- `backend/app/domain/`
  - Entidades e regras de negócio independentes de framework.
  - Enums de status para estratégias, execuções, modelos e decisões.
  - Políticas de transição: aprovação apenas de modelo `VALIDATED`, rejeição com comentário obrigatório, finalização imutável de modelos aprovados/rejeitados.
- `backend/app/application/ports/`
  - Portas para repositórios, trainer, validator, market data, relógio e geração de IDs.
- `backend/app/application/use_cases/`
  - Casos de uso de treinamento, validação, consulta, aprovação e rejeição.
  - Não importa FastAPI, SQLAlchemy, XGBoost, sklearn, numpy nem filesystem.
- `backend/app/adapters/api/`
  - Adapter de entrada FastAPI/Swagger.
  - Faz mapeamento HTTP/DTO e converte exceções de domínio em respostas HTTP.
- `backend/app/adapters/persistence/`
  - Adapter SQLAlchemy.
  - Converte records ORM para entidades de domínio e vice-versa.
- `backend/app/adapters/ml/`
  - Adapters XGBoost para dataset real e dataset sintético de desenvolvimento.
  - Implementa as portas `ModelTrainer` e `ModelValidator`.
- `backend/app/adapters/market_data/`
  - Adapter público CCXT para candles OHLCV.
- `backend/app/infrastructure/`
  - Configuração, sessão de banco, composição de dependências, relógio e UUID.

Checagem executada:

- `rg -n "fastapi|sqlalchemy|ccxt|pandas|xgboost|sklearn|numpy|Path\\(" backend/app/domain backend/app/application`: sem ocorrências.

## Documentação Consultada

- FastAPI via Context7: path operations com response models e documentação OpenAPI automática.
- SQLAlchemy 2.0 ORM via Context7: `create_engine`, `sessionmaker`, declarative mappings e consultas ORM.
- XGBoost via Context7: `save_model`/`load_model` com formatos nativos `.json` e `.ubj`.

## Contratos Swagger Principais

- `GET /api/strategies`
- `GET /api/strategies/{strategy_id}`
- `POST /api/strategies/{strategy_id}/training-runs`
  - Corpo aceita `exchange_id`, `data_mode`, `sentiment_required`, `symbol`, `sentiment_symbol`, `timeframe`, `target_n`, `take_profit_pct`, `stop_loss_pct` e `training_rows`.
- `GET /api/training-runs/{run_id}`
- `GET /api/strategies/{strategy_id}/models`
- `GET /api/models/{model_id}`
- `POST /api/models/{model_id}/validate`
- `POST /api/models/{model_id}/approve`
- `POST /api/models/{model_id}/reject`
- `GET /api/audit-events`

## Observações

- O backend usa SQLite por padrão para execução local imediata (`sqlite:///./var/smart_trade.db`) e aceita `SMART_TRADE_DATABASE_URL` para MySQL, alinhado ao `compose.yaml`.
- A validação automática prevista no SAD pode ser acionada pelo campo `auto_validate` do endpoint de treinamento. Para o fluxo Swagger solicitado, o default é `false`, permitindo treinar primeiro e depois executar validação manualmente via `POST /api/models/{model_id}/validate`.
- Alembic ainda não foi materializado nesta fatia; a persistência usa `create_all` no startup para permitir validação rápida do fluxo backend. A próxima fatia de build deve substituir isso por migrações Alembic versionadas.
- O modo de produto default é `SMART_TRADE_DATA_MODE=real`, usando `ccxt.fetch_ohlcv` para candles fechados. Para testes automatizados, `SMART_TRADE_DATA_MODE=synthetic` evita dependência de rede.
- `sentiment_required=true` exige Open Interest, Long/Short Ratio e Taker Buy/Sell Ratio via CCXT. `sentiment_required=false` permite fallback para proxies OHLCV claramente marcados em `feature_schema.dataset.sentiment_status=ohlcv_proxy_features`.

## Evidência de Verificação

- `backend/.venv/bin/python -m pytest -q backend/tests`: 3 passed.
- Smoke interno do builder real: dataset real em memória produziu `(252, 4)` features com metadados `mode=real`.
- Smoke CCXT público: `binance BTC/USDT M5` retornou candles fechados.
- Smoke HTTP em modo real com `binance BTC/USDT M5`:
  - `POST /api/strategies/{strategy_id}/training-runs` retornou execução `TRAINED`.
  - `GET /api/models/{model_id}` retornou `dataset_metadata.mode=real`, `sentiment_status=ccxt_derivatives_sentiment`, `requested_training_rows=180` e `usable_rows=180`.
  - `POST /api/models/{model_id}/validate` retornou modelo `VALIDATED`.
- Smoke HTTP com servidor local:
  - `GET /health` retornou `{"status":"ok"}`.
  - `GET /api/strategies` retornou exatamente uma estratégia, `rsi_sentiment_xgboost_m1`.
  - `POST /api/strategies/{strategy_id}/training-runs` retornou execução `TRAINED` com `model_id`.
  - `GET /api/models/{model_id}` retornou modelo `TRAINED`.
  - `POST /api/models/{model_id}/validate` retornou modelo `VALIDATED` com métricas de ML e operacionais.

## Como Executar

Para iniciar o servidor local:

- `cd backend`
- `source .venv/bin/activate`
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Swagger: `http://127.0.0.1:8000/docs`

Fluxo mínimo via Swagger:

1. `GET /api/strategies`
2. `POST /api/strategies/{strategy_id}/training-runs`
3. Copiar `model_id` da resposta.
4. `GET /api/models/{model_id}`
5. `POST /api/models/{model_id}/validate`

Payload mínimo real recomendado no Swagger:

```json
{
  "exchange_id": "binance",
  "symbol": "BTC/USDT",
  "sentiment_symbol": "BTC/USDT:USDT",
  "timeframe": "M5",
  "training_rows": 180,
  "target_n": 5,
  "take_profit_pct": 0.0002,
  "stop_loss_pct": 0.0002,
  "sentiment_required": true
}
```
