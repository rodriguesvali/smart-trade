# PRD - MVP Pipeline de Treinamento

## 1. Sumário Executivo

Este PRD define o primeiro MVP do Smart Trade: um pipeline de treinamento controlado, auditável e preparado para múltiplas estratégias, embora o MVP entregue apenas uma estratégia de treinamento implementada para mercado crypto spot com timeframe configurável por execução de treinamento.

O objetivo do MVP é permitir que o operador percorra o fluxo mínimo de preparação de uma estratégia baseada em dados históricos, modelo XGBoost e validação temporal. Cada execução de treinamento deve produzir um novo modelo treinado, e esse modelo deve ficar disponível para validação e aprovação antes de qualquer uso operacional futuro.

Ao final deste MVP, o usuário deverá poder:

1. Listar a única estratégia de treinamento implementada.
2. Exibir os detalhes da estratégia de treinamento.
3. Iniciar uma execução de treinamento.
4. Validar o modelo treinado por meio de rotinas automáticas de validação.
5. Aprovar ou rejeitar o modelo treinado quando as evidências estiverem disponíveis.

Este PRD não cobre execução live, abertura de ordens, gestão de posição, widgets informativos do dashboard ou múltiplas estratégias implementadas. O sistema, porém, deve nascer com catálogo e contratos preparados para receber múltiplas estratégias em fases futuras.

## 2. Usuário-Alvo

O usuário-alvo é o operador técnico do Smart Trade, responsável por preparar estratégias, treinar modelos, validar evidências e aprovar modelos antes de qualquer uso operacional.

Esse usuário precisa de uma experiência simples e rastreável: saber quais estratégias existem, entender seus parâmetros, disparar treinamento, consultar os modelos produzidos, analisar evidências de validação e aprovar ou rejeitar o modelo treinado.

## 3. Escopo do MVP

### Dentro do Escopo

- Catálogo de estratégias preparado para múltiplas estratégias.
- Uma única estratégia de treinamento implementada e disponível no MVP.
- Exibição dos metadados da estratégia, incluindo nome, descrição, features requeridas, modelo utilizado e parâmetros principais.
- Execução manual do treinamento da estratégia.
- Coleta ou leitura de dados históricos M1 necessários ao treinamento, conforme configuração externa.
- Engenharia de features técnicas necessárias para a estratégia, garantindo estacionariedade quando aplicável.
- Treinamento de modelo XGBoost com parâmetros configuráveis externamente.
- Separação temporal rigorosa entre janela de treino, janela de validação interna para early stopping e janela final fora da amostra.
- Pipeline automático de validação após treinamento bem-sucedido, incluindo walk-forward e backtest fora da amostra.
- Persistência de execuções, modelos treinados, métricas, artefatos e status.
- Disponibilização de cada modelo treinado para consulta, validação e aprovação.
- Aprovação manual do modelo treinado pelo operador com base nas evidências de validação geradas.

### Fora do Escopo

- Execução de ordens em exchange.
- Modo paper trading.
- Modo live trading.
- Gestão de posição, stop loss, take profit, break even ou trailing stop em tempo real.
- Múltiplas estratégias implementadas.
- Edição dinâmica do código da estratégia pelo usuário através da interface.
- Autenticação e controle de acesso complexos.
- Otimização automática e dinâmica de hiperparâmetros, como grid search automatizado.
- Retreinamento agendado por cron jobs.
- Aprovação automática de modelos sem intervenção humana.

## 4. Definições

