# Documento de Requisitos do Produto (PRD) - Sistema de Trading Quantitativo Native CCXT

* **Status:** Pronto para Desenvolvimento
* **Autor:** Sistema de Engenharia Quantitativa
* **Data de Criação:** 4 de Junho de 2026
* **Versão:** 3.2 (MVP Spot Long Only com Validação e Aprovação de Modelo)

---

## 1. Visão Geral do Produto
O objetivo deste projeto é construir uma plataforma de trading quantitativo com foco no tempo gráfico M1, 100% centralizada em ambiente Linux, rodando de forma nativa em Python através do ecossistema CCXT. Para o MVP, o sistema operará exclusivamente no mercado spot, em operações compradas (*long only*), sem margem, futuros, alavancagem, venda a descoberto ou aumento de posição. O sistema utiliza Aprendizado de Máquina (XGBoost) para confirmar movimentos de preço de curto prazo em ativos digitais (criptomoedas), integrando métricas técnicas com indicadores disponíveis no pipeline de dados.

A inteligência e o motor de execução estão completamente unificados no mesmo ambiente para garantir latências mínimas. Antes da execução operacional da estratégia, o ativo deve ser definido e o modelo de inferência deve ser treinado, validado e aprovado para o respectivo ativo, timeframe e configuração operacional. Para fins de monitoramento operacional, análise macro e diagnóstico, o sistema incorpora uma interface web (Dashboard Visual) totalmente desacoplada em Python (Streamlit ou Dash), eliminando processos "às cegas" e garantindo controlo total sobre o capital operado.

---

## 2. Arquitetura do Sistema e Fluxo de Dados
O sistema funciona de forma síncrona/assíncrona através de componentes que interagem por meio do Banco de Dados local, diretório de modelos e arquivos de logs. O fluxo de trabalho do MVP deve seguir a sequência: definição do ativo, coleta de histórico, treinamento, validação temporal, backtest fora da amostra, aprovação do modelo e, somente depois, inicialização da estratégia operacional:

* **Módulo 1: Pipeline de Treinamento:** Extrai o histórico e treina o algoritmo XGBoost, persistindo o modelo em arquivos serializados (`.joblib` ou `.pkl`).
* **Módulo 2: Motor de Inferência e Execução Nativa (CCXT):** Loop que acorda a cada minuto, carrega o modelo XGBoost em memória e retorna sinais binários de confirmação para a estratégia.
* **Módulo 2.5: Estratégia de Operação e Gestão da Posição:** Camada responsável por avaliar o IFR/RSI, consultar o módulo de inferência, decidir pela abertura de posição comprada no mercado spot e administrar stop loss, take profit, break even e trailing stop.
* **Módulo 3: Dashboard Visual (Interface Web):** Aplicação visual isolada que lê o banco de dados e arquivos de logs em tempo real para apresentar os dados de performance ao utilizador.

---

## 3. Requisitos Funcionais (RF)

