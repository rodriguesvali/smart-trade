# Backend Build - MVP Pipeline de Treinamento

## Status

Build backend em andamento para o MVP resetado do pipeline de treinamento. A fatia atual separa os entrypoints de API e worker em processos Python distintos sobre um pacote backend compartilhado, mantendo treinamento assíncrono, candles reais via CCXT e dataset sintético apenas como modo explícito de desenvolvimento/teste.

## Escopo Implementado

- Backend FastAPI com Swagger/OpenAPI em `/docs`.
- Catálogo de estratégias com uma estratégia registrada: `RSI Sentiment XGBoost`.
- Endpoint para listar estratégias.
- Endpoint para abrir detalhes da estratégia.
- Endpoint para solicitar treinamento, retornando `202 Accepted` com execução `PENDING`.
- Worker assíncrono `smart_trade_training_worker.main` para reivindicar execuções pendentes e treinar fora do ciclo HTTP.
- Entrypoint HTTP separado em `smart_trade_api.main`, sem hospedar o loop do worker.
- Acompanhamento da execução por `progress_phase`, `progress_pct`, `progress_message`, `worker_id`, `locked_at` e `heartbeat_at`.
- `timeframe` tratado como parâmetro de treinamento, com default `M5`, e não como metadado fixo da estratégia.
- `training_rows` e `holdout_ratio` calculados pelo backend a partir do `timeframe`: janela bruta de 30 dias, warmup de indicadores, `target_n` para rótulos futuros e holdout final fixo de 72h.
- `exchange_id`, `data_mode` e `sentiment_required` tratados como parâmetros/configuração de treinamento.
- Adapter público CCXT para coleta de candles OHLCV reais da exchange configurada.
- Feature engineering real com pandas/NumPy para RSI/IFR e operadores de sentimento vindos da CCXT quando `sentiment_required=true`.
- Provider CCXT de sentimento para Open Interest, Long/Short Ratio e Taker Buy/Sell Ratio do mercado perpétuo correspondente.
- Guarda explícita para a retenção pública da Binance: os endpoints públicos desses indicadores de sentimento não suportam janela de 3 meses.
- Geração de um novo modelo treinado por execução.
- Persistência de execução, modelo, métricas, resultados de validação e eventos de auditoria via SQLAlchemy.
- Treinamento XGBoost determinístico sobre dataset sintético de desenvolvimento, com features RSI/IFR, Open Interest RoC, Long/Short Ratio e Taker Buy/Sell Ratio.
- Treinamento XGBoost com dataset real salvo junto ao artefato do modelo em `.dataset.npz`, permitindo validação reprodutível do mesmo modelo.
- Target de treinamento simplificado para o MVP spot long-only: label positivo somente quando `RSI/IFR <= rsi_oversold_threshold` e o preço fecha acima do preço atual após `target_n` candles.
- Parâmetros operacionais de validação/backtest (`probability_threshold`, TP, SL, trailing, custos e folds) separados do pedido de treinamento e aceitos no corpo de `POST /api/models/{model_id}/validate`.
- Artefato XGBoost salvo em formato nativo `.json`.
- Resposta de modelo expõe `dataset_metadata` com modo, exchange, símbolo, timeframe, fonte, período e janelas cronológicas.
- Endpoint explícito para executar validação do modelo pelo Swagger.
- Scorecard de validação com métricas de ML e métricas operacionais simuladas.
- Validação operacional sequencial no holdout, com gate de RSI/IFR, confirmação do modelo, posição única, TP/SL por `high`/`low` de candles futuros fechados, trailing stop após movimento favorável e custos round-trip opcionais.
- Análise de threshold de confiança no holdout com grade `0.50`, `0.55`, `0.60`, `0.65`, `0.70` e `0.75`, usando o mesmo backtest operacional para comparar sinais, trades, resultado, fator de lucro, drawdown, win rate e expectancy.
- Evidência walk-forward com múltiplos folds temporais antes do holdout, embargo baseado em `target_n`, retreino por fold, métricas de ML, métricas operacionais por fold e agregados de estabilidade.
- Endpoints de aprovação/rejeição incluídos como continuação natural do ciclo, com rejeição exigindo comentário.
- Endpoint para excluir modelos já `REJECTED`, com confirmação explícita, limpeza de artefatos, remoção das listas operacionais e evento de auditoria `MODEL_DELETED`.
- Endpoint `GET /api/audit-events`.

## Arquitetura Hexagonal + DDD

Após revisão arquitetural, o backend foi reorganizado para separar domínio, aplicação, adapters, infraestrutura e entrypoints executáveis:

- `backend/smart_trade/domain/`
  - Entidades e regras de negócio independentes de framework.
  - Enums de status para estratégias, execuções, modelos e decisões.
  - Políticas de transição: aprovação apenas de modelo `VALIDATED`, rejeição com comentário obrigatório, finalização imutável de modelos aprovados/rejeitados e exclusão permitida somente para modelo `REJECTED`.
