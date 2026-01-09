import os
import subprocess
import time
import random
import re
import sys
import shutil
import json
import signal

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"

# --- PROVEDORES ---
import google.generativeai as genai
try:
    from groq import Groq
except ImportError:
    Groq = None

API_KEY = None
SUPABASE_URL = None
SUPABASE_KEY = None
AI_MODEL = "models/gemini-2.5-flash-lite" 
PROVIDER = "google"
USE_DATABASE = False 

versao = "7.1-SHARED"

# Credentials
try:
    with open('credentials.txt', 'r', encoding='utf-8') as arquivo:
        conteudo = arquivo.read()
        
        match_google = re.search(r'>\s*GOOGLE API KEY\s*=?\s*["\'](.*?)["\']', conteudo)
        match_generic = re.search(r'>\s*API KEY\s*=?\s*["\'](.*?)["\']', conteudo)
        
        if match_google: API_KEY = match_google.group(1)
        elif match_generic: API_KEY = match_generic.group(1)

        match_url = re.search(r'>\s*SUPABASE URL\s*=?\s*["\'](.*?)["\']', conteudo)
        if match_url: SUPABASE_URL = match_url.group(1)

        match_key = re.search(r'>\s*SUPABASE KEY\s*=?\s*["\'](.*?)["\']', conteudo)
        if match_key: SUPABASE_KEY = match_key.group(1)

        match_model = re.search(r'>\s*Agent Model\s*=?\s*["\'](.*?)["\']', conteudo)
        if match_model: AI_MODEL = match_model.group(1)

except FileNotFoundError:
    print(f"\n{RED}❌ CRITICAL ERROR: File 'credentials.txt' not found.{RESET}")
    sys.exit()

if not API_KEY:
    print(f"\n{RED}❌ ERROR: API KEY is missing.{RESET}")
    sys.exit()

model_lower = AI_MODEL.lower()
client_groq = None

if "llama" in model_lower or "mixtral" in model_lower or API_KEY.startswith("gsk_"):
    PROVIDER = "groq"
    if not Groq:
        print(f"{RED}❌ ERROR: 'groq' library not installed.{RESET}")
        sys.exit()
    client_groq = Groq(api_key=API_KEY)
else:
    PROVIDER = "google"
    genai.configure(api_key=API_KEY)

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