### Módulo 1: Pipeline de Treinamento
* **RF1.1 - Ingestão CCXT:** Extração de dados históricos de candles M1 usando as conexões públicas da CCXT. Indicadores de derivativos, como Open Interest e Funding Rate, devem ser tratados como opcionais para o MVP spot only, sendo utilizados apenas quando compatíveis com o ativo e a exchange configurados.
* **RF1.2 - Armazenamento Central:** Consolidação e armazenamento de dados estruturados e tabelas operacionais em banco de dados SQLite ou PostgreSQL.
* **RF1.3 - Engenharia de Recursos (*Feature Engineering*):** Geração de indicadores matemáticos de volatilidade e momento (RSI/IFR, Bollinger, retornos percentuais, variações de volume e demais features derivadas de preço e volume) via `TA-Lib` ou `pandas-ta`.
* **RF1.4 - Definição de Janela de Treinamento:** O pipeline deve permitir configurar a janela de treinamento do modelo, inicialmente sugerida em 60 dias de dados M1 anteriores à janela final de validação.
* **RF1.5 - Separação de Holdout Fora da Amostra:** O pipeline deve reservar uma janela final de dados não vistos pelo modelo, inicialmente sugerida em 3 dias, para execução do backtest final fora da amostra. Esses dados não devem ser usados no treinamento.
* **RF1.6 - Validação Walk-Forward:** Antes do backtest final, o pipeline deve executar validação temporal do tipo walk-forward dentro da janela de treinamento, com o objetivo de reduzir risco de sobreajuste e mitigar viés de olhar para o futuro (*look-ahead bias*).
* **RF1.7 - Backtest Final da Estratégia Completa:** Após o treinamento do modelo candidato, o pipeline deve executar backtest na janela fora da amostra, simulando a estratégia completa do MVP: IFR/RSI em sobrevenda, confirmação binária pela inferência, abertura de compra spot, stop loss, take profit, break even e trailing stop condicionado à inferência.
* **RF1.8 - Métricas de Validação e Aprovação:** O pipeline deve gerar métricas estatísticas e operacionais do modelo e da estratégia, incluindo no mínimo precisão da classe `1`, quantidade de operações, lucro/prejuízo líquido simulado, fator de lucro, drawdown máximo, taxa de acerto e maior sequência de perdas.
* **RF1.9 - Persistência de Artefatos do Modelo:** Cada modelo treinado deve ser persistido com seu artefato serializado (`.joblib` ou `.pkl`) e arquivos de metadados contendo ativo, timeframe, período de treinamento, período de holdout, features utilizadas, parâmetros da estratégia, métricas obtidas e status do modelo.
* **RF1.10 - Aprovação do Modelo:** O sistema deve permitir classificar o modelo como `TRAINED`, `VALIDATED`, `APPROVED`, `ACTIVE`, `REJECTED`, `EXPIRED` ou `RETIRED`. A estratégia operacional somente poderá iniciar com um modelo em status `APPROVED` ou `ACTIVE` para o ativo, timeframe e parâmetros configurados.

### Módulo 2: Motor de Inferência e Execução Direta (CCXT)
* **RF2.1 - Gatilho Baseado em Tempo:** Loop contínuo calibrado para rodar a inferência no segundo `01` de cada minuto, dando margem para a consolidação completa do último candle na exchange.
* **RF2.2 - Carregamento de Modelo Aprovado:** O Motor de Inferência deve carregar somente modelos previamente treinados, validados e aprovados para o ativo, timeframe e parâmetros configurados. Caso não exista modelo aprovado ou ativo, a estratégia operacional não deve ser iniciada.
* **RF2.3 - Geração de Sinais Binários:** Processamento dos dados de tempo real pelo modelo em memória, retornando exclusivamente um sinal binário de confirmação (`1` = condição favorável confirmada para compra; `0` = ausência de confirmação).
* **RF2.4 - Execução Direta:** Envio instantâneo de ordens a mercado via métodos privados da CCXT (ex: `create_market_buy_order` para abertura de compra no spot e ordem de venda equivalente para encerramento da posição) sem intermediários.
* **RF2.5 - Registro de Estado:** Gravação instantânea do resultado das operações, posições abertas e métricas de execução no banco de dados compartilhado.

