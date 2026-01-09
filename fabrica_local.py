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
# Mudei o default para um modelo melhor. Se não tiver, ele avisa.
LOCAL_MODEL = "qwen2.5-coder:7b" 

def call_local_ai(system_prompt, user_prompt, json_mode=False):
    if not ollama:
        return "// Error: 'ollama' library not installed."

    try:
        model_to_use = LOCAL_MODEL
        try:
            # Verifica se o modelo existe, senão fallback
            ollama.show(LOCAL_MODEL)
        except:
            model_to_use = "llama3.2"
            
        options = {
            "temperature": 0.2 if json_mode else 0.6,
            "num_ctx": 8192 
        }
        
        response = ollama.chat(
            model=model_to_use, 
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            options=options
        )
        return response['message']['content']
    except Exception as e:
        return f"// Local AI Error: {str(e)}"

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
    print(f"{main.MAGENTA}>>> [🧹] FACTORY RESET: {main.RESET}Cleaning old files...\n")
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

def extract_json_array(text):
    """
    Extrator robusto: Tenta JSON -> Tenta Regex JSON -> Tenta Regex Arquivos
    """
    text = text.strip()
    
    # 1. Tentativa JSON limpo
    try:
        # Busca o primeiro '[' e o último ']'
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass

    # 2. Tentativa Limpeza Markdown
    try:
        cleaned = text.replace("```json", "").replace("```", "").strip()
        # Se não começar com [, tenta achar
        if not cleaned.startswith("["):
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1:
                cleaned = cleaned[start:end+1]
        return json.loads(cleaned)
    except:
        pass

    # 3. FALLBACK SUPREMO: Regex para pegar caminhos de arquivos
    # Se o modelo responder com lista ("- src/components/Header.jsx")
    print(f"{main.YELLOW}⚠️  JSON Parsing failed. Scanning text for filenames...{main.RESET}")
    found_files = re.findall(r'(src/[a-zA-Z0-9_\-\/]+\.jsx)', text)
    if found_files:
        return list(set(found_files)) # Remove duplicatas

    return None

def sanitizar_codigo_agressivo(code, filename):
    code = re.sub(r'^```[a-zA-Z]*\n', '', code)
    code = re.sub(r'\n```$', '', code)
    code = code.replace("```jsx", "").replace("```js", "").replace("```", "")

    # Fix 1: Alias Hallucination (@components -> ./components)
    if "from '@" in code or 'from "@' in code:
        code = code.replace("from '@components", "from './components")
        code = code.replace('from "@components', 'from "./components')
        code = code.replace("from '@/", "from './")
        code = code.replace('from "@/', 'from "./')

    # Fix 2: Missing Relative Path
    code = code.replace("from 'components/", "from './components/")
    code = code.replace('from "components/', 'from "./components/')
    code = code.replace("from 'pages/", "from './pages/")
    code = code.replace('from "pages/', 'from "./pages/')

    # Fix 3: Bad Prop Usage (Icon={...})
    code = re.sub(r'\sIcon=\{[^}]+\}', '', code)

    # Fix 4: Next.js hallucination
    if 'from "next/' in code or "from 'next/" in code:
        print(f"   {main.YELLOW}🔧 Fixing Next.js hallucination in {main.RESET}{filename}...")
        code = re.sub(r'import\s+.*?from\s+["\']next\/.*?["\'];', '', code)
        code = code.replace("<Link", "<a").replace("</Link>", "</a>")
        code = code.replace("<Image", "<img").replace("</Image>", "</img>")

    # Fix 5: Icons
    if "from 'lucide-react'" in code:
        if "Fa" in code or "Si" in code: 
             code = re.sub(r'[A-Z][a-z]+(Icon)?', 'Box', code)
             code = "import { Box } from 'lucide-react';\n" + code

    if "export default" not in code:
        name = os.path.basename(filename).replace(".jsx", "")
        code += f"\n\nexport default {name};"

    return code.strip()

