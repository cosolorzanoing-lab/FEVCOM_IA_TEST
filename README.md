# FEVCOM AI

Streamlit chatbot for industrial maintenance troubleshooting using the current OpenAI Responses API. It supports login, per-user permissions, vector-store manual lookup, web fallback for exact component manuals, and in-page PDF viewing for manuals or electrical diagrams.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```text
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4.1
OPENAI_SMART_MODEL=gpt-5.5
OPENAI_VECTOR_STORE_IDS=vs_your_manuals_store,vs_your_diagrams_store
```

The API key must be allowed to call the Responses API. If you use a restricted
OpenAI key, enable the `api.responses.write` scope. The OpenAI account also needs
an organization role with write access, such as Writer or Owner, and project
membership such as Member or Owner.

## Users and permissions

The bundled `config/users.yaml` includes demo logins so you can test immediately:

- `admin` / `admin123`
- `technician` / `tech123`

Set real passwords before production use:

```powershell
python manage_users.py set-password admin "change-this-admin-password"
python manage_users.py set-password technician "change-this-tech-password"
```

Add or change users:

```powershell
python manage_users.py add-user maria --role technician
python manage_users.py set-permission maria use_web_search true
python manage_users.py set-permission maria use_smart_model true
python manage_users.py set-permission maria view_diagrams false
python manage_users.py list-users
```

Permission flags:

- `use_smart_model`: lets the user switch from `OPENAI_MODEL` to `OPENAI_SMART_MODEL`.
- `use_web_search`: allows internet fallback when vector/manual data does not contain the exact component.
- `view_diagrams`: allows opening electrical diagram PDFs in the page.
- `manage_users`: reserved for future in-app admin controls; use `manage_users.py` now.
- `upload_images`: reserved for adding photo or nameplate upload controls.

## Run

```powershell
streamlit run app.py
```

The app opens with a login screen. After login, the bottom chat input is where technicians describe symptoms, fault codes, measurements, manuals, components, or diagram references.

## Manuals, vector data, and diagrams

Upload your manuals and electrical diagram PDFs to an OpenAI vector store, then put the vector store IDs in `OPENAI_VECTOR_STORE_IDS`.

For in-page PDF opening, also add matching records to `config/doc_index.yaml`. The vector store is for AI retrieval; the doc index tells Streamlit where to open the PDF and which page to show.

The app also has a local file library. Put files in:

```text
data/manuals
data/diagrams
data/uploads
```

Admins can upload PDFs, text files, Markdown, or CSV files from the sidebar. When a user asks about a filename or obvious filename terms, the app extracts readable text from matching local files and sends that context to the Responses API before asking the user for more details. PDF text extraction works best on searchable PDFs; scanned image-only PDFs need OCR before the text can be read.

For deployment, OpenAI vector stores should be the durable knowledge base. The sidebar includes an "OpenAI vector store files" browser that lists files attached to the configured vector stores and shows each `file_id`.

Important limitation: files uploaded for OpenAI file search may have purpose `assistants`. Those files are searchable through vector stores, but OpenAI may block downloading the original bytes with an error such as `Not allowed to download files of purpose: assistants`. In that case, the app falls back to showing extracted vector-store text. For an actual in-page PDF viewer, keep a PDF copy in persistent app storage, cloud storage, or another downloadable source, then link it in `config/doc_index.yaml`.

Example:

```yaml
documents:
  - component: "MTR-101"
    kind: "diagram"
    title: "Line 2 Conveyor Electrical Diagram"
    source: "local"
    path: "data/diagrams/line-2-conveyor.pdf"
    page: 7
    aliases: ["main conveyor motor"]
    marker:
      x_pct: 52
      y_pct: 38
      w_pct: 8
      h_pct: 5
```

The viewer uses `#page=` to open the PDF on the target page. If `marker` percentages are configured, the app overlays a red indicator near that component. For best accuracy, store page, zone, and marker metadata next to the same file/component in your vector data.

If vector search cannot find a requested manual and the signed-in user has `use_web_search`, the app enables the Responses API `web_search` tool and prompts the model to search only for the exact same manufacturer, component, model, and revision.

## Where to adjust things later

- Model: change `OPENAI_MODEL`, `OPENAI_SMART_MODEL`, or the `selected_model()` function in `app.py`.
- Prompt: edit `SYSTEM_PROMPT` in `app.py`.
- Vector search: edit `VECTOR_STORE_IDS`, `build_tools()`, and `max_num_results` in `app.py`.
- Local file access: edit `DOCUMENT_ROOTS`, `SUPPORTED_FILE_EXTENSIONS`, `find_local_file_matches()`, and `read_local_file_excerpt()` in `app.py`.
- OpenAI file browser: edit `list_openai_vector_files()`, `download_openai_file_bytes()`, and `render_openai_file()` in `app.py`.
- Web search: edit the `{"type": "web_search"}` entry in `build_tools()`; add filters there if you want approved manufacturer domains only.
- Image settings: add a Streamlit file uploader and pass uploaded images as Responses API image inputs. The `upload_images` permission flag is already reserved for that control.
- PDF page and component indicator: update `config/doc_index.yaml`; use `marker.x_pct`, `marker.y_pct`, `marker.w_pct`, and `marker.h_pct`.

## Validation plan

1. Authentication: verify invalid passwords fail, then log in as `technician` and `admin`.
2. Permissions: confirm the technician cannot toggle the smart model or use web fallback unless the flags are enabled.
3. Responses API: ask a basic fault question and confirm the code path uses `client.responses.create`, not Chat Completions.
4. Vector manuals: upload a known manual to the vector store, ask for that exact component manual, and confirm the answer cites vector/manual content first.
5. Web fallback: ask for a manual absent from vector data as a user with `use_web_search=true`; verify the answer states whether the component match is exact.
6. Diagram viewer: add a test PDF to `config/doc_index.yaml`, ask for its component, and confirm it opens in the right-side panel on the configured page.
7. Marker: add marker percentages and confirm the red box appears near the expected component location.
8. Safety behavior: ask for live electrical troubleshooting and confirm the assistant asks for LOTO/PPE/site procedure confirmation before invasive steps.

## Deployment notes

- Store `OPENAI_API_KEY` and other environment variables in your hosting provider secrets, not in source control.
- For restricted OpenAI keys, include `api.responses.write`; add vector-store/file-search scopes too if you enable manual retrieval.
- Use HTTPS and a real identity provider for production. The included YAML login is suitable for prototypes and small internal demos.
- Keep `config/users.yaml` and local PDFs in protected storage. Manuals and diagrams often contain plant-specific information.
- Pin dependency versions after acceptance testing.
- For Streamlit Community Cloud, put secrets in the app settings and avoid local-only PDF paths unless the files are deployed with the app.

## OpenAI API references

This app follows the Responses API pattern described in the OpenAI API reference, including `client.responses.create(...)`, `instructions`, `previous_response_id`, `tools`, and `include`. File search uses `{"type": "file_search", "vector_store_ids": [...]}`. Web fallback uses the current `{"type": "web_search"}` tool for new Responses API integrations.