- **Estratégia de treinamento:** receita versionada que define como preparar dados, gerar features, rotular o target, treinar o modelo, validar e calcular métricas. No MVP existe apenas uma estratégia implementada, mas o sistema deve suportar catálogo com múltiplas estratégias.
- **Execução de treinamento:** uma rodada concreta da estratégia de treinamento, com dados, parâmetros, artefatos e métricas persistidos.
- **Modelo treinado:** resultado de uma execução de treinamento. Cada nova execução deve produzir um novo modelo treinado, com identificador próprio, artefato serializado, metadados, status e evidências associadas.
- **Validação do modelo:** conjunto de rotinas aplicadas automaticamente a um modelo treinado, incluindo validação temporal walk-forward e backtest fora da amostra.
- **Aprovação do modelo:** decisão manual do usuário sobre um modelo treinado e validado. A aprovação torna esse modelo específico elegível para fases posteriores do produto.
- **Artefato do modelo:** arquivo nativo do XGBoost, em formato `.json` ou `.ubj`, acompanhado de metadados rastreáveis.
- **Target:** definição lógica do que o XGBoost tentará prever, como classificação binária de retorno futuro.
- **Estacionariedade:** propriedade estatística desejada para os inputs do XGBoost, reduzindo distorções de tendência e escala histórica.
- **Lag de segurança:** deslocamento temporal aplicado a features de sentimento quando houver risco de atraso de consolidação da API, garantindo que o modelo use apenas informações disponíveis no momento da decisão.

## 5. Fluxo do Usuário

O MVP deve suportar o seguinte fluxo operacional:

1. O usuário acessa o sistema.
2. O sistema abre o dashboard com menu lateral à esquerda, header e área interna inicialmente em branco.
3. O usuário acessa o menu `XGBoost Strategies`.
4. O sistema exibe uma tabela com as estratégias disponíveis.
5. O usuário clica no botão `Open` na linha da estratégia.
6. O sistema exibe os detalhes da estratégia, incluindo parâmetros de janelas e hiperparâmetros padrão.
7. O usuário inicia o treinamento manualmente.
8. O sistema registra uma execução de treinamento, consome os dados, aplica engenharia de features, treina o modelo XGBoost com early stopping e gera o artefato.
9. Se o treinamento finalizar com sucesso, o sistema dispara automaticamente as rotinas de validação: walk-forward e backtest fora da amostra.
10. O sistema apresenta o modelo na lista com status `VALIDATED` junto com suas métricas e evidências, ou `FAILED` se a validação falhar.
11. O usuário analisa os resultados e aprova ou rejeita o modelo treinado manualmente.
12. O sistema registra a decisão, data/hora, status final (`APPROVED` ou `REJECTED`) e observações associadas.

## 6. Primeira Estratégia do MVP

### Estratégia: RSI Sentiment XGBoost M1

A primeira estratégia implementada deve combinar um indicador técnico tradicional com três operadores de sentimento de mercado, modelados de forma estacionária quando necessário para reduzir distorções no XGBoost.

### Variável Alvo

O modelo será de classificação binária.

O target será definido como `1` se, dentro dos próximos `N` candles de M1, o preço atingir um ganho de `+X%` antes de atingir uma perda de `-Y%`. Caso contrário, o target será `0`.

Os valores de `N`, `X` e `Y` devem ser parametrizáveis externamente.

### Engenharia de Features

- **RSI / IFR:** usado em sua escala padrão de 0 a 100 para identificar sobrevenda e sobrecompra.
- **Open Interest:** não deve ser usado em valor absoluto. Deve ser transformado em taxa de variação, desvio em relação a uma média móvel ou outro formato estacionário.
- **Long/Short Ratio:** pode ser mantido em sua razão original por ser uma métrica naturalmente normalizada.
- **CVD / Cumulative Volume Delta:** não deve ser usado em valor absoluto acumulado. Deve ser usado como variação por candle, delta do CVD ou normalizado por janela móvel.

Todas as transformações baseadas em médias, desvios, z-scores, min-max ou janelas móveis devem usar apenas dados retrospectivos. Nenhuma estatística global calculada sobre o dataset completo pode ser usada.

Quando a fonte de sentimento apresentar atraso de coleta ou consolidação, as features de sentimento devem aplicar lag de segurança, como deslocamento de um candle M1, antes de serem usadas no treinamento.

