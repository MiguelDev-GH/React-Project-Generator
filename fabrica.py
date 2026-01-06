import os
import subprocess
import google.generativeai as genai
import time
import random
import re
import sys
import urllib.request
import json
import signal
from urllib.error import HTTPError

# -------------------------------- #
# FILL credentials.txt BEFORE RUN
# -------------------------------- #

AI_API_KEY = None
SUPABASE_URL = None
SUPABASE_KEY = None
AI_MODEL = "models/gemini-2.0-flash-exp" # Recomendado: Modelo mais rápido/inteligente se disponível
USE_DATABASE = False 

versao = "6.0-PRO"

# --- 1. LOAD CREDENTIALS ---
try:
    with open('credentials.txt', 'r', encoding='utf-8') as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            try:
                if "> GOOGLE API KEY" in linha:
                    AI_API_KEY = linha.split('"')[1]
                elif "> SUPABASE URL" in linha:
                    SUPABASE_URL = linha.split('"')[1]
                elif "> SUPABASE KEY" in linha:
                    SUPABASE_KEY = linha.split('"')[1]
                elif "> Agent Model" in linha:
                    temp_model = linha.split('"')[1]
                    if temp_model: AI_MODEL = temp_model
            except: pass
except FileNotFoundError:
    print("\n❌ CRITICAL ERROR: File 'credentials.txt' not found.")
    sys.exit()

if not AI_API_KEY:
    print("\n❌ ERROR: GOOGLE API KEY is missing.")
    sys.exit()

genai.configure(api_key=AI_API_KEY)

# --- UTILS ---
def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def input_limpo(texto):
    sys.stdout.flush()
    return input(texto).strip()

