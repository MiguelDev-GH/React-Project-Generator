import os
import sys
import re
import time
import subprocess
import importlib.util

# --- TERMINAL COLORS ---
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

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
    """Reads credentials.txt using robust Regex"""
    path = 'credentials.txt'
    if not os.path.exists(path):
        print_status(f"File '{path}' not found!", "ERROR")
        return None

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Internal config structure matches what fabrica.py expects
    config = {
        "google_key": None,
        "openai_key": None,
        "supabase_url": None,
        "supabase_key": None,
        "model": "models/gemini-2.5-flash-lite", # Default
        "provider": "google", # Default
        "generic_key": None
    }

    # --- RAW READING ---
    # Detects generic key
    match_generic = re.search(r'>\s*API KEY\s*=?\s*["\'](.*?)["\']', content)
    if match_generic: config["generic_key"] = match_generic.group(1)

    # Detects specific keys (Legacy support)
    match_google = re.search(r'>\s*GOOGLE API KEY\s*=?\s*["\'](.*?)["\']', content)
    if match_google: config["google_key"] = match_google.group(1)

    match_openai = re.search(r'>\s*OPENAI API KEY\s*=?\s*["\'](.*?)["\']', content)
    if match_openai: config["openai_key"] = match_openai.group(1)

    # Database config
    match_url = re.search(r'>\s*SUPABASE URL\s*=?\s*["\'](.*?)["\']', content)
    if match_url: config["supabase_url"] = match_url.group(1)

    match_key = re.search(r'>\s*SUPABASE KEY\s*=?\s*["\'](.*?)["\']', content)
    if match_key: config["supabase_key"] = match_key.group(1)

    # Agent Model
    match_model = re.search(r'>\s*Agent Model\s*=?\s*["\'](.*?)["\']', content)
    if match_model: config["model"] = match_model.group(1)

    return config

def resolve_ai_identity(config):
    """Auto-detects provider based on Model Name or Key Format"""
    model_lower = config["model"].lower()
    
    # Logic 1: Check Model Name
    if "gpt" in model_lower or "o1-" in model_lower:
        config["provider"] = "openai"
    elif "gemini" in model_lower or "gemma" in model_lower:
        config["provider"] = "google"
    else:
        # Logic 2: Check Key Format (sk- vs AIza)
        key_to_check = config["generic_key"]
        if key_to_check:
            if key_to_check.startswith("sk-"):
                config["provider"] = "openai"
            elif key_to_check.startswith("AIza"):
                config["provider"] = "google"
            else:
                config["provider"] = "google" # Default fallback

    # Assign generic key to the correct internal slot
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
            print_status("Google Key missing (API KEY or GOOGLE API KEY).", "ERROR")
            return False

    elif config["provider"] == "openai":
        if not check_library("openai"):
            print_status("Library 'openai' missing.", "ERROR")
            print(f"👉 Run: {YELLOW}pip install openai{RESET}")
            return False
        if not config["openai_key"]:
            print_status("OpenAI Key missing (API KEY or OPENAI API KEY).", "ERROR")
            return False

    return True

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{CYAN}╔══════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║    SYSTEM CHECK & AUTO-DETECT v7.4   ║{RESET}")
    print(f"{CYAN}╚══════════════════════════════════════╝{RESET}")
    
    print(">>> Reading configuration...\n")

    # 1. Load raw config
    config_raw = load_credentials()
    if not config_raw: sys.exit()

    # 2. Figure out which AI to use
    config = resolve_ai_identity(config_raw)

    # 3. Validate libraries and keys
    if not validate_environment(config):
        print("\n❌ System Check Failed. Please check 'credentials.txt'.")
        sys.exit()
    
    print_status("System Ready. Launching Factory...", "OK")
    time.sleep(1)

    # 4. Import and Run Factory
    try:
        import fabrica
        # Calls the function you defined in fabrica.py
        fabrica.iniciar_sistema(config)
    except ImportError as e:
        print_status(f"Error importing fabrica.py: {e}", "ERROR")
        print("Make sure 'fabrica.py' is in the same folder.")
    except Exception as e:
        print_status(f"Fatal Error: {e}", "ERROR")

if __name__ == "__main__":
    main()