import os
import subprocess
import google.generativeai as genai
import time
import random
import re
import sys
import shutil
import json
import signal

# -------------------------------- #
# 🚀 FABRICA v6.9 (Memory Fix)
# -------------------------------- #

AI_API_KEY = None
SUPABASE_URL = None
SUPABASE_KEY = None
AI_MODEL = "models/gemini-2.5-flash-lite" 
USE_DATABASE = False 

versao = "6.9-MEMORY"

# --- 1. LOAD CREDENTIALS ---
try:
    with open('credentials.txt', 'r', encoding='utf-8') as arquivo:
        conteudo = arquivo.read()
        
        match_google = re.search(r'>\s*GOOGLE API KEY\s*=?\s*["\'](.*?)["\']', conteudo)
        if match_google: AI_API_KEY = match_google.group(1)

        match_url = re.search(r'>\s*SUPABASE URL\s*=?\s*["\'](.*?)["\']', conteudo)
        if match_url: SUPABASE_URL = match_url.group(1)

        match_key = re.search(r'>\s*SUPABASE KEY\s*=?\s*["\'](.*?)["\']', conteudo)
        if match_key: SUPABASE_KEY = match_key.group(1)

        match_model = re.search(r'>\s*Agent Model\s*=?\s*["\'](.*?)["\']', conteudo)
        if match_model: AI_MODEL = match_model.group(1)

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
    try:
        if os.name == 'nt':
            subprocess.run(f"taskkill /F /T /PID {processo.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(os.getpgid(processo.pid), signal.SIGTERM)
    except: pass

# --- CONFIG ---
CAMINHO_PROJETO = os.path.join(os.getcwd(), "base-app")

model = genai.GenerativeModel(
    model_name=AI_MODEL,
    generation_config={"temperature": 0.7, "max_output_tokens": 8192}
)

try:
    model_json = genai.GenerativeModel(
        model_name=AI_MODEL,
        generation_config={"temperature": 0.5, "response_mime_type": "application/json"}
    )
except:
    model_json = model

# --- DATABASE SETUP ---
limpar_tela()
print(f"-=[ 🏭 FACTORY {versao} (Import Guard) ]=-")
print(f"🧠 Brain: {AI_MODEL}")

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

# --- FUNÇÃO DE LIMPEZA ---
def resetar_projeto():
    print(">>> [🧹] FACTORY RESET: Cleaning old files...")
    src_path = os.path.join(CAMINHO_PROJETO, "src")
    if not os.path.exists(src_path): return
    
    pastas_para_remover = ["components", "lib", "utils", "hooks", "pages", "context"]
    
    for item in os.listdir(src_path):
        item_path = os.path.join(src_path, item)
        if os.path.isdir(item_path) and item in pastas_para_remover:
            try: shutil.rmtree(item_path)
            except: pass
        elif os.path.isfile(item_path):
            if item not in ["main.jsx", "index.css", "vite-env.d.ts", "App.css"]:
                if item == "App.jsx":
                    with open(item_path, "w", encoding="utf-8") as f:
                        f.write("export default function App() { return <div>Loading...</div> }")
                else:
                    os.remove(item_path)
    print("✅ Project Cleaned.")

# --- PROMPTS ---
def get_db_instructions():
    if USE_DATABASE:
        return f"""
    💾 SUPABASE (REAL DATABASE):
       - URL: "{SUPABASE_URL}"
       - KEY: "{SUPABASE_KEY}"
       - Client: `import {{ createClient }} from '@supabase/supabase-js'`
        """
    else:
        return """
    💾 STORAGE MODE: [NO DATABASE]
    🛑 STRICT PROHIBITION: DO NOT import supabase.
    ✅ REQUIREMENT: Use HARDCODED Arrays of Objects (Mock Data).
        """

def planejar_arquitetura(prompt_usuario):
    print("\n>>> [1/3] 🧠 ARCHITECT: Blueprinting...")
    
    if USE_DATABASE:
        extra_rule = '5. Use "src/lib/supabase.js" for DB connection.'
    else:
        extra_rule = '5. 🛑 FORBIDDEN: Do NOT include "src/lib/supabase.js".'

    sistema = f"""
    ROLE: Senior React Architect.
    TASK: List files to build this app: "{prompt_usuario}".
    
    RULES:
    1. Output strictly a JSON Array of strings.
    2. Max 6 files.
    3. NEVER include "src/main.jsx", "index.html".
    4. INCLUDE "src/App.jsx".
    {extra_rule}
    """
    
    try:
        try:
            resp = model_json.generate_content(sistema)
            lista_arquivos = json.loads(resp.text)
        except:
            resp = model.generate_content(sistema)
            match_json = re.search(r'\[.*\]', resp.text, re.DOTALL)
            lista_arquivos = json.loads(match_json.group(0)) if match_json else json.loads(resp.text)

        arquivos_proibidos = ["src/main.jsx", "src/main.js", "index.html", "src/index.css", "vite.config.js"]
        if not USE_DATABASE: arquivos_proibidos.append("src/lib/supabase.js")

        lista_filtrada = [arq for arq in lista_arquivos if arq not in arquivos_proibidos]
        if "src/App.jsx" not in lista_filtrada: lista_filtrada.append("src/App.jsx")
        return lista_filtrada

    except Exception as e:
        print(f"⚠️ Architect Error: {e}. Fallback to basic.")
        return ["src/App.jsx"]

def planejar_modificacao(pedido_usuario, lista_arquivos_existentes):
    print("\n>>> [🔍] MAINTENANCE AGENT: Analyzing impact...")
    
    sistema = f"""
    ROLE: Code Maintenance Expert.
    TASK: Identify WHICH files need to be edited to satisfy the request: "{pedido_usuario}".
    
    EXISTING FILES: {json.dumps(lista_arquivos_existentes)}
    
    RULES:
    1. Return ONLY a JSON Array of strings (filenames).
    2. Select ONLY the files that strictly need changes.
    """
    
    try:
        try:
            resp = model_json.generate_content(sistema)
            return json.loads(resp.text)
        except:
            resp = model.generate_content(sistema)
            match_json = re.search(r'\[.*\]', resp.text, re.DOTALL)
            return json.loads(match_json.group(0)) if match_json else []
    except:
        return ["src/App.jsx"]

def gerar_arquivo_especifico(arquivo_alvo, contexto_global, prompt_usuario, eh_modificacao=False):
    acao = "MODIFYING" if eh_modificacao else "BUILDER"
    print(f">>> [2/3] 👷 {acao}: {arquivo_alvo}...")
    
    # --- MEMÓRIA CORRIGIDA: Se for modificação, pega o código REAL ---
    if eh_modificacao:
        codigo_antigo = contexto_global.get(arquivo_alvo, "// New File")
        prompt_foco = f"""
        TASK: EDIT THE FILE '{arquivo_alvo}'.
        USER REQUEST: "{prompt_usuario}"
        
        🛑 OLD CODE (BASE):
        {codigo_antigo}
        
        INSTRUCTIONS:
        1. Apply the User Request to the OLD CODE.
        2. KEEP THE REST OF THE CODE EXACTLY THE SAME (Do not rewrite layout unless asked).
        """
    else:
        # Modo Criação (Usa resumo para economizar token, mas contexto suficiente)
        resumo_projeto = ""
        for path, code in contexto_global.items():
            resumo_projeto += f"\n--- FILE: {path} ---\n{code[:500]}...\n"
        
        prompt_foco = f"""
        TASK: Write code for file: '{arquivo_alvo}'.
        USER GOAL: "{prompt_usuario}"
        EXISTING FILES: {resumo_projeto}
        """

    sistema = f"""
    ROLE: React Expert.
    {prompt_foco}
    
    CONTEXT:
    - {get_db_instructions()}
    
    🛑 GOLDEN RULES (STRICT):
    1. Output ONLY raw code.
    2. ICONS: If you use <Github /> you MUST write `import {{ Github }} from 'lucide-react';` at the top.
    3. ICONS: If you use <Menu /> you MUST write `import {{ Menu }} from 'lucide-react';` at the top.
    4. CHECK IMPORTS: Never use a component/icon without importing it.
    5. For 'src/App.jsx': MUST use `export default function App() {{ ... }}`.
    """
    
    for tentativa in range(2):
        try:
            resp = model.generate_content(sistema)
            if not resp.text: raise Exception("Empty Response")
            codigo = resp.text.replace("```jsx", "").replace("```javascript", "").replace("```js", "").replace("```", "")
            return codigo.strip()
        except Exception as e:
            print(f"⚠️ Error on attempt {tentativa+1} for {arquivo_alvo}: {e}")
            time.sleep(2)
            
    return f"// CRITICAL ERROR: {str(e)}"

def salvar_arquivo_caminho_custom(caminho_relativo, codigo):
    caminho_limpo = caminho_relativo.replace("base-app/", "").replace("./", "").replace("\\", "/")
    while "src/src/" in caminho_limpo: caminho_limpo = caminho_limpo.replace("src/src/", "src/")
    if not caminho_limpo.startswith("src/"): caminho_limpo = f"src/{caminho_limpo}"

    caminho_completo = os.path.join(CAMINHO_PROJETO, caminho_limpo)
    pasta = os.path.dirname(caminho_completo)
    if not os.path.exists(pasta): os.makedirs(pasta)
    
    with open(caminho_completo, "w", encoding="utf-8") as f:
        f.write(codigo)

def verificar_dependencias_global(contexto_global):
    print("\n>>> [3/3] 📦 DEPENDENCIES...")
    libs_obrigatorias = ['react', 'react-dom', 'vite', '@vitejs/plugin-react', 'tailwindcss', 'postcss', 'autoprefixer', 'lucide-react']
    blacklist = ['react-context', 'fs', 'path', 'os']

    texto_total = "".join(contexto_global.values())
    imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", texto_total)
    
    para_instalar = []
    for lib in imports:
        if lib.startswith(".") or lib.startswith("/"): continue
        partes = lib.split("/")
        root_lib = f"{partes[0]}/{partes[1]}" if lib.startswith("@") and len(partes) > 1 else partes[0]
            
        if root_lib not in libs_obrigatorias and root_lib not in blacklist:
            para_instalar.append(root_lib)
            
    if para_instalar:
        para_instalar = list(set(para_instalar))
        print(f"Installing: {para_instalar}")
        subprocess.run(f"npm install {' '.join(para_instalar)}", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL)

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
        prompt_inicial = input_limpo("\n📝 App Idea (or 'exit'): ")
        if prompt_inicial.lower() == 'exit': break
        
        resetar_projeto() # FAXINA INICIAL

        arquivos_atuais = planejar_arquitetura(prompt_inicial)
        print(f"📋 Plan: {arquivos_atuais}")
        
        contexto_projeto = {}
        for arquivo in arquivos_atuais:
            codigo = gerar_arquivo_especifico(arquivo, contexto_projeto, prompt_inicial)
            contexto_projeto[arquivo] = codigo
            salvar_arquivo_caminho_custom(arquivo, codigo)
            
        verificar_dependencias_global(contexto_projeto)
        
        processo_preview = None
        
        while True:
            if processo_preview: encerrar_processo(processo_preview)
            
            print("\n✨ App Ready. Opening Preview...")
            print("👉 http://localhost:5173")
            processo_preview = subprocess.Popen("npm run dev -- --open", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            
            print("\n" + "="*30)
            print(" [1] ✏️  MODIFY")
            print(" [2] 🚀 PUBLISH")
            print(" [3] 🔙 NEW PROJECT")
            print(" [4] ❌ EXIT")
            print("="*30)
            
            opcao = input_limpo(">>> ")
            
            if opcao == "1":
                pedido_mudanca = input_limpo("\n✏️  Change Request: ")
                arquivos_para_editar = planejar_modificacao(pedido_mudanca, arquivos_atuais)
                print(f"🎯 Files to Edit: {arquivos_para_editar}")
                
                for arq in arquivos_para_editar:
                    if arq not in arquivos_atuais: arquivos_atuais.append(arq)
                
                for arquivo in arquivos_para_editar:
                    # AQUI ESTÁ A MÁGICA: Passamos eh_modificacao=True
                    novo_codigo = gerar_arquivo_especifico(arquivo, contexto_projeto, pedido_mudanca, eh_modificacao=True)
                    contexto_projeto[arquivo] = novo_codigo
                    salvar_arquivo_caminho_custom(arquivo, novo_codigo)
                
                print("✅ Done! Reloading...")
                
            elif opcao == "2":
                encerrar_processo(processo_preview)
                link = fazer_deploy(prompt_inicial[:15])
                print(f"\n🚀 LIVE: https://{link}\n")
                input("Press ENTER...")
                break
            elif opcao == "3":
                encerrar_processo(processo_preview)
                break
            elif opcao == "4":
                encerrar_processo(processo_preview)
                sys.exit()

if __name__ == "__main__":
    main()