def chamar_ai(prompt, sistema, json_mode=False, temp=None):
    # Define temperatura padrão se não for informada
    if temp is None:
        temp = 0.5 if json_mode else 0.7

    if PROVIDER == "groq":
        try:
            resp = client_groq.chat.completions.create(
                messages=[
                    {"role": "system", "content": sistema},
                    {"role": "user", "content": prompt}
                ],
                model=AI_MODEL,
                temperature=temp, # Usa a temperatura customizada
                response_format={"type": "json_object"} if json_mode else None
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"Error Groq: {e}"

    else: # Google Gemini
        try:
            config = {"temperature": temp, "response_mime_type": "application/json"} if json_mode else {"temperature": temp}
            
            model = genai.GenerativeModel(
                model_name=AI_MODEL,
                generation_config=config,
                system_instruction=sistema
            )
            resp = model.generate_content(prompt)
            return resp.text
        except Exception as e:
            # Fallback simples
            return f"Error Google: {e}"

# --- CONFIG ---
CAMINHO_PROJETO = os.path.join(os.getcwd(), "base-app")

# --- DATABASE SETUP ---
limpar_tela()
print(f"{CYAN}╔════════════════════════════════════════════════════╗{RESET}")
print(f"{CYAN}║                     CLOUD AGENT                    ║{RESET}")
print(f"{CYAN}╚════════════════════════════════════════════════════╝{RESET}\n")
print(f"{MAGENTA}Brain: {YELLOW}{AI_MODEL} ({PROVIDER.upper()}){RESET}")

while True:
    print(f"\n{BLUE}🔌 Enable Database (Supabase)? (y/n){RESET}")
    choice = input_limpo(">>> ").lower()
    if choice == 'y':
        if not SUPABASE_URL or not SUPABASE_KEY:
            print(f"\n{RED}❌ ERROR: Supabase keys missing in credentials.txt{RESET}")
            sys.exit()
        USE_DATABASE = True
        break
    elif choice == 'n':
        USE_DATABASE = False
        break

def resetar_projeto():
    print(f"{MAGENTA}>>> [🧹] FACTORY RESET: {RESET}Cleaning old files...\n")
    src_path = os.path.join(CAMINHO_PROJETO, "src")
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
    print(f"{GREEN}✅ Project Cleaned.{RESET}")

def get_db_instructions():
    if USE_DATABASE:
        return f"""
    💾 SUPABASE (REAL DATABASE):
       - URL: "{SUPABASE_URL}"
       - KEY: "{SUPABASE_KEY}"
       - Client: `import {{ createClient }} from '@supabase/supabase-js'`
       - Init: `const supabase = createClient(URL, KEY)`
        """
    else:
        return """
    💾 STORAGE MODE: [NO DATABASE]
    🛑 STRICT PROHIBITION: DO NOT import supabase, DO NOT use fetch().
    ✅ REQUIREMENT: Use HARDCODED Arrays of Objects (Mock Data).
        """

def planejar_arquitetura(prompt_usuario):
    print(f"\n{CYAN}>>> [1/??] 🧠 CLOUD ARCHITECT: Blueprinting...{RESET}\n")
    
    extra_rule = '5. Use "src/lib/supabase.js" for DB connection.' if USE_DATABASE else '5. 🛑 FORBIDDEN: Do NOT include "src/lib/supabase.js".'

    sistema = f"""
    ROLE: Senior React Architect.
    TASK: List files to build this app.
    
    RULES:
    1. Output strictly a JSON Array of strings.
    2. Max 6 files.
    3. NEVER include "src/main.jsx", "index.html".
    4. INCLUDE "src/App.jsx".
    5. Paths MUST start with 'src/' (e.g., 'src/components/Header.jsx').
    {extra_rule}
    """
    
    prompt = f"App Goal: {prompt_usuario}"
    
    try:
        texto_resp = chamar_ai(prompt, sistema, json_mode=True)
        # Limpeza extra caso venha markdown
        match_json = re.search(r'\[.*\]', texto_resp, re.DOTALL)
        lista_arquivos = json.loads(match_json.group(0)) if match_json else json.loads(texto_resp)

        arquivos_proibidos = ["src/main.jsx", "src/main.js", "index.html", "src/index.css", "vite.config.js"]
        if not USE_DATABASE: arquivos_proibidos.append("src/lib/supabase.js")

        lista_filtrada = [arq for arq in lista_arquivos if arq not in arquivos_proibidos]
        if "src/App.jsx" not in lista_filtrada: lista_filtrada.append("src/App.jsx")
        return lista_filtrada

    except Exception as e:
        print(f"{YELLOW}⚠️ Architect Error: {e}. Fallback to basic.{RESET}")
        return ["src/App.jsx"]

def planejar_modificacao(pedido_usuario, lista_arquivos_existentes):
    print(f"\n{CYAN}>>> [🔍] CLOUD AGENT: Analyzing impact...{RESET}")
    
    sistema = f"""
    ROLE: Code Maintenance Expert.
    TASK: Identify WHICH files need to be edited.
    
    EXISTING FILES: {json.dumps(lista_arquivos_existentes)}
    
    RULES:
    1. Return ONLY a JSON Array of strings (filenames).
    2. Select ONLY files needing changes.
    3. If NEW file needed, add it.
    """
    
    try:
        texto_resp = chamar_ai(f"Request: {pedido_usuario}", sistema, json_mode=True)
        match_json = re.search(r'\[.*\]', texto_resp, re.DOTALL)
        return json.loads(match_json.group(0)) if match_json else json.loads(texto_resp)
    except:
        return ["src/App.jsx"]

def gerar_arquivo_especifico(arquivo_alvo, contexto_global, prompt_usuario, eh_modificacao=False, current_step=None, total_steps=None):
    acao = "MODIFYING" if eh_modificacao else "BUILDER"
    
    if current_step and total_steps:
        step_display = f"[{current_step}/{total_steps}]"
    else:
        step_display = "[2/3]"

    print(f"{YELLOW}>>> {step_display} 👷 {acao}: {RESET}{arquivo_alvo}...")
    
    # CONTEXTO GERAL (Resumo dos outros arquivos para referência)
    resumo_projeto = ""
    for path, code in contexto_global.items():
        if path != arquivo_alvo:
            resumo_projeto += f"\n--- FILE: {path} ---\n{code[:800]}...\n"

    # LÓGICA DE MODIFICAÇÃO vs CRIAÇÃO
    if eh_modificacao:
        # LÊ O ARQUIVO DIRETO DO DISCO
        caminho_real = os.path.join(CAMINHO_PROJETO, arquivo_alvo)
        try:
            with open(caminho_real, "r", encoding="utf-8") as f:
                codigo_atual = f.read()
        except Exception:
            codigo_atual = contexto_global.get(arquivo_alvo, "")

        sistema = f"""
        ROLE: Automated Code Patcher / React Maintenance Agent.
        TASK: Apply a specific transformation to the provided text file based on the instruction.

        INSTRUCTION: {prompt_usuario}

        INPUT FILE CONTENT:
        {codigo_atual}

        EXECUTION PROTOCOL:
        1. Analyze the INPUT FILE CONTENT.
        2. Locate ONLY the lines relevant to the INSTRUCTION.
        3. Modify those specific lines to satisfy the instruction.
        4. PRESERVE STRICTLY every other line, character, import, and indentation of the original file.
        5. DO NOT optimize, DO NOT refactor, DO NOT reorganize.
        6. If the instruction is visual (e.g., "change color"), change ONLY the Tailwind class.
        7. Output the COMPLETED file content.

        CRITICAL: The output must be a valid, compilable React file identical to the input, except for the requested change.
        """
        
        foco_prompt = f"Apply change: {prompt_usuario}. Return full file code."

    else:
        # Lógica de criação (Builder) - REGRAS RESTAURADAS
        sistema = f"""
        ROLE: React Senior Code Generator.
        TASK: Write code for file: '{arquivo_alvo}'.
        
        CONTEXT:
        - {get_db_instructions()}
        
        EXISTING FILES:
        {resumo_projeto}
        
        RULES:
        1. Output ONLY raw code (no markdown blocks like ```jsx).
        2. ACTIVELY USE 'lucide-react' icons.
        3. CRITICAL: You MUST write the import line for icons. Example: `import {{ Home, User }} from 'lucide-react';`.
        4. DO NOT use prefixes like 'LucideHome'. Use standard names: <Home />, <User />.
        5. Use 'tailwindcss' classes.
        6. For 'src/App.jsx': MUST use `export default function App() {{ ... }}`.
        7. Only modify things inside src/ folder.
        8. If you use a component in JSX, it MUST be imported at the top.
        9. NO UNUSED IMPORTS: It is forbidden to import components (like './pages/HomePage') if they are not rendered in the JSX. Check your imports against your return statement.
        10. ICON ACCURACY: Use standard Lucide names (e.g., `Linkedin`, `Github`, `Twitter`). DO NOT invent names like `LinkedinIcon`, `GithubIcon` or `TwitterIcon`.
        11. SPA STRUCTURE: If creating a Single Page App (scrollable), do not import Route/Page components. Use Section components instead.
        12. NO TRUNCATION: Prioritize finishing the file syntax (closing tags) over adding more content. The file MUST end with valid syntax.
        """
        foco_prompt = f"User Goal: {prompt_usuario}\nFile to write: {arquivo_alvo}"

    for tentativa in range(2):
        try:
            temperatura_uso = 0.1 if eh_modificacao else 0.7
            codigo = chamar_ai(foco_prompt, sistema, json_mode=False, temp=temperatura_uso)
            if not codigo: raise Exception("Empty Response")
            
            codigo = codigo.replace("```jsx", "").replace("```javascript", "").replace("```js", "").replace("```", "")
            return codigo.strip()
            
        except Exception as e:
            print(f"{RED}⚠️ Error on attempt {tentativa+1}: {e}{RESET}")
            time.sleep(2) 
            
    return f"// CRITICAL ERROR: {str(e)}"

def carregar_whitelist_lucide():
    caminho_index = os.path.join(CAMINHO_PROJETO, "node_modules", "lucide-react", "dist", "esm", "icons", "index.js")
    
    if not os.path.exists(caminho_index):
        return None

    try:
        with open(caminho_index, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
            icones = re.findall(r"default as ([a-zA-Z0-9]+)", conteudo)
            return set(icones)
    except:
        return None

def sanitizar_codigo_lucide(codigo):
    validos = carregar_whitelist_lucide()
    if not validos: return codigo 

    # Encontra a linha de importação do lucide-react
    match = re.search(r"import\s+\{(.*?)\}\s+from\s+['\"]lucide-react['\"]", codigo, re.DOTALL)
    if not match: return codigo

    bloco_imports = match.group(1)
    # Separa os itens importados removendo espaços e quebras de linha
    itens = [i.strip() for i in bloco_imports.split(',') if i.strip()]
    
    novos_itens = []
    modificado = False
    
    # Define o ícone de emergência (CircleHelp ou HelpCircle dependendo da versão)
    fallback = "CircleHelp" if "CircleHelp" in validos else "HelpCircle"
    if fallback not in validos: fallback = "AlertCircle" # Último recurso

    for item in itens:
        # Trata casos como "Icon as Alias" ou apenas "Icon"
        nome_real = item.split(' as ')[0].strip()
        alias_usado = item.split(' as ')[1].strip() if ' as ' in item else nome_real

        if nome_real in validos:
            novos_itens.append(item)
        else:
            print(f"{YELLOW}⚠️  Fixing hallucinated icon: '{nome_real}' -> '{fallback}'{RESET}")
            novos_itens.append(f"{fallback} as {alias_usado}")
            modificado = True

    if modificado:
        novo_import = f"import {{ {', '.join(novos_itens)} }} from 'lucide-react'"
        codigo = codigo.replace(match.group(0), novo_import)

    return codigo

def salvar_arquivo_caminho_custom(caminho_relativo, codigo):
    caminho_limpo = caminho_relativo.replace("base-app/", "").replace("./", "").replace("\\", "/")
    while "src/src/" in caminho_limpo: caminho_limpo = caminho_limpo.replace("src/src/", "src/")
    if not caminho_limpo.startswith("src/"): caminho_limpo = f"src/{caminho_limpo}"

    if caminho_limpo.endswith(".jsx") or caminho_limpo.endswith(".tsx"):
        codigo = sanitizar_codigo_lucide(codigo)

    caminho_completo = os.path.join(CAMINHO_PROJETO, caminho_limpo)
    pasta = os.path.dirname(caminho_completo)
    if not os.path.exists(pasta): os.makedirs(pasta)
    
    with open(caminho_completo, "w", encoding="utf-8") as f:
        f.write(codigo)

def verificar_dependencias_global(contexto_global, current_step=None, total_steps=None):
    if current_step and total_steps:
        step_display = f"[{current_step}/{total_steps}]"
    else:
        step_display = "[3/3]"

    print(f"\n{BLUE}>>> {step_display} 📦 DEPENDENCIES...{RESET}")
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

# --- DEPLOY & PREVIEW ---
def verificar_dominio_http(slug):
    try:
        import urllib.request
        req = urllib.request.Request(f"http://{slug}.surge.sh", method='HEAD')
        urllib.request.urlopen(req)
        return True 
    except: return False

def fazer_deploy(nome_inicial):
    print(f"\n{MAGENTA}>>> [BUILDING]...{RESET}")
    subprocess.run("npm run build", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL)
    
    nome_atual = nome_inicial.replace(" ", "-").lower()
    while verificar_dominio_http(nome_atual):
        nome_atual += f"-{random.randint(1,99)}"
    
    subprocess.run(f"npx surge ./dist --domain {nome_atual}.surge.sh", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL)
    return f"{nome_atual}.surge.sh"

# --- MAIN ENTRY ---
def iniciar_sistema(config=None):
    # Se chamado via main.py, sobrescreve configs
    global API_KEY, AI_MODEL, PROVIDER
    if config:
        AI_MODEL = config.get("model", AI_MODEL)
        if config["provider"] == "google":
            API_KEY = config.get("google_key") or config.get("generic_key")
        else:
            API_KEY = config.get("openai_key") or config.get("generic_key")
    
    main()

def main():
    while True:
        prompt_inicial = input_limpo(f"\n{YELLOW}📝 App Idea {RED}(or 'exit'){RESET}: ")
        if prompt_inicial.lower() == 'exit': break
        
        resetar_projeto()

        arquivos_atuais = planejar_arquitetura(prompt_inicial)
        
        total_files = len(arquivos_atuais)
        total_workflow_steps = total_files + 2 
        
        print(f"📋 Plan: {CYAN}{arquivos_atuais}{RESET} ({total_files} files)")
        
        contexto_projeto = {}
        for i, arquivo in enumerate(arquivos_atuais):
            current_step_num = i + 2
            codigo = gerar_arquivo_especifico(arquivo, contexto_projeto, prompt_inicial, 
                                              current_step=current_step_num, 
                                              total_steps=total_workflow_steps)
            contexto_projeto[arquivo] = codigo
            salvar_arquivo_caminho_custom(arquivo, codigo)
            
        verificar_dependencias_global(contexto_projeto, 
                                      current_step=total_workflow_steps, 
                                      total_steps=total_workflow_steps)
        
        processo_preview = None
        while True:
            if processo_preview: encerrar_processo(processo_preview)
            
            print(f"\n{GREEN}✨ App Ready. Preview: http://localhost:5173{RESET}")
            processo_preview = subprocess.Popen("npm run dev -- --open", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            
            print("\n" + f"{CYAN}={RESET}"*30)
            print(f" {GREEN}[1] ✏️  MODIFY{RESET}")
            print(f" {MAGENTA}[2] 🚀 PUBLISH{RESET}")
            print(f" {BLUE}[3] 🔙 NEW PROJECT{RESET}")
            print(f" {RED}[4] ❌ EXIT{RESET}")
            print(f"{CYAN}={RESET}"*30)
            
            opcao = input_limpo(">>> ")
            
            if opcao == "1":
                pedido = input_limpo(f"\n{YELLOW}✏️  Change Request: {RESET}")
                arquivos_edit = planejar_modificacao(pedido, arquivos_atuais)
                print(f"🎯 Files to Edit: {arquivos_edit}")
                
                total_mod_steps = len(arquivos_edit)
                
                for arq in arquivos_edit:
                    if arq not in arquivos_atuais: arquivos_atuais.append(arq)
                
                for i, arq in enumerate(arquivos_edit):
                    novo_codigo = gerar_arquivo_especifico(arq, contexto_projeto, pedido, 
                                                           eh_modificacao=True,
                                                           current_step=i+1,
                                                           total_steps=total_mod_steps)
                    contexto_projeto[arq] = novo_codigo
                    salvar_arquivo_caminho_custom(arq, novo_codigo)
                
                print(f"{GREEN}✅ Done! Reloading...{RESET}")

            elif opcao == "2":
                encerrar_processo(processo_preview)
                link = fazer_deploy(prompt_inicial[:10])
                print(f"\n{GREEN}🚀 LIVE: https://{link}{RESET}\n")
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