from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils import (
    authenticate_user, 
    get_max_limit_for_score, 
    log_limit_request, 
    calculate_score, 
    update_user_score,
    load_clientes
)
import os
import requests
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))

@tool
def check_auth(cpf: str, data_nascimento: str):
    """Autentica o usuário com CPF e Data de Nascimento (formato YYYY-MM-DD). Retorna os dados do usuário se sucesso."""
    user = authenticate_user(cpf, data_nascimento)
    if user:
        return {"status": "success", "user": user}
    return {"status": "failed", "message": "Autenticação falhou. Verifique os dados."}

@tool
def get_credit_limit(cpf: str):
    """Consulta o limite de crédito atual do usuário."""
    df = load_clientes()
    user = df[df['cpf'] == cpf]
    if not user.empty:
        return f"Seu limite atual é R\$ {user.iloc[0]['limite']}"
    return "Usuário não encontrado."

@tool
def request_limit_increase(cpf: str, new_limit: float):
    """Solicita aumento de limite de crédito. Verifica score e aprova/rejeita."""
    df = load_clientes()
    user = df[df['cpf'] == cpf]
    if user.empty:
        return "Usuário não encontrado."
    
    current_score = user.iloc[0]['score']
    current_limit = user.iloc[0]['limite']
    max_allowed = get_max_limit_for_score(current_score)
    
    if new_limit <= max_allowed:
        status = "aprovado"
        # Atualiza limite no BD (simplificado, geralmente seria uma etapa separada)
        df.loc[df['cpf'] == cpf, 'limite'] = new_limit
        df.to_csv(os.path.join('data', 'clientes.csv'), index=False)
        msg = f"Parabéns! Seu aumento para R\$ {new_limit} foi APROVADO."
    else:
        status = "rejeitado"
        msg = f"Solicitação REJEITADA. Seu score ({current_score}) permite no máximo R\$ {max_allowed}. Gostaria de fazer uma entrevista para tentar aumentar seu score?"
        
    log_limit_request(cpf, current_limit, new_limit, status)
    return msg

@tool
def process_interview(cpf: str, renda: float, tipo_emprego: str, dependentes: int, tem_dividas: str, despesas: float):
    """Processa a entrevista de crédito, recalcula e atualiza o score."""
    new_score = calculate_score(renda, tipo_emprego, dependentes, tem_dividas, despesas)
    update_user_score(cpf, new_score)
    return f"Entrevista concluída. Seu novo score é {new_score}. Você pode tentar solicitar o aumento de limite novamente."

@tool
def get_exchange_rate(currency: str = "USD"):
    """Consulta a taxa de câmbio atual usando exchangerate.host."""
    api_key = os.getenv("EXCHANGERATE_API_KEY")
    if not api_key:
        return "Erro de configuração: API Key não encontrada."
    
    # A API gratuita pode ter limitações no 'source'. Se falhar com source diferente de USD,
    # teríamos que usar USD como source e converter, mas vamos tentar usar o source solicitado.
    url = "http://api.exchangerate.host/live"
    params = {
        "access_key": api_key,
        "source": currency.upper(),
        "currencies": "BRL",
        "format": 1
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("success"):
            quotes = data.get("quotes", {})
            # A chave em quotes é geralmente SOURCE+DEST, ex: USDBRL
            pair = f"{currency.upper()}BRL"
            rate = quotes.get(pair)
            if rate:
                return f"A cotação atual do {currency.upper()} é R\$ {rate:.2f}"
            else:
                return f"Não foi possível obter a cotação para {currency} em BRL. Verifique se a moeda é válida."
        else:
            # Tentar fallback se o erro for relacionado ao Source (plano gratuito muitas vezes só permite USD)
            # Mas vamos primeiro retornar o erro para debug se necessário, ou tratar silenciosamente.
            error_code = data.get("error", {}).get("code")
            error_info = data.get("error", {}).get("info", "Erro desconhecido")
            
            if error_code == 105: # Access Restricted (provavelmente source não permitido)
                 return f"Erro: O plano atual da API não permite mudar a moeda base de USD. Tente converter USD."
            
            return f"Erro na API de câmbio: {error_info}"
            
    except Exception as e:
        return f"Erro ao conectar com serviço de câmbio: {str(e)}"

@tool
def end_conversation():
    """Encerra a conversa explicitamente quando o usuário solicitar."""
    return "Conversa encerrada pelo usuário."

# Prompts dos Agentes
TRIAGEM_PROMPT = """Você é o Agente de Triagem do Banco Ágil.
Seu objetivo é autenticar o cliente.
1. Peça o CPF.
2. Peça a Data de Nascimento (YYYY-MM-DD).
3. Use a ferramenta `check_auth` para validar.
4. Se autenticado com sucesso, cumprimente o usuário e pergunte qual opção ele deseja. (Crédito ou Câmbio).
5. Se falhar, peça para tentar novamente.
Caso o usuário queira sair, use a ferramenta `end_conversation`.
"""

CREDITO_PROMPT = """Você é o Agente de Crédito.
Responsabilidades:
1. Consultar limite atual (`get_credit_limit`).
2. Solicitar aumento de limite (`request_limit_increase`).

IMPORTANTE SOBRE FORMATAÇÃO:
- JAMAIS use formatação LaTeX para valores monetários (ex: NÃO use $100,00, \frac, etc).
- Escreva valores APENAS como texto simples Ex: "Rs 1.000,00".(Com s minúsculo)

IMPORTANTE SOBRE LÓGICA:
- Se o usuário pedir aumento para um valor IGUAL ou MENOR que o atual, explique claramente que o limite já é esse valor e pergunte se ele quer aumentar para um valor MAIOR. Seja direto.

Após fornecer a informação ou realizar a ação, PERGUNTE se o usuário deseja mais alguma coisa (ex: "Posso ajudar com mais alguma coisa?").
Caso o usuário queira sair, use a ferramenta `end_conversation`.
"""

ENTREVISTA_PROMPT = """Você é o Agente de Entrevista.
Conduza uma entrevista para atualizar o score.
Pergunte UM dado por vez:
1. Renda mensal
2. Tipo de emprego (formal, autonomo, desempregado)
3. Despesas mensais
4. Número de dependentes
5. Tem dívidas? (sim/nao)

Ao final, use `process_interview` para calcular e salvar o novo score.
Depois, informe o novo score e PERGUNTE claramente: "Deseja tentar solicitar o aumento de limite novamente agora?"
Caso o usuário queira sair, use a ferramenta `end_conversation`.
"""

CAMBIO_PROMPT = """Você é o Agente de Câmbio.
Forneça cotações de moedas usando `get_exchange_rate`.

IMPORTANTE SOBRE FORMATAÇÃO:
- JAMAIS use formatação LaTeX. Escreva valores como texto simples (ex: "R$ 5,50").

Após fornecer a cotação, pergunte se o usuário deseja ver outra moeda ou precisa de mais alguma ajuda.
Caso o usuário queira sair, use a ferramenta `end_conversation`.
"""