def encerrar_processo(processo):
    """Encerra processos de forma Cross-Platform"""
    try:
        if os.name == 'nt':
            subprocess.run(f"taskkill /F /T /PID {processo.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(os.getpgid(processo.pid), signal.SIGTERM)
    except: pass

# --- CONFIG ---
CAMINHO_PROJETO = os.path.join(os.getcwd(), "base-app")
ARQUIVO_HTML = os.path.join(CAMINHO_PROJETO, "index.html")

model = genai.GenerativeModel(
    model_name=AI_MODEL,
    generation_config={"temperature": 0.7, "max_output_tokens": 8192}
)

# --- DATABASE SETUP ---
limpar_tela()
print(f"-=[ 🏭 FACTORY {versao} (Multi-Agent) ]=-")

while True:
    print("🔌 Enable Database (Supabase)? (y/n)")
    choice = input_limpo(">>> ").lower()
    if choice == 'y':
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("\n❌ ERROR: Supabase keys missing in credentials.txt")
            sys.exit()
        USE_DATABASE = True
        break
    elif choice == 'n':
        USE_DATABASE = False
        break

# --- PROMPTS ---
def get_db_instructions():
    if USE_DATABASE:
        return f"""
    💾 SUPABASE (STRICT SECURITY):
       - URL: "{SUPABASE_URL}"
       - KEY: "{SUPABASE_KEY}"
       - Client: `import {{ createClient }} from '@supabase/supabase-js'`
       - Init: `const supabase = createClient(URL, KEY)`
       - RLS RULES: 
         * INSERT: No 'user_id' in payload. DB auto-fills it via `default auth.uid()`.
         * SELECT: No `.eq('user_id')`. DB filters automatically via RLS policy.
        """
    return "💾 STORAGE: Local useState/Context ONLY. No backend."

def planejar_arquitetura(prompt_usuario):
    print("\n>>> [1/3] 🧠 ARCHITECT: Blueprinting...")
    
    sistema = f"""
    ROLE: Senior React Architect.
    TASK: Return a JSON List of files to build this app: "{prompt_usuario}".
    
    RULES:
    1. Output strictly a JSON Array of strings.
    2. ALWAYS include: "src/App.jsx", "src/main.jsx".
    3. Use "src/components/..." for UI parts.
    4. Use "src/lib/supabase.js" if DB is needed.
    5. Max 6 files to ensure stability.
    
    EXAMPLE OUTPUT:
    ["src/main.jsx", "src/App.jsx", "src/components/Navbar.jsx", "src/lib/supabase.js"]
    """
    
    try:
        resp = model.generate_content(sistema)
        json_str = re.search(r'\[.*\]', resp.text, re.DOTALL).group(0)
        return json.loads(json_str)
    except Exception as e:
        print(f"⚠️ Architect Error: {e}. Fallback to basic.")
        return ["src/App.jsx"]

def gerar_arquivo_especifico(arquivo_alvo, contexto_global, prompt_usuario):
    print(f">>> [2/3] 👷 BUILDER: {arquivo_alvo}...")
    
    # Contexto acumulado
    resumo_projeto = ""
    for path, code in contexto_global.items():
        # Envia apenas os primeiros 500 chars de cada arquivo para economizar tokens, 
        # ou o arquivo todo se for pequeno (importante para imports)
        resumo_projeto += f"\n--- FILE: {path} ---\n{code[:1000]}...\n"

    sistema = f"""
    ROLE: React Expert.
    TASK: Write code for file: '{arquivo_alvo}'.
    
    CONTEXT:
    - User Goal: "{prompt_usuario}"
    - {get_db_instructions()}
    
    EXISTING FILES (For Import Reference):
    {resumo_projeto}
    
    RULES:
    1. Output ONLY raw code. No markdown.
    2. Imports must match 'EXISTING FILES'.
    3. Use 'lucide-react' for icons.
    4. Use 'tailwindcss' for styling.
    """
    
    try:
        resp = model.generate_content(sistema)
        # Limpeza agressiva
        codigo = resp.text.replace("```jsx", "").replace("```javascript", "").replace("```js", "").replace("```", "")
        return codigo.strip()
    except:
        return "// Error generating code"

def salvar_arquivo_caminho_custom(caminho_relativo, codigo):
    caminho_completo = os.path.join(CAMINHO_PROJETO, caminho_relativo)
    pasta = os.path.dirname(caminho_completo)
    
    if not os.path.exists(pasta):
        os.makedirs(pasta)
        
    with open(caminho_completo, "w", encoding="utf-8") as f:
        f.write(codigo)

def verificar_dependencias_global(contexto_global):
    print("\n>>> [3/3] 📦 DEPENDENCIES...")
    libs_obrigatorias = ['react', 'react-dom', 'vite', '@vitejs/plugin-react', 'tailwindcss', 'postcss', 'autoprefixer', 'lucide-react']
    
    # Análise simples de imports em todo o projeto
    texto_total = "".join(contexto_global.values())
    imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", texto_total)
    
    para_instalar = []
    for lib in imports:
        if lib.startswith(".") or lib.startswith("/"): continue
        root_lib = lib.split("/")[0]
        if root_lib not in libs_obrigatorias:
            para_instalar.append(root_lib)
            
    if para_instalar:
        # Remove duplicatas
        para_instalar = list(set(para_instalar))
        print(f"Installing: {para_instalar}")
        subprocess.run(f"npm install {' '.join(para_instalar)}", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL)

# --- DEPLOY & PREVIEW ---
def verificar_dominio_http(slug):
    dominio = f"http://{slug}.surge.sh"
    try:
        req = urllib.request.Request(dominio, method='HEAD')
        urllib.request.urlopen(req)
        return True 
    except: return False

def fazer_deploy(nome_inicial):
    print("\n>>> [BUILDING]...")
    subprocess.run("npm run build", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL)
    
    nome_atual = nome_inicial.replace(" ", "-").lower()
    while verificar_dominio_http(nome_atual):
        nome_atual += f"-{random.randint(1,99)}"
    
    subprocess.run(f"npx surge ./dist --domain {nome_atual}.surge.sh", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL)
    return f"{nome_atual}.surge.sh"

def main():
    while True:
        prompt = input_limpo("\n📝 App Idea (or 'exit'): ")
        if prompt.lower() == 'exit': break
        
        # 1. Planejamento
        arquivos_para_criar = planejar_arquitetura(prompt)
        print(f"📋 Plan: {arquivos_para_criar}")
        
        contexto_projeto = {}
        
        # 2. Execução (Loop de Agentes)
        for arquivo in arquivos_para_criar:
            codigo = gerar_arquivo_especifico(arquivo, contexto_projeto, prompt)
            contexto_projeto[arquivo] = codigo
            salvar_arquivo_caminho_custom(arquivo, codigo)
            
        # 3. Finalização
        verificar_dependencias_global(contexto_projeto)
        
        # 4. Preview
        print("\n✨ App Generated. Opening Preview...")
        processo = subprocess.Popen("npm run dev -- --open", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        
        input("Press ENTER to Deploy or CTRL+C to Exit...")
        
        encerrar_processo(processo)
        link = fazer_deploy(prompt[:15])
        print(f"\n🚀 LIVE: https://{link}\n")

if __name__ == "__main__":
    main()