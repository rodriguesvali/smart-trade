# Frontend Build - Dashboard Operacional

## Status

Primeira versão do frontend Angular + PrimeNG implementada para o MVP do pipeline de treinamento. O dashboard consome exclusivamente a API Python e não acessa banco, arquivos de modelo, logs locais, diretórios de artefato ou credenciais.

## Escopo Implementado

- Projeto Angular criado em `frontend/`.
- Estrutura Feature First:
  - `core/` para API, layout, tema e configuração;
  - `shared/` para componentes reutilizáveis;
  - `features/dashboard`;
  - `features/strategies`;
  - `features/audit`.
- PrimeNG configurado com tema Aura.
- Suporte Light/Dark/System via `ThemeService`, classe `.app-dark` e persistência em `localStorage`.
- Sidebar e shell do dashboard alinhados aos tokens Light/Dark para evitar áreas fixas em tema escuro quando o modo claro está ativo.
- App shell operacional com sidebar, header, status da API, toast e confirm dialog.
- Rotas:
  - `/dashboard`;
  - `/strategies`;
  - `/strategies/:strategyId`;
  - `/strategies/:strategyId/models/:modelId`;
  - `/audit-events`.
- Cliente HTTP tipado para contratos do backend:
  - `GET /health`;
  - `GET /api/strategies`;
  - `GET /api/strategies/{strategy_id}`;
  - `POST /api/strategies/{strategy_id}/training-runs`;
  - `GET /api/training-runs/{run_id}`;
  - `GET /api/strategies/{strategy_id}/models`;
  - `GET /api/models/{model_id}`;
  - `POST /api/models/{model_id}/validate`;
  - `POST /api/models/{model_id}/approve`;
  - `POST /api/models/{model_id}/reject`;
  - `DELETE /api/models/{model_id}`;
  - `GET /api/audit-events`.
- Tela de estratégias com tabela e ação `Open`.
- Tela de detalhe da estratégia com retorno para lista, resumo operacional, modelos treinados e início de treinamento.
- A tabela de parâmetros default foi removida da tela de detalhe da estratégia; os valores são revisados no diálogo de treinamento antes da confirmação.
- Dialog de treinamento com Reactive Forms, validações básicas e aviso de retenção pública da Binance.
- Campo manual `Training Rows` removido do diálogo; a UI agora informa a janela calculada pelo backend a partir do timeframe, usando 30 dias brutos, warmup de 80 candles, `target_n` e holdout final de 72h.
- Dialog de treinamento organizado em abas específicas para contexto/dataset, target e XGBoost.
- Aba XGBoost do treinamento expõe `max_depth`, `learning_rate`, `n_estimators`, `subsample` e `colsample_bytree`, enviando os valores confirmados ao backend.
- Campos do diálogo de treinamento exibem ícone `pi-info-circle` ao lado do label com tooltip contextual detalhado, incluindo uso, defaults e limites quando aplicável.
- Polling de execução assíncrona via `GET /api/training-runs/{run_id}`.
- Tela de detalhe do modelo com scorecard de métricas, validação, aprovação, rejeição com comentário e exclusão de modelo `REJECTED` após confirmação.
- Botão `Validate` abre um diálogo próprio de validação com threshold de confiança, IFR sobrevendido, TP, SL, trailing, custos, mínimo de trades e walk-forward.
- Campos do diálogo de validação exibem ícone `pi-info-circle` com tooltip detalhado, incluindo uso, defaults e limites quando aplicável.
- Quando `Trailing Stop` está desligado no diálogo de validação, `Trailing Activation` e `Trailing Distance` ficam desativados e não são enviados no payload.
- Scorecard do modelo exibe análise de threshold de confiança com recomendação e tabela operacional por threshold.
- Scorecard do modelo exibe evidência operacional adicional para decisão de aprovação: setup da validação, funil de execução, razões de saída e resumo/tabela de walk-forward.
- Tela de eventos de auditoria com payload JSON expandível.
- CORS habilitado no backend para `http://localhost:4200` e `http://127.0.0.1:4200`.
- Tasks/launch do VS Code atualizados para frontend, browser, Swagger e compound full stack.

## Arquitetura Frontend