- `backend/smart_trade/application/ports/`
  - Portas para repositórios, trainer, validator, market data, relógio e geração de IDs.
- `backend/smart_trade/application/use_cases/`
  - Casos de uso de treinamento, validação, consulta, aprovação e rejeição.
  - Não importa FastAPI, SQLAlchemy, XGBoost, sklearn, numpy nem filesystem.
- `backend/smart_trade/adapters/api/`
  - Adapter de entrada FastAPI/Swagger.
  - Faz mapeamento HTTP/DTO e converte exceções de domínio em respostas HTTP.
- `backend/smart_trade/adapters/persistence/`
  - Adapter SQLAlchemy.
  - Converte records ORM para entidades de domínio e vice-versa.
- `backend/smart_trade/adapters/ml/`
  - Adapters XGBoost para dataset real e dataset sintético de desenvolvimento.
  - Implementa as portas `ModelTrainer` e `ModelValidator`.
- `backend/smart_trade/adapters/market_data/`
  - Adapter público CCXT para candles OHLCV.
- `backend/smart_trade/infrastructure/`
  - Configuração, sessão de banco, composição de dependências, relógio e UUID.
- `backend/smart_trade_api/`
  - Entrypoint FastAPI/Uvicorn para Swagger e contratos HTTP.
- `backend/smart_trade_training_worker/`
  - Entrypoint de background que usa os mesmos casos de uso de aplicação.
  - Reivindica uma execução `PENDING` por vez no repositório e mantém concorrência efetiva em 1 worker local.

Checagem executada:

- `rg -n "fastapi|sqlalchemy|ccxt|pandas|xgboost|sklearn|numpy|Path\\(" backend/smart_trade/domain backend/smart_trade/application`: sem ocorrências.

## Documentação Consultada

- FastAPI via Context7: path operations com response models e documentação OpenAPI automática.
- SQLAlchemy 2.0 ORM/Core via Context7: `create_engine`, `sessionmaker`, declarative mappings, consultas ORM com `select()`/`Session.execute()`, `inspect()`/`get_columns()` e DDL textual para migração local de compatibilidade.
- SQLAlchemy 2.0 ORM via Context7: `Session.delete()` marca instâncias para deleção e emite o `DELETE` no próximo `commit`/`flush`, preservando cascades ORM configurados.
- FastAPI via Context7: operações `DELETE`, request body com modelo Pydantic, `response_model` e documentação OpenAPI automática.
- CCXT via Context7: métodos `fetchOpenInterestHistory` e `fetchLongShortRatioHistory`, parâmetros `since`, `limit` e `params.until`.
- XGBoost via Context7: `save_model`/`load_model` com formatos nativos `.json` e `.ubj`.
- XGBoost via Context7: `XGBClassifier` com objetivo `binary:logistic`, `fit`, `predict_proba`, hiperparâmetros de árvores e persistência nativa em JSON.
- Binance Developers: endpoints públicos de Open Interest Statistics, Long/Short Ratio e Taker Long/Short Ratio documentam retenção aproximada de 30 dias/1 mês.
- Artefato citado pelo agente backend, `project-context/2.build/setup.md`, não existe no workspace atual; implementação seguiu PRD, SAD, regra native-python e documentação deste backend build.

## Contratos Swagger Principais

- `GET /api/strategies`
- `GET /api/strategies/{strategy_id}`
- `POST /api/strategies/{strategy_id}/training-runs`
  - Corpo aceita `exchange_id`, `data_mode`, `sentiment_required`, `symbol`, `sentiment_symbol`, `timeframe`, `target_n`, `rsi_oversold_threshold`, `xgboost` e `training_rows` legado.
  - `training_rows`, se enviado por clientes legados, é ignorado e registrado em `training_window_policy.ignored_request_overrides`.
  - Parâmetros de execução como TP, SL e trailing não fazem parte do contrato oficial de treinamento.
  - Retorna `202 Accepted` com status inicial `PENDING`; o modelo aparece depois que o worker concluir a execução.
- `GET /api/training-runs/{run_id}`
- `GET /api/strategies/{strategy_id}/models`
- `GET /api/models/{model_id}`
- `POST /api/models/{model_id}/validate`
  - Corpo opcional aceita `probability_threshold`, `rsi_oversold_threshold`, `take_profit_pct`, `stop_loss_pct`, `trailing_stop_enabled`, `trailing_activation_pct`, `trailing_distance_pct`, `fee_pct`, `slippage_pct`, `threshold_min_trades`, `walk_forward_folds` e `walk_forward_embargo_rows`.
  - Quando omitido, usa defaults de validação registrados no catálogo da estratégia.
