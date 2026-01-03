import os
os.system('cls' if os.name == 'nt' else 'clear')

import subprocess
import google.generativeai as genai
import time
import random
import re
import sys
import urllib.request
from urllib.error import HTTPError

# -------------------------------- #

# FILL credentials.txt BEFORE RUN

# -------------------------------- #


# NO NEED to write here!
AI_API_KEY = ""
SUPABASE_URL = ""
SUPABASE_KEY = ""

versao = 5.3

AI_MODEL = "models/gemini-3-flash-preview"

print("")

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
                    if temp_model: 
                        AI_MODEL = temp_model
            except:
                pass

except FileNotFoundError:
    print("\n❌ CRITICAL ERROR: File 'credentials.txt' not found.")
    print("Please create it before running the factory.")
    sys.exit()

erros = []

if not AI_API_KEY:
    erros.append("- GOOGLE API KEY is missing or invalid.")

if not SUPABASE_URL:
    erros.append("- SUPABASE URL is missing or invalid.")

if not SUPABASE_KEY:
    erros.append("- SUPABASE KEY is missing or invalid.")

if erros:
    print("\n❌ CONFIGURATION ERROR:")
    for erro in erros:
        print(erro)
    print("\nCheck your 'credentials.txt' file formatting.")
    sys.exit()
            

genai.configure(api_key=AI_API_KEY)

print(f">>> [SYSTEM] Engine loaded: {AI_MODEL}")

