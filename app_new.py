import streamlit as st
import requests
import json
import re
import os
import zipfile
import tarfile
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# Given the text of a single .Rd file, return {alias_name: short_description}
def parse_rd_file(rd_text):
    docs = {}
    names = set()
    for m in re.findall(r"\\name\{([^}]*)\}", rd_text):
        names.add(m.strip())
    for m in re.findall(r"\\alias\{([^}]*)\}", rd_text):
        names.add(m.strip())
    # Prefer the concise \title; fall back to first sentence of \description
    desc = _clean_doc_text(_extract_braced_block(rd_text, "title"))
    if not desc:
        long_desc = _clean_doc_text(_extract_braced_block(rd_text, "description"))
        desc = long_desc[:160].strip()
    for n in names:
        if n:
            docs[n] = desc
    return docs

# Parse roxygen (#') comment blocks from raw R source -> {func_name: description}
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
            title = ""
            for b in buffer:
                if b and not b.startswith("@"):
                    title = b
                    break
            docs[m.group(1).strip()] = _clean_doc_text(title)
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
            metadata["function_docs"] = docs
            metadata["function_details"] = build_function_details(metadata["functions"], docs)
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
            metadata["function_docs"] = docs
            metadata["function_details"] = build_function_details(metadata["functions"], docs)
    except Exception as e:
        metadata["error"] = f"tar.gz parsing error: {str(e)}"
    return metadata

# Parse an R script for function declarations
def parse_r_script(file_content, filename):
    metadata = {"name": filename, "type": "script", "functions": []}
    pattern = r"([a-zA-Z0-9_\.]+)\s*(?:<-|=)\s*function\s*\((.*?)\)"
    matches = re.findall(pattern, file_content)
    for match in matches:
        func_name = match[0].strip()
        args = match[1].strip()
        metadata["functions"].append(f"{func_name}({args})")
    metadata["functions"] = sorted(list(set(metadata["functions"])))
    # NEW: pull roxygen (#') titles as per-function descriptions
    docs = parse_roxygen_docs(file_content)
    metadata["function_docs"] = docs
    metadata["function_details"] = build_function_details(metadata["functions"], docs)
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
        except Exception:
            pass
        metadata["function_docs"] = docs
        metadata["function_details"] = build_function_details(metadata.get("functions", []), docs)

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

# --- MAIN APP LAYOUT ---

st.markdown('<div class="main-header">R Shiny Code Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Generate clean, modern, and production-grade R Shiny code guided by agent best practices.</div>', unsafe_allow_html=True)

# Layout: Split into sidebar config and main area
# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
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

# Main Page Inputs
col_input, col_output = st.columns([1, 1])

