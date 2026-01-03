import os
import subprocess
import google.generativeai as genai
import time
import random
import re
import sys
import urllib.request
from urllib.error import HTTPError

versao = 5.1

# Api Key
CHAVE_API = ""

# Supabase data
SUPABASE_URL = ""
SUPABASE_KEY = ""

genai.configure(api_key=CHAVE_API)

# IA Model (From AI Studio)
NOME_MODELO = "models/gemini-3-flash-preview"

print(f">>> [SYSTEM] Motor carregado: {NOME_MODELO}")

config_seguranca = [
    { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE" },
    { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE" },
    { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE" },
    { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE" },
]

model = genai.GenerativeModel(
    model_name=NOME_MODELO,
    safety_settings=config_seguranca,
    generation_config={"temperature": 1, "max_output_tokens": 8192}
)

CAMINHO_PROJETO = os.path.join(os.getcwd(), "base-app")
ARQUIVO_ALVO = os.path.join(CAMINHO_PROJETO, "src", "App.jsx")
ARQUIVO_HTML = os.path.join(CAMINHO_PROJETO, "index.html")

# --- CONSTITUIÇÃO DO SISTEMA ---
def montar_prompt_sistema(contexto_extra=""):
    return f"""
    VOCÊ É UM GERADOR DE CÓDIGO REACT (VITE + TAILWIND).
    
    🛑 REGRAS DE OURO (Sua existência depende disso):
    1. LINGUAGEM: Use APENAS Javascript (JSX).
    2. SAÍDA: Entregue APENAS o código dentro de ```jsx.
    3. COMENTÁRIOS: PROIBIDO adicionar comentários.
    
    💾 BANCO DE DADOS (SUPABASE JSON):
       - URL: "{SUPABASE_URL}"
       - KEY: "{SUPABASE_KEY}"
       - Import: import {{ createClient }} from '@supabase/supabase-js';
       - Init: const supabase = createClient('{SUPABASE_URL}', '{SUPABASE_KEY}');
       - TABELA: 'app_universal' (JSONB).
       
    🖼️ ASSETS:
       - Imagens: '[https://picsum.photos/id/](https://picsum.photos/id/){{id}}/800/600'
       - Avatares: '[https://i.pravatar.cc/150?u=](https://i.pravatar.cc/150?u=){{id}}'
       - Ícones: lucide-react
       
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

# --- NOVO FILTRO DE LINGUAGEM (UNIVERSAL) ---
def extrair_codigo_inteligente(texto_ia):
    # 1. Lista Negra: Assinaturas de linguagens erradas
    assinaturas_proibidas = [
        "def main():", "print(", "if __name__ ==", # Python
        "#include <", "int main()", "std::cout",   # C++ / C
        "public class", "System.out.println",      # Java
        "package main", "func main()",             # Go
        "<?php",                                   # PHP
        "<!DOCTYPE html>"                          # HTML Puro (sem React)
    ]
    
    for assinatura in assinaturas_proibidas:
        if assinatura in texto_ia:
            print(f"\n❌ ALERTA: A IA usou linguagem errada ({assinatura}). Rejeitando...")
            return None
    
    # 2. Extrai o bloco de código
    match = re.search(r"```(?:jsx|javascript|js)?\s*(.*?)\s*```", texto_ia, re.DOTALL)
    if match:
        codigo = match.group(1)
    else:
        # Se não tiver markdown, assume que é o texto todo (mas perigoso)
        codigo = texto_ia.replace("```jsx", "").replace("```", "")

    # 3. Lista Branca: O código DEVE parecer React
    # Todo App.jsx precisa exportar algo e retornar JSX
    if "export default" not in codigo:
        print("\n❌ ALERTA: O código não exporta o componente (Falta 'export default'). Rejeitando...")
        return None
    
    if "return (" not in codigo and "return <" not in codigo:
        print("\n❌ ALERTA: O código não retorna JSX válido. Rejeitando...")
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
            print("\n🛑 COTA DIÁRIA ATINGIDA 🛑")
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
        print(f"\n>>> [AUTO] Instalando: {libs_para_instalar}")
        subprocess.run(f"npm install {' '.join(libs_para_instalar)}", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def obter_regra_colecao(ideia_app):
    nome_colecao = re.sub(r'[^a-zA-Z0-9]', '_', ideia_app.lower())[:20]
    return f"""
    📚 CONTEXTO DA APLICAÇÃO:
    - Objetivo: "{ideia_app}"
    - COLEÇÃO BANCO: '{nome_colecao}'
    - Login: OBRIGATÓRIO (Email/Senha).
    
    USO DO BANCO (Strict Mode):
    1. Insert: supabase.from('app_universal').insert([{{ collection: '{nome_colecao}', data: {{ ...dados, email: user.email }} }}])
    2. Select: supabase.from('app_universal').select('*').eq('collection', '{nome_colecao}')
    """

def gerar_codigo_ia(prompt_usuario):
    print(f"\n>>> [IA] Criando do zero...")
    contexto = obter_regra_colecao(prompt_usuario)
    sistema = montar_prompt_sistema(contexto)
    prompt_final = f"{sistema}\nTAREFA: Escreva App.jsx COMPLETO."
    return gerar_com_protecao(prompt_final)

def modificar_codigo_ia(codigo_atual, pedido_mudanca):
    print(f"\n>>> [IA] Aplicando correções...")
    match_col = re.search(r"eq\('collection',\s*'([^']+)'\)", codigo_atual)
    nome_colecao = match_col.group(1) if match_col else "app_generico"
    
    contexto = f"""
    🔧 EDIÇÃO:
    - Pedido: "{pedido_mudanca}"
    - Manter Coleção: '{nome_colecao}'
    """
    sistema = montar_prompt_sistema(contexto)
    prompt_final = f"{sistema}\nCÓDIGO BASE:\n{codigo_atual}\nTAREFA: Reescreva App.jsx com as mudanças."
    return gerar_com_protecao(prompt_final)

def resgatar_codigo_cortado(codigo_atual):
    print(f"\n>>> [IA] 🚑 RESGATANDO...")
    sistema = montar_prompt_sistema("EMERGÊNCIA: Código anterior cortado.")
    prompt_final = f"{sistema}\nTAREFA: Reescreva App.jsx DO ZERO."
    return gerar_com_protecao(prompt_final)

def salvar_arquivo(codigo):
    if not codigo: return False
    print(">>> [SISTEMA] Salvando...")
    try:
        with open(ARQUIVO_ALVO, "w", encoding="utf-8") as f:
            f.write(codigo)
        return True
    except FileNotFoundError:
        print(f"ERRO: Pasta base-app não encontrada.")
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
    print("\n>>> [BUILD] Compilando...")
    build = subprocess.run("npm run build", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if build.returncode != 0:
        print("\n❌ ERRO NO BUILD.")
        return None
    
    nome_atual = nome_inicial
    while True:
        print(f"\n🔍 Checando: {nome_atual}.surge.sh ...")
        if verificar_dominio_http(nome_atual):
            print(f"⚠️  '{nome_atual}' existe.")
            if input_limpo("É seu? (S/N): ").lower() == 's': break
            else: 
                nome_atual = re.sub(r'[^a-z0-9\s-]', '', input_limpo(">>> Novo nome: ").lower()).replace(" ", "-")
                if not nome_atual: return None
        else:
            print("✅ Livre!")
            break

    dominio_final = f"{nome_atual}.surge.sh"
    print(f">>> [DEPLOY] Enviando...")
    subprocess.run(f"npx surge ./dist --domain {dominio_final}", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL)
    return dominio_final

def limpar_nome(nome):
    nome = nome.lower()
    nome = re.sub(r'[^a-z0-9\s-]', '', nome)
    return re.sub(r'\s+', '-', nome)

def ciclo_visualizacao_edicao(prompt_inicial):
    limpar_tela()
    print("="*40)
    print("   MODO DE VISUALIZAÇÃO (AUTO-REFRESH)")
    print("="*40)
    
    processo = subprocess.Popen("npm run dev -- --open", cwd=CAMINHO_PROJETO, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    
    while True:
        try:
            with open(ARQUIVO_ALVO, "r", encoding="utf-8") as f:
                codigo_atual = f.read()
        except: break

        print("\n" + "-"*30)
        print(" [1] PEDIR MUDANÇA")
        print(" [2] PUBLICAR")
        print(" [3] SAIR")
        print(" [4] 🚑 REFAZER DO ZERO")
        print("-"*30)
        
        escolha = input_limpo(">>> ")
        
        if escolha == "1":
            pedido = input_limpo("\n📝 O que mudar? ")
            if not pedido: continue
            novo_codigo = modificar_codigo_ia(codigo_atual, pedido)
            if novo_codigo:
                verificar_e_instalar_libs(novo_codigo)
                salvar_arquivo(novo_codigo)
                print(">>> Atualizado!")
                time.sleep(1)
                limpar_tela()
        
        elif escolha == "4":
            novo_codigo = resgatar_codigo_cortado(codigo_atual)
            if novo_codigo:
                verificar_e_instalar_libs(novo_codigo)
                salvar_arquivo(novo_codigo)
                print(">>> Reconstruído.")
                time.sleep(2)
                limpar_tela()
        
        elif escolha == "2": break
        elif escolha == "3": break

    encerrar_processo(processo)
    return "sair" if escolha == "3" else "publicar"

def main():
    limpar_tela()
    print(f"-=[ 🏭 FÁBRICA v{versao} (Filtro Universal) 🛑 ]=-")

    while True:
        prompt = input_limpo("\n📝 Ideia do App (ou 'sair'): ")
        if prompt.lower() == 'sair': break
        nome = input_limpo("🏷️  Nome do Projeto: ") or "app-novo"
        
        codigo = gerar_codigo_ia(prompt)
        if codigo:
            verificar_e_instalar_libs(codigo)
            if salvar_arquivo(codigo):
                atualizar_titulo_html(nome)
                if ciclo_visualizacao_edicao(prompt) == "publicar":
                    link = fazer_deploy(limpar_nome(nome))
                    if link: print(f"\n✅ LINK: https://{link}\n")
                    input("Enter para continuar...")

if __name__ == "__main__":
    main()