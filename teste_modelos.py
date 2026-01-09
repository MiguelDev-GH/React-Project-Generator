import os
import sys
import re

try:
    import google.generativeai as genai
    LIB_GOOGLE = True
except ImportError:
    LIB_GOOGLE = False

try:
    from openai import OpenAI
    LIB_OPENAI = True
except ImportError:
    LIB_OPENAI = False

# --- TERMINAL COLORS ---
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def load_keys():
    """Reads keys from credentials.txt"""
    keys = {"google": None, "openai": None}
    
    try:
        with open('credentials.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            
            match_google = re.search(r'>\s*GOOGLE API KEY\s*=?\s*["\'](.*?)["\']', content)
            if match_google: keys["google"] = match_google.group(1)

            match_openai = re.search(r'>\s*OPENAI API KEY\s*=?\s*["\'](.*?)["\']', content)
            if match_openai: keys["openai"] = match_openai.group(1)

            match_generic = re.search(r'>\s*API KEY\s*=?\s*["\'](.*?)["\']', content)
            if match_generic:
                generic_key = match_generic.group(1)
                if generic_key.startswith("sk-"):
                    if not keys["openai"]: keys["openai"] = generic_key
                elif generic_key.startswith("AIza"):
                    if not keys["google"]: keys["google"] = generic_key

    except FileNotFoundError:
        print(f"\n{RED}❌ CRITICAL ERROR: File 'credentials.txt' not found.{RESET}")
        sys.exit()
        
    return keys

def list_google(api_key):
    print(f"\n{CYAN}>>> 🔵 Searching GOOGLE (Gemini) models...{RESET}")
    
    if not LIB_GOOGLE:
        print(f"{RED}❌ Library 'google-generativeai' not installed.{RESET}")
        return

    if not api_key:
        print(f"{YELLOW}⚠️  Google Key not found.{RESET}")
        return

    try:
        genai.configure(api_key=api_key)
        count = 0
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if "flash" in m.name:
                    print(f"  ✨ {GREEN}{m.name}{RESET}")
                else:
                    print(f"  - {m.name}")
                count += 1
        
        if count == 0: print("  (No compatible models found)")
            
    except Exception as e:
        print(f"{RED}❌ Error connecting to Google: {e}{RESET}")

def list_openai(api_key):
    print(f"\n{CYAN}>>> 🟢 Searching OPENAI (GPT) models...{RESET}")

    if not LIB_OPENAI:
        print(f"{RED}❌ Library 'openai' not installed.{RESET}")
        return

    if not api_key:
        print(f"{YELLOW}⚠️  OpenAI Key not found.{RESET}")
        return

    try:
        client = OpenAI(api_key=api_key)
        models = client.models.list()
        
        gpt_models = sorted([m.id for m in models.data if "gpt" in m.id])
        
        for model_id in gpt_models:
            if "gpt-4o" in model_id:
                print(f"  ✨ {GREEN}{model_id}{RESET}")
            else:
                print(f"  - {model_id}")
                
    except Exception as e:
        print(f"{RED}❌ Error connecting to OpenAI: {e}{RESET}")

# --- EXECUTION ---
os.system('cls' if os.name == 'nt' else 'clear')
print(f"📡 {CYAN}MODEL & CONNECTION TESTER{RESET}")
print("======================================")

keys = load_keys()

list_google(keys["google"])
list_openai(keys["openai"])

print("\n======================================")
print(">>> End of list.")