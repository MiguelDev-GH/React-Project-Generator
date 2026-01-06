import os
import sys
import re
import time
import subprocess
import importlib.util

# --- CORES PARA O TERMINAL ---
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

def print_status(msg, status="INFO"):
    if status == "OK":
        print(f"[{GREEN} OK {RESET}] {msg}")
    elif status == "ERROR":
        print(f"[{RED}ERRO{RESET}] {msg}")
    elif status == "WARN":
        print(f"[{YELLOW}WARN{RESET}] {msg}")
    else:
        print(f"[{CYAN}INFO{RESET}] {msg}")

def verificar_biblioteca(nome_lib, nome_import=None):
    if nome_import is None: nome_import = nome_lib
    spec = importlib.util.find_spec(nome_import)
    return spec is not None

def ler_credenciais():
    """Lê credenciais genéricas ou específicas"""
    caminho = 'credentials.txt'
    if not os.path.exists(caminho):
        print_status(f"Arquivo '{caminho}' não encontrado!", "ERROR")
        return None

    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    config = {
        "google_key": None,
        "openai_key": None,
        "supabase_url": None,
        "supabase_key": None,
        "model": "models/gemini-2.5-flash-lite", # Default se nada for informado
        "provider": "google", # Default inicial
        "generic_key": None   # Chave genérica temporária
    }

    # --- 1. LEITURA BRUTA ---
    
    # Procura chave Genérica (> API KEY)
    match_generic = re.search(r'>\s*API KEY\s*=?\s*["\'](.*?)["\']', conteudo)
    if match_generic: config["generic_key"] = match_generic.group(1)

    # Procura chaves Específicas (Legacy Support)
    match_google = re.search(r'>\s*GOOGLE API KEY\s*=?\s*["\'](.*?)["\']', conteudo)
    if match_google: config["google_key"] = match_google.group(1)

    match_openai = re.search(r'>\s*OPENAI API KEY\s*=?\s*["\'](.*?)["\']', conteudo)
    if match_openai: config["openai_key"] = match_openai.group(1)

    # Supabase e Modelo
    match_url = re.search(r'>\s*SUPABASE URL\s*=?\s*["\'](.*?)["\']', conteudo)
    if match_url: config["supabase_url"] = match_url.group(1)

    match_key = re.search(r'>\s*SUPABASE KEY\s*=?\s*["\'](.*?)["\']', conteudo)
    if match_key: config["supabase_key"] = match_key.group(1)

    match_model = re.search(r'>\s*Agent Model\s*=?\s*["\'](.*?)["\']', conteudo)
    if match_model: config["model"] = match_model.group(1)

    return config

def resolver_identidade_da_ia(config):
    """
    Decide quem é o provedor (Google vs OpenAI) baseado
    no nome do modelo OU no formato da chave.
    """
    
    model_lower = config["model"].lower()
    
    # HEURÍSTICA 1: Nome do Modelo (O mais confiável)
    if "gpt" in model_lower or "o1-" in model_lower:
        config["provider"] = "openai"
    elif "gemini" in model_lower or "gemma" in model_lower:
        config["provider"] = "google"
    else:
        # HEURÍSTICA 2: Formato da Chave (Se o modelo for desconhecido)
        # Se temos uma chave genérica, analisamos ela
        key_to_check = config["generic_key"]
        
        if key_to_check:
            if key_to_check.startswith("sk-"):
                config["provider"] = "openai"
            elif key_to_check.startswith("AIza"):
                config["provider"] = "google"
            else:
                # Se não dá pra saber, assume Google (padrão do script)
                config["provider"] = "google"

    # --- ATRIBUIÇÃO FINAL DA CHAVE ---
    # Se o usuário usou a chave genérica, movemos ela para o lugar certo
    if config["generic_key"]:
        if config["provider"] == "openai":
            config["openai_key"] = config["generic_key"]
        else:
            config["google_key"] = config["generic_key"]

    return config

def validar_ambiente(config):
    print_status(f"Provedor Detectado: {config['provider'].upper()}", "INFO")
    print_status(f"Modelo Alvo: {config['model']}", "INFO")

    # Validação Google
    if config["provider"] == "google":
        if not verificar_biblioteca("google.generativeai"):
            print_status("Biblioteca 'google-generativeai' faltando.", "ERROR")
            print(f"👉 Execute: {YELLOW}pip install google-generativeai{RESET}")
            return False
        if not config["google_key"]:
            print_status("Chave do Google não encontrada (API KEY ou GOOGLE API KEY).", "ERROR")
            return False

    # Validação OpenAI
    elif config["provider"] == "openai":
        if not verificar_biblioteca("openai"):
            print_status("Biblioteca 'openai' faltando.", "ERROR")
            print(f"👉 Execute: {YELLOW}pip install openai{RESET}")
            return False
        if not config["openai_key"]:
            print_status("Chave da OpenAI não encontrada (API KEY ou OPENAI API KEY).", "ERROR")
            return False

    return True

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{CYAN}╔══════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║    SYSTEM CHECK & AUTO-DETECT v7.2   ║{RESET}")
    print(f"{CYAN}╚══════════════════════════════════════╝{RESET}")
    
    print(">>> Lendo configurações...\n")

    # 1. Ler
    config_raw = ler_credenciais()
    if not config_raw: sys.exit()

    # 2. Resolver Inteligência (Quem é a IA?)
    config = resolver_identidade_da_ia(config_raw)

    # 3. Validar se tem tudo que precisa
    if not validar_ambiente(config):
        print("\n❌ Falha na verificação. Verifique seu credentials.txt.")
        sys.exit()
    
    print_status("Sistema pronto. Iniciando Fábrica...", "OK")
    time.sleep(1)

    # 4. Executar Fabrica
    try:
        import fabrica
        fabrica.iniciar_sistema(config)
    except ImportError as e:
        print_status(f"Erro ao importar fabrica.py: {e}", "ERROR")
    except Exception as e:
        print_status(f"Erro fatal: {e}", "ERROR")

if __name__ == "__main__":
    main()