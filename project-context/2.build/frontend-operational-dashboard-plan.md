# Plano de Implementação - Frontend Dashboard Operacional

## 1. Objetivo

Construir o frontend Angular + PrimeNG do MVP como console operacional profissional para o ciclo:

1. acessar estratégias de treinamento;
2. abrir detalhes da estratégia;
3. iniciar nova execução de treinamento;
4. acompanhar execução assíncrona;
5. consultar modelos gerados;
6. validar modelo treinado;
7. aprovar ou reprovar modelo;
8. consultar demais informações expostas pela API, incluindo eventos de auditoria.

O frontend deve consumir somente contratos HTTP do backend Python. Não deve acessar banco, arquivos de modelo, logs locais, diretórios de artefatos ou credenciais.

## 2. Stack e Documentação Consultada

- Angular via Context7:
  - aplicação standalone;
  - roteamento;
  - `provideHttpClient()`;
  - lazy-loaded routes;
  - Reactive Forms.
- PrimeNG MCP:
  - `table`, `paginator`, `timeline`;
  - `inputtext`, `inputnumber`, `select`, `toggleswitch`, `textarea`;
  - `dialog`, `drawer`, `confirmdialog`, `tooltip`.

## 3. Arquitetura Frontend

### 3.1 Estrutura Feature First

Criar um projeto Angular em `frontend/` com organização por feature, não por tipo técnico global.

Estrutura proposta:

```text
frontend/
  src/
    app/
      app.config.ts
      app.routes.ts
      app.component.ts

      core/
        api/
          smart-trade-api.client.ts
          api-error.model.ts
        config/
          environment.model.ts
        interceptors/
          api-error.interceptor.ts
        layout/
          app-shell.component.ts
          app-sidebar.component.ts
          app-header.component.ts

      shared/
        ui/
          status-tag.component.ts
          metric-tile.component.ts
          empty-state.component.ts
          loading-state.component.ts
        utils/
          format-number.ts
          format-date.ts

      features/
        dashboard/
          dashboard.routes.ts
          pages/
            dashboard-home.page.ts

        strategies/
          strategies.routes.ts
          api/
            strategies.api.ts
          models/
            strategy.model.ts
            training-run.model.ts
            trained-model.model.ts
            audit-event.model.ts
          pages/
            strategy-list.page.ts
            strategy-detail.page.ts
          components/
            strategy-table.component.ts
            training-request-dialog.component.ts
            training-run-progress.component.ts
            trained-models-table.component.ts
            model-scorecard.component.ts
            model-approval-panel.component.ts

        audit/
          audit.routes.ts
          api/
            audit.api.ts
          pages/
            audit-events.page.ts
          components/
            audit-events-table.component.ts
```

### 3.2 Separação de Responsabilidades

- `core/api`: cliente HTTP base, tratamento de erros e configuração de URL.
- `core/layout`: shell visual com menu lateral, header e área interna.
- `shared/ui`: componentes pequenos e reutilizáveis, sem regra de negócio.
- `features/strategies`: todo o fluxo de estratégia, treinamento, modelo, validação e aprovação.
- `features/audit`: visualização de eventos de auditoria.

## 4. Rotas

Rotas propostas:

```text
/dashboard
/strategies
/strategies/:strategyId
/strategies/:strategyId/models/:modelId
/audit-events
```

Comportamento inicial:

- `/` redireciona para `/dashboard`.
- Dashboard inicial exibe shell profissional e área interna preparada para widgets futuros.
- Menu lateral contém:
  - Dashboard
  - XGBoost Strategies
  - Audit Events

## 5. Contratos Backend Consumidos

Contratos já disponíveis:

- `GET /health`
- `GET /api/strategies`
- `GET /api/strategies/{strategy_id}`
- `POST /api/strategies/{strategy_id}/training-runs`
- `GET /api/training-runs/{run_id}`
- `GET /api/strategies/{strategy_id}/models`
- `GET /api/models/{model_id}`
- `POST /api/models/{model_id}/validate`
- `POST /api/models/{model_id}/approve`
- `POST /api/models/{model_id}/reject`
- `GET /api/audit-events`