No MVP, `X` e `Y` do target podem ser percentuais estáticos configuráveis. A interface ou documentação operacional deve sinalizar que esses parâmetros precisam ser revisados quando houver mudança relevante de regime de volatilidade. Uma evolução futura poderá permitir `X` e `Y` adaptativos por ATR ou desvio padrão.

Para o MVP, a estratégia deve expor em seus detalhes:

- Nome: `RSI Sentiment XGBoost M1`.
- Identificador lógico estável.
- Versão.
- Timeframe default: `M1`, definido em `default_parameters` e alterável por solicitação de treinamento.
- Mercado alvo: crypto spot, usando dados de sentimento do mercado de derivativos correspondente como proxy quando disponíveis.
- Indicador técnico: RSI/IFR.
- Operadores de sentimento: Open Interest, Long/Short Ratio e CVD.
- Modelo: XGBoost.
- Hiperparâmetros configuráveis, como `max_depth`, `learning_rate` e `scale_pos_weight`.
- Parâmetros configuráveis de target, janelas de treino, validação interna e holdout.
- Lista de features requeridas.
- Regras de lag de segurança para features de sentimento, quando aplicáveis.
- Procedimentos automáticos de validação disponíveis para modelos treinados.
- Critérios sugeridos para aprovação manual.

## 7. Requisitos Funcionais

### RF1 - Abrir Dashboard

Ao acessar o sistema, o usuário deve visualizar um dashboard inicial contendo menu lateral à esquerda, header superior e área interna inicialmente em branco reservada para expansões.

### RF2 - Listar Estratégias XGBoost

O sistema deve disponibilizar a tela `XGBoost Strategies` para listar as estratégias de treinamento implementadas.

Para o MVP, a tabela deve exibir exatamente uma estratégia implementada, com contrato preparado para múltiplas estratégias futuras.

A tabela deve exibir, no mínimo:

- ID.
- Nome.
- Versão.
- Descrição.
- Modelo utilizado.
- Timeframe default nos parâmetros de treinamento.
- Botão ou ação `Open`.

### RF3 - Exibir Estratégia de Treinamento

O sistema deve permitir consultar os detalhes da estratégia implementada, incluindo:

- Objetivo operacional.
- Regras de negócio do target.
- Lista de features.
- Regras de transformação das features.
- Parâmetros padrão de execução.
- Hiperparâmetros do XGBoost.
- Tamanhos das janelas temporais.
- Modelos treinados já produzidos para a estratégia.
- Procedimentos disponíveis para aprovar ou rejeitar modelos validados.

### RF4 - Iniciar Treinamento

Ao acionar o início do treinamento, o sistema deve:

- Criar um registro de execução com status `PENDING`.
- Validar parâmetros obrigatórios.
- Carregar os dados históricos do ativo configurado.
- Aplicar transformações para melhorar a estacionariedade das features de volume e sentimento, especialmente CVD e Open Interest.
- Aplicar lag de segurança nas features de sentimento quando houver risco de atraso da fonte de dados.
- Dividir os dados cronologicamente em três partições: treino, validação interna e holdout fora da amostra.
- Garantir ausência de vazamento temporal.
- Treinar o XGBoost utilizando a partição de validação interna para early stopping.
- Gerar um novo modelo treinado.
- Salvar o artefato nativo do XGBoost em `.json` ou `.ubj` no diretório configurado.
- Persistir metadados da execução e do modelo treinado.

### RF5 - Consultar Status da Execução e do Modelo

O sistema deve gerenciar os estados do ciclo de vida de forma independente.

Status da execução:

- `PENDING`
- `RUNNING`
- `TRAINED`
- `FAILED`

Status do modelo treinado:

- `TRAINED`
- `VALIDATING`
- `VALIDATED`
- `APPROVED`
- `REJECTED`
- `FAILED`

### RF6 - Pipeline Automático de Validação

