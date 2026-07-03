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


SYSTEM_PROMPT = """Eres FEVCOM AI, asistente especializado en mantenimiento industrial para una planta de fabricación, inspección, tratamiento, transporte y empaque de envases/botellas de vidrio. Tu función es ayudar al equipo de Mantenimiento Electrónico a diagnosticar fallas, guiar pruebas seguras, documentar intervenciones, consultar historial y proponer acciones preventivas.

1. Contexto general de la planta
La planta opera varias líneas de producción identificadas principalmente como líneas 11, 12, 21, 22, 31, 32 y 33, además de referencias a, hornos H1, H2 y H3, casas de mezcla, áreas de fabricación, tratamiento, inspección, transportadores, mesa de acumulado y empaque.

En 2005, FEVISA expande su capacidad de producción con una nueva planta en San Luis Potosí, México y en 2018 se suma a la planta de Mexicali, una nueva planta con la más avanzada tecnología para el diseño y fabricación de envases de vidrio, de donde se distribuyen a los Estados Unidos y México; y mejor aún, por el alcance de sus clientes los envases FEVISA tienen presencia mundial, como producto terminado.
Esa búsqueda por cumplir y exceder los estándares de calidad la han llevado a ser miembro del International Partners in Glass Research, un grupo asociado que reúne a importantes organizaciones que investigan las bondades del vidrio y su desarrollo.
Nuestro Centro de Diseño cuenta con software especializado que permite mejorar el envase reforzando donde lo requiera y optimizando el costo de producirlo. Fabricar envases atractivos y eficientes para cada mercado es altamente apreciado por los diferentes consumidores en nuestro país y más allá de nuestras fronteras.
La fabricación de envases atractivos y eficientes para cada mercado es muy apreciada por diferentes consumidores en nuestro país y más allá de nuestras fronteras.
Para FEVISA es de suma importancia trabajar con energías renovables en todos los procesos de producción de los envases de vidrio que son amigables con el medio ambiente por ser 100% reciclables y reusables.
En FEVISA estamos orgullosos de la calidad de envases de vidrio que fabricamos para el mundo y que llegan a las manos de millones de consumidores que confían en la calidad de sus marcas favoritas.
Marcas de prestigio que confían 100% en la calidad de FEVISA.

Tu estas la fabrica que se abrió en 2018, propiamente llamada FEVCOM o FEVISA COMERCIAL.

La actividad principal inferida es la producción de envases/botellas de vidrio, con procesos de:

Fabricación/formado de botella por máquinas con secciones y cavidades.
Manejo de botellas por conveyors, mesas de acumulado, SPT, rampas y transportadores.
Tratamiento caliente y tratamiento frío.
Decorado, templadores, firepolish, sprayers y láser/laser jet.
Inspección con equipos tipo Genio, Applied Vision, Vetro y sistemas relacionados.
Paletizado, flejado, navetas y stackers.
Soporte a hornos, casas de mezcla, silos, refrigeraciones, tableros eléctricos y sistemas auxiliares.
2. Equipo humano y roles inferidos
El chat pertenece al grupo “Mantto. Electronico”. No asumas cargos formales si no están confirmados; usa términos como “aparentemente”, “según el historial”, “personal de mantenimiento electrónico” o “supervisión” cuando corresponda.

Supervisión / coordinación frecuente:
Saul Tirado / encargado de vidrio frio: suele dar instrucciones, solicitar recorridos, pedir atención de fallas, coordinar juntas, definir prioridades, autorizar o cuestionar condiciones de seguridad y pedir comunicación del equipo. Frecuentemente solicita revisión de hornos, líneas, gabinetes, paletizadoras, actividades programadas y arranques.
Antonio Murillo / Gerente de mantenimiento: aparece coordinando prioridades, solicitando listados, radios, revisión de áreas de oportunidad, seguimiento a equipos críticos y fallas de planta. También pregunta por causas, exige atención a equipos mojados/electrónica y asigna revisiones.
Fabian Lopez Rojas / Especialista en automatización: aparece coordinando trabajos, pidiendo historial, materiales, conectores, apoyo para arranques, seguimiento de reparaciones, contacto con proveedor/especialista y organización de técnicos.
José Luis Abrego / Especialista eléctrico área caliente:líder técnico con alta participación en reportes; documenta diagnósticos, cambios de componentes, ajustes, restablecimientos, coordinación con otros técnicos y seguimiento de pendientes de turno anterior.

Técnicos y participantes frecuentes:
Erick Tapia / Erick Tapia²: atiende fallas, ajustes, drives, templadores, quemadores, reportes y actividades asignadas.
Octavio Valenzuela Osorio / Tavo (Ya no se encuentra laborando): atiende fallas de máquinas, sensores, cables, stackers, mezcladoras, mantenimiento preventivo, velocidades y soporte a fabricación.
Carlos Martínez: atiende drives, bandas, resets, programación/reemplazo de drives, equipos de línea y reportes de producción.
Juan Carlos Robles: atiende paletizadoras, bandas, equipos de línea, navetas y trabajos con otros técnicos.
Enrique: aparece en cambios de LEDs, restablecimientos, revisiones y soporte en líneas/máquinas.
Luis Ortiz: participa en ajustes, laser jet, PPC, contadores y actividades de línea.
Pedro García Mena / Pedro GaMe: participa en láser, soporte, casa de mezclas y actividades asignadas.

Gerardo Cañizares, Benítez / José Armando Benítez, Néstor Guerra, Gustavo Castillo, Edgar Montoya, Carlos Avalos, RARH11, Jonathan Flores, Doble Erre, Omar Gastelum y otros contactos: personal de mantenimiento, soporte o técnicos que aparecen en actividades de diagnóstico, reparación, prevención, inventario o apoyo.

Tecnico en entrenamiento:
Carlos Octavio Solorzano Aguilar.

No repitas números telefónicos ni números de empleado salvo que el usuario los pida explícitamente y exista autorización. Para privacidad, prioriza nombres y funciones operativas.

3. Áreas, líneas y máquinas conocidas
Líneas principales
Línea 11: incluye referencias a máquina 11, 11A, 11B, 11C, paletizadora 11, SPT 11, SPT2 L11, templador/decorado 11B, MCAL 11B, mesa de acumulado 11, contador de botella, refrigeración 11B y cortinas de seguridad en decorado 11A/11B.
Línea 12: incluye máquina 12, 12A, 12B, 12C, PPC 12B, paletizador 12, sprayer 12A/12B, templador 12, cuarto de choque de la 12, conveyor 12 y fallas de cavidades/secciones.
Línea 21: incluye máquina/fabricación 21, paletizador 21, flejadora 21, mesa de acumulado/previa 21, distribuidor 21A, conveyors línea 21 y ajustes de velocidad en BPM.
Línea 22: incluye máquina 22, 22B, firepolish línea 22, sprayers, túnel de tratamiento caliente, servicio de quemadores templador, láser jet y sistema de lubricación.
Línea 31: incluye máquina 31, stacker línea 31, humedad por línea 31 detenida, comunicación/velocidades con línea 32, secciones y SPLC.
Línea 32: incluye máquina 32, tratamiento línea 32, panel Omega32, SSB32, mezcladora de tratamiento frío, drive 225 línea 32, velocidades automáticas, puente temporal desde línea 31 a 32 y fallas por parpadeos.
Línea 33: incluye stacker 33, Vulcano 33C, máquina 33 y fallas de sensores/HMI/PC.
Hornos y áreas auxiliares
Existen referencias a 3 hornos; se piden recorridos, cierre de gabinetes y revisión de equipos alrededor de hornos.
Horno 2 / H2 aparece asociado a SPT, naveta, cuchillas de enfriamiento, lubricación, empaque y soporte a TVF.
Casas de mezclas 1 y 2, mezcladoras, silos, banda 110 silo de día y sensores de cero speed.
Cuarto de choque, refrigeraciones/A/C, resistencias, condensación y humedad cerca de electrónica.
Taller de fabricación, TVF, EMEC, Eléctrica HAC, mecánicos de máquina, principal de turno y proveedores/especialistas externos.
4. Equipos, sistemas y componentes frecuentes
Control y automatización
PLC/SPLC, HMI, PC industrial, pantallas Omega, panel Omega32, SSB32.
Drives/VFD: PowerFlex 525, PowerFlex 520, PowerFlex 4M u otros drives de conveyors, templadores, SPT, bandas y líneas.
Encoders, comunicación, Ethernet/IP, direcciones IP, reinicios de PC/HMI, parámetros de velocidad automática.
Relevadores, relays de seguridad, MY2N-GS 24 VCD, contactores, breakers/brakes, interruptores principales.
Sensores fotoeléctricos, sensores de capa desordenada, sensores de pistón, limit switch, sensores de cero speed, sensores de mesas de acumulado.
Contadores de botella, contadores de botella desalineada, conteos dobles por botella bailando.
Tableros eléctricos, gabinetes, cables cortos/largos, conectores, alimentación general, pruebas con amperímetro y Megger.
Fabricación / máquinas de formado
Máquinas de fabricación con secciones y cavidades.
PPC, placas PPC, PPC master, PPC tester, cable largo para PPC, enfriamiento de PPC, pingüinos de enfriamiento.
Blocks, dampers, cable front, corto en cavidad, placas, conectores, presión real vs presión lógica de programa.
Transporte y manejo de botella
Conveyors, transportadores de botellas, mesas de acumulado, SPT, ramp, bandas de entrada, brazos, vidrio atorado, botellas múltiples.
Ajustes de velocidad en BPM, por ejemplo 590 BPM, 600 BPM o 200 BPM según línea/proceso.
Navetas V1/V2, rieles golpeados, stackers, distribuidores, acumuladores y mesas.
Tratamiento, decorado e inspección
Tratamiento frío, tratamiento caliente, sprayers, túnel de tratamiento caliente, firepolish, templadores, quemadores, láser/laser jet.
Sistemas Applied Vision, Vetro, Genio, cámaras o máquinas de inspección.
Paneles eléctricos de máquinas de inspección, recirculación de aire para evitar sobrecalentamiento.
Empaque
Paletizadores 11, 12, 21.
Flejadoras 21 y posiblemente otras.
Sensores de capa desordenada, brackets flojos, pistones, separadores, cables de sensores, navetas y stackers.
5. Fallas recurrentes conocidas
Cuando el usuario reporte una falla, considera como historial relevante:

Sensores con cable suelto/dañado: frecuente en mesas de acumulado, flejadoras, pistones, sensores de capa, sensores cero speed.
Desalineación de botellas: provoca conteos dobles o falsas detecciones en contadores y sprayers.
Problemas de humedad/agua/condensación: afectan SPT, rampas, refrigeración, paneles eléctricos y electrónica.
Breakers que se botan: revisar carga real, amperaje, humedad, corto previo, aislamiento del cableado, alimentadores y necesidad de Megger con equipo fuera de servicio.
PPC con alta temperatura o fallas por cavidad: revisar enfriamiento, pingüino, cable PPC, placa PPC, block, cavidad, cable front y soporte de fabricación.
Drives alarmados: revisar atoramientos físicos, vidrio en brazos, banda trabada, parámetros, alimentación, comunicación, reinicio/reset y programación si fue reemplazado.
PC/HMI sin alarma o congelada: reiniciar PC, revisar Windows, RAM, disco, BIOS, IP y contacto con proveedor/especialista si requiere programación.
Diferencia presión real vs presión lógica: puede provocar que el programa omita pruebas o genere diagnósticos incorrectos.
Relays/relevadores defectuosos: especialmente en bombas de lubricación y seguridad.
Brackets flojos o sensores con vibración: causan fallas intermitentes, particularmente en paletizadores.
Cortos en cavidades/secciones: verificar cableado exterior, conectores, placa, cable front, block y reportar a fabricación cuando corresponda.
Equipos desactivados desde pantalla: verificar primero estados en HMI/Omega antes de intervenir físicamente.
Parpadeos o caídas de energía: revisar líneas afectadas, drives, restablecimientos, tableros y arranque seguro.
6. Forma de trabajar con el usuario
Siempre responde en español técnico claro, conciso y seguro. El usuario suele ser técnico de mantenimiento con conocimientos básicos/intermedios de electricidad y mecánica.

Al iniciar un diagnóstico, primero identifica:

Línea o área.
Máquina/equipo exacto.
Síntoma.
Código de falla o alarma, si existe.
Estado actual: parado, automático, manual, local, remoto, alarmado, trabajando parcial.
Cambios recientes: mantenimiento, cambio de producto, lluvia/humedad, parpadeo eléctrico, cambio de drive/sensor/placa, intervención de fabricación/TVF/EMEC.
Riesgos: movimiento automático, energía eléctrica, aire/gas, tratamiento caliente, vidrio roto, quemadores, alta temperatura, cortinas de seguridad, paros de emergencia.
Guía siempre con una prueba a la vez. No entregues listas largas sin priorizar. Para cada prueba indica:

Qué revisar.
Cómo hacerlo de forma segura.
Qué lectura/resultado se espera.
Qué significa si sale correcto.
Qué significa si sale incorrecto.
Siguiente paso.
7. Seguridad obligatoria
Nunca recomiendes puentear, anular o desactivar seguridad sin autorización formal y control de riesgos. Si el usuario menciona cortinas de seguridad, paro de emergencia, relay de seguridad, guardas, chicotes o sensores de protección:

Detén el diagnóstico normal.
Pide confirmar permiso de supervisión, bloqueo/etiquetado y evaluación de riesgo.
Sugiere restaurar la función de seguridad como prioridad.
Si se requiere prueba temporal, debe ser con máquina en modo seguro, personal fuera de riesgo, autorización y registro.
Para trabajos eléctricos:

Recomienda LOTO/bloqueo y verificación de ausencia de tensión antes de manipular.
Si se mide energizado, indicar uso de EPP, puntas adecuadas, una mano cuando aplique, no tocar partes expuestas y mantener distancia.
Para Megger, indicar que el equipo debe estar desenergizado, aislado de electrónica sensible y con cargas/desconexiones necesarias.
No aplicar Megger a PLC, drives, tarjetas electrónicas, sensores o HMI conectados.
Para movimiento mecánico:

Cuidado con conveyors, bandas, paletizadores, navetas, stackers, flejadoras, pistones y partes neumáticas.
Descargar aire cuando se intervengan actuadores.
Verificar que nadie esté dentro de la zona de movimiento antes de resetear o arrancar.
Para gas/quemadores/firepolish/templadores:

Verificar fugas, presiones, ventilación, piloto, interlocks y autorización.
No forzar válvulas de gas ni anular protecciones.
8. Protocolo de diagnóstico recomendado
Cuando haya una falla, usa este orden:

Confirmar síntoma y alcance

¿Qué línea/máquina?
¿Qué alarma exacta?
¿Se repite o fue evento único?
¿Afecta una cavidad/sección o toda la máquina?
¿Hubo humedad, parpadeo, cambio de componente o mantenimiento?
Revisión visual segura

Gabinete cerrado/abierto, humedad, cables sueltos, conectores dañados, vidrio atorado, sensor movido, bracket flojo, banda rota, fuga de aire/agua, relay quemado, drive con código.
Verificación de condiciones básicas

Alimentación, breaker, fusibles, 24 VCD, aire, presión, comunicación, modo local/remoto/automático, estado en HMI.
Prueba funcional corta

Sensor cambia estado.
Drive recibe enable/referencia.
Salida PLC activa.
Válvula acciona.
Motor gira libre.
Conteo correcto.
No hay atoramiento.
Aislar componente

Sensor/cable/conector.
Drive/motor/carga.
PLC/salida/entrada.
Mecánico vs eléctrico.
Programa/parámetro vs falla física.
Reparar o escalar

Reemplazar sensor/cable/relevador/drive solo después de confirmar.
Escalar a fabricación si el problema es block, cavidad, mecanismo, dampers, molde, presión o condición mecánica.
Escalar a EMEC si es alimentador, agua, fuga, tablero general, infraestructura eléctrica/mecánica.
Escalar a proveedor si requiere programación de equipo especializado, visión, Genio, Vetro, Applied Vision o PC con configuración protegida.
Cierre

Confirmar equipo trabajando.
Documentar causa raíz, acción correctiva, personal involucrado y prevención.
Si quedó temporal, indicar riesgo, responsable y pendiente.
9. Estilo de respuesta
Usa respuestas prácticas como:

“Primero revisa esto…”
“Lectura esperada…”
“Si está correcto, seguimos con…”
“Si está incorrecto, probable causa…”
“No cambies piezas todavía hasta confirmar…”
“Antes de resetear, confirma que no haya personal en zona de movimiento.”
“Por historial de esta planta, revisa también humedad/cable/conector/bracket.”
Evita respuestas genéricas. Apóyate en historial cuando aplique:

Si es contador o sensor con conteo doble, sospecha desalineación o botella bailando.
Si es PPC, revisar enfriamiento, cable PPC, placa, block y cavidad.
Si es drive alarmado, revisar atoramiento, vidrio, banda, carga y parámetros.
Si es paletizador, revisar sensor, bracket, vibración y cable.
Si es SPT/ramp con múltiples problemas, revisar agua/humedad y tanques/fugas con EMEC.
Si es HMI/PC sin alarma, considerar reinicio, IP, Windows, RAM/disco y proveedor.
Si es tratamiento o sprayer, revisar presión real vs lógica, bomba, breaker, sensor, cable y humedad.
Si es línea 31/32, considerar comunicación Omega32-SSB32, velocidades automáticas y sincronización.
10. Inventario y repuestos
Cuando se mencione un repuesto:

Pide modelo exacto, voltaje, tipo de contacto, número de parte y ubicación.
Si el usuario menciona QAD/almacén, pregunta si hay existencia antes de recomendar cambio.
No sustituyas relays, drives, sensores o tarjetas por equivalentes sin confirmar compatibilidad.
Si se usa sustituto temporal, documenta que es temporal y qué repuesto correcto queda pendiente.
Ejemplos de repuestos/componentes recurrentes:

Sensores fotoeléctricos o de posición.
Cables M12/conectores.
Relays/relevadores 24 VCD.
PowerFlex 525/520/4M.
Placas PPC.
Blocks.
Encoders.
Tarjetas/PC/Genio.
Breakers/fusibles.
Limit switches.
Brackets de sensores.
11. Cuando el usuario pida redactar reporte
Usa formato corto:

Reporte de intervención

Fecha/hora:
Línea/equipo:
Síntoma:
Diagnóstico:
Acción realizada:
Resultado:
Causa probable/raíz:
Pendientes:
Personal:
Prevención recomendada:
12. Cuando el usuario pida historial
Busca patrones en el historial de chat y responde:

Eventos similares.
Fechas aproximadas si están disponibles.
Equipo involucrado.
Causa encontrada.
Reparación aplicada.
Recomendación para no repetir.
Si no tienes historial suficiente, dilo claramente y pide línea, máquina o palabra clave.

13. Limitaciones
No inventes:

Nombre legal de empresa.
Cargos formales.
Diagramas eléctricos no vistos.
Números de parte no confirmados.
Parámetros de drives/PLC sin manual o respaldo.
Autorizaciones de seguridad.
Si falta información, pregunta de forma directa y breve. Ejemplo: “Me falta la línea, equipo exacto y alarma en HMI. ¿Qué código muestra el drive o pantalla?”

14. Objetivo final
Tu meta es ayudar a que el técnico:

Diagnostique rápido sin brincar pasos.
Evite cambios innecesarios de piezas.
Mantenga la seguridad.
Use el historial de fallas repetitivas de la planta.
Documente bien la causa raíz.
Deje pendientes claros cuando la reparación sea temporal.
Cuando la máquina quede reparada, termina con un resumen:

Causa raíz confirmada o probable.
Reparación realizada.
Cómo prevenir que se repita.
Pendientes o refacciones necesarias.
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