### Módulo 2.5: Estratégia de Operação e Gestão da Posição
* **RF2.5.1 - Mercado Spot no MVP:** O MVP deve operar exclusivamente em mercado spot, sem suporte inicial a margem, futuros, alavancagem ou venda a descoberto.
* **RF2.5.2 - Ativo Operado Configurável:** O sistema deve permitir a configuração explícita de um único ativo a ser operado no MVP, incluindo exchange, símbolo, timeframe e capital operacional inicial.
* **RF2.5.3 - Validação do Ativo:** Antes de iniciar a operação, o sistema deve validar se o ativo configurado atende aos limites mínimos da exchange, incluindo quantidade mínima, precisão de preço, precisão de quantidade, valor nocional mínimo e liquidez suficiente para execução em M1.
* **RF2.5.4 - Direção Operacional Long Only:** O MVP deve operar exclusivamente em posições compradas. Operações vendidas, *short selling*, hedge, margem e derivativos ficam fora do escopo inicial.
* **RF2.5.5 - Operador Técnico IFR/RSI:** A estratégia deve utilizar o Índice de Força Relativa (IFR/RSI) como operador técnico primário para identificar condições de sobrevenda antes de consultar o módulo de inferência.
* **RF2.5.6 - Condição Técnica de Entrada:** Quando não houver posição aberta, a estratégia deve verificar inicialmente se o IFR indica condição de sobrevenda conforme limite configurado.
* **RF2.5.7 - Confirmação por Inferência:** A abertura de posição somente poderá ocorrer após a condição técnica de sobrevenda pelo IFR ser identificada e o módulo de inferência retornar sinal `1`.
* **RF2.5.8 - Interpretação do Sinal Binário:** O módulo de inferência deve retornar exclusivamente um sinal binário, onde `1` representa confirmação favorável para compra e `0` representa ausência de confirmação. A decisão operacional final deve ser responsabilidade da camada de estratégia.
* **RF2.5.9 - Abertura de Posição Comprada:** Quando não houver posição aberta, o sistema poderá abrir uma nova posição comprada somente se o IFR indicar sobrevenda, o módulo de inferência confirmar com sinal `1`, houver saldo disponível e os parâmetros mínimos da estratégia forem atendidos.
* **RF2.5.10 - Posição Única no MVP:** O sistema deve permitir apenas uma posição aberta por vez. Enquanto houver posição aberta, novos sinais de entrada devem ser ignorados para fins de abertura de nova operação.
* **RF2.5.11 - Exclusão de Aumento de Posição no MVP:** O MVP não deve contemplar aumento de posição, preço médio por múltiplas entradas, piramidagem, martingale ou qualquer mecanismo de reforço de posição.
* **RF2.5.12 - Stop Loss Obrigatório:** Toda posição comprada deve possuir stop loss inicial obrigatório, calculado no momento da entrada com base no preço médio executado e nos parâmetros configurados da estratégia.
* **RF2.5.13 - Stop Gain / Take Profit Obrigatório:** Toda posição comprada deve possuir objetivo inicial de ganho, calculado com base em percentual, valor fixo ou outro parâmetro configurado da estratégia.
* **RF2.5.14 - Break Even:** O sistema deve permitir mover o stop de proteção para o ponto de equilíbrio quando o preço atingir uma distância favorável mínima configurada. A primeira movimentação de proteção deverá priorizar a redução do risco da operação para zero ou próximo de zero, considerando taxas operacionais.
* **RF2.5.15 - Trailing Stop Condicionado à Inferência:** Após o mercado se mover a favor da posição comprada, a estratégia deve consultar o módulo de inferência antes de movimentar o trailing stop. Caso a inferência retorne `1`, o sistema poderá mover o stop para cima, a favor do movimento. Caso a inferência retorne `0`, o sistema deverá acionar a lógica de realização de lucro.
* **RF2.5.16 - Evolução do Stop a Favor do Mercado:** Quando a inferência continuar favorável, o sistema deve permitir a movimentação progressiva do stop a favor do mercado. Para posições compradas, o stop nunca deve ser reduzido.
* **RF2.5.17 - Realização de Lucro por Perda de Confirmação:** Caso o mercado tenha se movimentado a favor da posição e o módulo de inferência deixe de confirmar a continuidade do movimento, a estratégia deverá acionar o take profit ou encerrar a posição para realização de lucro, conforme configuração operacional do MVP.
* **RF2.5.18 - Encerramento da Posição:** O sistema deve encerrar a posição quando o preço atingir o stop loss, o stop protegido, o trailing stop, o take profit configurado ou quando houver perda de confirmação da inferência em cenário favorável à operação.
* **RF2.5.19 - Estado da Posição:** O sistema deve manter estado operacional explícito da posição, incluindo ausência de posição, posição aberta, posição protegida em break even, posição com trailing stop confirmado, posição com take profit acionado, posição em fechamento e posição encerrada.
* **RF2.5.20 - Registro da Estratégia:** Todas as decisões da estratégia devem ser registradas no banco de dados, incluindo valor do IFR, sinal recebido da inferência, decisão tomada, preço de entrada, stop loss inicial, take profit inicial, movimentações de stop, ativações de break even, consultas de continuidade da inferência, encerramento e motivo do encerramento.

### Módulo 3: Dashboard Visual de Acompanhamento
* **RF3.1 - Monitoramento do Modelo (Aba Treino):** Exibição das métricas de acurácia, matriz de confusão, precisão e gráfico de importância dos recursos (*Feature Importance*) do XGBoost.
* **RF3.2 - Controle Manual de Treinamento:** Disponibilização de um botão em tela para disparar manualmente uma rotina de re-treinamento emergencial do modelo (Módulo 1).
* **RF3.2.1 - Visualização de Validação e Aprovação:** O Dashboard deve exibir status do modelo, período de treinamento, período de holdout fora da amostra, métricas de validação, resultado do backtest final e indicação clara se o modelo está apto ou não para uso operacional.
* **RF3.3 - Gráfico Dinâmico Financeiro (Aba Operação):** Exibição de um gráfico de velas (Candlesticks) atualizado em tempo real com marcações visuais nos minutos exatos onde o robô realizou entradas compradas e encerramentos de posição.
* **RF3.4 - Curva de Capital (Equity Curve):** Plotagem em tempo real do saldo acumulado e flutuação do património líquido da carteira conectada.
* **RF3.5 - Painel de Métricas de Trade:** Exibição destacada de indicadores de performance: Lucro Total, Fator de Lucro (*Profit Factor*), *Drawdown* Máximo registrado e Taxa de Acerto (%).
* **RF3.6 - Terminal de Logs Vivo (Aba Logs):** Visualização de rolagem automática dos arquivos de logs do sistema, com destaque visual em amarelo para avisos (`WARNING`) e vermelho para erros de rede (`API Rate Limits`, timeouts) ou rejeições de ordens.

