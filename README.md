# Banco Ágil - Agente de Atendimento Inteligente

Este projeto implementa um sistema de atendimento bancário automatizado utilizando Agentes de IA. O sistema é capaz de autenticar usuários, consultar limites, processar solicitações de aumento de crédito, realizar entrevistas para atualização de score e fornecer cotações de moedas.

## Arquitetura

O sistema utiliza uma arquitetura multi-agente orquestrada pelo **LangGraph**:

- **Agente de Triagem**: Responsável pela autenticação do usuário (CPF e Data de Nascimento).
- **Agente de Crédito**: Gerencia consultas e solicitações de limite de crédito.
- **Agente de Entrevista**: Conduz uma entrevista para recalcular o score de crédito do cliente.
- **Agente de Câmbio**: Fornece cotações de moedas.

A interface do usuário é construída com **Streamlit**.

## Tecnologias

- Python 3.12+
- LangChain & LangGraph
- Google Gemini (LLM)
- Streamlit
- Pandas

## Configuração e Execução

1. **Clone o repositório** (ou baixe os arquivos).

2. **Crie um ambiente virtual e instale as dependências:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **Configure a chave da API:**
   - O arquivo `.env` já deve conter a chave `GOOGLE_API_KEY`.

4. **Execute a aplicação:**
   ```bash
   streamlit run app.py
   ```

## Uso

1. Ao abrir a aplicação, inicie a conversa (ex: "Olá").
2. Forneça um CPF e Data de Nascimento válidos para autenticação.
   - **Teste 1**: CPF `12345678900`, Data `1990-01-01`
   - **Teste 2**: CPF `98765432100`, Data `1985-05-15`
3. Após autenticado, você pode:
   - Perguntar seu limite de crédito.
   - Pedir aumento de limite.
   - Solicitar cotação do dólar.

## Estrutura de Arquivos

- `app.py`: Interface Streamlit.
- `src/agents.py`: Definição dos agentes e ferramentas.
- `src/graph.py`: Lógica de orquestração do LangGraph.
- `src/utils.py`: Funções utilitárias e lógica de negócios.
- `data/`: Arquivos CSV simulando o banco de dados.
