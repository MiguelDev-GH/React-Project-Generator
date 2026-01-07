import os
import subprocess
import time
import random
import re
import sys
import shutil
import json
import signal
import main

try:
    import ollama
except ImportError:
    ollama = None

PROJECT_PATH = os.path.join(os.getcwd(), "base-app")
USE_DATABASE = False 
LOCAL_MODEL = "llama3.2" # Valor padrão (será sobrescrito pelo main.py)

def call_local_ai(system_prompt, user_prompt):
    if not ollama:
        return "// Error: 'ollama' library not installed."

    try:
        response = ollama.chat(model=LOCAL_MODEL, messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ])
        return response['message']['content']
    except Exception as e:
        return f"// Local Llama Error: {str(e)}"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def clean_input(text):
    sys.stdout.flush()
    return input(text).strip()

def kill_process(process):
    try:
        if os.name == 'nt':
            subprocess.run(f"taskkill /F /T /PID {process.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except: pass

def reset_project():
    print(f"{main.MAGENTA}>>> [🧹] FACTORY RESET: {main.RESET}Cleaning old files...")
    src_path = os.path.join(PROJECT_PATH, "src")
    if not os.path.exists(src_path): return
    
    folders_to_remove = ["components", "lib", "utils", "hooks", "pages", "context"]
    
    for item in os.listdir(src_path):
        item_path = os.path.join(src_path, item)
        if os.path.isdir(item_path) and item in folders_to_remove:
            try: shutil.rmtree(item_path)
            except: pass
        elif os.path.isfile(item_path):
            if item not in ["main.jsx", "index.css", "vite-env.d.ts", "App.css"]:
                if item == "App.jsx":
                    with open(item_path, "w", encoding="utf-8") as f:
                        f.write("export default function App() { return <div>Loading...</div> }")
                else:
                    os.remove(item_path)
    print(f"{main.GREEN}✅ Project Cleaned.{main.RESET}")

def sanitizar_codigo_agressivo(code, filename):
    if 'from "next/' in code or "from 'next/" in code:
        print(f"   {main.YELLOW}🔧 Fixing Next.js hallucination in {main.RESET}{filename}...")
        code = re.sub(r'import\s+.*?from\s+["\']next\/.*?["\'];', '', code)
        code = code.replace("<Link", "<a").replace("</Link>", "</a>")
        code = code.replace("<Image", "<img").replace("</Image>", "</img>")

    bad_prefixes = ("Si", "Fa", "Gi", "Bi", "Ai", "Io", "Ri", "Ti", "Go", "Tb", "Hi", "Md", "Bs")
    
    for prefix in bad_prefixes:
        if f"<{prefix}" in code:
            code = re.sub(f"<{prefix}[a-zA-Z0-9]*", "<Box", code)
            code = re.sub(f"{prefix}[a-zA-Z0-9]*", "Box", code) 

    if "from 'lucide-react'" in code or 'from "lucide-react"' in code:
        match = re.search(r"import\s+\{(.*?)\}\s+from\s+['\"]lucide-react['\"]", code, re.DOTALL)
        if match:
            original_content = match.group(1)
            clean_content = original_content.replace('\n', '').replace('\r', '')
            icons = [i.strip() for i in clean_content.split(',') if i.strip()]
            
            valid_icons = []
            has_bad_icon = False
            
            for icon in icons:
                if icon.startswith(bad_prefixes) or "Outline" in icon:
                    has_bad_icon = True
                else:
                    valid_icons.append(icon)
            
            if "<Box" in code or has_bad_icon:
                if "Box" not in valid_icons:
                    valid_icons.append("Box")
                if has_bad_icon:
                     print(f"   {main.YELLOW}🔧 Fixing bad icons in {filename}: {main.RED}Found Invalid{main.RESET} -> Box")
            
            new_import_line = f"import {{ {', '.join(valid_icons)} }} from 'lucide-react';"
            code = code.replace(match.group(0), new_import_line)

    if "<Box" in code and "Box" not in code.split("from 'lucide-react'")[0]:
        if "from 'lucide-react'" in code:
             code = re.sub(r"import\s+\{(.*?)\}\s+from\s+['\"]lucide-react['\"]", r"import { \1, Box } from 'lucide-react'", code)
        else:
             code = "import { Box } from 'lucide-react';\n" + code

    if "export default" not in code:
        if "export function" in code:
            code = code.replace("export function", "export default function")
        else:
            name = os.path.basename(filename).replace(".jsx", "")
            code += f"\n\nexport default {name};"

    return code

def fix_json_response(text):
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match: return json.loads(match.group(0))
        return None
    except: return None

def plan_architecture(user_prompt):
    print(f"\n{main.CYAN}>>> [1/3] 🧠 LOCAL ARCHITECT: Blueprinting...{main.RESET}\n")
    
    system = "You are a software architect. OUTPUT ONLY VALID JSON ARRAY."
    user = f"""
    Create a list of 4 to 6 files for a React App (Vite): "{user_prompt}".
    RULES:
    1. Output strictly a JSON Array of strings.
    2. Example: ["src/App.jsx", "src/components/Header.jsx"]
    3. INCLUDE "src/App.jsx".
    4. DO NOT include main.jsx, index.html.
    """
    
    try:
        resp_text = call_local_ai(system, user)
        file_list = fix_json_response(resp_text)
        
        if not file_list: raise Exception("Invalid JSON")

        forbidden = ["src/main.jsx", "src/main.js", "index.html", "src/index.css", "vite.config.js"]
        filtered_list = [f for f in file_list if f not in forbidden]
        
        if "src/App.jsx" not in filtered_list: filtered_list.append("src/App.jsx")
        return filtered_list

    except Exception as e:
        print(f"{main.YELLOW}⚠️ Architect Error: {main.RED} {e}. {main.RESET} Using Emergency Plan.")
        return ["src/App.jsx", "src/components/Header.jsx", "src/components/Footer.jsx"]

def plan_modification(user_request, existing_files):
    print(f"\n{main.CYAN}>>> [🔍] LOCAL AGENT: Analyzing impact...{main.RESET}")
    system = "Output ONLY JSON Array."
    user = f"""Which files need changes for: "{user_request}"? 
    Existing: {json.dumps(existing_files)}"""
    try:
        resp_text = call_local_ai(system, user)
        return fix_json_response(resp_text) or ["src/App.jsx"]
    except:
        return ["src/App.jsx"]

def generate_file(target_file, global_context, user_prompt, is_modification=False):
    action = "MODIFYING" if is_modification else "BUILDER"
    print(f"{main.YELLOW}>>> [2/3] 👷 {action} (Local): {main.RESET}{target_file}...")
    
    project_summary = ""
    for path, code in global_context.items():
        project_summary += f"\n--- FILE: {path} ---\n{code[:400]}...\n"

    system = """You are a React Code Generator using Vite.
    1. Output ONLY CODE. No markdown.
    2. ALWAYS use 'export default function ComponentName'.
    3. ICONS: Use ONLY generic names from 'lucide-react' (e.g., Home, User, Settings, Box).
    4. DO NOT import 'next/link' or 'next/image'. Use <a> and <img> tags.
    5. DO NOT import icons starting with Si, Fa, Ai, Bi, Gi.
    """

    if is_modification:
        old_code = global_context.get(target_file, "// New File")
        user = f"EDIT '{target_file}' for: '{user_prompt}'.\nOLD CODE:\n{old_code}"
    else:
        user = f"WRITE CODE for '{target_file}'.\nGOAL: '{user_prompt}'.\nCONTEXT:\n{project_summary}"

    for attempt in range(2):
        try:
            resp_text = call_local_ai(system, user)
            
            code = resp_text.replace("```jsx", "").replace("```javascript", "").replace("```js", "").replace("```", "").strip()
            
            code = sanitizar_codigo_agressivo(code, target_file)

            return code
        except Exception as e:
            print(f"{main.RED}⚠️ Error on attempt {main.RESET}{attempt+1}: {e}")
            time.sleep(1)
            
    return f"// LOCAL ERROR: {str(e)}"

def save_file(rel_path, code):
    clean_path = rel_path.replace("base-app/", "").replace("./", "").replace("\\", "/")
    while "src/src/" in clean_path: clean_path = clean_path.replace("src/src/", "src/")
    if not clean_path.startswith("src/"): clean_path = f"src/{clean_path}"

    full_path = os.path.join(PROJECT_PATH, clean_path)
    folder = os.path.dirname(full_path)
    if not os.path.exists(folder): os.makedirs(folder)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(code)

def check_dependencies(global_context):
    print(f"\n{main.BLUE}>>> [3/3] 📦 DEPENDENCIES...{main.RESET}")
    required_libs = ['react', 'react-dom', 'vite', '@vitejs/plugin-react', 'tailwindcss', 'postcss', 'autoprefixer', 'lucide-react']
    subprocess.run(f"npm install {' '.join(required_libs)}", cwd=PROJECT_PATH, shell=True, stdout=subprocess.DEVNULL)

def check_http_domain(slug):
    domain = f"http://{slug}.surge.sh"
    try:
        import urllib.request
        req = urllib.request.Request(domain, method='HEAD')
        urllib.request.urlopen(req)
        return True 
    except: return False

def deploy_project(initial_name):
    print(f"\n{main.MAGENTA}>>> [BUILDING]...{main.RESET}")
    subprocess.run("npm run build", cwd=PROJECT_PATH, shell=True, stdout=subprocess.DEVNULL)
    
    current_name = initial_name.replace(" ", "-").lower()[:15]
    while check_http_domain(current_name):
        current_name += f"-{random.randint(1,99)}"
    
    subprocess.run(f"npx surge ./dist --domain {current_name}.surge.sh", cwd=PROJECT_PATH, shell=True, stdout=subprocess.DEVNULL)
    return f"{current_name}.surge.sh"

def iniciar_sistema_local(model_name_from_config=None):
    global LOCAL_MODEL
    
    if not ollama:
        print(f"{main.RED}❌ Error: 'ollama' library missing.{main.RESET}")
        return

    # Atualiza o modelo com o que veio do credentials.txt via main.py
    if model_name_from_config:
        LOCAL_MODEL = model_name_from_config

    clear_screen()
    print(f"{main.CYAN}╔════════════════════════════════════════════════════╗{main.RESET}")
    print(f"{main.CYAN}║                  LOCAL GENERATOR                   ║{main.RESET}")
    print(f"{main.CYAN}╚════════════════════════════════════════════════════╝{main.RESET}\n")
    print(f"{main.MAGENTA}Model in use: {main.YELLOW}{LOCAL_MODEL}{main.RESET}")
    
    try:
        ollama.list()
    except:
        print(f"{main.RED}❌ Error: Could not connect to Ollama.{main.RESET}")
        return

    while True:
        initial_prompt = clean_input(f"\n{main.YELLOW}📝 App Idea {main.RED}(or 'exit'){main.RESET}: ")
        if initial_prompt.lower() == 'exit': break
        
        reset_project()

        files_to_create = plan_architecture(initial_prompt)
        print(f"📋 Plan: {main.CYAN}{files_to_create}\n")
        
        project_context = {}
        for file in files_to_create:
            code = generate_file(file, project_context, initial_prompt)
            project_context[file] = code
            save_file(file, code)
            
        check_dependencies(project_context)
        
        preview_process = None
        
        while True:
            if preview_process: kill_process(preview_process)
            
            print(f"\n{main.GREEN}✨ App Ready. Opening Preview...{main.RESET}")
            print("👉 http://localhost:5173")
            preview_process = subprocess.Popen("npm run dev -- --open", cwd=PROJECT_PATH, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            
            print("\n" + f"{main.CYAN}={main.RESET}"*30)
            print(f" {main.GREEN}[1] ✏️  MODIFY{main.RESET}")
            print(f" {main.MAGENTA}[2] 🚀 PUBLISH{main.RESET}")
            print(f" {main.BLUE}[3] 🔙 NEW PROJECT{main.RESET}")
            print(f" {main.RED}[4] ❌ EXIT{main.RESET}")
            print(f"{main.CYAN}={main.RESET}"*30)
            
            option = clean_input(">>> ")
            
            if option == "1":
                change_request = clean_input(f"\n{main.YELLOW}✏️  Change Request: {main.RESET}")
                files_to_edit = plan_modification(change_request, files_to_create)
                print(f"🎯 Files to Edit: {files_to_edit}")
                
                for f in files_to_edit:
                    if f not in files_to_create: files_to_create.append(f)
                
                for file in files_to_edit:
                    new_code = generate_file(file, project_context, change_request, is_modification=True)
                    project_context[file] = new_code
                    save_file(file, new_code)
                
                print(f"{main.GREEN}✅ Done! Reloading...{main.RESET}")
                
            elif option == "2":
                kill_process(preview_process)
                link = deploy_project(initial_prompt)
                print(f"\n{main.GREEN}🚀 LIVE: https://{link}{main.RESET}\n")
                input("Press ENTER...")
                break
            elif option == "3":
                kill_process(preview_process)
                break
            elif option == "4":
                kill_process(preview_process)
                sys.exit()