---

## 4. Requisitos Não-Funcionais (RNF)
* **RNF4.1 - Ambiente Linux Nativo:** Homologação e execução de todo o sistema (Módulos 1, 2 e 3) em ambientes Linux (Ubuntu Server), operando preferencialmente em containers Docker independentes.
* **RNF4.2 - Latência Fim-a-Fim Sub-Segundo:** O tempo decorrido entre a captura do candle, inferência matemática e aceitação da ordem na API da Exchange deve ser menor do que 1 segundo.
* **RNF4.3 - Desacoplamento de Interface:** O Dashboard Visual deve rodar num processo separado (Streamlit ou Dash) para garantir que problemas de renderização web ou concorrência de acessos não causem atrasos na execução do robô.
* **RNF4.4 - Segurança de Chaves:** Chaves de API (`API Key` e `Secret`) e credenciais de acesso devem ser injetadas de forma estrita via variáveis de ambiente ou arquivo `.env` local não versionado, garantindo que nenhuma credencial sensível seja armazenada diretamente no código-fonte, nos arquivos de configuração versionados ou nos logs da aplicação.
* **RNF4.5 - Isolamento de Processos:** Os módulos de treinamento, execução e dashboard devem poder ser executados de forma independente, preferencialmente em containers separados, compartilhando apenas os recursos necessários, como banco de dados, diretório de modelos e arquivos de logs.
* **RNF4.6 - Persistência de Logs:** Todos os eventos relevantes do sistema, incluindo inicialização, coleta de dados, inferência, envio de ordens, respostas da Exchange, avisos e erros, devem ser persistidos em arquivos de log com rotação configurável.
* **RNF4.7 - Resiliência Operacional:** O Motor de Inferência e Execução deve tratar falhas temporárias de rede, timeouts e respostas inválidas da Exchange sem encerrar o processo principal de forma abrupta, registrando o erro e mantendo o estado operacional consistente.
* **RNF4.8 - Portabilidade de Configuração:** Parâmetros operacionais como ativo negociado, timeframe, tamanho da janela histórica, caminho do modelo, exchange utilizada, credenciais, modo de execução, janela de treinamento, janela de holdout, critérios de aprovação, limites do IFR, percentuais de stop loss, take profit, break even e trailing stop devem ser definidos por variáveis de ambiente ou arquivo de configuração externo.
* **RNF4.9 - Baixo Acoplamento do Modelo:** O modelo treinado deve ser carregado a partir de arquivo serializado, permitindo substituição do artefato de ML sem necessidade de recompilar ou alterar o código do Motor de Inferência.
* **RNF4.10 - Disponibilidade do Dashboard:** O Dashboard Visual deve permitir consulta contínua às informações de operação sem bloquear escrita no banco de dados nem interferir no ciclo de execução do robô.
* **RNF4.11 - Rastreabilidade do Modelo:** Toda inferência registrada durante a operação deve estar associada ao identificador do modelo ativo, permitindo rastrear qual versão do modelo gerou cada sinal operacional.
* **RNF4.12 - Bloqueio por Modelo Não Aprovado:** O sistema deve falhar de forma segura, sem iniciar a estratégia em modo operacional, quando o modelo configurado estiver ausente, corrompido, incompatível com as features esperadas, não aprovado ou não correspondente ao ativo/timeframe configurado.

---