Gaps pequenos recomendados para o backend, mas não bloqueantes para o primeiro frontend:

- listar execuções de treinamento por estratégia;
- listar execuções recentes globalmente;
- expor critérios objetivos de aprovação quando forem definidos;
- expor capabilities/limitações de fonte de sentimento por exchange/timeframe para orientar o formulário.

No primeiro frontend, o acompanhamento de execução pode funcionar com o `run_id` retornado pelo `POST` e polling em `GET /api/training-runs/{run_id}`.

## 6. Telas e Experiência

### 6.1 App Shell

Objetivo: entregar uma aparência de console operacional, não landing page.

Elementos:

- menu lateral fixo;
- header compacto com título da tela, status da API e horário local;
- seletor Light/Dark no header;
- área de conteúdo com densidade adequada para uso recorrente;
- feedback global de erro/sucesso via toast;
- confirmação para ações irreversíveis.

PrimeNG:

- menu/sidebar customizado ou PrimeNG menu;
- `Toast`;
- `ConfirmDialog`;
- `Tooltip`.

### 6.2 Dashboard Home

Primeira versão:

- área interna limpa;
- cards discretos com:
  - API status;
  - total de estratégias;
  - modelos treinados recentes quando disponível;
  - último evento de auditoria.

Sem widgets complexos ainda.

### 6.3 XGBoost Strategies - Lista

Objetivo: atender RF2.

Tabela com:

- ID;
- nome;
- versão;
- modelo;
- status;
- descrição curta;
- ação `Open`.

PrimeNG:

- `Table`;
- `Tag` para status;
- botão com ícone para abrir.

### 6.4 Strategy Detail

Objetivo: atender RF3 e concentrar ações operacionais.

Seções:

- cabeçalho da estratégia;
- feature contract;
- parâmetros default;
- hiperparâmetros XGBoost;
- modelos treinados;
- última execução criada na sessão;
- ações principais.

Ações:

- `Start Training`;
- `Refresh Models`;
- abrir detalhe de modelo;
- validar modelo;
- aprovar modelo;
- rejeitar modelo.

### 6.5 Start Training Dialog

Objetivo: atender RF4.

Formulário reativo com defaults vindos de `strategy.default_parameters`.

Campos:

- `exchange_id`;
- `data_mode`;
- `sentiment_required`;
- `symbol`;
- `sentiment_symbol`;
- `timeframe`;
- `training_rows`;
- `target_n`;
- `take_profit_pct`;
- `stop_loss_pct`;
- `auto_validate`.

Validações UI:

- `training_rows >= 180`;
- `take_profit_pct > 0 && < 1`;
- `stop_loss_pct > 0 && < 1`;
- `target_n >= 2`;
- alerta contextual para Binance + sentimento obrigatório + janelas acima de aproximadamente 30 dias em `M5`.

PrimeNG:

- `Dialog`;
- `InputText`;
- `InputNumber`;
- `Select`;
- `ToggleSwitch`;
- botões com ícones.

### 6.6 Training Run Progress

Objetivo: acompanhar execução assíncrona.

Após criar run:

- guardar `run_id`;
- iniciar polling em `GET /api/training-runs/{run_id}`;
- parar polling em `TRAINED` ou `FAILED`;
- ao concluir `TRAINED`, atualizar lista de modelos.

Campos exibidos:

- status;
- `progress_phase`;
- `progress_pct`;
- `progress_message`;
- `worker_id`;
- `created_at`;
- `started_at`;
- `finished_at`;
- `failure_reason`.

PrimeNG:

- `ProgressBar`;
- `Tag`;
- `Message`.

### 6.7 Model Detail / Scorecard

Objetivo: exibir evidências para tomada de decisão.

Blocos:

- identificação do modelo;
- status;
- artifact format/path somente como metadado textual;
- dataset metadata;
- target parameters;
- training metrics;
- validation summary;
- validation results.