def plan_architecture(user_prompt):
    print(f"\n{main.CYAN}>>> [1/??] 🧠 LOCAL ARCHITECT: Blueprinting...{main.RESET}\n")
    
    system = """You are a Senior React Architect.
    OUTPUT RULES:
    1. Reply ONLY with a valid JSON Array of strings.
    2. DO NOT write "Here is the list" or any intro text.
    3. JUST THE JSON.
    
    TASK: List files to build:
    1. Max 5 files.
    2. Always include "src/App.jsx".
    3. If you need components, include them (e.g. "src/components/Navbar.jsx").
    """
    
    user = f"""Request: "{user_prompt}"
    JSON Array:"""
    
    try:
        resp_text = call_local_ai(system, user, json_mode=True)
        file_list = extract_json_array(resp_text)
        
        if not file_list: raise Exception("Parser failed to find any files.")

        forbidden = ["src/main.jsx", "src/main.js", "index.html", "src/index.css", "vite.config.js"]
        filtered_list = [f for f in file_list if f not in forbidden]
        
        final_list = []
        for f in filtered_list:
            if not f.startswith("src/"): f = f"src/{f}"
            final_list.append(f)

        if "src/App.jsx" not in final_list: final_list.insert(0, "src/App.jsx")
        
        return final_list

    except Exception as e:
        print(f"{main.YELLOW}⚠️ Architect Error: {main.RED} {e}. {main.RESET} Using Emergency Plan.")
        return ["src/App.jsx", "src/components/Header.jsx", "src/components/Hero.jsx"]

def plan_modification(user_request, existing_files):
    print(f"\n{main.CYAN}>>> [🔍] LOCAL AGENT: Analyzing impact...{main.RESET}")
    system = "You are a code analyzer. Return ONLY a JSON Array of filenames that need changes."
    user = f"""Request: "{user_request}"
    Files available: {json.dumps(existing_files)}
    
    Return JSON Array:"""
    
    try:
        resp_text = call_local_ai(system, user, json_mode=True)
        return extract_json_array(resp_text) or ["src/App.jsx"]
    except:
        return ["src/App.jsx"]

def generate_file(target_file, global_context, user_prompt, is_modification=False, current_step=None, total_steps=None):
    action = "MODIFYING" if is_modification else "BUILDER"
    
    if current_step and total_steps:
        step_display = f"[{current_step}/{total_steps}]"
    else:
        step_display = "[2/3]" if not is_modification else "[1/1]"

    print(f"{main.YELLOW}>>> {step_display} 👷 {action} (Local): {main.RESET}{target_file}...")
    
    project_summary = ""
    for path, code in global_context.items():
        if path != target_file:
            project_summary += f"\n// File: {path}\n{code[:300]}...\n"

    system = """ROLE: Senior React Developer (Vite + Tailwind).

    CRITICAL RULES:
    1. OUTPUT FORMAT: Return ONLY the raw code string. DO NOT use Markdown blocks (```). DO NOT write introductions.
    2. COMPONENT STRUCTURE: Use `export default function`. Ensure all hooks are at the top level.
    3. ICONS: STRICTLY import from 'lucide-react'.
       - CORRECT: import { Menu, X } from 'lucide-react';
       - WRONG: import { Menu } from './icons';
    4. IMPORTS: Use relative paths for local files (e.g., './Header').
    5. STYLING (Tailwind):
       - Always use `min-h-screen` and `w-full` for page containers.
       - Use `flex` and `grid` for layouts.
       - Ensure high contrast (e.g., bg-slate-950 text-white OR bg-gray-50 text-gray-900).
    6. SAFETY:
       - No nested <a> tags.
       - Check if variables are defined before usage.
    """

    if is_modification:
        old_code = global_context.get(target_file, "// New File")
        user = f"""TASK: Rewrite '{target_file}' to satisfy: "{user_prompt}"
        
        CURRENT CODE:
        {old_code}
        
        Output the FULL updated code."""
    else:
        user = f"""TASK: Create code for file '{target_file}'.
        APP GOAL: "{user_prompt}"
        
        OTHER FILES CONTEXT:
        {project_summary}
        
        Output the code for {target_file}:"""

    for attempt in range(2):
        try:
            resp_text = call_local_ai(system, user)
            code = sanitizar_codigo_agressivo(resp_text, target_file)
            if len(code) < 50: raise Exception("Generated code too short")
            return code
        except Exception as e:
            print(f"{main.RED}⚠️ Error on attempt {main.RESET}{attempt+1}: {e}")
            time.sleep(1)
            
    return "// ERROR: Failed to generate code."

