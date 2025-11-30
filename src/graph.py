from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator
from src.agents import (
    llm, 
    check_auth, get_credit_limit, request_limit_increase, process_interview, get_exchange_rate, end_conversation,
    TRIAGEM_PROMPT, CREDITO_PROMPT, ENTREVISTA_PROMPT, CAMBIO_PROMPT
)

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    cpf: str
    authenticated: bool
    current_agent: str
    triagem_attempts: int

# --- Funções dos Nós ---
def main_router(state: AgentState):
    # --- DEBUG ---
    messages = state['messages']
    last_user_msg = messages[-1]
    
    # Tratamento seguro para a mensagem do usuário (embora geralmente seja string)
    if isinstance(last_user_msg.content, str):
        text = last_user_msg.content.lower()
    else:
        text = str(last_user_msg.content).lower()
    
    current = state.get('current_agent', 'triagem')
    print(f"\n--- ROTEADOR ---")
    print(f"Agente Atual: {current}")
    print(f"Texto do Usuário: '{text}'")

    # 1. Retorno de Ferramenta (Prioridade Máxima)
    if len(messages) > 1 and messages[-1].type == 'tool':
        print("DECISÃO: Retorno de ferramenta. Mantendo agente.")
        return current

    # 2. Autenticação
    if not state.get('authenticated', False):
        is_auth = False
        for msg in messages:
            if msg.type == 'tool' and 'check_auth' in str(msg.name) and '"status": "success"' in msg.content:
                is_auth = True
                break
        
        if is_auth:
            state['authenticated'] = True
        else:
            print("DECISÃO: Não autenticado. Indo para Triagem.")
            return "triagem"

    # 3. Roteamento por Palavras-Chave
    if any(x in text for x in ["câmbio", "cambio", "dólar", "dolar", "moeda", "cotacao", "cotação", "euro", "converter"]):
        print("DECISÃO: Palavra-chave de Câmbio detectada -> cambio")
        return "cambio"

    if any(x in text for x in ["crédito", "credito", "limite", "aumento"]):
        print("DECISÃO: Palavra-chave de Crédito detectada -> credito")
        return "credito"
        
    if any(x in text for x in ["entrevista", "score", "pontuação", "pontuacao", "renda"]):
        print("DECISÃO: Palavra-chave de Entrevista detectada -> entrevista")
        return "entrevista"

    # 4. Checagem de CONTEXTO (Histórico Imediato) - COM CORREÇÃO DE ERRO
    if len(messages) >= 2:
        last_ai_msg = messages[-2]
        
        if hasattr(last_ai_msg, 'content') and isinstance(last_ai_msg, AIMessage):
            # --- CORREÇÃO AQUI: Extrair texto de forma segura ---
            content = last_ai_msg.content
            last_ai_text = ""
            
            if isinstance(content, str):
                last_ai_text = content.lower()
            elif isinstance(content, list):
                # Se for lista, junta as partes de texto e ignora as partes de ferramenta
                text_parts = []
                for part in content:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict) and 'text' in part:
                        text_parts.append(part['text'])
                last_ai_text = "".join(text_parts).lower()
            # ----------------------------------------------------
            
            print(f"   (Contexto Anterior IA: '{last_ai_text[:50]}...')")

            agreement_words = ["sim", "claro", "quero", "pode ser", "ok", "com certeza", "gostaria", "para"]
            
            # Verifica se o usuário concordou ou deu um valor (ex: "para 2000")
            user_agreed = any(w in text for w in agreement_words) or any(char.isdigit() for char in text)

            if user_agreed:
                if "câmbio" in last_ai_text or "moeda" in last_ai_text:
                    print("DECISÃO: Contexto (Bot ofereceu Câmbio) -> cambio")
                    return "cambio"
                
                if "entrevista" in last_ai_text or "score" in last_ai_text:
                    print("DECISÃO: Contexto (Bot ofereceu Entrevista) -> entrevista")
                    return "entrevista"
                
                # Contexto específico para crédito (ex: "para 2000")
                if "limite" in last_ai_text or "aumento" in last_ai_text or "r$" in last_ai_text:
                     print("DECISÃO: Contexto (Assunto de Crédito) -> credito")
                     return "credito"

    # 5. Fallback
    print(f"DECISÃO: Nenhuma mudança detectada. Mantendo: {current}")
    return current

def triagem_node(state: AgentState):
    messages = state['messages']
    current_attempts = state.get('triagem_attempts', 0)
    
    if len(messages) > 0 and messages[-1].type == 'tool' and 'check_auth' in str(messages[-1].name):
        if '"status": "failed"' in messages[-1].content:
            current_attempts += 1
            
    if current_attempts >= 3:
        return {
            "messages": [AIMessage(content="Número máximo de tentativas excedido.")],
            "triagem_attempts": current_attempts,
            "current_agent": "triagem"
        }

    response = llm.bind_tools([check_auth, end_conversation]).invoke(
        [{"role": "system", "content": TRIAGEM_PROMPT}] + messages
    )
    return {"messages": [response], "current_agent": "triagem", "triagem_attempts": current_attempts}

def credito_node(state: AgentState):
    response = llm.bind_tools([get_credit_limit, request_limit_increase, end_conversation]).invoke(
        [{"role": "system", "content": CREDITO_PROMPT}] + state['messages']
    )
    return {"messages": [response], "current_agent": "credito"}

def entrevista_node(state: AgentState):
    response = llm.bind_tools([process_interview, end_conversation]).invoke(
        [{"role": "system", "content": ENTREVISTA_PROMPT}] + state['messages']
    )
    return {"messages": [response], "current_agent": "entrevista"}

def cambio_node(state: AgentState):
    response = llm.bind_tools([get_exchange_rate, end_conversation]).invoke(
        [{"role": "system", "content": CAMBIO_PROMPT}] + state['messages']
    )
    return {"messages": [response], "current_agent": "cambio"}

# --- Construção do Grafo ---

workflow_router = StateGraph(AgentState)

workflow_router.add_node("triagem", triagem_node)
workflow_router.add_node("credito", credito_node)
workflow_router.add_node("entrevista", entrevista_node)
workflow_router.add_node("cambio", cambio_node)
workflow_router.add_node("tools", ToolNode([check_auth, get_credit_limit, request_limit_increase, process_interview, get_exchange_rate, end_conversation]))

def route_entry(state):
    return main_router(state)

workflow_router.set_conditional_entry_point(
    route_entry,
    {
        "triagem": "triagem",
        "credito": "credito",
        "entrevista": "entrevista",
        "cambio": "cambio"
    }
)

def agent_router(state):
    last_message = state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and len(last_message.tool_calls) > 0:
        return "tools"
    return END

workflow_router.add_conditional_edges("triagem", agent_router)
workflow_router.add_conditional_edges("credito", agent_router)
workflow_router.add_conditional_edges("entrevista", agent_router)
workflow_router.add_conditional_edges("cambio", agent_router)

def tool_router(state):
    return state.get('current_agent', 'triagem')

workflow_router.add_conditional_edges("tools", tool_router)

app_graph = workflow_router.compile()