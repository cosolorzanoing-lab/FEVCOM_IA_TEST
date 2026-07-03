import base64
import hashlib
import hmac
import os
from pathlib import Path
from typing import Any

import streamlit as st
import yaml
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader


APP_ROOT = Path(__file__).parent
load_dotenv(APP_ROOT / ".env", override=True)

USERS_FILE = Path(os.getenv("FEVCOM_USERS_FILE", "config/users.yaml"))
DOC_INDEX_FILE = Path(os.getenv("FEVCOM_DOC_INDEX", "config/doc_index.yaml"))
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
SMART_MODEL = os.getenv("OPENAI_SMART_MODEL", "gpt-5.5")
VECTOR_STORE_IDS = [
    value.strip()
    for value in os.getenv("OPENAI_VECTOR_STORE_IDS", "").split(",")
    if value.strip()
]
DOCUMENT_ROOTS = [
    APP_ROOT / "data" / "manuals",
    APP_ROOT / "data" / "diagrams",
    APP_ROOT / "data" / "uploads",
]
SUPPORTED_FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".csv"}


SYSTEM_PROMPT = """Eres FEVCOM AI, un asistente para resolver problemas de mantenimiento industrial.
Asume que el usuario tiene conocimientos basicos de electricidad y mecanica, pero mantenlo seguro.

Metodo de trabajo:
- Empieza identificando la maquina, sintoma, codigo de falla, estado de operacion, cambios recientes.
- Guia al tecnico con una prueba a la vez. Pide mediciones u observaciones cuando sea util.
- Da pasos concisos, lecturas esperadas, causas probables y que significa el siguiente resultado.
- Cuando la maquina quede reparada, resume causa raiz, reparacion y prevencion.

Manuales y diagramas:
- Si el usuario pide un manual o un componente en un diagrama electrico, usa primero los datos vectoriales.
- Si los datos vectoriales no son suficientes y hay busqueda web disponible, busca exactamente el mismo componente, modelo, revision y fabricante. No sustituyas por un componente similar sin decir que no es exacto.
- Al referenciar PDFs, incluye titulo, componente exacto, numero de pagina si se conoce y cualquier localizador/zona/coordenadas disponibles.
- Para diagramas electricos, da claramente los datos utiles para la app: titulo del PDF, nombre de archivo o URL, pagina y localizador del componente.
- Responde siempre en español, salvo que el usuario pida explicitamente otro idioma.
"""