with col_input:
    st.markdown("### 📝 Define Application")
    
    # User prompt
    user_prompt = st.text_area(
        "Describe the Shiny app you want to generate:",
        height=220,
        placeholder="e.g. Create a single-file bslib dashboard with a sidebar containing filters for a dataset (Species). The main panel should display a scatter plot using Plotly (Sepal.Length vs Sepal.Width) and an interactive DataTable underneath it showing the filtered dataset.",
        key="app_prompt"
    )
    
    # Package selection
    st.markdown("### 📦 Packages")
    
    # Run auto-extraction on current prompt
    detected = extract_packages(user_prompt) if user_prompt else []
    
    # Display detected packages
    if detected:
        st.markdown("**Auto-detected packages:**")
        html_tags = "".join([f'<span class="package-tag">{pkg}</span>' for pkg in detected])
        st.markdown(html_tags, unsafe_allow_html=True)
    
    # Manual checklist
    selected_packages = st.multiselect(
        "Manually specify packages to load/use:",
        options=sorted(COMMON_PACKAGES),
        default=detected,
        help="Select extra packages you want to guarantee are loaded in your shiny application."
    )
    
    # Text input for other custom/custom CRAN/Bioconductor packages
    custom_packages_str = st.text_input(
        "Additional packages (comma-separated):",
        placeholder="e.g. survival, lme4, BiocManager"
    )
    
    custom_packages = [p.strip() for p in custom_packages_str.split(",") if p.strip()]
    
    # 📁 Upload Custom R Packages / Scripts
    st.markdown("### 📁 Upload Custom R Packages & Scripts")
    uploaded_files = st.file_uploader(
        "Upload personal R packages (.zip, .tar.gz) or custom scripts (.R) to include in context:",
        type=["zip", "tar.gz", "R", "r"],
        accept_multiple_files=True
    )
    
    # 🐙 Import Custom R Packages from GitHub
    st.markdown("### 🐙 Import R Packages from GitHub")
    github_urls_str = st.text_area(
        "Enter GitHub repository URLs (one per line or comma-separated):",
        placeholder="e.g. https://github.com/r-lib/clipr\nhttps://github.com/r-lib/gargle",
        height=100
    )
    
    custom_packages_info = []
    
    # Process uploaded files
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            file_bytes = uploaded_file.read()
            
            if file_name.endswith(".zip"):
                info = parse_zip_package(file_bytes)
                info["filename"] = file_name
                custom_packages_info.append(info)
            elif file_name.endswith(".tar.gz") or file_name.endswith(".tgz"):
                info = parse_tar_package(file_bytes)
                info["filename"] = file_name
                custom_packages_info.append(info)
            elif file_name.endswith(".R") or file_name.endswith(".r"):
                file_content = file_bytes.decode("utf-8", errors="ignore")
                info = parse_r_script(file_content, file_name)
                custom_packages_info.append(info)
                
    # Process GitHub URLs
    if github_urls_str:
        # Split by comma or newline
        urls = re.split(r"[,\n]+", github_urls_str)
        github_urls = [u.strip() for u in urls if u.strip()]
        
        for url in github_urls:
            owner, repo, branch = parse_github_url(url)
            if owner and repo:
                with st.spinner(f"Fetching {owner}/{repo} details from GitHub..."):
                    info = get_cached_github_package(owner, repo, branch, github_token)
                    info["url"] = url
                    custom_packages_info.append(info)
            else:
                custom_packages_info.append({
                    "name": url,
                    "type": "github_package",
                    "url": url,
                    "error": f"Invalid GitHub URL format: '{url}'"
                })
        
    # ------------------------------------------------------------------
    # NEW: Interactive per-function selection.
    # Instead of just previewing everything, let the user SEE each exported
    # function with its description and CHOOSE which ones to feed to the LLM.
    # ------------------------------------------------------------------
    selected_functions_map = {}   # {package_key: [chosen function names]}
    if custom_packages_info:
        st.markdown("### 🔎 Choose Functions to Use")
        st.caption("Pick exactly which functions from each package/script the AI is allowed to use. Descriptions are shown below each selector.")
        for idx, info in enumerate(custom_packages_info):
            # Stable key for widget state across reruns
            pkg_key = info.get("url") or info.get("filename") or f"{info.get('name','pkg')}_{idx}"

            if info.get("type") == "script":
                st.markdown(f"📄 **Script File:** `{info['name']}`")
            elif info.get("type") == "github_package":
                if "error" in info:
                    st.markdown(f"❌ **GitHub Package error (`{info['name']}`):** {info['error']}")
                    st.markdown("---")
                    continue
                st.markdown(f"🐙 **GitHub Package:** [{info['name']}]({info.get('url','')})")
            else:
                st.markdown(f"📦 **R Package:** `{info['name']}` (from `{info.get('filename','')}`)")

            if info.get("description"):
                st.caption(info["description"])

            functions = info.get("functions", [])
            details = info.get("function_details") or [{"name": f, "description": ""} for f in functions]

            if functions:
                st.caption(f"Found **{len(functions)}** functions. Select the ones you want to use:")
                chosen = st.multiselect(
                    "Functions to include:",
                    options=functions,
                    default=functions,
                    key=f"funcsel_{pkg_key}",
                    label_visibility="collapsed",
                )
                selected_functions_map[pkg_key] = chosen

                # Show name -> description so the choice is informed
                with st.expander(f"ℹ️ Function descriptions ({info['name']})", expanded=False):
                    for d in details:
                        desc = d.get("description") or "_No description available._"
                        st.markdown(f"- `{d['name']}` — {desc}")
            else:
                st.markdown("_No functions detected._")
                selected_functions_map[pkg_key] = []
            st.markdown("---")

    # ------------------------------------------------------------------
    # NEW: Let the user choose the *form of presentation* (layout / theme /
    # components) instead of leaving everything to the model.
    # ------------------------------------------------------------------
    st.markdown("### 🎨 App Layout & Presentation")
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
    )
    ui_theme = st.selectbox(
        "Theme (bslib bootswatch):",
        options=["Auto / default", "flatly", "cosmo", "minty", "darkly", "cerulean", "journal", "lux", "sandstone"],
        index=0,
    )
    ui_components = st.multiselect(
        "Components to include on the page:",
        options=[
            "Filter/input sidebar",
            "Value boxes / KPI cards",
            "Interactive plot(s)",
            "Interactive data table (DT/reactable)",
            "Tabs / multiple pages",
            "Download button(s)",
            "Text / summary panel",
        ],
        default=[],
        help="These are passed to the AI as required UI elements. Leave empty to let the AI choose.",
    )

    # Button to generate code
    generate_btn = st.button("🚀 Generate R Shiny Code")

