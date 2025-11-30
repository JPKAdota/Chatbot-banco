import pandas as pd
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
CLIENTES_FILE = os.path.join(DATA_DIR, 'clientes.csv')
SCORE_FILE = os.path.join(DATA_DIR, 'score_limite.csv')
SOLICITACOES_FILE = os.path.join(DATA_DIR, 'solicitacoes_aumento_limite.csv')

def load_clientes():
    return pd.read_csv(CLIENTES_FILE, dtype={'cpf': str})

def save_clientes(df):
    df.to_csv(CLIENTES_FILE, index=False)

def authenticate_user(cpf, dob):
    df = load_clientes()
    user = df[(df['cpf'] == cpf) & (df['data_nascimento'] == dob)]
    if not user.empty:
        return user.iloc[0].to_dict()
    return None

def get_max_limit_for_score(score):
    df = pd.read_csv(SCORE_FILE)
    for _, row in df.iterrows():
        if row['min_score'] <= score <= row['max_score']:
            return row['limite_maximo']
    return 0.0

def log_limit_request(cpf, current_limit, requested_limit, status):
    new_request = {
        'cpf_cliente': cpf,
        'data_hora_solicitacao': datetime.now().isoformat(),
        'limite_atual': current_limit,
        'novo_limite_solicitado': requested_limit,
        'status_pedido': status
    }
    
    if os.path.exists(SOLICITACOES_FILE):
        df = pd.read_csv(SOLICITACOES_FILE)
    else:
        df = pd.DataFrame(columns=['cpf_cliente', 'data_hora_solicitacao', 'limite_atual', 'novo_limite_solicitado', 'status_pedido'])
        
    df = pd.concat([df, pd.DataFrame([new_request])], ignore_index=True)
    df.to_csv(SOLICITACOES_FILE, index=False)

def calculate_score(renda, tipo_emprego, dependentes, tem_dividas, despesas):
    peso_renda = 30
    peso_emprego = {
        "formal": 300,
        "autonomo": 200,
        "desempregado": 0
    }
    peso_dependentes = {
        0: 100,
        1: 80,
        2: 60,
        "3+": 30
    }
    peso_dividas = {
        "sim": -100,
        "nao": 100
    }
    
    # Trata a chave de dependentes
    dep_key = dependentes
    if isinstance(dependentes, int) and dependentes >= 3:
        dep_key = "3+"
    elif str(dependentes) not in ['0', '1', '2']:
         dep_key = "3+"
    else:
        dep_key = int(dependentes)

    score = (
        (renda / (despesas + 1)) * peso_renda +
        peso_emprego.get(tipo_emprego, 0) +
        peso_dependentes.get(dep_key, 30) +
        peso_dividas.get(tem_dividas, 0)
    )
    
    return min(max(int(score), 0), 1000) # Garante intervalo 0-1000

def update_user_score(cpf, new_score):
    df = load_clientes()
    if cpf in df['cpf'].values:
        df.loc[df['cpf'] == cpf, 'score'] = new_score
        save_clientes(df)
        return True
    return False