- `POST /api/models/{model_id}/approve`
- `POST /api/models/{model_id}/reject`
- `DELETE /api/models/{model_id}`
  - Corpo exige `confirmed=true`, aceita `operator` e `comments`.
  - Retorna `409` se o modelo não estiver em `REJECTED`.
  - Em sucesso, remove o modelo das leituras operacionais, apaga o artefato `.json` e dataset `.dataset.npz` quando existirem, e registra `MODEL_DELETED`.
- `GET /api/audit-events`

## Observações

- O backend usa SQLite por padrão para execução local imediata (`sqlite:///./var/smart_trade.db`) e aceita `SMART_TRADE_DATABASE_URL` para MySQL, alinhado ao `compose.yaml`.
- A validação automática prevista no SAD pode ser acionada pelo campo `auto_validate` do endpoint de treinamento. Quando `true`, o worker valida o modelo logo após o treinamento. Para o fluxo Swagger solicitado, o default é `false`, permitindo treinar primeiro e depois executar validação manualmente via `POST /api/models/{model_id}/validate`.
- Alembic ainda não foi materializado nesta fatia; a persistência usa `create_all` no startup para permitir validação rápida do fluxo backend. A próxima fatia de build deve substituir isso por migrações Alembic versionadas.
- Enquanto Alembic não entra, há uma migração local de compatibilidade para adicionar as colunas de controle assíncrono em bancos SQLite já existentes.
- O modo de produto default é `SMART_TRADE_DATA_MODE=real`, usando `ccxt.fetch_ohlcv` para candles fechados. Para testes automatizados, `SMART_TRADE_DATA_MODE=synthetic` evita dependência de rede.
- `sentiment_required=true` exige Open Interest, Long/Short Ratio e Taker Buy/Sell Ratio via CCXT. `sentiment_required=false` permite fallback para proxies OHLCV claramente marcados em `feature_schema.dataset.sentiment_status=ohlcv_proxy_features`.
- O treinamento agora separa contexto/dataset e hiperparâmetros XGBoost dos parâmetros de validação. O bloco `default_parameters.validation` no catálogo guarda defaults operacionais para validação, mas o target treinado não usa TP/SL/trailing.
- Para respeitar o MVP spot long-only, a validação operacional só transforma inferência em candidato de entrada quando o candle está em zona sobrevendida (`RSI/IFR <= rsi_oversold_threshold`). Zona sobrecomprada não gera confirmação de entrada short.
- O treinamento usa uma política de janela calculada pelo backend. `training_rows` recebido pelo Swagger é tratado como override legado e ignorado. Em `M5` com `target_n=15`, a janela bruta de 30 dias possui `8640` candles, dos quais `80` são warmup, `15` são horizonte futuro de rótulo, `8545` viram linhas úteis, `864` compõem o holdout final de 72h e `7681` ficam para treino/validação/walk-forward.
- Com `exchange_id=binance` e `sentiment_required=true`, a janela real fica limitada pela retenção dos endpoints públicos de sentimento da Binance. Treinamento de 3 meses com esses três indicadores exigirá um provedor histórico externo ou persistência própria de coleta contínua.
- A consulta de sentimento usa exatamente a janela de candles fechados coletados, sem buffer anterior, para manter o treinamento `M5` dentro da retenção pública aproximada de 30 dias da Binance.
- A paginação dos indicadores de sentimento usa janelas coerentes `startTime`/`endTime` por página para evitar combinações inválidas dentro da retenção suportada.
- A validação operacional não trata mais todo sinal bruto acima do threshold como trade independente. O scorecard separa `signals_generated`, `entry_candidates`, `blocked_by_open_position` e `simulated_trades` para evidenciar o funil real da estratégia.
- O backtest usa `high`/`low` para detectar TP/SL intra-candle em candles futuros fechados. Quando TP e SL são tocados no mesmo candle, a validação usa decisão conservadora e registra stop primeiro.
- O trailing stop fica habilitado por default. Ele ativa após movimento favorável igual ao `stop_loss_pct` e usa distância igual ao `stop_loss_pct`, salvo override explícito. Por conservadorismo em candles agregados, uma atualização de trailing passa a valer a partir do candle seguinte.
- A análise de threshold registra uma recomendação em `window_metadata.threshold_analysis.recommended_probability_threshold`, mas não aprova modelo automaticamente. A regra de recomendação exige quantidade mínima de trades, resultado positivo e expectancy positiva; entre elegíveis, escolhe maior profit factor e depois maior resultado líquido.
- O walk-forward aplica embargo entre fim do treino e início da validação para reduzir vazamento temporal causado por labels que olham `target_n` candles à frente.
- O `validation_summary` agora inclui `window_metadata`, preservando a evidência walk-forward no resumo exibido pela API de detalhe do modelo.

