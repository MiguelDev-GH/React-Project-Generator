import os
import sys
import re
import time
import subprocess
import importlib.util
import shutil # Necessário para deletar pastas

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
        "provider": "google",
        "generic_key": None
    }

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
    elif "gemini" in model_lower or "gemma" in model_lower:
        config["provider"] = "google"
    else:
        key_to_check = config["generic_key"]
        if key_to_check:
            if key_to_check.startswith("sk-"):
                config["provider"] = "openai"
            elif key_to_check.startswith("AIza"):
                config["provider"] = "google"
            else:
                config["provider"] = "google"

    if config["generic_key"]:
        if config["provider"] == "openai":
            config["openai_key"] = config["generic_key"]
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

    return True

# --- FUNÇÃO DE RESET (NOVA) ---
def executar_reset_template():
    src_path = os.path.join(PROJECT_PATH, "src")
    
    if not os.path.exists(src_path):
        print_status("Pasta 'src' não encontrada. Criando...", "WARN")
        os.makedirs(src_path)
        
    print(f"\n{YELLOW}>>> Cleaning 'src' folder...{RESET}")
    
    # 1. Deletar tudo (pastas e arquivos soltos indesejados)
    for item in os.listdir(src_path):
        item_path = os.path.join(src_path, item)
        # Não deleta os arquivos sagrados ainda, vamos sobrescrever depois
        if os.path.isdir(item_path):
            try:
                shutil.rmtree(item_path) # Deleta components, lib, hooks, etc
                print(f"    - Deleted folder: {item}")
            except Exception as e:
                print(f"    - Error deleting {item}: {e}")
        elif os.path.isfile(item_path):
            if item not in ["App.jsx", "main.jsx", "index.css", "vite-env.d.ts"]:
                os.remove(item_path) # Deleta api.js, setup.js, etc
                print(f"    - Deleted file: {item}")

    print(f"{YELLOW}>>> Restoring Base Template Files...{RESET}")

    # 2. Restaurar App.jsx
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

    # 3. Restaurar index.css
    css_code = """@tailwind base;
@tailwind components;
@tailwind utilities;"""
    with open(os.path.join(src_path, "index.css"), "w", encoding="utf-8") as f:
        f.write(css_code)

    # 4. Restaurar main.jsx
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

# --- MENU PRINCIPAL ---
def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{CYAN}╔════════════════════════════════════════════════════╗{RESET}")
        print(f"{CYAN}║              REACT PROJECT GENERATOR               ║{RESET}")
        print(f"{CYAN}╚════════════════════════════════════════════════════╝{RESET}")
        
        print(f"\n{YELLOW}Select Option:{RESET}\n")
        
        print(f"   {GREEN}[1] 🏠 LOCAL AGENT{RESET}    (Llama 3 | Offline)")
        print(f"   {MAGENTA}[2] ☁️  CLOUD AGENT{RESET}    (Google/OpenAI | Online)")
        print(f"   {BLUE}[3] 🧹 RESET TEMPLATE{RESET}  (Clean Project Folder)")
        print(f"   {RED}[4] ❌ EXIT{RESET}")
        
        print(f"\n{CYAN}══════════════════════════════════════════════════════{RESET}")
        choice = input(">>> Select Option (1-4): ").strip()

        # === OPÇÃO 1: LOCAL ===
        if choice == "1":
            print(f"\n{GREEN}>>> Initializing Local Environment...{RESET}")
            if not check_library("ollama"):
                print_status("Library 'ollama' missing.", "ERROR")
                print(f"👉 Run: {YELLOW}pip install ollama{RESET}")
                input("\nPress ENTER to continue...")
                continue
            
            time.sleep(1)
            try:
                import fabrica_local
                fabrica_local.iniciar_sistema_local()
                # Não damos break aqui para permitir que o usuário volte ao menu se quiser
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
                fabrica.start_system(config)
            except ImportError:
                print_status("Error: 'fabrica.py' not found.", "ERROR")
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