config_seguranca = [
    { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE" },
    { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE" },
    { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE" },
    { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE" },
]

model = genai.GenerativeModel(
    model_name=AI_MODEL,
    safety_settings=config_seguranca,
    generation_config={"temperature": 1, "max_output_tokens": 8192}
)

CAMINHO_PROJETO = os.path.join(os.getcwd(), "base-app")
ARQUIVO_ALVO = os.path.join(CAMINHO_PROJETO, "src", "App.jsx")
ARQUIVO_HTML = os.path.join(CAMINHO_PROJETO, "index.html")

# --- SYSTEM CONSTITUTION (Translated to English) ---
def montar_prompt_sistema(contexto_extra=""):
    return f"""
    YOU ARE A REACT CODE GENERATOR (VITE + TAILWIND).
    
    🛑 GOLDEN RULES (Your existence depends on this):
    1. LANGUAGE: Use ONLY Javascript (JSX).
    2. OUTPUT: Deliver ONLY the code inside ```jsx. No conversational text.
    3. COMMENTS: DO NOT add comments (// or /* */). Keep it clean.
    
    💾 DATABASE (SUPABASE JSON):
       - URL: "{SUPABASE_URL}"
       - KEY: "{SUPABASE_KEY}"
       - Import: import {{ createClient }} from '@supabase/supabase-js';
       - Init: const supabase = createClient('{SUPABASE_URL}', '{SUPABASE_KEY}');
       - TABLE: 'app_universal' (JSONB).
       
    🖼️ ASSETS:
       - Images: '[https://picsum.photos/id/](https://picsum.photos/id/){{id}}/800/600'
       - Avatars: '[https://i.pravatar.cc/150?u=](https://i.pravatar.cc/150?u=){{id}}'
       - Icons: lucide-react
       
    {contexto_extra}
    """

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def input_limpo(texto):
    sys.stdout.flush()
    return input(texto).strip()

def atualizar_titulo_html(novo_titulo):
    try:
        with open(ARQUIVO_HTML, "r", encoding="utf-8") as f:
            conteudo = f.read()
        padrao = r"<title>.*?</title>"
        novo_conteudo = re.sub(padrao, f"<title>{novo_titulo}</title>", conteudo)
        with open(ARQUIVO_HTML, "w", encoding="utf-8") as f:
            f.write(novo_conteudo)
    except Exception:
        pass

# --- LANGUAGE FILTER (UNIVERSAL) ---
def extrair_codigo_inteligente(texto_ia):
    # 1. Blacklist: Wrong languages signatures
    assinaturas_proibidas = [
        "def main():", "print(", "if __name__ ==", # Python
        "#include <", "int main()", "std::cout",   # C++ / C
        "public class", "System.out.println",      # Java
        "package main", "func main()",             # Go
        "<?php",                                   # PHP
        "<!DOCTYPE html>"                          # Pure HTML (no React)
    ]
    
    for assinatura in assinaturas_proibidas:
        if assinatura in texto_ia:
            print(f"\n❌ ALERT: AI used wrong language ({assinatura}). Rejecting...")
            return None
    
    # 2. Extract code block
    match = re.search(r"```(?:jsx|javascript|js)?\s*(.*?)\s*```", texto_ia, re.DOTALL)
    if match:
        codigo = match.group(1)
    else:
        codigo = texto_ia.replace("```jsx", "").replace("```", "")

    # 3. Whitelist: Code MUST look like React
    if "export default" not in codigo:
        print("\n❌ ALERT: Code does not export component (Missing 'export default'). Rejecting...")
        return None
    
    if "return (" not in codigo and "return <" not in codigo:
        print("\n❌ ALERT: Code does not return valid JSX. Rejecting...")
        return None

    return codigo

def gerar_com_protecao(prompt):
    try:
        resposta = model.generate_content(prompt)
        codigo = extrair_codigo_inteligente(resposta.text)
        if not codigo: return None
        return codigo
    except Exception as e:
        if "429" in str(e):
            print("\n🛑 DAILY QUOTA EXCEEDED 🛑")
            sys.exit(0)
        return None

def verificar_e_instalar_libs(codigo):
    if not codigo: return
    libs_padrao = ['react', 'react-dom', 'lucide-react', 'vite', '@vitejs/plugin-react', 'tailwindcss', 'postcss', 'autoprefixer']
    imports = re.findall(r"from\s+['\"]([^'\"]+)['\"]", codigo)
    libs_para_instalar = []
    for lib in imports:
        if lib.startswith('.') or lib.startswith('@'): continue
        nome = lib.split('/')[0]
        if nome not in libs_padrao: libs_para_instalar.append(nome)
    
    if libs_para_instalar:
        print(f"\n>>> [AUTO] Installing: {libs_para_instalar}")
        subprocess.run(f"npm install {' '.join(libs_para_instalar)}", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def obter_regra_colecao(ideia_app):
    nome_colecao = re.sub(r'[^a-zA-Z0-9]', '_', ideia_app.lower())[:20]
    return f"""
    📚 APPLICATION CONTEXT:
    - Goal: "{ideia_app}"
    - DB COLLECTION: '{nome_colecao}'
    - Login: MANDATORY (Email/Password).
    
    DB USAGE (Strict Mode):
    1. Insert: supabase.from('app_universal').insert([{{ collection: '{nome_colecao}', data: {{ ...data, email: user.email }} }}])
    2. Select: supabase.from('app_universal').select('*').eq('collection', '{nome_colecao}')
    """

def gerar_codigo_ia(prompt_usuario):
    print(f"\n>>> [AI] Creating from scratch...")
    contexto = obter_regra_colecao(prompt_usuario)
    sistema = montar_prompt_sistema(contexto)
    prompt_final = f"{sistema}\nTASK: Write COMPLETE App.jsx."
    return gerar_com_protecao(prompt_final)

def modificar_codigo_ia(codigo_atual, pedido_mudanca):
    print(f"\n>>> [AI] Applying fixes...")
    match_col = re.search(r"eq\('collection',\s*'([^']+)'\)", codigo_atual)
    nome_colecao = match_col.group(1) if match_col else "app_generic"
    
    contexto = f"""
    🔧 EDIT MODE:
    - User Request: "{pedido_mudanca}"
    - Keep Collection: '{nome_colecao}'
    """
    sistema = montar_prompt_sistema(contexto)
    prompt_final = f"{sistema}\nBASE CODE:\n{codigo_atual}\nTASK: Rewrite App.jsx with changes."
    return gerar_com_protecao(prompt_final)

def resgatar_codigo_cortado(codigo_atual):
    print(f"\n>>> [AI] 🚑 RESCUING CODE...")
    sistema = montar_prompt_sistema("EMERGENCY: Previous code was cut off.")
    prompt_final = f"{sistema}\nTASK: Rewrite App.jsx FROM SCRATCH."
    return gerar_com_protecao(prompt_final)

def salvar_arquivo(codigo):
    if not codigo: return False
    print(">>> [SYSTEM] Saving file...")
    try:
        with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
            f.write(codigo)
        return True
    except FileNotFoundError:
        print(f"ERROR: base-app folder not found.")
        return False

def encerrar_processo(processo):
    subprocess.run(f"taskkill /F /T /PID {processo.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def verificar_dominio_http(slug):
    dominio = f"http://{slug}.surge.sh"
    try:
        req = urllib.request.Request(dominio, method='HEAD')
        urllib.request.urlopen(req)
        return True 
    except HTTPError as e:
        if e.code == 404: return False
        return True
    except Exception:
        return False

def fazer_deploy(nome_inicial):
    limpar_tela()
    print("\n>>> [BUILD] Compiling...")
    build = subprocess.run("npm run build", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if build.returncode != 0:
        print("\n❌ BUILD ERROR.")
        return None
    
    nome_atual = nome_inicial
    while True:
        print(f"\n🔍 Checking: {nome_atual}.surge.sh ...")
        if verificar_dominio_http(nome_atual):
            print(f"⚠️  '{nome_atual}' already exists.")
            if input_limpo("Is it yours? (Y/N): ").lower() == 'y': break
            else: 
                nome_atual = re.sub(r'[^a-z0-9\s-]', '', input_limpo(">>> New name: ").lower()).replace(" ", "-")
                if not nome_atual: return None
        else:
            print("✅ Available!")
            break

    dominio_final = f"{nome_atual}.surge.sh"
    print(f">>> [DEPLOY] Uploading...")
    subprocess.run(f"npx surge ./dist --domain {dominio_final}", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL)
    return dominio_final

def limpar_nome(nome):
    nome = nome.lower()
    nome = re.sub(r'[^a-z0-9\s-]', '', nome)
    return re.sub(r'\s+', '-', nome)

def ciclo_visualizacao_edicao(prompt_inicial):
    limpar_tela()
    print("="*40)
    print("   PREVIEW MODE (AUTO-REFRESH)")
    print("="*40)
    
    processo = subprocess.Popen("npm run dev -- --open", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    
    while True:
        try:
            with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
                codigo_atual = f.read()
        except: break

        print("\n" + "-"*30)
        print(" [1] REQUEST CHANGE (AI will rewrite)")
        print(" [2] PUBLISH (Deploy)")
        print(" [3] EXIT")
        print(" [4] 🚑 RETRY FROM SCRATCH")
        print("-"*30)
        
        escolha = input_limpo(">>> ")
        
        if escolha == "1":
            pedido = input_limpo("\n📝 What to change? ")
            if not pedido: continue
            novo_codigo = modificar_codigo_ia(codigo_atual, pedido)
            if novo_codigo:
                verificar_e_instalar_libs(novo_codigo)
                salvar_arquivo(novo_codigo)
                print(">>> Updated! Check browser.")
                time.sleep(1)
                limpar_tela()
        
        elif escolha == "4":
            novo_codigo = resgatar_codigo_cortado(codigo_atual)
            if novo_codigo:
                verificar_e_instalar_libs(novo_codigo)
                salvar_arquivo(novo_codigo)
                print(">>> Reconstructed.")
                time.sleep(2)
                limpar_tela()
        
        elif escolha == "2": break
        elif escolha == "3": break

    encerrar_processo(processo)
    return "exit" if escolha == "3" else "publish"

def main():
    limpar_tela()
    print(f"-=[ 🏭 FACTORY v{versao} (Universal Filter) 🛑 ]=-")

    while True:
        prompt = input_limpo("\n📝 App Idea (or 'exit'): ")
        if prompt.lower() == 'exit': break
        nome = input_limpo("🏷️  Project Name: ") or "new-app"
        
        codigo = gerar_codigo_ia(prompt)
        if codigo:
            verificar_e_instalar_libs(codigo)
            if salvar_arquivo(codigo):
                atualizar_titulo_html(nome)
                if ciclo_visualizacao_edicao(prompt) == "publish":
                    link = fazer_deploy(limpar_nome(nome))
                    if link: print(f"\n✅ LINK: https://{link}\n")
                    input("Press Enter to continue...")

if __name__ == "__main__":
    main()