## Evidência de Verificação

- `cd backend && .venv/bin/python -m pytest -q tests`: 14 passed.
- Checagem arquitetural: `rg -n "fastapi|sqlalchemy|ccxt|pandas|xgboost|sklearn|numpy|Path\\(" backend/smart_trade/domain backend/smart_trade/application` sem ocorrências.
- Teste de exclusão de modelo rejeitado cobre: bloqueio para `VALIDATED`, rejeição com comentário, `DELETE /api/models/{model_id}` com confirmação, remoção de `GET /api/models/{model_id}`, ausência na lista por estratégia, remoção de artefatos e evento `MODEL_DELETED`.
- Testes de validação cobrem: backtest sequencial bloqueando novos candidatos enquanto há posição aberta, decisão conservadora quando TP/SL ocorrem no mesmo candle, trailing stop após movimento favorável, embargo walk-forward, persistência/API de `entry_candidates` e exposição de `walk_forward` no `validation_summary`.
- Testes de backend cobrem envio de parâmetros próprios no corpo de validação e persistência de `probability_threshold`/`rsi_oversold_threshold` aplicados no resultado operacional.
- Testes do builder real cobrem metadado `target_label_mode=long_only_oversold_reversal_after_n_candles`, deixando explícito que o label de treino não depende mais de TP/SL/trailing.
- Testes de threshold cobrem presença de `0.70` e `0.75` na análise e persistência da recomendação no `validation_summary.window_metadata`.
- Testes de janela calculada cobrem: política M5 de 30 dias, `8545` linhas úteis com `target_n=15`, holdout de `864` candles e registro de override legado de `training_rows` ignorado.
- Teste do adapter real cobre que a consulta de sentimento começa no primeiro candle coletado, evitando extrapolar a retenção da Binance com buffer anterior.
- Validação JSON: `.vscode/launch.json` e `.vscode/tasks.json` válidos via `python -m json.tool`.
- Smoke interno do builder real: dataset real em memória produziu `(252, 4)` features com metadados `mode=real`.
- Smoke CCXT público: `binance BTC/USDT M5` retornou candles fechados.
- Smoke anterior do pipeline real com `binance BTC/USDT M5`:
  - Dataset real com sentimento CCXT produziu modelo e `dataset_metadata.mode=real`.
  - Metadados incluíram `sentiment_status=ccxt_derivatives_sentiment`, `requested_training_rows=180` e `usable_rows=180`.
  - Validação do modelo real retornou métricas de ML e operacionais.
- Smoke HTTP assíncrono com servidor local:
  - `GET /health` retornou `{"status":"ok"}`.
  - `GET /api/strategies` retornou exatamente uma estratégia, `rsi_sentiment_xgboost_m1`.
  - `GET /openapi.json` expôs `POST /api/strategies/{strategy_id}/training-runs` com resposta `202`.
  - `POST /api/strategies/{strategy_id}/training-runs` retornou execução `PENDING` sem `model_id`, com janela calculada registrada em `requested_parameters.training_window_policy`.
  - Uma passada do worker sintético (`run_once("smoke-worker")`) processou a execução.
  - `GET /api/training-runs/{run_id}` retornou execução `TRAINED` com `model_id` e `progress_phase=trained`.

## Como Executar

Para iniciar o servidor local:

- `cd backend`
- `source .venv/bin/activate`
- `uvicorn smart_trade_api.main:app --host 0.0.0.0 --port 8000 --reload`
- Swagger: `http://127.0.0.1:8000/docs`

Para iniciar o worker de treinamento em outro terminal:

- `cd backend`
- `source .venv/bin/activate`
- `python -m smart_trade_training_worker.main`

No VS Code, use o compound `Backend: API + Worker` para subir API e worker juntos.

Fluxo mínimo via Swagger:

1. `GET /api/strategies`
2. `POST /api/strategies/{strategy_id}/training-runs`
3. Copiar `id` da execução retornada.
4. Consultar `GET /api/training-runs/{run_id}` até `status=TRAINED`.
5. Copiar `model_id` da execução treinada.
6. `GET /api/models/{model_id}`
7. `POST /api/models/{model_id}/validate`

Payload mínimo real recomendado no Swagger:

Treinamento:

```json
{
  "exchange_id": "binance",
  "symbol": "BTC/USDT",
  "sentiment_symbol": "BTC/USDT:USDT",
  "timeframe": "M5",
  "target_n": 5,
  "sentiment_required": true
}
```

Validação:

```json
{
  "probability_threshold": 0.7,
  "rsi_oversold_threshold": 30,
  "take_profit_pct": 0.0002,
  "stop_loss_pct": 0.0002,
  "trailing_stop_enabled": true,
  "trailing_activation_pct": 0.0002,
  "trailing_distance_pct": 0.0002
}
```