# Main Page Outputs
with col_output:
    st.markdown("### 💻 Generated R Shiny App Code")
    
    if generate_btn:
        # Input Validation
        if not user_prompt.strip():
            st.error("Please enter a prompt first describing what app to build.")
        elif provider != "Ollama" and not api_key:
            st.error(f"Please provide an API Key for {provider} in the sidebar or in your `.env` file.")
        else:
            with st.spinner("Analyzing prompt and generating R code using the R Shiny Knowledge Base..."):
                try:
                    # 1. Load the knowledge base contents
                    kb_content = load_knowledge_base()
                    
                    # 2. Build system and prompt
                    all_packages = list(set(selected_packages + custom_packages))
                    package_inst = ""
                    if all_packages:
                        package_inst = f"\n- Load and use these R packages: {', '.join(all_packages)}\n"
                    
                    custom_pkg_text = ""
                    if custom_packages_info:
                        custom_pkg_text = "\n### USER-SELECTED CUSTOM R PACKAGES & FUNCTIONS:\n"
                        for idx, info in enumerate(custom_packages_info):
                            if info.get("type") == "github_package" and "error" in info:
                                continue
                            pkg_key = info.get("url") or info.get("filename") or f"{info.get('name','pkg')}_{idx}"
                            # Only the functions the user actually selected
                            chosen = selected_functions_map.get(pkg_key, info.get("functions", []))
                            docs = info.get("function_docs", {})

                            def _doc_for(fn):
                                base = re.split(r"\(", fn, 1)[0].strip()
                                return docs.get(base, docs.get(fn, ""))

                            if info.get("type") == "script":
                                custom_pkg_text += f"\nScript File: `{info['name']}`\nSelected Functions (use ONLY these):\n"
                            else:
                                custom_pkg_text += f"\nPackage Name: `{info['name']}`\nDescription: {info.get('description', '')}\nSelected Functions (use ONLY these):\n"
                            if chosen:
                                for func in chosen:
                                    d = _doc_for(func)
                                    custom_pkg_text += f"- `{func}`" + (f" — {d}\n" if d else "\n")
                            else:
                                custom_pkg_text += "- (user selected no specific functions)\n"
                        custom_pkg_text += """
When generating the R Shiny application code:
- If a package from this list is requested or relevant, load it using library(package_name). Prefer the user-selected functions above; do not invent other functions from these packages.
- If a custom script is provided, write appropriate comments to advise the user to source the script (e.g., source("script_name.R")) to access those functions, and write code that utilizes those functions.
"""

                    # NEW: presentation / layout instructions chosen by the user
                    presentation_text = ""
                    layout_lines = []
                    if layout_style and not layout_style.startswith("Auto"):
                        layout_lines.append(f"- Use this layout style: {layout_style}.")
                    if ui_theme and not ui_theme.startswith("Auto"):
                        layout_lines.append(f"- Apply the bslib bootswatch theme '{ui_theme}' via bs_theme(bootswatch = \"{ui_theme}\").")
                    if ui_components:
                        layout_lines.append("- The page MUST include these components: " + ", ".join(ui_components) + ".")
                    if layout_lines:
                        presentation_text = "\n### USER-REQUESTED PRESENTATION / LAYOUT:\n" + "\n".join(layout_lines) + "\n"

                    
                    system_instruction = f"""You are a senior R Shiny developer.
Your task is to write a high-quality R Shiny application based on the user's requirements.
You MUST strictly follow the conventions, layouts, design patterns, and performance/security guidelines described in the R Shiny Agent Knowledge Base below.

### R SHINY AGENT KNOWLEDGE BASE:
{kb_content}
{custom_pkg_text}
### EXPLICIT CODING DIRECTIONS:
1. Always load the required packages at the top of the code (e.g., using `library()`).
2. Use modern layout packages like `bslib` for styling where appropriate, or as specified in the knowledge base.
3. Write clean, modular, and reactive code.
4. Output ONLY the complete R code file content. Do not include markdown code block syntax (like ```r or ```) in your output—output raw R code only. No introductory or concluding text, just valid R code.
"""

                    prompt = f"""Generate an R Shiny application code based on the following user requirements:
{user_prompt}
{package_inst}
{presentation_text}
Remember to return ONLY the raw R code with no markdown wrapping or explanations.
"""
                    
                    # 3. Call LLM API
                    raw_output = call_llm(
                        provider=provider,
                        model_name=model_name,
                        system_instruction=system_instruction,
                        prompt=prompt,
                        api_key=api_key,
                        ollama_host=ollama_host
                    )
                    
                    # 4. Clean code
                    cleaned_code = clean_r_code(raw_output)
                    
                    # Save results to session state
                    st.session_state.generated_code = cleaned_code
                    st.success("App code generated successfully!")
                    
                except Exception as e:
                    st.error(f"Failed to generate application code: {str(e)}")
                    if hasattr(e, 'response') and e.response is not None:
                        st.code(e.response.text, language="json")
    
    # Code display section
    if "generated_code" in st.session_state:
        # Code block representation
        st.code(st.session_state.generated_code, language="r")
        
        # Download button
        st.download_button(
            label="💾 Download app.R",
            data=st.session_state.generated_code,
            file_name="app.R",
            mime="text/plain"
        )
    else:
        st.info("Fill out the prompt and configurations on the left, then click 'Generate R Shiny Code' to view output.")
