import streamlit as st
import requests
import json
import re
import os
import zipfile
import tarfile
import io
import random
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN_USAGE_FILE = "token_usage.json"
SAVED_CHATS_FILE = "saved_chats.json"

def load_token_usage():
    if os.path.exists(TOKEN_USAGE_FILE):
        try:
            with open(TOKEN_USAGE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_token_usage(usage):
    try:
        with open(TOKEN_USAGE_FILE, "w") as f:
            json.dump(usage, f)
    except Exception:
        pass

def get_daily_tokens(username):
    usage = load_token_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    user_data = usage.get(username, {})
    return user_data.get(today, 0)

def add_tokens(username, count):
    usage = load_token_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    if username not in usage:
        usage[username] = {}
    current = usage[username].get(today, 0)
    usage[username][today] = current + count
    save_token_usage(usage)

def load_saved_chats(username):
    if os.path.exists(SAVED_CHATS_FILE):
        try:
            with open(SAVED_CHATS_FILE, "r") as f:
                all_chats = json.load(f)
                return all_chats.get(username, [])
        except Exception:
            pass
    return []

def save_saved_chats(username, chats):
    all_chats = {}
    if os.path.exists(SAVED_CHATS_FILE):
        try:
            with open(SAVED_CHATS_FILE, "r") as f:
                all_chats = json.load(f)
        except Exception:
            pass
    all_chats[username] = chats
    try:
        with open(SAVED_CHATS_FILE, "w") as f:
            json.dump(all_chats, f)
    except Exception:
        pass

PROJECT_KEYS = [
    "step", "custom_packages_info", "added_functions", "pages_config", 
    "generated_code", "app_prompt_val", "num_pages_val", "layout_style_val", 
    "ui_theme_val", "selected_packages_val", "custom_packages_str_val", "github_urls_input_val"
]

def load_project_to_state(project):
    for key in PROJECT_KEYS:
        if key in project:
            st.session_state[key] = project[key]
        else:
            if key == "step":
                st.session_state[key] = 1
            elif key in ["custom_packages_info", "added_functions", "selected_packages_val"]:
                st.session_state[key] = []
            elif key == "pages_config":
                st.session_state[key] = {}
            elif key in ["generated_code", "app_prompt_val", "custom_packages_str_val", "github_urls_input_val"]:
                st.session_state[key] = ""
            elif key == "num_pages_val":
                st.session_state[key] = 2
            elif key in ["layout_style_val", "ui_theme_val"]:
                st.session_state[key] = "Auto (let the AI decide)"
    st.session_state.current_project_id = project.get("id")
    st.session_state.current_project_name = project.get("name")

def get_current_project_state(project_id, project_name):
    project = {
        "id": project_id,
        "name": project_name,
    }
    for key in PROJECT_KEYS:
        project[key] = st.session_state.get(key)
    return project

def save_current_project():
    if "current_project_id" in st.session_state and st.session_state.current_project_id:
        username = st.session_state.username
        chats = load_saved_chats(username)
        updated_project = get_current_project_state(st.session_state.current_project_id, st.session_state.current_project_name)
        
        found = False
        for idx, ch in enumerate(chats):
            if ch.get("id") == st.session_state.current_project_id:
                chats[idx] = updated_project
                found = True
                break
        if not found:
            chats.append(updated_project)
        save_saved_chats(username, chats)


# Set up page config
st.set_page_config(
    page_title="R Shiny Code Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #0054AD, #00B4DB);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #6c757d;
        margin-bottom: 2rem;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #0054AD 0%, #0082b4 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 84, 173, 0.2);
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #0082b4 0%, #0054AD 100%);
        box-shadow: 0 6px 20px rgba(0, 84, 173, 0.3);
        transform: translateY(-2px);
    }
    
    .card {
        border-radius: 12px;
        background-color: #f8f9fa;
        padding: 1.5rem;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 1.5rem;
    }
    
    .package-tag {
        display: inline-block;
        background-color: #e3f2fd;
        color: #0d47a1;
        padding: 0.2rem 0.6rem;
        border-radius: 16px;
        font-size: 0.85rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
        border: 1px solid #bbdefb;
    }
    </style>
""", unsafe_allow_html=True)

# List of common packages for multi-select
COMMON_PACKAGES = [
    "shiny", "bslib", "shinydashboard", "shinydashboardPlus", "shinyWidgets", "bsicons",
    "plotly", "ggplot2", "echarts4r", "leaflet", "DT", "reactable", "visNetwork", "dygraphs",
    "dplyr", "tidyr", "readr", "readxl", "haven", "lubridate", "stringr", "forcats", "janitor",
    "glue", "shinyjs", "htmltools", "waiter", "shinycssloaders", "shinyFeedback", "shinyalert",
    "pool", "config", "golem", "rhino", "shinytest2", "profvis"
]

# Load Knowledge Base behind the scenes (not visible to user)
def load_knowledge_base():
    kb_path = "SHINY_KNOWLEDGE_BASE.md"
    if os.path.exists(kb_path):
        try:
            with open(kb_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error loading knowledge base file: {str(e)}"
    return "Knowledge base file 'SHINY_KNOWLEDGE_BASE.md' not found."

# Extract packages mentioned in the user prompt
def extract_packages(prompt):
    extracted = []
    # Tokenize input and find match
    words = set(re.findall(r'[a-zA-Z0-9_]+', prompt.lower()))
    for pkg in COMMON_PACKAGES:
        if pkg.lower() in words:
            extracted.append(pkg)
    return extracted

# Strip markdown wrapper from code block if model outputted it
def clean_r_code(response_text):
    text = response_text.strip()
    if text.startswith("```"):
        # find the first newline
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline:].strip()
        # strip closing ```
        if text.endswith("```"):
            text = text[:-3].strip()
    return text

# ---------------------------------------------------------------------------
# NEW: Helpers to extract *per-function descriptions* so the UI can show what
# each exported function does (e.g. haven::read_sas -> "Read SAS files").
# ---------------------------------------------------------------------------

# Balanced-brace extraction for an Rd command like \title{...} or \description{...}
def _extract_braced_block(text, keyword):
    marker = "\\" + keyword + "{"
    idx = text.find(marker)
    if idx == -1:
        return ""
    i = idx + len(marker)
    depth = 1
    start = i
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return text[start:i - 1]

# Strip common Rd/LaTeX-ish markup (\code{x} -> x) and collapse whitespace
def _clean_doc_text(s):
    if not s:
        return ""
    # \code{foo}, \link{foo}, \emph{foo}, \pkg{foo} ... -> keep inner text
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", s)
    s = s.replace("\\%", "%")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _clean_arguments_block(args_text):
    if not args_text:
        return ""
    items = []
    idx = 0
    while True:
        marker = "\\item{"
        pos = args_text.find(marker, idx)
        if pos == -1:
            break
        name_start = pos + len(marker)
        depth = 1
        i = name_start
        while i < len(args_text) and depth > 0:
            if args_text[i] == "{":
                depth += 1
            elif args_text[i] == "}":
                depth -= 1
            i += 1
        name = args_text[name_start:i - 1].strip()
        
        desc_start = args_text.find("{", i)
        if desc_start == -1:
            idx = i
            continue
        depth = 1
        j = desc_start + 1
        while j < len(args_text) and depth > 0:
            if args_text[j] == "{":
                depth += 1
            elif args_text[j] == "}":
                depth -= 1
            j += 1
        desc = args_text[desc_start + 1:j - 1].strip()
        desc = _clean_doc_text(desc)
        items.append(f"- {name}: {desc}")
        idx = j
    return "\n".join(items)

# Given the text of a single .Rd file, return {alias_name: metadata_dict}
def parse_rd_file(rd_text):
    docs = {}
    names = set()
    for m in re.findall(r"\\name\{([^}]*)\}", rd_text):
        names.add(m.strip())
    for m in re.findall(r"\\alias\{([^}]*)\}", rd_text):
        names.add(m.strip())

    desc = _clean_doc_text(_extract_braced_block(rd_text, "title"))
    if not desc:
        long_desc = _clean_doc_text(_extract_braced_block(rd_text, "description"))
        desc = long_desc[:160].strip()

    usage = _clean_doc_text(_extract_braced_block(rd_text, "usage"))
    arguments_raw = _extract_braced_block(rd_text, "arguments")
    arguments = _clean_arguments_block(arguments_raw)
    # Examples are runnable R code — keep raw (no whitespace collapsing)
    examples = _extract_braced_block(rd_text, "examples").strip()
    returns = _clean_doc_text(_extract_braced_block(rd_text, "value"))

    for n in names:
        if n:
            docs[n] = {
                "description": desc,
                "usage": usage,
                "parameters": arguments,
                "examples": examples,
                "returns": returns
            }
    return docs

# Extract {function_name: full_source} from raw R source using balanced-brace matching
def extract_function_bodies(file_content):
    bodies = {}
    for match in re.finditer(r"([a-zA-Z0-9_\.]+)\s*(?:<-|=)\s*function\s*\(", file_content):
        func_name = match.group(1).strip()
        brace_start = file_content.find("{", match.end())
        if brace_start == -1:
            continue
        depth = 1
        i = brace_start + 1
        while i < len(file_content) and depth > 0:
            if file_content[i] == "{":
                depth += 1
            elif file_content[i] == "}":
                depth -= 1
            i += 1
        bodies[func_name] = file_content[match.start():i]
    return bodies

# Parse roxygen (#') comment blocks from raw R source -> {func_name: metadata_dict}
def parse_roxygen_docs(file_content):
    docs = {}
    lines = file_content.splitlines()
    buffer = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#'"):
            buffer.append(stripped[2:].strip())
            continue
        # A function definition immediately following a roxygen block
        m = re.match(r"([a-zA-Z0-9_\.]+)\s*(?:<-|=)\s*function\b", stripped)
        if m and buffer:
            func_name = m.group(1).strip()
            title = ""
            params = []
            usage = ""
            for b in buffer:
                if b and not b.startswith("@"):
                    if not title:
                        title = b
                elif b.startswith("@param"):
                    parts = b[6:].strip().split(" ", 1)
                    if len(parts) == 2:
                        params.append(f"- {parts[0].strip()}: {parts[1].strip()}")
                    else:
                        params.append(f"- {parts[0].strip()}")
                elif b.startswith("@usage"):
                    usage = b[6:].strip()
            
            docs[func_name] = {
                "description": _clean_doc_text(title),
                "parameters": "\n".join(params),
                "usage": usage
            }
        if not stripped.startswith("#'"):
            buffer = []
    return docs

# Merge a {name: desc} docs dict onto a list of function names ->
# list of {"name":..., "description":...}
def build_function_details(functions, docs):
    details = []
    for fn in functions:
        base = re.split(r"\(", fn, 1)[0].strip()  # handles "name(args)" from scripts
        details.append({"name": fn, "description": docs.get(base, docs.get(fn, ""))})
    return details



# Parse a uploaded .zip R package
def parse_zip_package(file_bytes):
    metadata = {"name": "Unknown", "description": "", "functions": [], "type": "package"}
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            desc_file = None
            ns_file = None
            for name in z.namelist():
                if name.endswith("DESCRIPTION"):
                    desc_file = name
                elif name.endswith("NAMESPACE"):
                    ns_file = name
            
            if desc_file:
                desc_content = z.read(desc_file).decode("utf-8", errors="ignore")
                pkg_match = re.search(r"^Package:\s*(.*)$", desc_content, re.MULTILINE)
                desc_match = re.search(r"^Description:\s*([\s\S]*?)(?:^[a-zA-Z\d-]+:|\Z)", desc_content, re.MULTILINE)
                if pkg_match:
                    metadata["name"] = pkg_match.group(1).strip()
                if desc_match:
                    metadata["description"] = re.sub(r"\s+", " ", desc_match.group(1)).strip()
            
            if ns_file:
                ns_content = z.read(ns_file).decode("utf-8", errors="ignore")
                exports = re.findall(r"export\s*\((.*?)\)", ns_content)
                functions = []
                for exp in exports:
                    functions.extend([f.strip() for f in exp.split(",") if f.strip()])
                metadata["functions"] = sorted(list(set(functions)))

            # NEW: read man/*.Rd help files to build per-function descriptions
            docs = {}
            for name in z.namelist():
                if "man/" in name and name.endswith(".Rd"):
                    try:
                        rd_text = z.read(name).decode("utf-8", errors="ignore")
                        docs.update(parse_rd_file(rd_text))
                    except Exception:
                        pass
            # Read R/*.R source files to capture real function bodies
            bodies = {}
            for name in z.namelist():
                if re.search(r"(^|/)R/[^/]+\.[rR]$", name):
                    try:
                        src_text = z.read(name).decode("utf-8", errors="ignore")
                        bodies.update(extract_function_bodies(src_text))
                    except Exception:
                        pass
            metadata["function_docs"] = {k: v["description"] for k, v in docs.items()}
            metadata["function_params"] = {k: v["parameters"] for k, v in docs.items()}
            metadata["function_usage"] = {k: v["usage"] for k, v in docs.items()}
            metadata["function_examples"] = {k: v.get("examples", "") for k, v in docs.items()}
            metadata["function_returns"] = {k: v.get("returns", "") for k, v in docs.items()}
            metadata["function_codes"] = bodies
            metadata["function_details"] = build_function_details(metadata["functions"], metadata["function_docs"])
    except Exception as e:
        metadata["error"] = f"ZIP parsing error: {str(e)}"
    return metadata

# Parse a uploaded .tar.gz R package
def parse_tar_package(file_bytes):
    metadata = {"name": "Unknown", "description": "", "functions": [], "type": "package"}
    try:
        with tarfile.open(fileobj=io.BytesIO(file_bytes), mode="r:gz") as tar:
            desc_member = None
            ns_member = None
            for member in tar.getmembers():
                if member.name.endswith("DESCRIPTION"):
                    desc_member = member
                elif member.name.endswith("NAMESPACE"):
                    ns_member = member
            
            if desc_member:
                f = tar.extractfile(desc_member)
                if f:
                    desc_content = f.read().decode("utf-8", errors="ignore")
                    pkg_match = re.search(r"^Package:\s*(.*)$", desc_content, re.MULTILINE)
                    desc_match = re.search(r"^Description:\s*([\s\S]*?)(?:^[a-zA-Z\d-]+:|\Z)", desc_content, re.MULTILINE)
                    if pkg_match:
                        metadata["name"] = pkg_match.group(1).strip()
                    if desc_match:
                        metadata["description"] = re.sub(r"\s+", " ", desc_match.group(1)).strip()
            
            if ns_member:
                f = tar.extractfile(ns_member)
                if f:
                    ns_content = f.read().decode("utf-8", errors="ignore")
                    exports = re.findall(r"export\s*\((.*?)\)", ns_content)
                    functions = []
                    for exp in exports:
                        functions.extend([f.strip() for f in exp.split(",") if f.strip()])
                    metadata["functions"] = sorted(list(set(functions)))

            # NEW: read man/*.Rd help files to build per-function descriptions
            docs = {}
            for member in tar.getmembers():
                if "man/" in member.name and member.name.endswith(".Rd"):
                    try:
                        rf = tar.extractfile(member)
                        if rf:
                            rd_text = rf.read().decode("utf-8", errors="ignore")
                            docs.update(parse_rd_file(rd_text))
                    except Exception:
                        pass
            # Read R/*.R source files to capture real function bodies
            bodies = {}
            for member in tar.getmembers():
                if re.search(r"(^|/)R/[^/]+\.[rR]$", member.name):
                    try:
                        rf = tar.extractfile(member)
                        if rf:
                            src_text = rf.read().decode("utf-8", errors="ignore")
                            bodies.update(extract_function_bodies(src_text))
                    except Exception:
                        pass
            metadata["function_docs"] = {k: v["description"] for k, v in docs.items()}
            metadata["function_params"] = {k: v["parameters"] for k, v in docs.items()}
            metadata["function_usage"] = {k: v["usage"] for k, v in docs.items()}
            metadata["function_examples"] = {k: v.get("examples", "") for k, v in docs.items()}
            metadata["function_returns"] = {k: v.get("returns", "") for k, v in docs.items()}
            metadata["function_codes"] = bodies
            metadata["function_details"] = build_function_details(metadata["functions"], metadata["function_docs"])
    except Exception as e:
        metadata["error"] = f"tar.gz parsing error: {str(e)}"
    return metadata

# Parse an R script for function declarations
def parse_r_script(file_content, filename):
    metadata = {
        "name": filename, 
        "type": "script", 
        "functions": [],
        "function_codes": {},
        "function_params": {},
        "function_usage": {}
    }
    pattern = r"([a-zA-Z0-9_\.]+)\s*(?:<-|=)\s*function\s*\((.*?)\)"
    matches = list(re.finditer(pattern, file_content))
    for match in matches:
        func_name = match.group(1).strip()
        args = match.group(2).strip()
        full_sig = f"{func_name}({args})"
        metadata["functions"].append(full_sig)
        metadata["function_params"][full_sig] = args
        metadata["function_usage"][full_sig] = f"{func_name}({args})"
        
        # Extract balanced brace block for function code
        start_idx = match.end()
        brace_start = file_content.find("{", start_idx)
        if brace_start != -1:
            depth = 1
            i = brace_start + 1
            while i < len(file_content) and depth > 0:
                if file_content[i] == "{":
                    depth += 1
                elif file_content[i] == "}":
                    depth -= 1
                i += 1
            func_code = file_content[match.start():i]
        else:
            line_end = file_content.find("\n", start_idx)
            if line_end != -1:
                func_code = file_content[match.start():line_end]
            else:
                func_code = file_content[match.start():]
                
        metadata["function_codes"][full_sig] = func_code

    metadata["functions"] = sorted(list(set(metadata["functions"])))
    docs = parse_roxygen_docs(file_content)
    metadata["function_docs"] = {k: v["description"] for k, v in docs.items()}
    metadata["function_params_parsed"] = {k: v["parameters"] for k, v in docs.items()}
    metadata["function_usage_parsed"] = {k: v["usage"] for k, v in docs.items()}
    
    # Fill in fallback details from signature parsing
    for fn in metadata["functions"]:
        base = fn.split("(")[0].strip()
        if base in docs:
            # If usage is not set by roxygen @usage, default to signature fn
            if not metadata["function_usage_parsed"].get(base):
                metadata["function_usage"][fn] = fn
            else:
                metadata["function_usage"][fn] = metadata["function_usage_parsed"][base]
            
            # If parameters are not set by roxygen @param, default to args list
            if not metadata["function_params_parsed"].get(base):
                metadata["function_params"][fn] = metadata["function_params"].get(fn, "")
            else:
                metadata["function_params"][fn] = metadata["function_params_parsed"][base]
        else:
            metadata["function_usage"][fn] = fn
            
    metadata["function_details"] = build_function_details(metadata["functions"], metadata["function_docs"])
    return metadata


# Extract owner and repo from GitHub URL
def parse_github_url(url):
    pattern = r"(?:github\.com[:/])([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)(?:\.git)?(?:/tree/([a-zA-Z0-9_-]+))?"
    match = re.search(pattern, url)
    if match:
        owner = match.group(1)
        repo = match.group(2)
        branch = match.group(3) if match.group(3) else None
        return owner, repo, branch
    return None, None, None

# Fetch DESCRIPTION and NAMESPACE files from GitHub repository
def fetch_github_package(owner, repo, branch=None, github_token=None):
    metadata = {"name": repo, "description": "", "functions": [], "type": "github_package", "url": f"https://github.com/{owner}/{repo}"}
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
        
    try:
        desc_content = None
        active_branch = branch
        
        # If branch is specified, check only that branch.
        # Otherwise, try 'main' directly first, falling back to 'master'.
        # This completely avoids calling api.github.com, bypassing rate limits.
        if active_branch:
            desc_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{active_branch}/DESCRIPTION"
            res = requests.get(desc_url, headers=headers, timeout=5)
            if res.status_code == 200:
                desc_content = res.text
            else:
                metadata["error"] = f"DESCRIPTION file not found in branch '{active_branch}'."
                return metadata
        else:
            # Direct raw download from 'main' (extremely fast)
            desc_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/DESCRIPTION"
            res = requests.get(desc_url, headers=headers, timeout=5)
            if res.status_code == 200:
                desc_content = res.text
                active_branch = "main"
            else:
                # Direct raw download from 'master' (fallback branch)
                desc_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/DESCRIPTION"
                res = requests.get(desc_url, headers=headers, timeout=5)
                if res.status_code == 200:
                    desc_content = res.text
                    active_branch = "master"
                else:
                    # If both fail, optionally try API to check for custom default branch if token is provided
                    if github_token:
                        repo_info_url = f"https://api.github.com/repos/{owner}/{repo}"
                        api_res = requests.get(repo_info_url, headers=headers, timeout=5)
                        if api_res.status_code == 200:
                            api_branch = api_res.json().get("default_branch")
                            if api_branch and api_branch not in ["main", "master"]:
                                desc_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{api_branch}/DESCRIPTION"
                                res = requests.get(desc_url, headers=headers, timeout=5)
                                if res.status_code == 200:
                                    desc_content = res.text
                                    active_branch = api_branch
                                    
                    if not desc_content:
                        metadata["error"] = "DESCRIPTION file not found in repository (tried 'main' and 'master' branches)."
                        return metadata
                        
        # Parse DESCRIPTION file contents
        pkg_match = re.search(r"^Package:\s*(.*)$", desc_content, re.MULTILINE)
        desc_match = re.search(r"^Description:\s*([\s\S]*?)(?:^[a-zA-Z\d-]+:|\Z)", desc_content, re.MULTILINE)
        if pkg_match:
            metadata["name"] = pkg_match.group(1).strip()
        if desc_match:
            metadata["description"] = re.sub(r"\s+", " ", desc_match.group(1)).strip()
            
        # 3. Fetch NAMESPACE
        ns_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{active_branch}/NAMESPACE"
        ns_res = requests.get(ns_url, headers=headers, timeout=5)
        if ns_res.status_code == 200:
            ns_content = ns_res.text
            exports = re.findall(r"export\s*\((.*?)\)", ns_content)
            functions = []
            for exp in exports:
                functions.extend([f.strip() for f in exp.split(",") if f.strip()])
            metadata["functions"] = sorted(list(set(functions)))

        # 4. NEW: best-effort per-function descriptions from man/*.Rd help files.
        #    One recursive git-trees call lists the repo; then fetch a bounded
        #    number of .Rd files. Fully optional: any failure just means no
        #    descriptions, functions are still listed.
        docs = {}
        bodies = {}
        try:
            tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{active_branch}?recursive=1"
            tree_res = requests.get(tree_url, headers=headers, timeout=5)
            if tree_res.status_code == 200:
                tree = tree_res.json().get("tree", [])
                rd_paths = [
                    t["path"] for t in tree
                    if t.get("type") == "blob"
                    and t.get("path", "").startswith("man/")
                    and t.get("path", "").endswith(".Rd")
                ]
                for path in rd_paths[:60]:  # cap to protect against huge repos / rate limits
                    rd_raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{active_branch}/{path}"
                    rd_res = requests.get(rd_raw, headers=headers, timeout=5)
                    if rd_res.status_code == 200:
                        docs.update(parse_rd_file(rd_res.text))
                # R/*.R source files give the real function bodies
                r_paths = [
                    t["path"] for t in tree
                    if t.get("type") == "blob"
                    and t.get("path", "").startswith("R/")
                    and t.get("path", "").lower().endswith(".r")
                ]
                for path in r_paths[:40]:  # cap to protect against huge repos / rate limits
                    r_raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{active_branch}/{path}"
                    r_res = requests.get(r_raw, headers=headers, timeout=5)
                    if r_res.status_code == 200:
                        bodies.update(extract_function_bodies(r_res.text))
        except Exception:
            pass
        metadata["function_docs"] = {k: v["description"] for k, v in docs.items()}
        metadata["function_params"] = {k: v["parameters"] for k, v in docs.items()}
        metadata["function_usage"] = {k: v["usage"] for k, v in docs.items()}
        metadata["function_examples"] = {k: v.get("examples", "") for k, v in docs.items()}
        metadata["function_returns"] = {k: v.get("returns", "") for k, v in docs.items()}
        metadata["function_codes"] = bodies
        metadata["function_details"] = build_function_details(metadata.get("functions", []), metadata["function_docs"])

    except Exception as e:
        metadata["error"] = f"GitHub fetch error: {str(e)}"
    return metadata

# Cached wrapper for fetching GitHub packages to prevent API limit exhaustion
@st.cache_data(show_spinner=False)
def get_cached_github_package(owner, repo, branch=None, github_token=None):
    return fetch_github_package(owner, repo, branch, github_token)

# Call LLM APIs using standard requests library
def call_llm(provider, model_name, system_instruction, prompt, api_key, ollama_host=None):
    if provider == "Gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.2
            }
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        res_json = response.json()
        try:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        except KeyError:
            return f"API Error: Could not parse response. Response json: {json.dumps(res_json)}"
            
    elif provider == "Groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        res_json = response.json()
        return res_json['choices'][0]['message']['content']
        
    elif provider == "Anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "max_tokens": 8000,
            "system": system_instruction,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        res_json = response.json()
        return res_json['content'][0]['text']
        
    elif provider == "Ollama":
        if not ollama_host:
            ollama_host = "http://localhost:11434"
        url = f"{ollama_host}/api/chat"
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        res_json = response.json()
        return res_json['message']['content']
        
    return "Error: Unknown provider"

def render_simulated_function(fn):
    st.markdown(f"""
    <div style="background-color: #ffffff; border: 1px solid #e9ecef; border-left: 4px solid #0054AD; padding: 15px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
        <span style="font-weight: 600; color: #0054AD;">📦 Mapped Endpoint:</span> <code>{fn}</code>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        import numpy as np
        import pandas as pd
    except ImportError:
        np = None
        pd = None
        
    if np is None or pd is None:
        st.warning("Numpy and Pandas are required to run the simulation. Showing code preview only.")
        st.code(f"# Simulated call to {fn}")
        return
        
    col_w1, col_w2 = st.columns([1, 2])
    with col_w1:
        st.markdown("**🔧 Inputs**")
        slider_val = st.slider("Hazard Ratio / Effect Size Control", min_value=0.1, max_value=3.0, value=1.0, step=0.1, key=f"sim_slider_{fn}")
        sample_size = st.number_input("Sample Size (N)", min_value=10, max_value=10000, value=100, step=10, key=f"sim_n_{fn}")
        time_horizon = st.slider("Simulation Time Horizon (Days)", min_value=10, max_value=1000, value=365, step=10, key=f"sim_time_{fn}")
        data_type = st.selectbox("Plot Type", ["Line Plot", "Bar Chart", "Area Chart"], key=f"sim_plot_type_{fn}")
        
    with col_w2:
        st.markdown("**📊 Visual Output**")
        t_grid = np.linspace(0, time_horizon, 50)
        lam = 0.005
        s_t = np.exp(-lam * t_grid * slider_val)
        
        # Add random noise
        noise = np.random.normal(0, 0.02, len(t_grid))
        s_t = np.clip(s_t + noise, 0, 1)
        
        df_sim = pd.DataFrame({
            "Time (Days)": t_grid,
            "Survival Probability": s_t,
            "Reference Control": np.exp(-lam * t_grid)
        }).set_index("Time (Days)")
        
        if data_type == "Line Plot":
            st.line_chart(df_sim)
        elif data_type == "Bar Chart":
            st.bar_chart(df_sim)
        else:
            st.area_chart(df_sim)
            
        median_survival = "Infinity"
        idx_below = np.where(s_t < 0.5)[0]
        if len(idx_below) > 0:
            median_survival = f"{int(t_grid[idx_below[0]]):,} days"
            
        df_stats = pd.DataFrame({
            "Statistic": ["Median Survival Time", "Hazard Ratio (Input)", "Total Events Logged"],
            "Value": [median_survival, f"{slider_val:.2f}", f"{int(sample_size * (1 - s_t[-1]))} events"]
        })
        st.dataframe(df_stats, hide_index=True, use_container_width=True)
        
        st.code(f"""
[Shiny Server Output - {fn}]
Evaluating black-box function call:
> {fn.split('(')[0]}(data, HR = {slider_val}, N = {sample_size})
Status: 200 OK
Reactive chain execution completed in 0.04s.
        """, language="r")

# Initialize session state variables for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "auth_step" not in st.session_state:
    st.session_state.auth_step = "credentials"
if "mfa_code" not in st.session_state:
    st.session_state.mfa_code = None
if "user_plan" not in st.session_state:
    st.session_state.user_plan = "Free"
if "username" not in st.session_state:
    st.session_state.username = ""

# Authentication screen
if not st.session_state.authenticated:
    st.markdown('<div class="main-header" style="text-align: center; margin-top: 50px;">R Shiny Code Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header" style="text-align: center;">Secure Login Gateway</div>', unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        if st.session_state.auth_step == "credentials":
            st.subheader("🔑 Step 1: Sign In")
            username_input = st.text_input("Username / Email", key="username_input_val_login")
            password_input = st.text_input("Password", type="password", key="password_input_val_login")
            
            # Simple credentials DB
            users_db = {
                "pro_user": {"password": "pro123", "plan": "Pro"},
                "free_user": {"password": "free123", "plan": "Free"}
            }
            
            if st.button("Continue ➡️", use_container_width=True):
                if username_input in users_db and users_db[username_input]["password"] == password_input:
                    st.session_state.username = username_input
                    st.session_state.user_plan = users_db[username_input]["plan"]
                    st.session_state.auth_step = "mfa"
                    st.session_state.mfa_code = str(random.randint(100000, 999999))
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
        
        elif st.session_state.auth_step == "mfa":
            st.subheader("📱 Step 2: Multi-Factor Verification")
            st.write(f"Hello **{st.session_state.username}** ({st.session_state.user_plan} Plan).")
            
            # Simulated MFA Notification
            st.markdown(f"""
            <div style="background-color: #e3f2fd; border-left: 5px solid #0054AD; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <span style="font-weight: 600; color: #0d47a1;">📱 Simulated Authenticator notification:</span><br/>
                Your one-time MFA passcode is: <strong style="font-size: 1.2rem; letter-spacing: 2px; color: #0d47a1;">{st.session_state.mfa_code}</strong>
            </div>
            """, unsafe_allow_html=True)
            
            mfa_input = st.text_input("Enter 6-digit Verification Code", placeholder="XXXXXX", key="mfa_code_input_val")
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                if st.button("Verify & Login ✅", type="primary", use_container_width=True):
                    if mfa_input.strip() == st.session_state.mfa_code:
                        st.session_state.authenticated = True
                        st.session_state.auth_step = "done"
                        # Load projects
                        chats = load_saved_chats(st.session_state.username)
                        if chats:
                            load_project_to_state(chats[-1])
                        else:
                            # default project
                            proj_id = str(random.randint(10000000, 99999999))
                            st.session_state.current_project_id = proj_id
                            st.session_state.current_project_name = "Untitled Project"
                            st.session_state.step = 1
                            save_current_project()
                        st.success("Successfully logged in!")
                        st.rerun()
                    else:
                        st.error("Incorrect MFA passcode. Please try again.")
            with col_m2:
                if st.button("⬅️ Back to Login", use_container_width=True):
                    st.session_state.auth_step = "credentials"
                    st.session_state.username = ""
                    st.session_state.user_plan = "Free"
                    st.session_state.mfa_code = None
                    st.rerun()
                    
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Initialize session state variables
if "step" not in st.session_state:
    st.session_state.step = 1
if "custom_packages_info" not in st.session_state:
    st.session_state.custom_packages_info = []
if "added_functions" not in st.session_state:
    st.session_state.added_functions = []
if "pages_config" not in st.session_state:
    st.session_state.pages_config = {}


# --- MAIN APP LAYOUT ---

st.markdown('<div class="main-header">R Shiny Code Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Generate clean, modern, and production-grade R Shiny code guided by agent best practices.</div>', unsafe_allow_html=True)

# Layout: Split into sidebar config and main area
# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # User Profile & Plan Info
    st.markdown("### 👤 Profile")
    st.write(f"Logged in: **{st.session_state.username}**")
    st.write(f"Plan: **{st.session_state.user_plan}**")
    
    # Logout button
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.auth_step = "credentials"
        st.session_state.username = ""
        st.session_state.mfa_code = None
        st.rerun()
        
    st.markdown("---")
    
    # Token Usage Tracker
    st.markdown("### 📊 Daily Token Usage")
    daily_tokens = get_daily_tokens(st.session_state.username)
    token_limit = 500000 if st.session_state.user_plan == "Pro" else 15000
    pct = min(100, int((daily_tokens / token_limit) * 100))
    st.write(f"Usage: **{daily_tokens:,} / {token_limit:,}**")
    st.progress(pct / 100.0)
    if pct >= 100:
        st.error("⚠️ Token limit exceeded for today!")
        
    st.markdown("---")
    
    # Context-based chats/projects list
    st.markdown("### 📂 Saved Projects (Chats)")
    username = st.session_state.username
    chats = load_saved_chats(username)
    
    # Button to create a new project
    if st.button("🆕 New Project", use_container_width=True):
        # Save current project before switching
        save_current_project()
        
        # Initialize fresh state
        proj_id = str(random.randint(10000000, 99999999))
        st.session_state.current_project_id = proj_id
        st.session_state.current_project_name = "Untitled Project"
        st.session_state.step = 1
        
        # Reset other keys
        for key in PROJECT_KEYS:
            if key == "step":
                st.session_state[key] = 1
            elif key in ["custom_packages_info", "added_functions", "selected_packages_val"]:
                st.session_state[key] = []
            elif key == "pages_config":
                st.session_state[key] = {}
            elif key in ["generated_code", "app_prompt_val", "custom_packages_str_val", "github_urls_input_val"]:
                st.session_state[key] = ""
            elif key == "num_pages_val":
                st.session_state[key] = 2
            elif key in ["layout_style_val", "ui_theme_val"]:
                st.session_state[key] = "Auto (let the AI decide)"
                
        save_current_project()
        st.success("New project started!")
        st.rerun()
        
    if chats:
        st.write("Your active projects:")
        for ch in chats:
            ch_id = ch.get("id")
            ch_name = ch.get("name", "Untitled Project")
            col_ch1, col_ch2 = st.columns([4, 1])
            with col_ch1:
                # Highlight active project
                is_active = (st.session_state.get("current_project_id") == ch_id)
                btn_label = f"📁 **{ch_name}**" if is_active else f"📄 {ch_name}"
                if st.button(btn_label, key=f"load_ch_{ch_id}", use_container_width=True):
                    # Save current before switching
                    save_current_project()
                    load_project_to_state(ch)
                    st.rerun()
            with col_ch2:
                if st.button("❌", key=f"del_ch_{ch_id}", help="Delete Project"):
                    updated_chats = [c for c in chats if c.get("id") != ch_id]
                    save_saved_chats(username, updated_chats)
                    # If we deleted the active project, load another or start new
                    if st.session_state.get("current_project_id") == ch_id:
                        if updated_chats:
                            load_project_to_state(updated_chats[-1])
                        else:
                            st.session_state.current_project_id = str(random.randint(10000000, 99999999))
                            st.session_state.current_project_name = "Untitled Project"
                            st.session_state.step = 1
                            save_current_project()
                    st.rerun()
                    
        # Rename project inline
        new_proj_name = st.text_input("Rename Active Project:", value=st.session_state.get("current_project_name", "Untitled Project"), key="rename_proj_input_val")
        if new_proj_name.strip() and new_proj_name != st.session_state.get("current_project_name"):
            st.session_state.current_project_name = new_proj_name.strip()
            save_current_project()
            st.rerun()
            
    st.markdown("---")

    
    # Model Provider Selection
    provider = st.selectbox(
        "AI Provider",
        options=["Gemini", "Groq", "Ollama", "Anthropic"],
        index=0
    )
    
    # Default model names and API keys loaded from dotenv
    default_key = ""
    model_options = []
    
    if provider == "Gemini":
        default_key = os.getenv("GEMINI_API_KEY", "")
        model_options = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    elif provider == "Groq":
        default_key = os.getenv("GROQ_API_KEY", "")
        model_options = ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"]
    elif provider == "Anthropic":
        default_key = os.getenv("ANTHROPIC_API_KEY", "")
        model_options = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
    elif provider == "Ollama":
        model_options = ["llama3", "mistral", "codellama", "qwen2.5-coder"]
        
    # Model selection
    if provider == "Ollama":
        model_name = st.text_input("Ollama Model Name", value="qwen2.5-coder")
        ollama_host = st.text_input("Ollama Host URL", value=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        api_key = None
    else:
        model_name = st.selectbox("Model Name", options=model_options)
        api_key = st.text_input(
            f"{provider} API Key", 
            value=default_key, 
            type="password",
            placeholder="Enter API key or set it in .env"
        )
        ollama_host = None

    st.markdown("### 🐙 GitHub Settings")
    github_token = st.text_input(
        "GitHub Access Token (Optional)",
        value=os.getenv("GITHUB_PAT", ""),
        type="password",
        help="Provide a personal access token to authorize private repository access and lift public rate limits."
    )

    st.markdown("---")
    st.markdown("""
    ### About
    This app reads the local **R Shiny Knowledge Base** behind the scenes to guide the selected LLM.
    
    It injects best-practice templates, routing schemas, modular programming rules, bslib layout details, and package execution parameters straight into the model context.
    """)

# Dynamic Step Progress Indicator
step = st.session_state.step
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    if step == 1:
        st.markdown("<div style='text-align: center; font-weight: bold; border-bottom: 4px solid #0054AD; color: #0054AD; padding-bottom: 5px;'>1. Upload & Functions</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align: center; color: #adb5bd; border-bottom: 2px solid #dee2e6; padding-bottom: 5px;'>1. Upload & Functions</div>", unsafe_allow_html=True)
with col_s2:
    if step == 2:
        st.markdown("<div style='text-align: center; font-weight: bold; border-bottom: 4px solid #0054AD; color: #0054AD; padding-bottom: 5px;'>2. Pages & Function Mapping</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align: center; color: #adb5bd; border-bottom: 2px solid #dee2e6; padding-bottom: 5px;'>2. Pages & Function Mapping</div>", unsafe_allow_html=True)
with col_s3:
    if step == 3:
        st.markdown("<div style='text-align: center; font-weight: bold; border-bottom: 4px solid #0054AD; color: #0054AD; padding-bottom: 5px;'>3. LLM Code Generation</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='text-align: center; color: #adb5bd; border-bottom: 2px solid #dee2e6; padding-bottom: 5px;'>3. LLM Code Generation</div>", unsafe_allow_html=True)
st.write("")

# ---------------------------------------------------------------------------
# STEP 1: SOURCE UPLOAD & FUNCTION VERIFICATION
# ---------------------------------------------------------------------------
if step == 1:
    col_input, col_funcs = st.columns([1, 1])
    
    with col_input:
        st.markdown("### 📥 1. Specify Sources")
        st.caption("Upload source code files or connect a GitHub repository containing R packages/scripts.")
        
        github_urls_str = st.text_area(
            "GitHub repository URLs (one per line or comma-separated):",
            value=st.session_state.get("github_urls_input_val", ""),
            placeholder="e.g. https://github.com/r-lib/clipr\nhttps://github.com/r-lib/gargle",
            height=100,
            key="github_urls_input_val"
        )
        
        uploaded_files = st.file_uploader(
            "Upload personal R packages (.zip, .tar.gz) or custom scripts (.R):",
            type=["zip", "tar.gz", "R", "r"],
            accept_multiple_files=True,
            key="uploaded_files_input_val"
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            analyze_btn = st.button("🔍 Analyze Sources", type="primary", use_container_width=True)
        with col_btn2:
            clear_btn = st.button("🗑️ Clear Loaded Sources", use_container_width=True)
            
        if analyze_btn:
            st.cache_data.clear() # Clear streamlit cached data to parse documentation files fresh
            new_packages_info = []
            
            # Process uploaded files
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    file_name = uploaded_file.name
                    file_bytes = uploaded_file.read()
                    
                    if file_name.endswith(".zip"):
                        info = parse_zip_package(file_bytes)
                        info["filename"] = file_name
                        new_packages_info.append(info)
                    elif file_name.endswith(".tar.gz") or file_name.endswith(".tgz"):
                        info = parse_tar_package(file_bytes)
                        info["filename"] = file_name
                        new_packages_info.append(info)
                    elif file_name.endswith(".R") or file_name.endswith(".r"):
                        file_content = file_bytes.decode("utf-8", errors="ignore")
                        info = parse_r_script(file_content, file_name)
                        new_packages_info.append(info)
                        
            # Process GitHub URLs
            if github_urls_str:
                urls = re.split(r"[,\n]+", github_urls_str)
                github_urls = [u.strip() for u in urls if u.strip()]
                
                for url in github_urls:
                    owner, repo, branch = parse_github_url(url)
                    if owner and repo:
                        with st.spinner(f"Fetching {owner}/{repo} details from GitHub..."):
                            info = get_cached_github_package(owner, repo, branch, github_token)
                            info["url"] = url
                            new_packages_info.append(info)
                    else:
                        new_packages_info.append({
                            "name": url,
                            "type": "github_package",
                            "url": url,
                            "error": f"Invalid GitHub URL format: '{url}'"
                        })
            
            st.session_state.custom_packages_info = new_packages_info
            if new_packages_info:
                st.success(f"Loaded {len(new_packages_info)} sources successfully!")
            else:
                st.info("No package/script sources found or uploaded.")
                
        if clear_btn:
            st.cache_data.clear() # Clear streamlit cached data
            st.session_state.custom_packages_info = []
            st.session_state.added_functions = []
            st.success("Cleared all loaded source details, manually added functions, and cleared cache!")
            st.rerun()

    with col_funcs:
        st.markdown("### ➕ Add Missing/Lost Functions")
        st.caption("Manually enter missing functions and associate code, descriptions, and package mappings:")
        
        mapped_package = st.text_input("R Package Mapped To (optional):", placeholder="e.g. survival", key="manual_mapped_package")
        new_fn_name = st.text_input("Function Name & Signature:", placeholder="e.g. estimate_cox(data, threshold)", key="manual_fn_name")
        new_fn_desc = st.text_input("Mini Description:", placeholder="e.g. Fit a Cox proportional hazards model.", key="manual_fn_desc")
        new_fn_params = st.text_area("Parameters:", placeholder="e.g. data: data frame containing covariates\nthreshold: cutoff score", key="manual_fn_params")
        new_fn_usage = st.text_area("Usage Format:", placeholder="e.g. estimate_cox(heart_data, 0.5)", key="manual_fn_usage")
        new_fn_returns = st.text_input("Returns (object class/structure, optional):", placeholder="e.g. a coxph fit object with fields coef, var, loglik", key="manual_fn_returns")
        
        code_source = st.radio(
            "How to supply function code?",
            options=["No Code (Signature Only)", "Paste Code Manually", "Upload R/txt File"],
            key="manual_code_source"
        )
        
        manual_code = ""
        if code_source == "Paste Code Manually":
            manual_code = st.text_area("Paste Function Code:", placeholder="estimate_cox <- function(data, threshold) {\n  ...\n}", key="manual_pasted_code")
        elif code_source == "Upload R/txt File":
            code_file = st.file_uploader("Upload Function Code File:", type=["R", "r", "txt"], key="manual_uploaded_code_file")
            if code_file is not None:
                try:
                    manual_code = code_file.read().decode("utf-8", errors="ignore")
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
                    
        add_btn = st.button("➕ Add Function to List", type="primary", use_container_width=True)
        if add_btn:
            if not new_fn_name.strip():
                st.error("Function name cannot be empty.")
            else:
                cleaned_name = new_fn_name.strip()
                # Check if already added
                exists = False
                for fn in st.session_state.added_functions:
                    if fn["name"] == cleaned_name:
                        exists = True
                        break
                if not exists:
                    st.session_state.added_functions.append({
                        "name": cleaned_name,
                        "description": new_fn_desc.strip(),
                        "parameters": new_fn_params.strip(),
                        "usage": new_fn_usage.strip(),
                        "returns": new_fn_returns.strip(),
                        "code": manual_code,
                        "mapped_package": mapped_package.strip(),
                        "source": "Manually Added"
                    })
                    st.success(f"Added function: `{cleaned_name}`")
                    st.rerun()
                else:
                    st.warning("Function already exists in the manually added list.")
                        
        # Display listed functions
        st.markdown("### 🔎 Listed Functions")
        
        grouped_funcs = {}
        
        # From custom packages info
        for info in st.session_state.custom_packages_info:
            pkg_name = info.get("name", "Unknown Package")
            pkg_type = info.get("type", "package")
            funcs = info.get("functions", [])
            docs = info.get("function_docs", {})
            codes = info.get("function_codes", {})
            params = info.get("function_params", {})
            usage = info.get("function_usage", {})
            
            source_header = f"📦 Package: {pkg_name}" if pkg_type in ["package", "github_package"] else f"📄 Script: {pkg_name}"
            grouped_funcs[source_header] = []
            
            for fn in funcs:
                base = fn.split("(")[0].strip()
                desc = docs.get(base, docs.get(fn, ""))
                
                # Fetch code details
                fn_code = codes.get(fn, "")
                fn_params = params.get(fn, "")
                if not fn_params:
                    fn_params = params.get(base, "")
                fn_usage = usage.get(fn, "")
                if not fn_usage:
                    fn_usage = usage.get(base, "")
                
                grouped_funcs[source_header].append({
                    "name": fn,
                    "description": desc,
                    "parameters": fn_params,
                    "usage": fn_usage,
                    "code": fn_code,
                    "mapped_package": pkg_name if pkg_type in ["package", "github_package"] else "",
                    "source": pkg_type.upper()
                })
                
        # From manually added
        if st.session_state.added_functions:
            source_header = "➕ Manually Added Functions"
            grouped_funcs[source_header] = []
            for fn in st.session_state.added_functions:
                grouped_funcs[source_header].append({
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters", ""),
                    "usage": fn.get("usage", ""),
                    "code": fn.get("code", ""),
                    "mapped_package": fn.get("mapped_package", ""),
                    "source": "Manually Added"
                })
                
        if not grouped_funcs:
            st.info("No functions currently registered. Upload files or use 'Add Function' form.")
        else:
            for source, funcs in grouped_funcs.items():
                if funcs:
                    st.markdown(f"#### {source}")
                    for idx, fn in enumerate(funcs):
                        display_label = f"⚙️ `{fn['name']}`"
                        if fn.get("mapped_package"):
                            display_label = f"📦 {fn['mapped_package']}::`{fn['name']}`"
                            
                        with st.expander(display_label, expanded=False):
                            if fn.get("mapped_package"):
                                st.markdown(f"**Mapped R Package:** `{fn['mapped_package']}`")
                            
                            if fn['description']:
                                st.markdown(f"**Description:** {fn['description']}")
                            else:
                                st.markdown("*No description available.*")
                                
                            if fn.get("parameters"):
                                st.markdown("**Parameters:**")
                                st.text(fn["parameters"])
                                
                            if fn.get("usage"):
                                st.markdown("**Usage:**")
                                st.code(fn["usage"])
                                
                            if fn.get("code"):
                                st.markdown("**Source Code:**")
                                st.code(fn["code"], language="r")
                            
                            if fn['source'] == "Manually Added":
                                if st.button("🗑️ Remove Function", key=f"del_fn_{source}_{idx}"):
                                    st.session_state.added_functions = [f for f in st.session_state.added_functions if f["name"] != fn["name"]]
                                    st.rerun()

    # Step 1 Navigation
    st.markdown("---")
    col_prev, col_next = st.columns([1, 1])
    with col_next:
        if st.button("Next: App Structure & Mapping ➡️", type="primary", use_container_width=True):
            st.session_state.step = 2
            st.rerun()

# ---------------------------------------------------------------------------
# STEP 2: APP STRUCTURE & FUNCTION MAPPING
# ---------------------------------------------------------------------------
elif step == 2:
    # Gather all available functions
    all_available_functions = []
    for info in st.session_state.custom_packages_info:
        for fn in info.get("functions", []):
            if fn not in all_available_functions:
                all_available_functions.append(fn)
    for fn in st.session_state.added_functions:
        if fn["name"] not in all_available_functions:
            all_available_functions.append(fn["name"])
            
    col_structure, col_mapping = st.columns([1, 1])
    
    with col_structure:
        st.markdown("### 📄 Page & Sub-page Configuration")
        num_pages = st.number_input(
            "Number of main pages/tabs:",
            min_value=1,
            max_value=20,
            value=st.session_state.get("num_pages_val", 2),
            step=1,
            key="num_pages_val"
        )
        
        pages_config = {}
        
        for p_idx in range(num_pages):
            st.markdown("---")
            st.markdown(f"##### 📁 Page {p_idx + 1}")
            
            page_title = st.text_input(
                f"Page {p_idx + 1} Name",
                value=f"Page {p_idx + 1}",
                key=f"page_title_val_{p_idx}"
            )
            
            num_subs = st.number_input(
                f"Number of sub-pages for '{page_title}'",
                min_value=0,
                max_value=10,
                value=0,
                step=1,
                key=f"num_subs_val_{p_idx}"
            )
            
            pages_config[page_title] = {
                "sub_pages": {}
            }
            
            if num_subs > 0:
                for s_idx in range(num_subs):
                    sub_title = st.text_input(
                        f"  Sub-page {s_idx + 1} Name",
                        value=f"{page_title} Sub {s_idx + 1}",
                        key=f"sub_title_val_{p_idx}_{s_idx}"
                    )
                    # Placeholder for mapped functions
                    pages_config[page_title]["sub_pages"][sub_title] = []
            else:
                pages_config[page_title]["mapped_functions"] = []
                
    with col_mapping:
        st.markdown("### 🔗 Function Mapping")
        st.caption("Map custom functions to load and display on each page/sub-page.")
        
        if not all_available_functions:
            st.warning("⚠️ No custom/loaded functions are registered from Step 1. You can continue, and the AI will generate placeholder tabs and charts, or you can map standard code.")
            
        # Dynamic Multiselect mapping using index-based keys for stable session states
        for p_idx, (page_name, config) in enumerate(pages_config.items()):
            st.markdown(f"##### 🗂️ {page_name}")
            sub_pages = config.get("sub_pages", {})
            if sub_pages:
                for s_idx, sub_name in enumerate(sub_pages.keys()):
                    mapped_funcs = st.multiselect(
                        f"Functions for '{sub_name}':",
                        options=all_available_functions,
                        key=f"mapped_val_{p_idx}_{s_idx}"
                    )
                    pages_config[page_name]["sub_pages"][sub_name] = mapped_funcs
            else:
                mapped_funcs = st.multiselect(
                    f"Functions for '{page_name}':",
                    options=all_available_functions,
                    key=f"mapped_val_{p_idx}"
                )
                pages_config[page_name]["mapped_functions"] = mapped_funcs
                
    # Layout and Themes options
    st.markdown("---")
    st.markdown("### 🎨 App Presentation & Package Settings")
    col_lay, col_theme = st.columns(2)
    with col_lay:
        layout_style = st.selectbox(
            "Layout style:",
            options=[
                "Auto (let the AI decide)",
                "bslib dashboard — page_sidebar (filters left, content right)",
                "bslib navbar tabs — page_navbar (multiple top tabs)",
                "bslib cards grid — layout_columns / card()",
                "Classic fluidPage + sidebarLayout",
                "shinydashboard (header / sidebar / body)",
            ],
            index=0,
            key="layout_style_val"
        )
    with col_theme:
        ui_theme = st.selectbox(
            "Theme (bslib bootswatch):",
            options=["Auto / default", "flatly", "cosmo", "minty", "darkly", "cerulean", "journal", "lux", "sandstone"],
            index=0,
            key="ui_theme_val"
        )
        
    st.markdown("##### 📦 Package Dependencies")
    selected_packages = st.multiselect(
        "Standard R packages to load/use:",
        options=sorted(COMMON_PACKAGES),
        default=["shiny", "bslib"] if "shiny" in COMMON_PACKAGES else [],
        key="selected_packages_val"
    )
    custom_packages_str = st.text_area(
        "Custom CRAN/Bioconductor packages to load (one per line or comma-separated):",
        placeholder="e.g. survival\nlme4\nBiocManager",
        key="custom_packages_str_val",
        height=100
    )
    
    # Store finalized structural config in session state
    st.session_state.pages_config = pages_config
    
    # Navigation
    st.markdown("---")
    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if st.button("⬅️ Back to Upload & Source", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col_next:
        if st.button("Next: Review & Generate ➡️", type="primary", use_container_width=True):
            st.session_state.step = 3
            st.rerun()

# ---------------------------------------------------------------------------
# STEP 3: REVIEW & CODE GENERATION
# ---------------------------------------------------------------------------
elif step == 3:
    st.markdown("### 🚀 3. Compile and Generate R Shiny Code")
    
    # Retrieve configuration and selection variables
    layout_style = st.session_state.get("layout_style_val", "Auto (let the AI decide)")
    ui_theme = st.session_state.get("ui_theme_val", "Auto / default")
    selected_packages = st.session_state.get("selected_packages_val", [])
    custom_packages_str = st.session_state.get("custom_packages_str_val", "")
    custom_packages = [p.strip() for p in re.split(r"[,\n]+", custom_packages_str) if p.strip()]
    
    col_gen_input, col_gen_output = st.columns([1, 1])
    
    with col_gen_input:
        user_custom_notes = st.text_area(
            "Describe the application requirements or styling guidelines (optional):",
            value=st.session_state.get("app_prompt_val", ""),
            placeholder="e.g. Add sliders to control thresholds, use a modern dark palette, add reactive plots using plotly.",
            height=150,
            key="app_prompt_val"
        )
        
        # Build prompt
        prompt_parts = []
        prompt_parts.append("Generate a complete, single-file R Shiny application structure.")
        
        # Layout details
        prompt_parts.append("\n### APPLICATION PAGE STRUCTURE:")
        if not layout_style.startswith("Auto"):
            prompt_parts.append(f"- Layout Style: {layout_style}")
        if not ui_theme.startswith("Auto"):
            prompt_parts.append(f"- Apply the bslib bootswatch theme '{ui_theme}' via bs_theme(bootswatch = \"{ui_theme}\").")
            
        # Pages details
        pages_config = st.session_state.get("pages_config", {})
        for page_name, config in pages_config.items():
            sub_pages = config.get("sub_pages", {})
            if sub_pages:
                prompt_parts.append(f"- Page: '{page_name}' containing sub-pages:")
                for sub_name, funcs in sub_pages.items():
                    func_str = ", ".join([f"`{f}`" for f in funcs]) if funcs else "none"
                    prompt_parts.append(f"  - Sub-page: '{sub_name}' (uses functions: {func_str})")
            else:
                funcs = config.get("mapped_functions", [])
                func_str = ", ".join([f"`{f}`" for f in funcs]) if funcs else "none"
                prompt_parts.append(f"- Page: '{page_name}' (uses functions: {func_str})")
                
        # Required packages
        all_packages = list(set(selected_packages + custom_packages))
        if all_packages:
            prompt_parts.append(f"\n### REQUIRED R PACKAGES:\nLoad and use these R packages at the top: {', '.join(all_packages)}")
            
        # Custom source package / script details
        custom_pkg_text = ""
        if st.session_state.custom_packages_info:
            custom_pkg_text = "\n### USER-SELECTED CUSTOM R PACKAGES & FUNCTIONS:\n"
            for idx, info in enumerate(st.session_state.custom_packages_info):
                if info.get("type") == "github_package" and "error" in info:
                    continue
                pkg_key = info.get("url") or info.get("filename") or f"{info.get('name','pkg')}_{idx}"
                
                if info.get("type") == "script":
                    custom_pkg_text += f"\nScript File: `{info['name']}`\n"
                else:
                    custom_pkg_text += f"\nPackage Name: `{info['name']}`\nDescription: {info.get('description', '')}\n"
                    
            custom_pkg_text += "\nWhen generating the R Shiny application code:\n- If a custom script is provided, advise sourcing it (e.g. source('script.R')) in comments to call custom functions.\n- Call custom functions reactively where mapped.\n- These are custom/non-CRAN packages: do NOT guess their function signatures, argument names, or argument types. Use only what the FUNCTIONS SPECIFICATION below provides; if a signature is missing, mark the call with a '# WARNING: UNVERIFIED CALL' comment advising the user to check formals(pkg::fn) and ?pkg::fn."
            prompt_parts.append(custom_pkg_text)
            
        # Function specifications details (signatures, descriptions, code, params, usage)
        used_functions = set()
        for page_name, config in pages_config.items():
            sub_pages = config.get("sub_pages", {})
            if sub_pages:
                for sub_name, funcs in sub_pages.items():
                    used_functions.update(funcs)
            else:
                used_functions.update(config.get("mapped_functions", []))
                
        if used_functions:
            NOT_PROVIDED = "NOT PROVIDED"
            func_desc_map = {}
            func_params_map = {}
            func_sig_map = {}
            func_example_map = {}
            func_returns_map = {}
            func_code_map = {}
            func_pkg_map = {}

            for info in st.session_state.custom_packages_info:
                pkg_name = info.get("name", "")
                pkg_type = info.get("type", "")
                docs = info.get("function_docs", {})
                codes = info.get("function_codes", {})
                params = info.get("function_params", {})
                usage = info.get("function_usage", {})
                examples = info.get("function_examples", {})
                returns = info.get("function_returns", {})

                for fn in info.get("functions", []):
                    base = re.split(r"\(", fn, 1)[0].strip()
                    func_desc_map[fn] = docs.get(base, docs.get(fn, ""))
                    func_params_map[fn] = params.get(fn, params.get(base, ""))
                    func_sig_map[fn] = usage.get(fn, usage.get(base, ""))
                    func_example_map[fn] = examples.get(fn, examples.get(base, ""))
                    func_returns_map[fn] = returns.get(fn, returns.get(base, ""))
                    func_code_map[fn] = codes.get(fn, codes.get(base, ""))
                    if pkg_type in ["package", "github_package"]:
                        func_pkg_map[fn] = pkg_name

            for fn in st.session_state.added_functions:
                name = fn["name"]
                func_desc_map[name] = fn.get("description", "")
                func_params_map[name] = fn.get("parameters", "")
                # Manual entries put the signature in the name ("fn(arg1, arg2)")
                func_sig_map[name] = name if "(" in name else ""
                func_example_map[name] = fn.get("usage", "")
                func_returns_map[name] = fn.get("returns", "")
                func_code_map[name] = fn.get("code", "")
                func_pkg_map[name] = fn.get("mapped_package", "")

            def _fn_base(f):
                return re.split(r"\(", f, 1)[0].strip()

            # Upstream dependencies: other functions of the same package that this
            # function's docs, example, or source body reference
            def detect_dependencies(fn):
                deps = []
                search_text = "\n".join([
                    func_params_map.get(fn, ""), func_sig_map.get(fn, ""),
                    func_example_map.get(fn, ""), func_code_map.get(fn, ""),
                ])
                fn_base = _fn_base(fn)
                for other in func_desc_map:
                    other_base = _fn_base(other)
                    if other == fn or other_base == fn_base:
                        continue
                    if func_pkg_map.get(other, "") != func_pkg_map.get(fn, ""):
                        continue
                    pat_call = r"\b" + re.escape(other_base) + r"\s*\("
                    pat_ref = r"(?:by|of|from)\s+`?" + re.escape(other_base) + r"`?\b"
                    if re.search(pat_call, search_text) or re.search(pat_ref, search_text):
                        deps.append(other)
                return deps

            prompt_parts.append("\n### FUNCTIONS SPECIFICATION (Implement and display outputs for these mapped functions):\nEach block below carries the function's real API extracted from the package (signature, source, runnable example, return value, upstream dependencies). Fields marked NOT PROVIDED could not be extracted — the USAGE INSTRUCTIONS after the blocks say how to handle them.")
            for fn in sorted(used_functions):
                desc = func_desc_map.get(fn, "")
                pkg = func_pkg_map.get(fn, "")
                params = func_params_map.get(fn, "").strip()
                sig = func_sig_map.get(fn, "").strip()
                example = func_example_map.get(fn, "").strip()
                returns_val = func_returns_map.get(fn, "").strip()
                code = func_code_map.get(fn, "").strip()

                func_prompt = f"- Function Name: `{fn}`\n"
                if pkg:
                    func_prompt += f"  - Maps to R package: `{pkg}` (so call it as `{pkg}::{fn.split('(')[0].strip()}` or ensure library({pkg}) is called)\n"
                if desc:
                    func_prompt += f"  - Mini Description: {desc}\n"
                func_prompt += f"  - Signature (formals): {sig if sig else NOT_PROVIDED}\n"
                if params:
                    func_prompt += f"  - Parameters (documented arguments): {params}\n"
                if code:
                    func_prompt += f"  - Source / Reference Implementation:\n  ```r\n{code}\n  ```\n"
                else:
                    func_prompt += f"  - Source / Reference Implementation: {NOT_PROVIDED}\n"
                if example:
                    func_prompt += f"  - Full Example (runnable):\n  ```r\n{example}\n  ```\n"
                else:
                    func_prompt += f"  - Full Example (runnable): {NOT_PROVIDED}\n"
                func_prompt += f"  - Returns: {returns_val if returns_val else NOT_PROVIDED}\n"

                deps = detect_dependencies(fn)
                if deps:
                    func_prompt += "  - Dependency Functions (upstream functions this one needs):\n"
                    for dep in deps:
                        dep_sig = func_sig_map.get(dep, "").strip()
                        dep_code = func_code_map.get(dep, "").strip()
                        dep_ex = func_example_map.get(dep, "").strip()
                        dep_ret = func_returns_map.get(dep, "").strip()
                        func_prompt += f"    - `{dep}`:\n"
                        func_prompt += f"      - Signature (formals): {dep_sig if dep_sig else NOT_PROVIDED}\n"
                        if dep in used_functions and (dep_code or dep_ex):
                            func_prompt += "      - Source / Full Example: see this function's own block in this specification\n"
                        else:
                            if dep_code:
                                func_prompt += f"      - Source / Reference Implementation:\n      ```r\n{dep_code}\n      ```\n"
                            else:
                                func_prompt += f"      - Source / Reference Implementation: {NOT_PROVIDED}\n"
                            if dep_ex:
                                func_prompt += f"      - Full Example (runnable):\n      ```r\n{dep_ex}\n      ```\n"
                            else:
                                func_prompt += f"      - Full Example (runnable): {NOT_PROVIDED}\n"
                        func_prompt += f"      - Returns: {dep_ret if dep_ret else NOT_PROVIDED}\n"
                else:
                    func_prompt += f"  - Dependency Functions: {NOT_PROVIDED} (none auto-detected — re-check the parameter descriptions and example above for objects produced by other package functions)\n"
                prompt_parts.append(func_prompt)

            prompt_parts.append("""### FUNCTIONS SPECIFICATION USAGE INSTRUCTIONS:
1. When Source / Reference Implementation is provided, treat it as the HIGHEST-AUTHORITY source — above the Parameters prose and above the Signature line. Read the body to determine: exact argument names and defaults, how each argument is consumed (e.g. whether a hazard argument is called as a function, integrated, or indexed as a vector), the class and fields of the returned object, and any internal preconditions (like a setting that must be present for a downstream function to work).
2. When building a page, generate calls that match how the source actually uses arguments, not how the description phrases them. If the body integrates or vectorizes over an argument, supply that argument in the form the body expects. If the body reads specific fields off an input object, ensure the upstream constructor call produces those fields.
3. Preserve the object flow the code reveals. If an endpoint's body reads fields written by an upstream constructor, generate the full constructor -> object -> endpoint chain using both functions' real signatures, with any required settings (such as show.setting = "Y") passed on the constructor call itself.
4. Source is for UNDERSTANDING, not reimplementation. The Source / Reference Implementation is provided only so you can read a function's arguments, object flow, and preconditions. NEVER reimplement, split, or copy from it — do not lift sections, loops, or plot calls out of a function body into the app. Call the mapped function as a single BLACK BOX and handle only its return value or its side effects. If the body contains multiple internal steps (several plots, several computations), those are internal to that one call, not separate outputs to expose as separate panels.
5. Match the OUTPUT WRAPPER to the function's output mode, which you determine from Source and Returns:
   - Draws base-R graphics as a side effect (body calls plot(), lines(), abline(), etc. and returns nothing or invisibly): call it ONCE inside ONE renderPlot on one device. If the body produces multiple base plots, set par(mfrow = c(rows, cols)) sized to the number of plots, capture and restore par with on.exit(), and give the single plotOutput a height large enough for the grid. Do NOT create one panel per internal plot.
   - Returns a ggplot object: capture it and print() it in renderPlot, or pass it to the appropriate ggplot output. One returned object, one output.
   - Returns a list of plot objects or a combined object (patchwork/grid): render according to that structure, still from the single returned value — do not re-derive the pieces yourself.
   - Output mode unclear (Returns is NOT PROVIDED and the body is truncated): do NOT guess a decomposition. Call the function once into a single output and add a comment noting the output mode is unverified and the user should confirm whether it draws directly, returns a plot object, or returns a list.
   GOVERNING PRINCIPLE: the number of outputs in the app is determined by the number of times you CALL mapped functions, not by the number of plots or steps inside those functions. One mapped function call produces one output region unless the function's documented return value is explicitly a collection meant to be shown separately.
6. UNDOCUMENTED INTERNAL HELPERS signal an unverified object contract. A mapped function's body may call a helper that is NOT documented in the spec, on its own input object (e.g. `nph = f.extract(nphDesign)` at the top of display.nphDesign). The fields that helper reads off the object are a HIDDEN CONTRACT: the object from the upstream constructor must contain them, but that contract is not written down. Do NOT try to reconstruct which fields the helper needs, and do NOT trim, reshape, or "optimize" the constructor call to only the fields you think are used. Instead, replicate the documented constructor example EXACTLY as given and assume its output is a compatible object. Add a comment naming the undocumented helper as an unverified internal dependency, e.g.: `# NOTE: display.nphDesign calls f.extract() internally; the object from finalize.nphDesign is assumed compatible. Verify with str() on the constructor output if this errors.` Reason: when an endpoint reads its input through an undocumented extractor, a technically-correct constructor call can still produce an object that fails deep inside the black box with an error that gives no hint of the real cause. Constructor fidelity is the only defense — replicate the example rather than reasoning about internals.
7. VALIDATE LENGTHS of related vector inputs before calling. When the source shows multiple arguments that must have matching or related lengths (revealed by the body indexing them together, e.g. `alpha[i]`, `T[j]`, or derived relationships like `K = length(f.ws)` and `timing = targetEvents/targetEvents[K]`), validate those lengths in the server with `shiny::validate()` + `need()` and show a clear message BEFORE making the call — do not pass mismatched vectors into the function. When an input arrives as comma-separated text (analysis times, alpha values), parse it to numeric explicitly and check BOTH that parsing succeeded (no NAs) AND that the resulting length matches the related arguments; never pass unparsed strings or length-mismatched vectors into a mapped function. Reason: a length mismatch among parallel vector arguments detonates inside the function as a "wrong length" or "length zero" error that is hard to trace back to the input. Guarding lengths at the boundary turns an opaque internal crash into a clear user-facing message.
8. If Signature and Source are both NOT PROVIDED for a required function (including a Dependency Function), do NOT invent them. A Source body that is TRUNCATED (cut off mid-function) counts as NOT PROVIDED for any function the app would call DIRECTLY — apply the same handling. Mark the call `# WARNING: UNVERIFIED CALL`, name the specific function, and tell the user to run `formals(pkg::fn)`, `print(pkg::fn)`, and `?pkg::fn` and paste the FULL body back. A function is only safe to generate as verified when its real signature or complete source was supplied. (A truncated body IS still usable for a function that is only an internal dependency the app never calls directly — see rule 6.)
9. All prior rules remain in force: exact argument names/types, replicate documented examples over prose-built calls, vectorize functions passed to numerical routines to return length(t) values when the source confirms the argument is function-valued, and every function in the call chain must have a verified signature before the app is complete.""")
                
        # Custom requirements
        if user_custom_notes.strip():
            prompt_parts.append(f"\n### USER ADDITIONAL REQUIREMENTS:\n{user_custom_notes.strip()}")
            
        llm_prompt = "\n".join(prompt_parts)
        
        # Expandable prompt preview
        with st.expander("🔍 Preview Compiled LLM Prompt", expanded=False):
            st.code(llm_prompt, language="markdown")
            
        # Generate code button
        generate_btn = st.button("🚀 Generate R Shiny Code", type="primary", use_container_width=True)
        
        if generate_btn:
            if provider != "Ollama" and not api_key:
                st.error(f"Please provide an API Key for {provider} in the sidebar or in your `.env` file.")
            else:
                with st.spinner("Analyzing structures and generating R Shiny application..."):
                    try:
                        kb_content = load_knowledge_base()
                        
                        system_instruction = f"""You are a senior R Shiny developer.
Your task is to write a high-quality R Shiny application based on the user's requirements.
You MUST strictly follow the conventions, layouts, design patterns, and performance/security guidelines described in the R Shiny Agent Knowledge Base below.

### R SHINY AGENT KNOWLEDGE BASE:
{kb_content}

### EXPLICIT CODING DIRECTIONS:
1. Always load the required packages at the top of the code (e.g., using `library()`).
2. Use modern layout packages like `bslib` for styling where appropriate, or as specified in the knowledge base.
3. Write clean, modular, and reactive code.
4. VECTORIZATION (critical): any function passed to `integrate()`, `curve()`, `outer()`, `optimize()`, `uniroot()`, or used to compute hazard/survival/density curves MUST return a vector the same length as its input. Wrap constants in `rep(value, length(t))`, use `ifelse()`/`pmin()`/`pmax()` instead of `if`/`else` inside such functions, compute cumulative integrals per time point with `sapply(t_grid, function(tt) integrate(f, 0, tt)$value)`, and extract `$value` from `integrate()` results. Follow ALL rules in Knowledge Base sections 14.4 and 14.5.
5. CUSTOM PACKAGE APIS (critical): for functions from custom/non-CRAN packages, NEVER guess signatures, argument names, or argument types. Each FUNCTIONS SPECIFICATION block carries the real API: Signature (formals), Parameters, Source / Reference Implementation, Full Example (runnable), Returns, and Dependency Functions. Authority order: Source / Reference Implementation is highest (read the body for exact argument names/defaults, how each argument is consumed, returned object fields, and internal preconditions), then Signature and Full Example, then Parameters prose. Use exact argument names (no renaming, adding, or dropping), exact object flow between functions, and exact argument types (a hazard may be a rate vector + cut points, not a function). Replicate provided example calls rather than constructing calls from prose. If Signature and Source are both NOT PROVIDED for a function, precede your best-guess call with a prominent `# WARNING: UNVERIFIED CALL` comment naming the function and telling the user to run `formals(pkg::fn)`, `print(pkg::fn)`, and `?pkg::fn` and paste the results back. Follow ALL rules in Knowledge Base section 14.6.
6. DEPENDENCY CHAINS (critical): treat each mapped custom-package function as an ENDPOINT that may require objects built by upstream functions of the same package (e.g. a display function requiring the object from a finalize/constructor function — watch for parameter descriptions like "an object generated by X()" or usage preconditions like "must set arg = value when calling X()"). Every function in that chain is required: generate the full chain constructor -> object -> endpoint, passing any required constructor arguments (like show.setting = "Y") ON the constructor call itself. If a dependency's signature is NOT documented in the FUNCTIONS SPECIFICATION, do not invent it silently — mark that specific call with `# WARNING: UNVERIFIED CALL`, name the undocumented function, state that the app cannot run end to end until its signature is supplied, and include the exact `formals(pkg::fn)` / `?pkg::fn` commands to fix it. Never present a guessed call as working code. Follow ALL rules in Knowledge Base section 14.7.
7. BLACK-BOX OUTPUT (critical): a mapped function's Source is for understanding only — NEVER reimplement, split, or copy plot/loop/computation code out of its body into the app. Call each mapped function once as a black box and handle only its return value or side effects. The number of app outputs equals the number of mapped-function CALLS, not the number of plots/steps inside them. Match the output wrapper to the function's output mode: base-R side-effect drawing -> one renderPlot on one device (use par(mfrow) + on.exit() for multiple internal plots, never one panel each); returns a ggplot -> print() it in renderPlot; returns a list/patchwork -> render from that structure; unclear -> one output plus a comment that the mode is unverified. Follow ALL rules in Knowledge Base section 14.8.
8. BOUNDARY CORRECTNESS (critical): because failures hide inside the black box of a called function, the app must be correct at the boundary. (a) If a mapped function's body calls an undocumented helper on its input object (e.g. f.extract(nphDesign)), replicate the documented constructor example EXACTLY — do not trim/reshape the constructor call to fields you think are used — and add a comment naming the helper as an unverified internal dependency. (b) When related vector arguments must share lengths (body indexes them together, or derives K = length(...)), parse any comma-separated text inputs to numeric and validate with shiny::validate()/need() that parsing succeeded and lengths match BEFORE calling. (c) A TRUNCATED source body counts as NOT PROVIDED for any function the app calls directly — apply UNVERIFIED CALL handling. Follow ALL rules in Knowledge Base section 14.9.
9. Guard every render/reactive on the inputs it reads using `req()` so the app does not error before the user provides inputs.
10. Output ONLY the complete R code file content. Do not include markdown code block syntax (like ```r or ```) in your output—output raw R code only. No introductory or concluding text, just valid R code.
"""
                        
                        # Estimate prompt tokens
                        prompt_tokens = (len(system_instruction) + len(llm_prompt)) // 4
                        daily_tokens = get_daily_tokens(st.session_state.username)
                        token_limit = 500000 if st.session_state.user_plan == "Pro" else 15000
                        
                        if daily_tokens >= token_limit:
                            st.error("⚠️ Cannot generate code: Daily token limit reached. Please upgrade to Pro or wait until tomorrow.")
                        else:
                            raw_output = call_llm(
                                provider=provider,
                                model_name=model_name,
                                system_instruction=system_instruction,
                                prompt=llm_prompt,
                                api_key=api_key,
                                ollama_host=ollama_host
                            )
                            
                            # Estimate response tokens and accumulate
                            response_tokens = len(raw_output) // 4
                            total_consumed = prompt_tokens + response_tokens
                            add_tokens(st.session_state.username, total_consumed)
                            
                            cleaned_code = clean_r_code(raw_output)
                            st.session_state.generated_code = cleaned_code
                            save_current_project()
                            st.success(f"App code generated successfully! Consumed ~{total_consumed} tokens.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to generate application code: {str(e)}")
                        if hasattr(e, 'response') and e.response is not None:
                            st.code(e.response.text, language="json")
                            
    with col_gen_output:
        if "generated_code" in st.session_state:
            tab_code, tab_preview = st.tabs(["💻 R Shiny Code", "👁️ Live App Preview"])
            
            with tab_code:
                st.markdown("### 💻 Generated R Shiny Code")
                st.code(st.session_state.generated_code, language="r")
                
                st.download_button(
                    label="💾 Download app.R",
                    data=st.session_state.generated_code,
                    file_name="app.R",
                    mime="text/plain",
                    use_container_width=True
                )
                
            with tab_preview:
                st.markdown("### 👁️ Live Interactive App Preview")
                if st.session_state.user_plan == "Free":
                    st.markdown("""
                    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 20px; border-radius: 8px; text-align: center; margin-top: 30px;">
                        <h3 style="color: #856404; margin-top: 0;">🔒 Pro Feature Required</h3>
                        <p style="color: #856404;">The <strong>Live Interactive App Preview</strong> allows Pro plan subscribers to test their dashboard widgets and visualize generated code live inside the generator without downloading.</p>
                        <p style="font-weight: bold; color: #856404;">Please log in as <code>pro_user</code> to access this feature.</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    pages_config = st.session_state.get("pages_config", {})
                    if not pages_config:
                        st.info("No pages or tabs configured in Step 2. Please configure them to view the interactive preview.")
                    else:
                        st.markdown("""
                        <div style="background-color: #f1f3f5; border: 1px solid #dee2e6; padding: 10px; border-radius: 6px; margin-bottom: 20px; font-family: monospace; font-size: 0.9rem; color: #495057;">
                            🌐 <b>Simulated R Shiny Application Frame</b>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        layout_style = st.session_state.get("layout_style_val", "Auto (let the AI decide)")
                        ui_theme = st.session_state.get("ui_theme_val", "Auto / default")
                        st.caption(f"Theme applied: `{ui_theme}` | Layout: `{layout_style}`")
                        
                        # Render simulated pages tabs
                        page_titles = list(pages_config.keys())
                        sim_tabs = st.tabs(page_titles)
                        
                        for idx, tab in enumerate(sim_tabs):
                            page_name = page_titles[idx]
                            config = pages_config[page_name]
                            
                            with tab:
                                st.markdown(f"#### 📁 {page_name}")
                                
                                sub_pages = config.get("sub_pages", {})
                                if sub_pages:
                                    sub_titles = list(sub_pages.keys())
                                    sub_tabs = st.tabs(sub_titles)
                                    
                                    for s_idx, s_tab in enumerate(sub_tabs):
                                        sub_name = sub_titles[s_idx]
                                        funcs = sub_pages[sub_name]
                                        with s_tab:
                                            st.markdown(f"##### 📄 {sub_name}")
                                            if not funcs:
                                                st.info("No functions mapped to this sub-page.")
                                            else:
                                                for fn in funcs:
                                                    render_simulated_function(fn)
                                else:
                                    funcs = config.get("mapped_functions", [])
                                    if not funcs:
                                        st.info("No functions mapped to this page.")
                                    else:
                                        for fn in funcs:
                                            render_simulated_function(fn)
        else:
            st.info("Ensure Step 1 and 2 are filled, then click 'Generate R Shiny Code' to view results.")
            
    # Step 3 Navigation
    st.markdown("---")
    if st.button("⬅️ Back to App Structure", use_container_width=True):
        st.session_state.step = 2
        st.rerun()

# Automatically save project state on any user interaction if authenticated
if st.session_state.get("authenticated"):
    save_current_project()