def save_file(rel_path, code):
    clean_path = rel_path.replace("base-app/", "").replace("./", "").replace("\\", "/")
    if "src/" in clean_path and not clean_path.startswith("src/"):
        clean_path = clean_path.split("src/")[-1]
    
    if not clean_path.startswith("src/"): clean_path = f"src/{clean_path}"

    full_path = os.path.join(PROJECT_PATH, clean_path)
    folder = os.path.dirname(full_path)
    if not os.path.exists(folder): os.makedirs(folder)
    
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(code)

def check_dependencies(global_context, current_step=None, total_steps=None):
    if current_step and total_steps:
        step_display = f"[{current_step}/{total_steps}]"
    else:
        step_display = "[3/3]"

    print(f"\n{main.BLUE}>>> {step_display} 📦 DEPENDENCIES...{main.RESET}")
    required_libs = [
        'react', 'react-dom', 'vite', 
        '@vitejs/plugin-react-swc', 
        'tailwindcss', 'postcss', 'autoprefixer', 'lucide-react'
    ]
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

    clear_screen()
    print(f"{main.CYAN}╔════════════════════════════════════════════════════╗{main.RESET}")
    print(f"{main.CYAN}║                  LOCAL GENERATOR                   ║{main.RESET}")
    print(f"{main.CYAN}╚════════════════════════════════════════════════════╝{main.RESET}\n")
    
    # Check for better models
    try:
        models_info = ollama.list()
        available_models = [m['model'] for m in models_info['models']]
        
        # Priority Queue
        if "qwen2.5-coder:7b" in available_models: LOCAL_MODEL = "qwen2.5-coder:7b"
        elif "deepseek-r1:7b" in available_models: LOCAL_MODEL = "deepseek-r1:7b"
        elif "mistral:latest" in available_models: LOCAL_MODEL = "mistral:latest"
        elif model_name_from_config: LOCAL_MODEL = model_name_from_config
        else: LOCAL_MODEL = "llama3.2:latest"
        
    except:
        LOCAL_MODEL = "llama3.2"

    print(f"{main.MAGENTA}Model in use: {main.YELLOW}{LOCAL_MODEL}{main.RESET}")

    while True:
        initial_prompt = clean_input(f"\n{main.YELLOW}📝 App Idea {main.RED}(or 'exit'){main.RESET}: ")
        print("")
        
        if initial_prompt.lower() == 'exit': break
        
        reset_project()

        files_to_create = plan_architecture(initial_prompt)
        
        total_files = len(files_to_create)
        total_workflow_steps = total_files + 2

        print(f"📋 Plan: {main.CYAN}{files_to_create} {main.RESET}({total_files} files)\n")
        
        project_context = {}
        if "src/App.jsx" in files_to_create:
            files_to_create.remove("src/App.jsx")
            files_to_create.insert(0, "src/App.jsx")

        for i, file in enumerate(files_to_create):
            current_step_num = i + 2
            code = generate_file(file, project_context, initial_prompt, 
                                 current_step=current_step_num, 
                                 total_steps=total_workflow_steps)
            project_context[file] = code
            save_file(file, code)
            
        check_dependencies(project_context, 
                           current_step=total_workflow_steps, 
                           total_steps=total_workflow_steps)
        
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
                
                total_mod_steps = len(files_to_edit)

                for f in files_to_edit:
                    if f not in files_to_create: files_to_create.append(f)
                
                for i, file in enumerate(files_to_edit):
                    new_code = generate_file(file, project_context, change_request, 
                                             is_modification=True, 
                                             current_step=i+1, 
                                             total_steps=total_mod_steps)
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