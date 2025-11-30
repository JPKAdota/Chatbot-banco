import streamlit as st
from src.graph import app_graph
from langchain_core.messages import HumanMessage, AIMessage
import pandas as pd

def get_message_text(message):
    if isinstance(message.content, str):
        return message.content
    elif isinstance(message.content, list):
        # Trata lista de blocos (ex: [{'type': 'text', 'text': '...'}])
        text_parts = []
        for part in message.content:
            if isinstance(part, dict) and 'text' in part:
                text_parts.append(part['text'])
            elif isinstance(part, str):
                text_parts.append(part)
        return "".join(text_parts)
    return str(message.content)

st.set_page_config(page_title="Banco Ágil - Atendimento Inteligente", page_icon="🏦")

st.title("🏦 Banco Ágil - Atendimento Virtual")

# Barra lateral para debug/info
with st.sidebar:
    st.header("Debug / Info")
    if st.checkbox("Mostrar Dados dos Clientes"):
        try:
            df = pd.read_csv("data/clientes.csv")
            st.dataframe(df)
        except:
            st.error("Arquivo de clientes não encontrado.")
            
    if st.checkbox("Mostrar Solicitações"):
        try:
            df = pd.read_csv("data/solicitacoes_aumento_limite.csv")
            st.dataframe(df)
        except:
            st.write("Nenhuma solicitação ainda.")

# Inicializa o estado da sessão
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "graph_state" not in st.session_state:
    st.session_state.graph_state = {"messages": [], "authenticated": False, "current_agent": "triagem"}

# Exibe mensagens do chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada do chat
if prompt := st.chat_input("Digite sua mensagem..."):
    # Adiciona mensagem do usuário à UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Adiciona ao estado do grafo
    st.session_state.graph_state['messages'].append(HumanMessage(content=prompt))
    
    # Executa o grafo
    with st.spinner("Processando..."):
        # Precisamos executar o grafo até que ele pare no FIM
        # O compile() retorna um Runnable
        
        # Nota: O estado do LangGraph é imutável no sentido de que o invoke retorna um novo estado
        # Precisamos passar o histórico do estado atual
        
        # Idealmente usamos um checkpointer para persistência, mas para este app Streamlit simples
        # podemos apenas passar o dicionário de estado.
        
        final_state = app_graph.invoke(st.session_state.graph_state)
        
        # Atualiza nosso estado de sessão com o novo estado
        st.session_state.graph_state = final_state
        
        # Obtém a última mensagem da IA
        last_msg = final_state['messages'][-1]
        
        if isinstance(last_msg, AIMessage):
            content = get_message_text(last_msg)
            st.session_state.messages.append({"role": "assistant", "content": content})
            with st.chat_message("assistant"):
                st.markdown(content)

# Informações de ajuda
st.markdown("---")
st.caption("Dica: Comece dizendo 'Olá' e forneça seu CPF e Data de Nascimento para se autenticar.")
st.caption("CPFs de teste: 12345678900 (1990-01-01), 98765432100 (1985-05-15)")