Métricas destacadas:

- precision positiva;
- F1;
- log loss;
- confusion matrix;
- sinais gerados;
- trades simulados;
- resultado líquido;
- profit factor;
- max drawdown;
- win rate;
- maior sequência de perdas.

PrimeNG:

- `Table` para métricas;
- cards pequenos para KPIs;
- tags de status;
- timeline para validações e decisões, quando disponível.

### 6.8 Validate Model

Objetivo: atender RF6/RF7 pelo contrato atual.

Comportamento:

- habilitar botão apenas para modelos `TRAINED` ou `FAILED` quando revalidação for permitida pelo backend;
- chamar `POST /api/models/{model_id}/validate`;
- mostrar loading;
- atualizar detalhe do modelo.

Observação: hoje a validação é síncrona no backend. A UI deve bloquear só o botão da ação, não a página inteira.

### 6.9 Approval / Rejection

Objetivo: atender aprovação manual.

Regras UI:

- `Approve` habilitado somente para `VALIDATED`;
- `Reject` habilitado para modelos não finalizados, respeitando backend;
- rejeição exige comentário;
- aprovação permite comentário opcional se o backend evoluir para aceitar.

PrimeNG:

- `ConfirmDialog` para aprovação;
- `Dialog` com `Textarea` para rejeição.

### 6.10 Audit Events

Objetivo: cobrir funcionalidade adicional já exposta pela API.

Tabela com:

- data/hora;
- tipo do evento;
- mensagem;
- payload resumido;
- ação para expandir payload JSON.

PrimeNG:

- `Table`;
- `Dialog` para payload completo.

## 7. Estado e Comunicação

Primeira versão sem store global pesada.

Padrões:

- services por feature;
- estado local por página usando Signals ou RxJS simples;
- polling controlado por componente;
- `takeUntilDestroyed` quando aplicável;
- cliente HTTP tipado.

Erros:

- 422: exibir mensagem de validação do backend;
- 404: estado de não encontrado;
- 409: conflito de estado, por exemplo tentar aprovar modelo não validado;
- 500/rede: toast global e mensagem inline na área afetada.

## 8. Design Profissional

Direção visual:

- operacional, denso e legível;
- sem hero/landing page;
- sem ilustrações decorativas;
- tabelas e painéis orientados à leitura rápida;
- suporte completo a tema Light/Dark;
- cores de status consistentes:
  - `PENDING`: cinza/azul;
  - `RUNNING`/`VALIDATING`: azul;
  - `TRAINED`/`VALIDATED`: verde;
  - `FAILED`/`REJECTED`: vermelho;
  - `APPROVED`: verde forte.

Layout:

- sidebar com largura fixa;
- header compacto;
- conteúdo com grid responsivo;
- cards somente para métricas/itens repetidos, sem cards dentro de cards.

### 8.1 Light/Dark Theme

O dashboard deve suportar alternância entre tema claro e escuro desde o MVP.

Comportamento:

- botão/toggle no header;
- detectar preferência inicial do sistema via `prefers-color-scheme`;
- persistir escolha do usuário em `localStorage`;
- aplicar tema antes ou durante o bootstrap para evitar flicker visível;
- garantir que tabelas, dialogs, menus, tags, inputs e cards respeitem o tema ativo.

Estrutura proposta:

```text
core/theme/
  theme.service.ts
  theme.model.ts
```

Estados:

```typescript
type ThemeMode = 'light' | 'dark' | 'system';
```

Primeira implementação recomendada:

- usar tema PrimeNG compatível com modo claro/escuro;
- aplicar classe `app-dark` ou atributo `data-theme="dark"` no elemento raiz;
- definir tokens CSS próprios apenas para layout da aplicação, sem sobrescrever agressivamente os componentes PrimeNG.

Critérios visuais:

- contraste adequado em ambos os modos;
- status tags preservam significado em Light/Dark;
- gráficos/tabelas não dependem apenas de cor;
- modais e overlays mantêm legibilidade.

