# Plano de Finalizacao Backend - Treinamento com Dados Reais

## Status

Plano de build para transformar o backend atual de um MVP com dataset sintetico para um produto funcional de treinamento com dados reais via CCXT.

## Objetivo

Ao final desta etapa, o operador deve conseguir, via Swagger:

1. Listar a estrategia disponivel.
2. Consultar a estrategia e seus parametros padrao.
3. Iniciar uma execucao de treinamento usando dados reais da exchange configurada via CCXT.
4. Obter o modelo treinado gerado por essa execucao.
5. Executar validacao do modelo com dados reais separados cronologicamente.
6. Aprovar ou rejeitar o modelo validado.

## Estado Atual

O backend ja possui:

- FastAPI e Swagger.
- Catalogo de estrategias.
- Casos de uso de treinamento, validacao, aprovacao e rejeicao.
- Persistencia SQLAlchemy de estrategias, execucoes, modelos, validacoes e auditoria.
- Artefato XGBoost em formato nativo `.json`.
- Separacao em arquitetura hexagonal + DDD.

O backend ainda nao possui:

- Coleta real de candles via CCXT.
- Persistencia de candles e/ou datasets de treinamento reais.
- Feature engineering real baseada em dados de mercado.
- Open Interest, Long/Short Ratio e Funding Rate vindos de fonte real.
- Metadados rastreaveis de origem, periodo e qualidade dos dados.
- Alembic materializado para evolucao de schema.

## Decisoes de Implementacao

- **Fonte primaria de dados:** CCXT, usando metodos publicos da exchange configurada.
- **Exchange padrao local:** configuravel por `.env`, sem hardcode arquitetural.
- **Timeframe:** parametro de treinamento, com default `M1`.
- **Indicadores tecnicos:** `pandas` + calculos proprios testados para manter controle sobre janelas retrospectivas e evitar vazamento temporal.
- **Bibliotecas evitadas inicialmente:** `TA-Lib`, por friccao de instalacao nativa; `pandas-ta`, salvo se o calculo proprio se tornar custoso.
- **Sentimento:** preferencialmente via CCXT quando a exchange configurada expuser dados publicos compativeis. Caso alguma feature obrigatoria nao esteja disponivel, a construcao do dataset deve falhar de forma explicita e auditavel.
- **Dataset sintetico:** manter apenas como adapter de desenvolvimento/teste, nunca como default de produto.

## Arquitetura Alvo

Manter a arquitetura hexagonal:

- `domain/`
  - Entidades puras: estrategia, execucao, modelo, validacao, dataset, janela temporal.
  - Regras de status e aprovacao.
- `application/ports/`
  - `MarketDataProvider`
  - `SentimentDataProvider`
  - `TrainingDatasetBuilder`
  - `TrainingDatasetRepository`
  - `ModelTrainer`
  - `ModelValidator`
- `application/use_cases/`
  - Orquestra treinamento sem conhecer CCXT, pandas, SQLAlchemy ou XGBoost.
- `adapters/market_data/`
  - Adapter CCXT publico.
- `adapters/features/`
  - Feature engineering com pandas/NumPy.
- `adapters/ml/`
  - XGBoost trainer/validator.
- `adapters/persistence/`
  - SQLAlchemy repositories e migrations Alembic.

## Plano de Execucao

### B2.1 - Configuracao Real de Dados

Adicionar configuracoes:

- `SMART_TRADE_EXCHANGE_ID`
- `SMART_TRADE_SYMBOL`
- `SMART_TRADE_DEFAULT_TIMEFRAME`
- `SMART_TRADE_TRAINING_LOOKBACK_DAYS`
- `SMART_TRADE_HOLDOUT_DAYS`
- `SMART_TRADE_SENTIMENT_REQUIRED`
- `SMART_TRADE_DATA_MODE=real|synthetic`

Entregaveis:

- `.env.example`
- leitura tipada em `Settings`
- validacao de parametros de treinamento
- Swagger mostrando `exchange`, `symbol`, `timeframe` e janela solicitada

### B2.2 - Adapter CCXT de Candles

Implementar porta `MarketDataProvider` e adapter CCXT:

- buscar OHLCV publico por exchange, simbolo, timeframe e intervalo;
- paginar chamadas ate cobrir a janela necessaria;
- normalizar candles para modelo interno;
- respeitar rate limit do CCXT;
- registrar origem, exchange, simbolo, timeframe, periodo, quantidade de candles e eventuais buracos.

Entregaveis:

- adapter `CcxtMarketDataProvider`
- testes unitarios com provider fake
- teste de integracao opcional marcado para rede real

### B2.3 - Persistencia de Dados Brutos e Dataset

Adicionar tabelas versionadas por Alembic:

- `market_candles`
- `training_datasets`
- `training_dataset_features`

Campos minimos:

- exchange
- symbol
- timeframe
- timestamp do candle
- OHLCV
- source metadata
- dataset id
- periodo de treino, validacao interna e holdout
- hash/configuracao do dataset

Entregaveis:

- migrations Alembic
- repositorios
- indices por exchange/symbol/timeframe/timestamp

### B2.4 - Feature Engineering Real

Criar builder real de dataset:

- calcular `rsi_14` com janela retrospectiva;
- transformar `open_interest` em `open_interest_roc`;
- manter `long_short_ratio` como razao normalizada;
- consumir `funding_rate` do mercado perpétuo correspondente e alinhar retrospectivamente aos candles;
- aplicar lag de seguranca em features de sentimento quando configurado;
- rejeitar dataset com buracos ou features obrigatorias ausentes;
- produzir `feature_schema` com regras, janelas, lag e fonte de cada feature.

Entregaveis:

- `PandasFeatureEngineeringAdapter`
- testes de ausencia de look-ahead
- testes de RSI com serie conhecida
- testes de falha quando sentimento obrigatorio estiver ausente

### B2.5 - Sentiment Data Provider

Implementar a porta `SentimentDataProvider` em duas etapas:

1. Provider nulo/controlado para deixar clara a falha quando sentimento obrigatorio nao existe.
2. Provider CCXT quando a exchange configurada disponibilizar metricas publicas compativeis.

Politica:

- se `SMART_TRADE_SENTIMENT_REQUIRED=true`, treinamento falha sem Open Interest, Long/Short Ratio ou Funding Rate;
- se `false`, features indisponiveis podem ser omitidas somente se a estrategia declarar isso explicitamente;
- para esta estrategia MVP, as tres features de sentimento seguem como obrigatorias ate nova decisao de produto.

Entregaveis:

- metadados de disponibilidade por feature
- erro de dominio claro
- evento de auditoria para indisponibilidade de dados

### B2.6 - Integracao do Treinamento Real

Substituir o default sintetico pelo fluxo real:

1. validar parametros;
2. coletar ou reutilizar candles persistidos;
3. coletar sentimento;
4. construir dataset real;
5. dividir cronologicamente;
6. treinar XGBoost;
7. salvar artefato;
8. persistir modelo e metadados do dataset;
9. permitir validacao via Swagger.

Entregaveis:

- `RealXGBoostTrainingAdapter` ou composicao equivalente
- `SMART_TRADE_DATA_MODE=real` como default de produto
- dataset sintetico restrito a testes/desenvolvimento

### B2.7 - Validacao Real

Atualizar validacao para usar o mesmo dataset real da execucao:

- impedir validar com dataset diferente do usado no treinamento;
- registrar janelas exatas;
- calcular metricas de ML no holdout;
- calcular metricas operacionais simuladas usando retornos reais do holdout;
- preservar scorecard e metadados.

Entregaveis:

- validacao reprodutivel por `model_id`
- scorecard com periodo real
- erro se o dataset original nao estiver disponivel

### B2.8 - Swagger e Observabilidade

Melhorar contratos:

- resposta de treinamento deve mostrar fonte de dados, periodo solicitado, periodo efetivo e quantidade de candles;
- modelo deve mostrar `dataset_id`, `exchange`, `symbol`, `timeframe`, `train_period`, `validation_period`, `holdout_period`;
- erros de dados devem aparecer como mensagens claras no Swagger;
- eventos de auditoria devem registrar coleta, falhas, treinamento, validacao e aprovacao.

Entregaveis:

- DTOs atualizados
- exemplos Swagger
- logs estruturados basicos

### B2.9 - Testes e Gates

Cobertura minima:

- unidade de calculo de RSI;
- unidade de rotulagem do target;
- unidade de split cronologico;
- unidade de deteccao de buracos nos candles;
- unidade de falha quando sentimento obrigatorio esta ausente;
- integracao do fluxo completo com providers fake;
- smoke via Swagger/local para treinamento real quando rede estiver habilitada.

Gate arquitetural:

- `domain/` e `application/` continuam sem importar FastAPI, SQLAlchemy, CCXT, pandas, NumPy, sklearn, XGBoost ou filesystem.

## Criterios de Aceite

O backend sera considerado funcional para treinamento real quando:

1. `POST /api/strategies/{strategy_id}/training-runs` conseguir treinar com `SMART_TRADE_DATA_MODE=real`.
2. O modelo gerado possuir referencia para `dataset_id`, exchange, simbolo, timeframe e periodos reais.
3. A validacao usar dados reais e janelas cronologicas persistidas.
4. O artefato XGBoost `.json` for salvo e recuperavel.
5. O Swagger permitir observar falhas de dados de forma compreensivel.
6. A aprovacao continuar bloqueada ate status `VALIDATED`.
7. Testes automatizados passarem.
8. O adapter sintetico nao for usado no fluxo default de produto.

## Riscos

- **Disponibilidade desigual de sentimento via CCXT:** algumas exchanges podem nao expor Open Interest, Long/Short Ratio ou Funding Rate pela API publica.
- **Granularidade de Funding Rate:** geralmente e mais esparsa que candles M1 e deve ser alinhada retrospectivamente sem look-ahead.
- **Rate limits:** coleta historica pode exigir paginacao com backoff.
- **Buracos de candles:** datasets incompletos precisam falhar ou ser reparados com regra explicita.
- **Look-ahead bias:** qualquer feature com lag ou janela deve ser testada contra vazamento temporal.

## Primeiro Marco Recomendado

Implementar primeiro candles reais via CCXT + RSI real + persistencia de dataset, mantendo sentimento como gate explicito. Isso permite validar a coleta real e a arquitetura antes de resolver a disponibilidade completa das tres features de sentimento.