Assim que a execução de treinamento atingir status `TRAINED`, o sistema deve mover o modelo para `VALIDATING` e disparar automaticamente as rotinas de validação:

- Backtest simulado na janela de holdout fora da amostra, usando dados nunca vistos pelo modelo.
- Testes de estabilidade via walk-forward nas subjanelas de treino para avaliar consistência das métricas.
- Persistência das métricas e evidências geradas.
- Bloqueio de qualquer tentativa de alteração para `APPROVED` enquanto o status do modelo não for `VALIDATED`.

### RF7 - Métricas de Validação

O sistema deve calcular e persistir as seguintes métricas após a validação:

- Precisão da classe positiva.
- Matriz de confusão.
- Log loss.
- F1-score.
- Quantidade de sinais gerados.
- Total de operações simuladas.
- Resultado líquido simulado.
- Fator de lucro.
- Drawdown máximo.
- Taxa de acerto.
- Maior sequência de perdas.
- Metadados dos períodos exatos utilizados em cada janela cronológica.

### RF8 - Aprovação Manual do Modelo Treinado

O usuário poderá alterar o status do modelo para `APPROVED` apenas se ele estiver em estado `VALIDATED`.

O sistema deve exigir confirmação manual e permitir um campo de texto para observações do operador.

### RF9 - Rejeitar Modelo Treinado

O sistema deve permitir mudar o status do modelo para `REJECTED` a partir de qualquer estado pós-treino, preservando todo o histórico de métricas e logs para auditoria e comparação.

### RF10 - Persistência de Artefatos e Metadados

Cada execução deve salvar de forma estruturada e durável:

- ID da execução.
- ID do modelo treinado.
- Versão da estratégia.
- Hiperparâmetros utilizados.
- Parâmetros do target.
- Janelas temporais utilizadas.
- Lista de features.
- Referência aos dados brutos e transformados usados.
- Caminho lógico do artefato do modelo.
- Formato nativo do artefato, `.json` ou `.ubj`.
- Métricas calculadas.
- Status da execução e do modelo.

### RF11 - Auditoria

O sistema deve registrar eventos de auditoria para cada ação crítica:

- Disparo de treino.
- Conclusão ou falha de treinamento.
- Criação do modelo treinado.
- Início, conclusão ou falha de validação.
- Decisões de aprovação ou rejeição, contendo timestamp e usuário ou agente responsável.

## 8. Requisitos Não Funcionais

### RNF1 - Execução Local e Nativa

O pipeline deve ser executável em ambiente Linux com backend Python nativo, utilizando bibliotecas da stack de dados como `xgboost`, `pandas`, `numpy` e `scikit-learn`.

### RNF2 - Configuração Externa Completa

Todos os parâmetros operacionais devem ser lidos de configuração externa, como `.env`, `.yaml` ou `.json`.

Isso inclui, no mínimo:

- Ativo padrão.
- Exchange ou fonte de dados.
- Janelas de tempo.
- Hiperparâmetros do XGBoost.
- Parâmetros do target `N`, `X` e `Y`.
- Diretório de artefatos.

Parâmetros hardcoded devem ser evitados fora dos defaults versionados da estratégia.

### RNF3 - Reprodutibilidade Rigorosa

O pipeline de treinamento deve fixar a semente de aleatoriedade (`random_state` ou `seed`) do XGBoost e das divisões de dados para garantir reprodutibilidade com o mesmo conjunto de dados e parâmetros.

### RNF4 - Sem Vazamento Temporal

O pipeline de dados deve garantir proteção cronológica estrita. Nenhum dado ou informação estatística da janela de validação ou holdout pode ser conhecida pela janela de treino.

Normalizações, padronizações, médias, desvios, z-scores e scalers devem ser ajustados exclusivamente com dados de treino e depois aplicados às janelas de validação interna e holdout. Transformações rolling devem usar apenas dados retrospectivos.