```text
frontend/src/app/
  core/
    api/
    config/
    layout/
    theme/
  shared/
    ui/
    utils/
  features/
    dashboard/
    strategies/
    audit/
```

Decisões:

- Sem store global pesada no MVP.
- Estado local com Signals e serviços Angular.
- Comunicação HTTP centralizada em `SmartTradeApiClient`.
- Features isolam modelos, páginas e componentes próprios.
- O frontend trata `VALIDATED` como evidência técnica, não como aprovação operacional.
- O formulário de treinamento não envia parâmetros operacionais de backtest; TP, SL, trailing, custos e threshold pertencem ao formulário de validação.
- O formulário de validação apresenta percentuais de forma amigável, mas preserva o contrato backend como frações decimais.
- O formulário de treinamento não envia mais `training_rows`; esse valor é calculado e auditado no backend em `requested_parameters.training_window_policy`.
- Os hiperparâmetros XGBoost são confirmados no diálogo de treinamento, não na tela de detalhe da estratégia.

## Documentação Consultada

- Angular via Context7:
  - standalone app;
  - routing;
  - `provideHttpClient()`;
  - `HttpClient.delete()` com corpo;
  - `Router.navigate()`;
  - lazy-loaded routes;
  - Reactive Forms.
  - control flow de template `@if`/`@for` e uso de `track` em templates standalone.
  - Reactive Forms com `FormGroup`, `FormControl`, validadores e submissão em componente standalone.
  - limpeza de imports standalone não usados após remoção de template.
- PrimeNG MCP:
  - instalação/setup standalone;
  - `confirmdialog` slots disponíveis;
  - data components: `table`, `paginator`, `timeline`;
  - form components: `inputtext`, `inputnumber`, `select`, `toggleswitch`, `textarea`;
  - overlay components: `dialog`, `confirmdialog`, `tooltip`.
  - `TableModule` / `p-table` para tabelas pequenas de evidência operacional.
  - `Dialog`, `InputNumber` e `ToggleSwitch` para formulário modal de validação operacional.
  - `Tabs` / `TabsModule` para organizar o diálogo de treinamento em abas.
  - `Tooltip` / `TooltipModule` para ajuda contextual acionada por ícone ao lado do label.
- PrimeNG v20/v21 theming via Context7:
  - `providePrimeNG`;
  - Aura preset;
  - `darkModeSelector`.

## Como Executar

Backend API:

- `cd backend`
- `.venv/bin/python -m uvicorn smart_trade_api.main:app --host 0.0.0.0 --port 8000 --reload`

Worker:

- `cd backend`
- `.venv/bin/python -m smart_trade_training_worker.main`

Frontend:

- `cd frontend`
- `npm start -- --host 0.0.0.0`
- URL: `http://localhost:4200/`

No VS Code:

- `Frontend: Angular`;
- `Frontend: Browser`;
- `Backend: API + Swagger`;
- `Full Stack: API + Worker + Frontend`.
- `Full Stack: API + Worker + Frontend + Browser`.

## Evidência de Verificação

- `cd frontend && npm run build`: passou.
  - Observação: warning de budget inicial do Angular, bundle inicial `673.11 kB` contra budget default `500 kB`, causado pela combinação Angular + PrimeNG. Não bloqueia o MVP.
- `cd backend && .venv/bin/python -m pytest -q tests`: 14 passed.
- `.vscode/tasks.json` e `.vscode/launch.json` válidos via `python -m json.tool`.
- Smoke HTTP:
  - `curl -I http://localhost:4200/`: `200 OK`;
  - `curl http://localhost:8000/health`: `{"status":"ok"}`;
  - `OPTIONS /api/strategies` com `Origin: http://localhost:4200` retornou `access-control-allow-origin: http://localhost:4200`.

## Pendências e Riscos

- O frontend ainda depende de polling por `run_id` retornado no início do treinamento; o backend não possui endpoint de listagem de runs por estratégia.
- A validação de modelo ainda é síncrona no backend.
- Ainda não há critérios objetivos de aprovação/reprovação; a UI respeita o estado `VALIDATED`, mas a decisão segue manual.
- `npm audit` reporta vulnerabilidades transitivas no scaffold Angular atual. Não foi aplicado `npm audit fix --force` para evitar upgrades quebrando compatibilidade Angular/PrimeNG.