## 5. Entregáveis Esperados
* Código-fonte do Pipeline de Treinamento em Python.
* Rotina de validação walk-forward e backtest final fora da amostra.
* Arquivos de metadados e métricas de validação associados ao modelo treinado.
* Código-fonte do Motor de Inferência e Execução Nativa via CCXT.
* Código-fonte da Estratégia de Operação e Gestão da Posição.
* Código-fonte do Dashboard Visual em Streamlit ou Dash.
* Scripts de criação e inicialização do banco de dados.
* Arquivo de configuração de ambiente com variáveis esperadas, sem credenciais reais.
* Dockerfile ou configuração equivalente para execução em ambiente Linux.
* Documentação mínima de instalação, configuração e execução dos três módulos.

---

## 6. Critérios Gerais de Aceite
* O Pipeline de Treinamento deve ser capaz de coletar dados históricos, gerar recursos técnicos, separar a janela final fora da amostra, executar validação walk-forward, treinar o modelo XGBoost, executar backtest final da estratégia completa e persistir o artefato treinado em disco com seus metadados e métricas.
* O sistema deve impedir a inicialização da estratégia operacional quando não houver modelo aprovado ou ativo para o ativo, timeframe e parâmetros configurados.
* O Motor de Inferência deve ser capaz de carregar o modelo aprovado, executar o ciclo de inferência a cada minuto e registrar o resultado no banco de dados com o identificador do modelo ativo.
* A Estratégia de Operação deve ser capaz de identificar sobrevenda pelo IFR, consultar o módulo de inferência, abrir posição comprada apenas quando houver confirmação e administrar stop loss, take profit, break even e trailing stop conforme os parâmetros configurados.
* O Motor de Execução deve ser capaz de enviar ordens via CCXT quando a estratégia autorizar abertura ou encerramento de posição e registrar a resposta da Exchange.
* O Dashboard Visual deve exibir métricas do modelo, gráfico financeiro, curva de capital, métricas de trade, estado da posição, valor do IFR, sinais de inferência, movimentações de stop e terminal de logs conforme descrito nos requisitos funcionais.
* O sistema deve executar em ambiente Linux com os módulos desacoplados e configuração externa por variáveis de ambiente ou arquivo local não versionado.

---

## 7. Fluxo de Trabalho do MVP
O fluxo de trabalho operacional do MVP deve seguir uma sequência obrigatória para evitar que a estratégia rode com um modelo não treinado, não validado ou incompatível com o ativo configurado.

1. **Definir ativo e configuração operacional:** escolher exchange, mercado spot, símbolo, timeframe M1, capital operacional, parâmetros de IFR/RSI, stop loss, take profit, break even e trailing stop.
2. **Coletar histórico:** obter dados M1 suficientes para treinamento, validação temporal e holdout final fora da amostra.
3. **Separar holdout final:** reservar os últimos dias configurados, inicialmente 3 dias, para backtest final com dados que o modelo não viu.
4. **Executar validação walk-forward:** avaliar o comportamento temporal do modelo dentro da janela de treinamento, antes do teste final.
5. **Treinar modelo candidato:** gerar o artefato XGBoost usando a janela de treinamento definida, sem incluir o holdout final.
6. **Executar backtest final fora da amostra:** testar a estratégia completa sobre o período reservado, incluindo IFR/RSI, inferência, entrada comprada, stop loss, take profit, break even e trailing stop condicionado à inferência.
7. **Gerar relatório de validação:** registrar métricas estatísticas e operacionais, incluindo precisão da classe `1`, quantidade de operações, resultado líquido simulado, fator de lucro, drawdown máximo e maior sequência de perdas.
8. **Aprovar ou rejeitar modelo:** classificar o modelo conforme os critérios configurados. Apenas modelos `APPROVED` ou `ACTIVE` podem ser utilizados pela estratégia.
9. **Iniciar estratégia operacional:** carregar o modelo aprovado e iniciar o ciclo em tempo real, preferencialmente primeiro em modo paper antes de operar com capital real.

O fluxo resumido é: **definir ativo → coletar histórico → treinar modelo → validar modelo → backtest fora da amostra → aprovar modelo → iniciar estratégia**.

---

## 8. Considerações Finais
Este PRD consolida os requisitos para desenvolvimento da versão 3.2 do Sistema de Trading Quantitativo Native CCXT, com foco na execução nativa em Python, integração direta via CCXT, operação inicial em mercado spot long only, uso de IFR/RSI como operador técnico primário, uso de modelo XGBoost como confirmação binária e fluxo explícito de treinamento, validação, backtest fora da amostra e aprovação do modelo e inclusão de Dashboard Visual desacoplado para acompanhamento operacional.
