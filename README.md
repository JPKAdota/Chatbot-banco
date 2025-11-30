# Banco Ágil - Agente de Atendimento Inteligente

## Visão Geral do Projeto

Este projeto implementa um sistema de atendimento bancário automatizado utilizando Agentes de IA. O sistema é capaz de autenticar usuários, consultar limites, processar solicitações de aumento de crédito, realizar entrevistas para atualização de score e fornecer cotações de moedas. O objetivo é demonstrar uma arquitetura robusta de agentes autônomos aplicados ao contexto financeiro.

## Arquitetura do Sistema

O sistema utiliza uma arquitetura multi-agente orquestrada pelo **LangGraph**, onde cada agente possui responsabilidades específicas e ferramentas dedicadas.

### Agentes e Fluxos
- **Agente de Triagem**: Ponto de entrada. Responsável pela autenticação do usuário (CPF e Data de Nascimento). Se falhar 3 vezes, encerra o atendimento.
- **Agente de Crédito**: Gerencia consultas de limite e solicitações de aumento. Verifica regras de negócio baseadas no score do cliente.
- **Agente de Entrevista**: Conduz uma entrevista interativa para coletar dados financeiros (renda, despesas, etc.) e recalcular o score de crédito do cliente em tempo real.
- **Agente de Câmbio**: Fornece cotações de moedas em tempo real utilizando uma API externa.

### Manipulação de Dados
- Os dados dos clientes são simulados em arquivos CSV na pasta `data/`.
- O estado da conversa (autenticação, histórico de mensagens) é mantido globalmente pelo objeto `AgentState` do LangGraph, permitindo que diferentes agentes compartilhem o contexto sem perder informações.

## Funcionalidades Implementadas

- **Autenticação Segura**: Validação de CPF e Data de Nascimento contra uma base de dados.
- **Consulta de Limite**: Visualização imediata do limite de crédito disponível.
- **Solicitação de Aumento de Limite**: Análise automática baseada no score atual.
- **Atualização de Score (Entrevista)**: Processo interativo onde o usuário fornece dados atualizados para tentar melhorar seu score e, consequentemente, seu limite.
- **Cotação de Moedas**: Consulta de taxas de câmbio atualizadas (ex: Dólar, Euro).
- **Interface Chat**: Interface amigável construída com Streamlit.

## Desafios Enfrentados e Como Foram Resolvidos

1.  **Manutenção de Contexto entre Agentes**:
    - *Desafio*: Garantir que o agente de Crédito saiba que o usuário já foi autenticado pelo agente de Triagem sem pedir os dados novamente.
    - *Solução*: Utilização do `AgentState` do LangGraph para compartilhar um estado global (variáveis `authenticated`, `cpf`, `messages`) entre todos os nós do grafo.

2.  **Roteamento de Intenção Ambígua**:
    - *Desafio*: Distinguir quando o usuário quer "ver saldo" (Crédito) ou "ver cotação" (Câmbio) apenas pelo texto, ou quando ele apenas concorda ("sim") com uma oferta anterior.
    - *Solução*: Implementação de um `main_router` híbrido que analisa palavras-chave e verifica o histórico imediato da conversa (última mensagem da IA) para entender o contexto de respostas curtas.

3.  **Consistência nas Respostas do LLM**:
    - *Desafio*: Evitar que o LLM invente dados ou formatos inválidos.
    - *Solução*: Uso estrito de *Tools* (ferramentas Python) para todas as operações de dados e *System Prompts* que proíbem formatação LaTeX e instruem o uso de linguagem natural simples para valores monetários.

4. **Conflito de Renderização Markdown/LaTeX**:

    - *Desafio*: O Streamlit utiliza Markdown que interpreta o símbolo de cifrão ($) como indicador de fórmulas matemáticas (LaTeX). Quando o agente retornava valores monetários (ex: "R$ 1.000,00"), a interface tentava renderizar o texto como uma equação, gerando erros de formatação (LaTeX-incompatible input) e ocultando o texto.
    - *Solução*: Implementação de uma regra de formatação nas ferramentas (tools) para "escapar" o símbolo de cifrão. Todas as saídas monetárias foram alteradas de R$ para R\$, garantindo que o Streamlit interprete o cifrão como texto literal e não como comando matemático.
   
## Escolhas Técnicas e Justificativas.

- **Python 3.12+**: Linguagem moderna e robusta para IA e manipulação de dados.
- **LangChain & LangGraph**:
    - *Justificativa*: O LangGraph foi escolhido por permitir a criação de fluxos cíclicos e controle de estado granular, essencial para um sistema onde o usuário pode transitar livremente entre diferentes contextos (crédito, câmbio, entrevista).
- **Google Gemini (LLM)**:
    - *Justificativa*: Modelo com excelente janela de contexto e raciocínio lógico, oferecendo um bom equilíbrio entre performance e custo.
- **Streamlit**:
    - *Justificativa*: Permite a criação rápida de interfaces de dados interativas em Python puro, ideal para prototipagem e demonstração de agentes.
- **Pandas**: Para manipulação eficiente da base de dados simulada (CSV).
- **Exchangerate.host API**: Serviço externo utilizado para obter as taxas de câmbio em tempo real.

## Tutorial de Execução e Testes

### Pré-requisitos
- Python 3.12 ou superior instalado.
- Uma chave de API do Google (Gemini).

### Instalação

1. **Clone o repositório** (ou baixe os arquivos).
2. **Crie um ambiente virtual e instale as dependências:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
3. **Configure a chave da API:**
   - O arquivo `.env` contém a chave `GOOGLE_API_KEY`.

### Execução

4. **Execute a aplicação:**
   ```bash
   streamlit run app.py
   ```
   
   > **Dica (Windows):** Você também pode executar o arquivo `run_app.bat` para iniciar a aplicação automaticamente.

### Roteiro de Testes

1. **Autenticação**:
   - Inicie a conversa com "Olá".
   - Forneça CPF `12345678900` e Data `1990-01-01`.
2. **Crédito**:
   - Pergunte "Qual meu limite?".
   - Peça "Aumentar meu limite para 5000".
3. **Entrevista**:
   - Se o aumento for negado, aceite fazer a entrevista.
   - Responda as perguntas (Renda, Emprego, etc.).
   - Verifique se o score foi atualizado.
4. **Câmbio**:
   - Pergunte "Quanto está o dólar?".

## Estrutura de Arquivos

- `app.py`: Interface Streamlit.
- `src/agents.py`: Definição dos agentes e ferramentas.
- `src/graph.py`: Lógica de orquestração do LangGraph.
- `src/utils.py`: Funções utilitárias e lógica de negócios.
- `data/`: Arquivos CSV simulando o banco de dados.
