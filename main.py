import os
import sys
import re
import time
import subprocess
import importlib.util
import shutil 

# --- TERMINAL COLORS ---
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"

# --- CAMINHO DO PROJETO ---
PROJECT_PATH = os.path.join(os.getcwd(), "base-app")

def print_status(msg, status="INFO"):
    if status == "OK":
        print(f"[{GREEN} OK {RESET}] {msg}")
    elif status == "ERROR":
        print(f"[{RED}FAIL{RESET}] {msg}")
    elif status == "WARN":
        print(f"[{YELLOW}WARN{RESET}] {msg}")
    else:
        print(f"[{CYAN}INFO{RESET}] {msg}")

def check_library(lib_name, import_name=None):
    if import_name is None: import_name = lib_name
    spec = importlib.util.find_spec(import_name)
    return spec is not None

def load_credentials():
    path = 'credentials.txt'
    if not os.path.exists(path):
        print_status(f"File '{path}' not found!", "ERROR")
        return None

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    config = {
        "google_key": None,
        "openai_key": None,
        "supabase_url": None,
        "supabase_key": None,
        "model": "models/gemini-2.5-flash-lite", 
        "local_model": None, # Adicionado para modelo local
        "provider": "google",
        "generic_key": None
    }

    # Busca > MODEL (Para o agente local)
    match_local = re.search(r'>\s*MODEL\s*=?\s*["\'](.*?)["\']', content)
    if match_local: config["local_model"] = match_local.group(1)

    match_generic = re.search(r'>\s*API KEY\s*=?\s*["\'](.*?)["\']', content)
    if match_generic: config["generic_key"] = match_generic.group(1)

    match_google = re.search(r'>\s*GOOGLE API KEY\s*=?\s*["\'](.*?)["\']', content)
    if match_google: config["google_key"] = match_google.group(1)

    match_openai = re.search(r'>\s*OPENAI API KEY\s*=?\s*["\'](.*?)["\']', content)
    if match_openai: config["openai_key"] = match_openai.group(1)

    match_url = re.search(r'>\s*SUPABASE URL\s*=?\s*["\'](.*?)["\']', content)
    if match_url: config["supabase_url"] = match_url.group(1)

    match_key = re.search(r'>\s*SUPABASE KEY\s*=?\s*["\'](.*?)["\']', content)
    if match_key: config["supabase_key"] = match_key.group(1)

    match_model = re.search(r'>\s*Agent Model\s*=?\s*["\'](.*?)["\']', content)
    if match_model: config["model"] = match_model.group(1)

    return config

def resolve_ai_identity(config):
    model_lower = config["model"].lower()
    
    if "gpt" in model_lower or "o1-" in model_lower:
        config["provider"] = "openai"
    # Adicionado suporte a Groq (Llama/Mixtral)
    elif "llama" in model_lower or "mixtral" in model_lower or "gemma" in model_lower and "groq" in config.get("generic_key", ""):
        # Nota: Gemma pode rodar no Google ou Groq, assumindo Groq se for Llama/Mixtral
        # ou se o usuário estiver usando um modelo específico da Groq.
        config["provider"] = "groq"
    elif "gemini" in model_lower:
        config["provider"] = "google"
    else:
        # Fallback por chave
        key_to_check = config["generic_key"]
        if key_to_check:
            if key_to_check.startswith("sk-"):
                config["provider"] = "openai"
            elif key_to_check.startswith("gsk_"): # Chaves Groq geralmente começam com gsk_
                config["provider"] = "groq"
            elif key_to_check.startswith("AIza"):
                config["provider"] = "google"
            else:
                config["provider"] = "google"

    # Mapeamento da chave genérica
    if config["generic_key"]:
        if config["provider"] == "openai":
            config["openai_key"] = config["generic_key"]
        elif config["provider"] == "groq":
            config["openai_key"] = config["generic_key"] # Groq usa um cliente similar, armazenamos aqui ou em var nova
        else:
            config["google_key"] = config["generic_key"]

    return config

def validate_environment(config):
    print_status(f"Detected Provider: {config['provider'].upper()}", "INFO")
    print_status(f"Target Model: {config['model']}", "INFO")

    if config["provider"] == "google":
        if not check_library("google.generativeai"):
            print_status("Library 'google-generativeai' missing.", "ERROR")
            print(f"👉 Run: {YELLOW}pip install google-generativeai{RESET}")
            return False
        if not config["google_key"]:
            print_status("Google Key missing.", "ERROR")
            return False

    elif config["provider"] == "openai":
        if not check_library("openai"):
            print_status("Library 'openai' missing.", "ERROR")
            print(f"👉 Run: {YELLOW}pip install openai{RESET}")
            return False
        if not config["openai_key"]:
            print_status("OpenAI Key missing.", "ERROR")
            return False
            
    # Validação Groq
    elif config["provider"] == "groq":
        if not check_library("groq"):
            print_status("Library 'groq' missing.", "ERROR")
            print(f"👉 Run: {YELLOW}pip install groq{RESET}")
            return False
        if not config["generic_key"] and not config["openai_key"]: # Reusa lógica de chave genérica
            print_status("Groq Key missing.", "ERROR")
            return False

    return True