TRANSLATIONS = {
    "en": {
        "subtitle_login": "Industrial maintenance troubleshooting",
        "subtitle_main": "Troubleshoot safely, step by step",
        "sign_in": "Sign in",
        "password_note": "Use `python manage_users.py set-password admin <password>` before production use.",
        "user": "User",
        "password": "Password",
        "log_in": "Log in",
        "invalid_login": "Invalid user or password.",
        "signed_in_as": "Signed in as",
        "role": "Role",
        "openai_key": "OpenAI key",
        "use_smart_model": "Use smarter model",
        "model": "Model",
        "enabled_tools": "Enabled tools",
        "vector_file_search": "Vector file search",
        "web_fallback": "Web fallback",
        "diagram_viewer": "Diagram viewer",
        "local_files": "Local files",
        "no_local_files": "No files yet. Add PDFs or text files under `data/manuals`, `data/diagrams`, or `data/uploads`.",
        "more_files": "...and {count} more",
        "add_local_file": "Add local file",
        "saved": "Saved {path}",
        "openai_vector_files": "OpenAI vector store files",
        "set_vector_ids": "Set `OPENAI_VECTOR_STORE_IDS` in `.env` or Streamlit secrets.",
        "set_api_key_browse": "Set `OPENAI_API_KEY` before browsing OpenAI files.",
        "files_attached": "Files attached to configured OpenAI vector stores.",
        "refresh_openai_files": "Refresh OpenAI file list",
        "click_refresh": "Click refresh to load the OpenAI file list.",
        "openai_file": "OpenAI file",
        "file_id": "File ID",
        "vector_store": "Vector store",
        "open_selected": "Open selected OpenAI file",
        "new_session": "New troubleshooting session",
        "log_out": "Log out",
        "manuals_diagrams": "Manuals and diagrams",
        "matched_local_files": "Matched local files:",
        "matching_pdfs": "Matching PDFs from `config/doc_index.yaml` will appear here.",
        "no_diagram_access": "This user does not have diagram access.",
        "chat_placeholder": "Describe the machine, symptom, fault code, or component...",
        "missing_key": "OPENAI_API_KEY is not set. Add it to `.env` or your environment, then refresh the page. If you set it outside `.env`, restart Streamlit.",
        "spinner": "Checking manuals, diagrams, and the troubleshooting path...",
        "not_configured": "not configured",
        "configured": "configured",
        "vector_no_text": "OpenAI returned no extracted text for this vector-store file.",
        "vector_text_preview": "OpenAI vector-store text preview",
        "file_download_blocked": "This file is stored for OpenAI file search, so OpenAI does not allow downloading the original PDF bytes from the Files API. Showing the extracted vector-store text instead. To open the real PDF viewer in production, keep a PDF copy in app storage, cloud storage, or another downloadable file source and link it in `config/doc_index.yaml`.",
        "download_file": "Download file",
        "binary_download": "This OpenAI file is not a PDF or readable UTF-8 text, so it is available as a download.",
        "openai_file_preview": "OpenAI file preview",
        "pdf_not_found": "PDF configured but not found: {path}",
        "api_key_not_configured": "OPENAI_API_KEY is not configured.",
        "vector_ids_empty": "OPENAI_VECTOR_STORE_IDS is empty.",
        "local_context_intro": "The app found these local files that appear to match the user's request. Use this local file content before asking for more details. If the excerpt is insufficient, say exactly what is missing.",
    },
    "es": {
        "subtitle_login": "Diagnostico de mantenimiento industrial",
        "subtitle_main": "Diagnostico seguro, paso a paso",
        "sign_in": "Iniciar sesion",
        "password_note": "Usa `python manage_users.py set-password admin <password>` antes de usarlo en produccion.",
        "user": "Usuario",
        "password": "Contraseña",
        "log_in": "Entrar",
        "invalid_login": "Usuario o contraseña invalido.",
        "signed_in_as": "Sesion iniciada como",
        "role": "Rol",
        "openai_key": "Clave OpenAI",
        "use_smart_model": "Usar modelo mas inteligente",
        "model": "Modelo",
        "enabled_tools": "Herramientas activas",
        "vector_file_search": "Busqueda en archivos vectoriales",
        "web_fallback": "Busqueda web de respaldo",
        "diagram_viewer": "Visor de diagramas",
        "local_files": "Archivos locales",
        "no_local_files": "Aun no hay archivos. Agrega PDFs o textos en `data/manuals`, `data/diagrams` o `data/uploads`.",
        "more_files": "...y {count} mas",
        "add_local_file": "Agregar archivo local",
        "saved": "Guardado {path}",
        "openai_vector_files": "Archivos del vector store de OpenAI",
        "set_vector_ids": "Configura `OPENAI_VECTOR_STORE_IDS` en `.env` o en los secretos de Streamlit.",
        "set_api_key_browse": "Configura `OPENAI_API_KEY` antes de explorar archivos de OpenAI.",
        "files_attached": "Archivos adjuntos a los vector stores configurados.",
        "refresh_openai_files": "Actualizar lista de archivos OpenAI",
        "click_refresh": "Haz clic en actualizar para cargar la lista de archivos OpenAI.",
        "openai_file": "Archivo OpenAI",
        "file_id": "ID de archivo",
        "vector_store": "Vector store",
        "open_selected": "Abrir archivo OpenAI seleccionado",
        "new_session": "Nueva sesion de diagnostico",
        "log_out": "Cerrar sesion",
        "manuals_diagrams": "Manuales y diagramas",
        "matched_local_files": "Archivos locales encontrados:",
        "matching_pdfs": "Aqui apareceran los PDFs encontrados en `config/doc_index.yaml`.",
        "no_diagram_access": "Este usuario no tiene acceso a diagramas.",
        "chat_placeholder": "Describe la maquina, sintoma, codigo de falla o componente...",
        "missing_key": "OPENAI_API_KEY no esta configurada. Agregala en `.env` o en el entorno y refresca la pagina. Si la configuraste fuera de `.env`, reinicia Streamlit.",
        "spinner": "Revisando manuales, diagramas y ruta de diagnostico...",
        "not_configured": "no configurada",
        "configured": "configurada",
        "vector_no_text": "OpenAI no regreso texto extraido para este archivo del vector store.",
        "vector_text_preview": "Vista previa del texto del vector store OpenAI",
        "file_download_blocked": "Este archivo esta almacenado para busqueda de archivos en OpenAI, por eso OpenAI no permite descargar los bytes originales del PDF desde la API de archivos. Se muestra el texto extraido del vector store. Para abrir el PDF real en produccion, conserva una copia del PDF en el almacenamiento de la app, almacenamiento en la nube u otra fuente descargable y enlazala en `config/doc_index.yaml`.",
        "download_file": "Descargar archivo",
        "binary_download": "Este archivo OpenAI no es PDF ni texto UTF-8 legible, asi que queda disponible como descarga.",
        "openai_file_preview": "Vista previa del archivo OpenAI",
        "pdf_not_found": "PDF configurado pero no encontrado: {path}",
        "api_key_not_configured": "OPENAI_API_KEY no esta configurada.",
        "vector_ids_empty": "OPENAI_VECTOR_STORE_IDS esta vacio.",
        "local_context_intro": "La app encontro estos archivos locales que parecen coincidir con la solicitud del usuario. Usa este contenido local antes de pedir mas detalles. Si el extracto no es suficiente, di exactamente que falta.",
    },
}