### RNF5 - Falha Segura

Qualquer inconsistência na volumetria de dados, integridade do arquivo do modelo ou cálculo de métricas deve interromper o processo, mover o status aplicável para `FAILED` e impedir aprovação.

### RNF6 - Rastreabilidade

Toda métrica e decisão de aprovação deve apontar para uma execução, uma estratégia, um modelo treinado, um período de dados e um artefato específico.

### RNF7 - Segurança de Credenciais

Nenhuma credencial real deve ser armazenada em código, logs ou artefatos versionados.

### RNF8 - Portabilidade do Artefato XGBoost

O modelo treinado deve ser persistido estritamente em formato nativo do XGBoost, `.json` ou `.ubj`, evitando serialização Python via `.pkl` ou `.joblib` para reduzir acoplamento com versão de Python, sistema operacional ou bibliotecas auxiliares.

### RNF9 - Disponibilidade Temporal das Features

As features usadas pelo modelo devem representar somente informações disponíveis no tempo do candle correspondente. Quando APIs de sentimento apresentarem risco de atraso, o pipeline deve aplicar lag de segurança documentado e rastreável.

## 9. Requisitos de Dados e Modelo

O MVP deve considerar a persistência durável e consultável das seguintes entidades conceituais:

- `training_strategies`: catálogo das estratégias implementadas.
- `training_runs`: execuções de treinamento e seus respectivos logs.
- `trained_models`: modelos treinados produzidos, vinculados aos seus caminhos de arquivo.
- `training_validation_results`: resultados agregados de ML e do backtest fora da amostra.
- `training_approval_decisions`: histórico de decisões manuais de aprovação ou rejeição.
- `audit_events`: logs de auditoria do ciclo de vida do sistema.

## 10. Experiência Esperada

A interface visual deve guiar o operador de forma intuitiva:

- Menu lateral com acesso a `XGBoost Strategies`.
- Tabela limpa listando a estratégia disponível e um botão proeminente `Open`.
- Dentro da estratégia, visão clara dos parâmetros de dados vigentes e botão `Train Strategy`.
- Exibição de status `RUNNING` e logs ou eventos de progresso enquanto o treinamento estiver em execução.
- Seção inferior com a tabela histórica de modelos gerados por aquela estratégia, exibindo claramente os status `TRAINED`, `VALIDATING`, `VALIDATED`, `APPROVED`, `REJECTED` e `FAILED`.
- Ao clicar em um modelo `VALIDATED`, expansão de painel lateral ou modal contendo scorecard de métricas de ML e operacionais, junto aos botões `Approve Model` e `Reject Model`.
- Modal ou painel de aprovação/rejeição com campo para comentários do operador.

## 11. Critérios de Aceite

### CA1 - Dashboard Inicial

Dado que o usuário acessa o sistema, quando a aplicação carregar, então deve exibir o dashboard com menu lateral esquerdo, header e área interna em branco.

### CA2 - Listagem de Estratégias

Dado que o usuário acessa `XGBoost Strategies`, quando a tela carregar, então o sistema deve exibir a tabela com a estratégia `RSI Sentiment XGBoost M1` disponível e estrutura de dados flexível para novas adições.

### CA3 - Exibição de Detalhes e Features Estacionárias

Dado que o usuário abre os detalhes da estratégia, o sistema deve detalhar explicitamente as regras de transformação de features, incluindo deltas ou taxa de variação para CVD e Open Interest, regras de lag de segurança para sentimento quando aplicáveis, além da lógica de rotulagem do target.

### CA4 - Execução e Early Stopping

Dado que o usuário inicia o treinamento, o sistema deve processar as três janelas cronológicas, executar o treinamento do XGBoost utilizando a janela secundária para early stopping e salvar o artefato nativo `.json` ou `.ubj` em caso de sucesso.

### CA5 - Disparo Automático da Validação