def executar_reset_template():
    src_path = os.path.join(PROJECT_PATH, "src")
    
    if not os.path.exists(src_path):
        print_status("Pasta 'src' não encontrada. Criando...", "WARN")
        os.makedirs(src_path)
        
    print(f"\n{YELLOW}>>> Cleaning 'src' folder...{RESET}")
    
    for item in os.listdir(src_path):
        item_path = os.path.join(src_path, item)
        if os.path.isdir(item_path):
            try:
                shutil.rmtree(item_path)
                print(f"    - Deleted folder: {item}")
            except Exception as e:
                print(f"    - Error deleting {item}: {e}")
        elif os.path.isfile(item_path):
            if item not in ["App.jsx", "main.jsx", "index.css", "vite-env.d.ts"]:
                os.remove(item_path)
                print(f"    - Deleted file: {item}")

    print(f"{YELLOW}>>> Restoring Base Template Files...{RESET}")

    app_code = """export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <h1 className="text-2xl font-bold text-gray-500">
        Base Template (Waiting for IA...)
      </h1>
    </div>
  )
}"""
    with open(os.path.join(src_path, "App.jsx"), "w", encoding="utf-8") as f:
        f.write(app_code)

    css_code = """@tailwind base;
@tailwind components;
@tailwind utilities;"""
    with open(os.path.join(src_path, "index.css"), "w", encoding="utf-8") as f:
        f.write(css_code)

    main_code = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""
    with open(os.path.join(src_path, "main.jsx"), "w", encoding="utf-8") as f:
        f.write(main_code)

    print_status("Template Reset Successfully!", "OK")
    time.sleep(1)

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{CYAN}╔════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}║             REACT PROJECT GENERATOR                ║{RESET}")
        print(f"{CYAN}╚════════════════════════════════════════════════════╝{RESET}")
        
        print(f"\n{YELLOW}Select Option:{RESET}\n")
        
        print(f"   {GREEN}[1] 🏠 LOCAL AGENT{RESET}    (Ollama | Offline)")
        print(f"   {MAGENTA}[2] ☁️  CLOUD AGENT{RESET}    (Google/OpenAI | Online)")
        print(f"   {BLUE}[3] 🧹 RESET TEMPLATE{RESET}  (Clean Project Folder)")
        print(f"   {RED}[4] ❌ EXIT{RESET}")
        
        print(f"\n{CYAN}══════════════════════════════════════════════════════{RESET}")
        choice = input(">>> Select Option (1-4): ").strip()

        # === OPÇÃO 1: LOCAL ===
        if choice == "1":
            print(f"\n{GREEN}>>> Initializing Local Environment...{RESET}")
            
            # 1. Verifica Instalação
            if not check_library("ollama"):
                print_status("Library 'ollama' missing.", "ERROR")
                print(f"👉 Run: {YELLOW}pip install ollama{RESET}")
                input("\nPress ENTER to continue...")
                continue

            # 2. Verifica Credenciais (MODELO)
            config_raw = load_credentials()
            if not config_raw or not config_raw.get("local_model"):
                print_status("Missing 'MODEL' in credentials.txt", "ERROR")
                print(f"👉 Add line: {YELLOW}> MODEL = \"llama3.2\"{RESET}")
                input("\nPress ENTER to continue...")
                continue
            
            local_model_name = config_raw["local_model"]
            print_status(f"Target Local Model: {local_model_name}", "INFO")
            
            time.sleep(1)
            try:
                import fabrica_local
                # Passa o modelo lido para o script local
                fabrica_local.iniciar_sistema_local(local_model_name)
            except ImportError:
                print_status("Error: 'fabrica_local.py' not found.", "ERROR")
                input("\nPress ENTER to continue...")
            except Exception as e:
                print_status(f"Fatal Local Error: {e}", "ERROR")
                input("\nPress ENTER to continue...")

        # === OPÇÃO 2: CLOUD ===
        elif choice == "2":
            print(f"\n{MAGENTA}>>> Reading Cloud Credentials...{RESET}")
            config_raw = load_credentials()
            
            if not config_raw:
                input("\nPress ENTER to return to menu...")
                continue

            config = resolve_ai_identity(config_raw)

            if not validate_environment(config):
                print("\n❌ System Check Failed.")
                input("\nPress ENTER to return to menu...")
                continue
            
            print_status("System Ready. Launching Cloud Factory...", "OK")
            time.sleep(1)

            try:
                import fabrica
                fabrica.iniciar_sistema(config)
            except ImportError:
                print_status("Error: 'fabrica.py' not found.", "ERROR")
                input("\nPress ENTER to continue...")
            except AttributeError:
                print_status("Error: Function 'iniciar_sistema' not found in fabrica.py.", "ERROR")
                input("\nPress ENTER to continue...")
            except Exception as e:
                print_status(f"Fatal Cloud Error: {e}", "ERROR")
                input("\nPress ENTER to continue...")

        # === OPÇÃO 3: RESET ===
        elif choice == "3":
            executar_reset_template()
            input(f"\n{YELLOW}Press ENTER to return to menu...{RESET}")

        # === OPÇÃO 4: SAIR ===
        elif choice == "4":
            print("\nExiting... Goodbye! 👋")
            sys.exit()

        else:
            print(f"\n{RED}Invalid Option.{RESET}")
            time.sleep(1)

if __name__ == "__main__":
    main()