st.set_page_config(page_title="FEVCOM AI", page_icon="FEVCOM", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --fevcom-bg: #0b1117;
        --fevcom-panel: #111a22;
        --fevcom-line: #2e4656;
        --fevcom-accent: #e8b84b;
        --fevcom-muted: #a7b7c2;
    }
    .stApp {
        background: var(--fevcom-bg);
        color: #f5f8fb;
    }
    header[data-testid="stHeader"] {
        background: transparent;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 6rem;
        max-width: 1280px;
    }
    .fevcom-top {
        position: sticky;
        top: 0;
        z-index: 99;
        background: #05080c;
        border-bottom: 1px solid var(--fevcom-line);
        padding: 18px 24px;
        margin: -1rem -1rem 1rem -1rem;
    }
    .fevcom-title {
        color: white;
        font-size: 30px;
        font-weight: 800;
        letter-spacing: 0;
    }
    .fevcom-subtitle {
        color: var(--fevcom-muted);
        font-size: 13px;
        margin-top: 2px;
    }
    div[data-testid="stChatInput"] {
        background: #05080c;
        border-top: 1px solid var(--fevcom-line);
        padding: 12px 10px;
    }
    div[data-testid="stSidebar"] {
        background: var(--fevcom-panel);
        border-right: 1px solid var(--fevcom-line);
    }
    .pdf-frame {
        width: 100%;
        height: 760px;
        border: 1px solid var(--fevcom-line);
        border-radius: 8px;
        background: #ffffff;
    }
    .marker-box {
        position: absolute;
        border: 3px solid #e53935;
        background: rgba(229, 57, 53, 0.14);
        pointer-events: none;
        z-index: 5;
    }
    .pdf-wrap {
        position: relative;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_yaml(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or default


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, rounds, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(rounds)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except ValueError:
        return False


def user_can(permission: str) -> bool:
    user = st.session_state.get("user", {})
    return bool(user.get("permissions", {}).get(permission))


def login_screen() -> None:
    st.markdown(
        '<div class="fevcom-top"><div class="fevcom-title">FEVCOM AI</div>'
        '<div class="fevcom-subtitle">Industrial maintenance troubleshooting</div></div>',
        unsafe_allow_html=True,
    )
    st.subheader("Sign in")
    st.caption("Use `python manage_users.py set-password admin <password>` before production use.")
    with st.form("login"):
        username = st.text_input("User")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if not submitted:
        return

    users = load_yaml(USERS_FILE, {"users": {}}).get("users", {})
    record = users.get(username)
    if not record or not verify_password(password, record.get("password_hash", "")):
        st.error("Invalid user or password.")
        return

    st.session_state.user = {"username": username, **record}
    st.session_state.messages = []
    st.session_state.previous_response_id = None
    st.rerun()


def build_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    if VECTOR_STORE_IDS:
        tools.append(
            {
                "type": "file_search",
                "vector_store_ids": VECTOR_STORE_IDS,
                "max_num_results": 8,
            }
        )
    if user_can("use_web_search"):
        tools.append({"type": "web_search"})
    return tools


def selected_model() -> str:
    if user_can("use_smart_model") and st.session_state.get("use_smart_model"):
        return SMART_MODEL
    return DEFAULT_MODEL


def openai_api_key_is_configured() -> bool:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    placeholders = {"", "replace-with-your-openai-api-key", "sk-your-key-here"}
    return api_key not in placeholders


def redacted_openai_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key_is_configured():
        return "not configured"
    if len(api_key) <= 12:
        return "configured"
    return f"{api_key[:7]}...{api_key[-4:]}"


def find_index_matches(query: str, kind: str | None = None) -> list[dict[str, Any]]:
    index = load_yaml(DOC_INDEX_FILE, {"documents": []})
    documents = index.get("documents") or []
    needle = query.lower()
    matches = []
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        if kind and doc.get("kind") != kind:
            continue
        terms = [doc.get("component", ""), doc.get("title", ""), *doc.get("aliases", [])]
        if any(term and term.lower() in needle for term in terms):
            matches.append(doc)
    return matches


def iter_local_files() -> list[Path]:
    files: list[Path] = []
    for root in DOCUMENT_ROOTS:
        root.mkdir(parents=True, exist_ok=True)
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED_FILE_EXTENSIONS:
                files.append(path)
    return sorted(files, key=lambda item: str(item.relative_to(APP_ROOT)).lower())


def find_local_file_matches(query: str) -> list[Path]:
    needle = query.lower()
    matches = []
    for path in iter_local_files():
        rel = str(path.relative_to(APP_ROOT)).lower()
        if path.name.lower() in needle or any(part.lower() in needle for part in path.stem.split()):
            matches.append(path)
            continue
        if rel in needle:
            matches.append(path)
    return matches[:4]


def read_local_file_excerpt(path: Path, max_chars: int = 6000) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            chunks = []
            for page_number, page in enumerate(reader.pages[:8], start=1):
                text = page.extract_text() or ""
                if text.strip():
                    chunks.append(f"[Page {page_number}]\n{text.strip()}")
                if sum(len(chunk) for chunk in chunks) >= max_chars:
                    break
            return "\n\n".join(chunks)[:max_chars]
        if suffix in {".txt", ".md", ".csv"}:
            return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception as exc:
        return f"Could not read {path.name}: {exc}"
    return ""


def local_file_context(prompt: str) -> tuple[str, list[Path]]:
    matches = find_local_file_matches(prompt)
    if not matches:
        return "", []
    sections = []
    for path in matches:
        rel = path.relative_to(APP_ROOT)
        excerpt = read_local_file_excerpt(path)
        if excerpt.strip():
            sections.append(f"Local file: {rel}\nReadable excerpt:\n{excerpt}")
        else:
            sections.append(f"Local file: {rel}\nNo readable text could be extracted.")
    return "\n\n---\n\n".join(sections), matches


def local_pdf_to_data_url(path: Path) -> str:
    pdf_bytes = path.read_bytes()
    encoded = base64.b64encode(pdf_bytes).decode("ascii")
    return f"data:application/pdf;base64,{encoded}"


def bytes_to_data_url(file_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(file_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def binary_response_to_bytes(response: Any) -> bytes:
    if hasattr(response, "read"):
        return response.read()
    content = getattr(response, "content", None)
    if isinstance(content, bytes):
        return content
    if isinstance(response, bytes):
        return response
    raise TypeError("OpenAI file content response did not contain readable bytes.")


def openai_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def list_openai_vector_files() -> tuple[list[dict[str, Any]], str | None]:
    if not openai_api_key_is_configured():
        return [], "OPENAI_API_KEY is not configured."
    if not VECTOR_STORE_IDS:
        return [], "OPENAI_VECTOR_STORE_IDS is empty."

    client = openai_client()
    records: list[dict[str, Any]] = []
    try:
        for vector_store_id in VECTOR_STORE_IDS:
            page = client.vector_stores.files.list(
                vector_store_id=vector_store_id,
                limit=100,
            )
            for vector_file in page.data:
                file_id = vector_file.id
                file_info = client.files.retrieve(file_id)
                filename = getattr(file_info, "filename", file_id)
                records.append(
                    {
                        "vector_store_id": vector_store_id,
                        "file_id": file_id,
                        "filename": filename,
                        "status": getattr(vector_file, "status", "unknown"),
                        "bytes": getattr(file_info, "bytes", None),
                        "purpose": getattr(file_info, "purpose", None),
                    }
                )
    except Exception as exc:
        return records, format_openai_error(exc)
    return records, None


def download_openai_file_bytes(file_id: str) -> bytes:
    response = openai_client().files.content(file_id)
    return binary_response_to_bytes(response)


def openai_vector_file_text(record: dict[str, Any], max_chars: int = 12000) -> str:
    client = openai_client()
    page = client.vector_stores.files.content(
        file_id=record["file_id"],
        vector_store_id=record["vector_store_id"],
    )
    chunks = []
    for item in getattr(page, "data", []) or []:
        text = getattr(item, "text", None)
        if text:
            chunks.append(text)
        if sum(len(chunk) for chunk in chunks) >= max_chars:
            break
    return "\n\n---\n\n".join(chunks)[:max_chars]


def render_openai_vector_text(record: dict[str, Any], reason: str | None = None) -> None:
    if reason:
        st.info(reason)
    try:
        text = openai_vector_file_text(record)
    except Exception as exc:
        st.error(format_openai_error(exc))
        return
    if not text.strip():
        st.warning("OpenAI returned no extracted text for this vector-store file.")
        return
    st.text_area("OpenAI vector-store text preview", text, height=420)


def render_openai_file(record: dict[str, Any]) -> None:
    filename = record.get("filename") or record.get("file_id")
    file_id = record["file_id"]
    st.markdown(f"**{filename}**")
    st.caption(f"OpenAI file: `{file_id}`")
    try:
        file_bytes = download_openai_file_bytes(file_id)
    except Exception as exc:
        message = str(exc)
        if "Not allowed to download files of purpose: assistants" in message:
            render_openai_vector_text(
                record,
                "This file is stored for OpenAI file search, so OpenAI does not allow "
                "downloading the original PDF bytes from the Files API. Showing the "
                "extracted vector-store text instead. To open the real PDF viewer in "
                "production, keep a PDF copy in app storage, cloud storage, or another "
                "downloadable file source and link it in `config/doc_index.yaml`.",
            )
            return
        st.error(format_openai_error(exc))
        return

    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        url = bytes_to_data_url(file_bytes, "application/pdf")
        st.markdown(
            f'<iframe class="pdf-frame" src="{url}#page=1"></iframe>',
            unsafe_allow_html=True,
        )
        return

    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        st.download_button(
            "Download file",
            data=file_bytes,
            file_name=filename,
            mime="application/octet-stream",
        )
        st.info("This OpenAI file is not a PDF or readable UTF-8 text, so it is available as a download.")
        return

    st.text_area("OpenAI file preview", text[:12000], height=420)


def render_pdf(doc: dict[str, Any]) -> None:
    page = int(doc.get("page", 1))
    source = doc.get("source", "local")
    title = doc.get("title", "PDF document")
    url = ""

    if source == "local":
        path = Path(doc.get("path", ""))
        if not path.is_absolute():
            path = APP_ROOT / path
        if not path.exists():
            st.warning(f"PDF configured but not found: {path}")
            return
        url = local_pdf_to_data_url(path)
    else:
        url = doc.get("url", "")

    if not url:
        return

    st.markdown(f"**{title}** - page {page}")
    marker = doc.get("marker") or {}
    marker_html = ""
    if marker:
        marker_html = (
            f'<div class="marker-box" style="left:{marker.get("x_pct", 0)}%;'
            f'top:{marker.get("y_pct", 0)}%;width:{marker.get("w_pct", 8)}%;'
            f'height:{marker.get("h_pct", 5)}%;"></div>'
        )
    st.markdown(
        f'<div class="pdf-wrap">{marker_html}'
        f'<iframe class="pdf-frame" src="{url}#page={page}"></iframe></div>',
        unsafe_allow_html=True,
    )


def response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) == "message":
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", None) == "output_text":
                    chunks.append(getattr(content, "text", ""))
    return "\n".join(chunks).strip()


def format_openai_error(exc: Exception) -> str:
    message = str(exc)
    if "api.responses.write" in message or "Missing scopes" in message:
        return (
            "OpenAI API permission issue: the API key is valid, but it does not have "
            "`api.responses.write`, which is required for the Responses API. Create or update "
            "the key with Responses write access, and make sure your OpenAI organization role "
            "is Writer or Owner and your project role is Member or Owner. Then update `.env` "
            "and restart Streamlit."
        )
    if "401" in message:
        return (
            "OpenAI authentication failed. Check that `OPENAI_API_KEY` is correct, active, "
            "belongs to the project you intend to use, and is not restricted away from the "
            "Responses API."
        )
    if "model" in message.lower() and ("not found" in message.lower() or "access" in message.lower()):
        return (
            f"OpenAI model access issue for `{selected_model()}`. Change `OPENAI_MODEL` or "
            "`OPENAI_SMART_MODEL` in `.env` to a model your project can use, then refresh."
        )
    return f"OpenAI request failed: {message}"


def build_model_input(prompt: str, file_context: str = "") -> str:
    if not file_context:
        return prompt
    return (
        f"{prompt}\n\n"
        "The app found these local files that appear to match the user's request. "
        "Use this local file content before asking for more details. If the excerpt is "
        "insufficient, say exactly what is missing.\n\n"
        f"{file_context}"
    )


def call_openai(prompt: str, file_context: str = "") -> tuple[str, Any]:
    client = OpenAI()
    kwargs: dict[str, Any] = {
        "model": selected_model(),
        "instructions": SYSTEM_PROMPT,
        "input": build_model_input(prompt, file_context),
        "tools": build_tools(),
        "include": ["file_search_call.results"],
        "metadata": {"app": "fevcom-ai", "user": st.session_state.user["username"]},
        "safety_identifier": hashlib.sha256(
            st.session_state.user["username"].encode("utf-8")
        ).hexdigest(),
    }
    if st.session_state.get("previous_response_id"):
        kwargs["previous_response_id"] = st.session_state.previous_response_id
    response = client.responses.create(**kwargs)
    st.session_state.previous_response_id = response.id
    return response_text(response), response


def sidebar() -> None:
    user = st.session_state.user
    st.sidebar.write(f"Signed in as **{user.get('display_name', user['username'])}**")
    st.sidebar.caption(f"Role: {user.get('role', 'user')}")
    st.sidebar.caption(f"OpenAI key: `{redacted_openai_key()}`")
    if user_can("use_smart_model"):
        st.session_state.use_smart_model = st.sidebar.toggle(
            "Use smarter model", value=st.session_state.get("use_smart_model", False)
        )
    st.sidebar.write(f"Model: `{selected_model()}`")
    st.sidebar.write("Enabled tools")
    st.sidebar.checkbox("Vector file search", value=bool(VECTOR_STORE_IDS), disabled=True)
    st.sidebar.checkbox("Web fallback", value=user_can("use_web_search"), disabled=True)
    st.sidebar.checkbox("Diagram viewer", value=user_can("view_diagrams"), disabled=True)

    with st.sidebar.expander("Local files", expanded=False):
        local_files = iter_local_files()
        if not local_files:
            st.caption("No files yet. Add PDFs or text files under `data/manuals`, `data/diagrams`, or `data/uploads`.")
        for path in local_files[:25]:
            st.caption(str(path.relative_to(APP_ROOT)))
        if len(local_files) > 25:
            st.caption(f"...and {len(local_files) - 25} more")

        if user_can("manage_users"):
            uploaded = st.file_uploader(
                "Add local file",
                type=["pdf", "txt", "md", "csv"],
                accept_multiple_files=True,
            )
            for file in uploaded or []:
                target = APP_ROOT / "data" / "uploads" / file.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(file.getbuffer())
                st.success(f"Saved {target.relative_to(APP_ROOT)}")

    with st.sidebar.expander("OpenAI vector store files", expanded=False):
        if not VECTOR_STORE_IDS:
            st.caption("Set `OPENAI_VECTOR_STORE_IDS` in `.env` or Streamlit secrets.")
        elif not openai_api_key_is_configured():
            st.caption("Set `OPENAI_API_KEY` before browsing OpenAI files.")
        else:
            st.caption("Files attached to configured OpenAI vector stores.")
            if st.button("Refresh OpenAI file list"):
                records, error = list_openai_vector_files()
                st.session_state.openai_vector_files = records
                st.session_state.openai_vector_files_error = error

            error = st.session_state.get("openai_vector_files_error")
            if error:
                st.error(error)

            records = st.session_state.get("openai_vector_files", [])
            if not records:
                st.caption("Click refresh to load the OpenAI file list.")
            else:
                options = {
                    f"{item['filename']} ({item['status']})": index
                    for index, item in enumerate(records)
                }
                selected_label = st.selectbox("OpenAI file", list(options.keys()))
                selected_record = records[options[selected_label]]
                st.caption(f"File ID: `{selected_record['file_id']}`")
                st.caption(f"Vector store: `{selected_record['vector_store_id']}`")
                if st.button("Open selected OpenAI file"):
                    st.session_state.active_openai_file = selected_record

    if st.sidebar.button("New troubleshooting session"):
        st.session_state.messages = []
        st.session_state.previous_response_id = None
        st.rerun()
    if st.sidebar.button("Log out"):
        st.session_state.clear()
        st.rerun()


def main_screen() -> None:
    sidebar()
    st.markdown(
        '<div class="fevcom-top"><div class="fevcom-title">FEVCOM AI</div>'
        '<div class="fevcom-subtitle">Troubleshoot safely, step by step</div></div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.58, 0.42], gap="large")
    with left:
        for message in st.session_state.get("messages", []):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    with right:
        st.subheader("Manuals and diagrams")
        active_openai_file = st.session_state.get("active_openai_file")
        if active_openai_file:
            render_openai_file(active_openai_file)
        active_local_files = st.session_state.get("active_local_files", [])
        if active_local_files:
            st.caption("Matched local files:")
            for rel_path in active_local_files:
                st.code(rel_path, language=None)
        active_docs = st.session_state.get("active_docs", [])
        if not active_docs and not active_local_files:
            st.caption("Matching PDFs from `config/doc_index.yaml` will appear here.")
        for doc in active_docs:
            if doc.get("kind") == "diagram" and not user_can("view_diagrams"):
                st.info("This user does not have diagram access.")
                continue
            render_pdf(doc)

    prompt = st.chat_input("Describe the machine, symptom, fault code, or component...")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.active_docs = find_index_matches(prompt)
    file_context, file_matches = local_file_context(prompt)
    st.session_state.active_local_files = [str(path.relative_to(APP_ROOT)) for path in file_matches]

    with st.chat_message("user"):
        st.markdown(prompt)

    if not openai_api_key_is_configured():
        answer = (
            "OPENAI_API_KEY is not set. Add it to `.env` or your environment, "
            "then refresh the page. If you set it outside `.env`, restart Streamlit."
        )
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.error(answer)
        return

    with st.chat_message("assistant"):
        with st.spinner("Checking manuals, diagrams, and the troubleshooting path..."):
            try:
                answer, _ = call_openai(prompt, file_context)
            except Exception as exc:
                answer = format_openai_error(exc)
                st.error(answer)
            else:
                st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()


if "user" not in st.session_state:
    login_screen()
else:
    main_screen()