## 9. Fases de Implementação

### Fase 1 - Bootstrap Angular + PrimeNG

- criar `frontend/`;
- configurar Angular standalone;
- instalar PrimeNG, PrimeIcons e tema;
- configurar `provideHttpClient()`;
- configurar rotas;
- criar layout base;
- implementar `ThemeService` com Light/Dark/System;
- adicionar toggle de tema no header.

Critério de aceite:

- `npm start` sobe a aplicação;
- `/dashboard`, `/strategies`, `/audit-events` navegam sem erro.
- alternância Light/Dark funciona e persiste após reload.

### Fase 2 - Cliente API Tipado

- criar modelos TypeScript alinhados ao backend;
- criar `SmartTradeApiClient`;
- implementar tratamento de erros;
- configurar `environment` com `apiBaseUrl`.

Critério de aceite:

- frontend chama `GET /health`;
- frontend lista estratégias reais do backend.

### Fase 3 - Estratégias

- tela `XGBoost Strategies`;
- tabela profissional;
- navegação para detalhe;
- detalhe com feature contract e default parameters.

Critério de aceite:

- usuário vê a estratégia `RSI Sentiment XGBoost`;
- usuário abre os detalhes.

### Fase 4 - Treinamento Assíncrono

- dialog de novo treinamento;
- criação de run;
- polling de status;
- progress panel;
- atualização da lista de modelos ao concluir.

Critério de aceite:

- usuário inicia treinamento;
- tela exibe `PENDING/RUNNING/TRAINED/FAILED`;
- quando `TRAINED`, modelo aparece disponível.

### Fase 5 - Modelo, Validação e Aprovação

- detalhe/scorecard do modelo;
- ação de validação;
- exibição de métricas;
- aprovação;
- rejeição com comentário obrigatório.

Critério de aceite:

- usuário valida modelo treinado;
- usuário aprova modelo `VALIDATED`;
- usuário rejeita modelo com comentário;
- estados finais aparecem corretamente.

### Fase 6 - Auditoria e Polimento

- tela de audit events;
- payload expandível;
- estados vazios/loading/error;
- responsividade básica;
- revisão visual em Light/Dark;
- revisão visual e acessibilidade.

Critério de aceite:

- usuário consegue rastrear eventos de treinamento, validação e decisão.

## 10. Testes e Verificação

Testes mínimos:

- build Angular;
- lint se configurado;
- testes unitários de API client;
- testes de componentes principais com mocks;
- smoke manual com backend real:
  1. abrir dashboard;
  2. listar estratégia;
  3. iniciar treino sintético ou real curto;
  4. acompanhar run;
  5. abrir modelo;
  6. validar;
  7. aprovar/rejeitar;
  8. ver audit events.

## 11. Dependências e Riscos

Dependências:

- backend API e worker precisam estar em execução para fluxo completo;
- CORS deve ser habilitado no backend se frontend rodar em porta diferente;
- backend ainda não tem endpoint de lista de training runs, o que limita histórico de execuções.

Riscos:

- validação atual é síncrona, podendo segurar a requisição HTTP;
- treinamento real com Binance + sentimento tem limite de aproximadamente 30 dias;
- ausência de critérios objetivos de aprovação pode confundir `VALIDATED` com `APPROVED`;
- sem autenticação no MVP, decisões de aprovação usam operador default ou input simples.

Mitigações:

- UI deve deixar claro que `VALIDATED` significa validação executada, não aprovação operacional;
- explicar limitações de janela no formulário;
- exigir confirmação explícita para aprovação/rejeição;
- priorizar endpoint posterior para listar runs por estratégia.

## 12. Entregáveis

- projeto Angular + PrimeNG em `frontend/`;
- estrutura Feature First;
- app shell profissional;
- telas de dashboard, estratégias, detalhe, modelo e auditoria;
- cliente API tipado;
- documentação em `project-context/2.build/frontend.md`;
- evidência de build/test/smoke.