Dado que o treinamento foi concluído com sucesso, o sistema deve alterar o status do modelo para `VALIDATING` e executar o backtest no holdout sem exigir nenhuma ação adicional do usuário.

### CA6 - Bloqueio de Segurança na Aprovação

Dado um modelo que esteja no status `TRAINED` ou `VALIDATING`, se o usuário tentar forçar uma aprovação, o sistema deve bloquear a ação pela interface e pela API, exigindo o status `VALIDATED`.

### CA7 - Scorecard Completo de Métricas

Dado um modelo no status `VALIDATED`, quando o usuário abrir seus detalhes, o sistema deve exibir de forma agrupada as métricas de machine learning e as métricas operacionais do backtest.

### CA8 - Mudança Estrita de Estado na Aprovação/Rejeição

Dado um modelo válido, quando o operador confirmar a aprovação ou rejeição, o sistema deve atualizar o estado para `APPROVED` ou `REJECTED`, gravar timestamp e comentários informados, e travar o modelo contra modificações futuras.

### CA9 - Proteção Contra Vazamento Estatístico

Dado que o pipeline gera features normalizadas ou agregadas por janela, quando executar treinamento e validação, então nenhuma estatística global do dataset completo pode ser usada para preparar as janelas de treino, validação interna ou holdout.

## 12. Decisões do MVP e Alinhamento Técnico

As seguintes premissas técnicas ficam definidas para o escopo deste MVP:

1. **Ativo padrão:** o pipeline será configurado via `.env` com a paridade `BTC/USDT`, utilizando CCXT como fronteira primária de obtenção de dados da exchange configurada. O preço spot será a referência operacional, e futuros perpétuos poderão ser usados como proxy para métricas de sentimento quando disponíveis pela exchange configurada.
2. **Automação da validação:** a validação será executada de forma automática após o sucesso do treinamento. Apenas a decisão de aprovação ou rejeição permanece estritamente manual.
3. **Filtros de aprovação:** para o MVP, não haverá travas automáticas por valor mínimo de métrica, como win rate mínimo. A validação serve para gerar evidências; o julgamento de qualidade do modelo é responsabilidade do operador técnico.
4. **Origem dos dados de sentimento:** Open Interest, Long/Short Ratio e variações de CVD serão consumidos preferencialmente via CCXT quando a exchange configurada expuser métricas públicas compatíveis. Qualquer provedor externo não-CCXT deverá ser aprovado como adapter separado, evitando calcular CVD bruto a partir de dados de tick, order book ou trades individuais dentro do MVP.
5. **Formato do modelo:** o artefato treinado será salvo em formato nativo do XGBoost, `.json` ou `.ubj`, e não em `.pkl` ou `.joblib`.
6. **Target no MVP:** `X` e `Y` serão configuráveis externamente como percentuais estáticos no MVP, com aviso operacional para revisão em mudanças de regime de volatilidade. Barreiras adaptativas por ATR ou desvio padrão ficam como evolução futura.

## 13. Fontes

- `docs/proposed-solution.md`
- `.codex/aamad/agents/product-mgr.md`
- `project-context/1.define/revisao.md`
- Revisão especializada em XGBoost recebida em 2026-06-15, cobrindo data leakage, lag de sentimento, target, formato de artefato e rastreabilidade do fluxo.
- Direcionamento do Agentic Architect em 2026-06-15: iniciar o projeto com PRD focado no pipeline de treinamento do MVP.
- Direcionamento do Agentic Architect em 2026-06-15: preparar suporte a múltiplas estratégias, gerar novo modelo por treinamento, e usar RSI/IFR com Open Interest, Long/Short Ratio e CVD na primeira estratégia.

## 14. Auditoria do Artefato

- Persona: `@product-mgr`
- Fase: Define
- Artefato: `project-context/1.define/prd.md`
- Data: 2026-06-15
- Status: aprovado pelo Agentic Architect em 2026-06-15
