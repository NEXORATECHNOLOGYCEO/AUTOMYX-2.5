"""
AUTOMYX Intent Engine v2.5
==========================
Motor de entendimiento de lenguaje natural para personas no técnicas.
- Diccionario de slang (es/en), jerga regional, typos comunes
- Mapeo de frases coloquiales → intent + parámetros
- Expansión de contracciones y abreviaciones
- Detección de typos con fuzzy matching
- Normalización de nombres de carpetas/archivos coloquiales
"""
from __future__ import annotations

import os
import re
import json
import unicodedata
import requests
from difflib import get_close_matches, SequenceMatcher
from typing import Dict, List, Any, Optional, Tuple


# ---------------------------------------------------------------------------
# Diccionario maestro de slang → forma canónica
# ---------------------------------------------------------------------------
SLANG_NORMALIZER: Dict[str, str] = {
    # Español coloquial
    "ahorita": "ahora",
    "ahorita mismo": "ahora",
    "ya mismo": "ahora",
    "ya mero": "ahora",
    "dele": "ejecutar",
    "dale": "ejecutar",
    "metele": "ejecutar",
    "mándale": "ejecutar",
    "hágale": "ejecutar",
    "órale": "ejecutar",
    "ándale": "ejecutar",
    "vo": "yo",  # voseo
    "haiga": "haya",
    "muévele": "ejecutar",
    "pilas": "rápido",
    "apúrale": "rápido",
    "apurate": "rápido",
    "apúrense": "rápido",
    "fíjate": "observar",
    "fijate": "observar",
    "mira": "observar",
    "fíjese": "observar",
    "te lo agradezco": "gracias",
    "le agradezco": "gracias",
    "de una": "ahora",
    "nel": "no",
    "nopi": "no",
    "nope": "no",
    "nel pastel": "no",
    "simón": "sí",
    "sisas": "sí",
    "asies": "sí",
    "va": "sí",
    "sale": "sí",
    "qué onda": "hola",
    "que onda": "hola",
    "cómo andas": "hola",
    "como andas": "hola",
    "que hubo": "hola",
    "qué hubo": "hola",
    "buenas": "hola",
    "epa": "hola",
    "wey": "",  # borra groserías suaves
    "güey": "",
    "carnal": "",
    "compa": "",
    "bro": "",
    "brother": "",
    "mami": "",
    "papi": "",
    # Contracciones y abreviaciones
    "q": "que",
    "xq": "porque",
    "porq": "porque",
    "x": "por",
    "tb": "también",
    "tmb": "también",
    "tampc": "tampoco",
    "k": "que",
    "xfa": "por favor",
    "xfavor": "por favor",
    "plis": "por favor",
    "plis": "por favor",
    "pls": "por favor",
    "fvr": "por favor",
    "xavor": "por favor",
    "favor": "por favor",
    "aver": "a ver",
    "haber": "a ver",
    "aki": "aquí",
    "alla": "allá",
    "toy": "estoy",
    "tamos": "estamos",
    "pa": "para",
    "pal": "para el",
    "ke": "que",
    "kiero": "quiero",
    "ker": "querer",
    "keria": "quería",
    "kiero": "quiero",
    "tmbn": "también",
    "mismo": "",
    "mismito": "",
    "mismitito": "",
    # Anglicismos coloquiales
    "googlealo": "buscar en google",
    "googlea": "buscar en google",
    "googleale": "buscar en google",
    "tiktoker": "tiktok",
    "yt": "youtube",
    "ig": "instagram",
    "fb": "facebook",
    "wsp": "whatsapp",
    "wasap": "whatsapp",
    "gua": "whatsapp",
    "tg": "telegram",
    "tw": "twitter",
    "tt": "tiktok",
    "tktk": "tiktok",
    "xp": "windows",
    "linuxero": "linux",
    "macero": "mac",
    "celu": "celular",
    "cel": "celular",
    "movil": "celular",
    "compu": "computadora",
    "pc": "computadora",
    "laptp": "computadora",
    "laptop": "computadora",
    "noti": "computadora",
    "notebook": "computadora",
    "desk": "escritorio",
    "desktop": "escritorio",
    "pantalla": "monitor",
    "screen": "monitor",
    "musica": "música",
    "videito": "video",
    "videillo": "video",
    "vidio": "video",
    "vid": "video",
    "cancion": "canción",
    "cancioncita": "canción",
    "temita": "canción",
    "temazo": "canción",
    "track": "canción",
    "song": "canción",
    "playlista": "playlist",
    "lista": "playlist",
    "fotovideo": "video",
    "reel": "video",
    "reels": "videos",
    "short": "video",
    "shorts": "videos",
    "peli": "película",
    "movie": "película",
    "film": "película",
    "bookmark": "marcador",
    "favorito": "marcador",
    "foto": "imagen",
    "pics": "imágenes",
    "pict": "imagen",
    "imagen": "imagen",
    "imagencita": "imagen",
    "pic": "imagen",
    "selfie": "foto",
    "selfi": "foto",
    "retocame": "editar imagen",
    "editame": "editar",
    "cortame": "recortar",
    "recortame": "recortar",
    "borrame": "eliminar",
    "bórralo": "eliminar",
    "borralo": "eliminar",
    "quítale": "eliminar",
    "sácale": "extraer",
    "sacame": "extraer",
    "juntame": "combinar",
    "combinalas": "combinar",
    "pegalos": "combinar",
    "juntalos": "combinar",
    "pegamela": "pegar",
    "pegamelo": "pegar",
    "pegala": "pegar",
    "pegalo": "pegar",
    "ponmelo": "pegar",
    "ponle": "agregar",
    "agregale": "agregar",
    "metele a youtube": "reproducir youtube",
    "metele play": "reproducir",
    "metele música": "reproducir música",
    "metele cancion": "reproducir canción",
    "metele a spotify": "reproducir spotify",
    "saca": "extraer",
    "sacale": "extraer",
    "sácale": "extraer",
    "sacamela": "extraer",
    "sacame": "extraer",
    "házmelo": "ejecutar",
    "hazmelo": "ejecutar",
    "hagamela": "ejecutar",
    "armame": "crear",
    "armalo": "crear",
    "armale": "crear",
    "háceme": "crear",
    "haceme": "crear",
    "hacé": "hacer",
    "diseñame": "diseñar",
    "creame": "crear",
    "crealo": "crear",
    "creala": "crear",
    "creame una": "crear",
    "haz una": "crear",
    "hazme una": "crear",
    "hazme un": "crear",
    "haz un": "crear",
    "haz": "crear",
    "mándame": "enviar",
    "mandame": "enviar",
    "pasame": "enviar",
    "pásame": "enviar",
    "envíale": "enviar",
    "enviale": "enviar",
    "mándale": "enviar",
    "mandale": "enviar",
    "dile": "enviar mensaje",
    "dile que": "enviar mensaje",
    "ponle": "agregar",
    "configura": "configurar",
    "configúrame": "configurar",
    "config": "configurar",
    "ajustá": "ajustar",
    "ajusta": "ajustar",
    "tunea": "ajustar",
    "tunear": "ajustar",
    "armar": "crear",
    "hacer": "crear",
    "realiza": "ejecutar",
    "realizar": "ejecutar",
    "efectúa": "ejecutar",
    "lanzar": "ejecutar",
    "arrancar": "ejecutar",
    "iniciar": "ejecutar",
    "abrir": "abrir",
    "abreme": "abrir",
    "abráme": "abrir",
    "abre": "abrir",
    "abrirlo": "abrir",
    "abrirla": "abrir",
    "ejecuta": "ejecutar",
    "corre": "ejecutar",
    "córrelo": "ejecutar",
    "correme": "ejecutar",
    "lánzalo": "ejecutar",
    "lanza": "ejecutar",
    "lanzar": "ejecutar",
    "enciéndelo": "iniciar",
    "enciendelo": "iniciar",
    "apágala": "cerrar",
    "apagala": "cerrar",
    "ciérralo": "cerrar",
    "cierralo": "cerrar",
    "mátalo": "cerrar",
    "matalo": "cerrar",
    "kill": "cerrar",
    "cerrá": "cerrar",
    "cierra": "cerrar",
    "salir": "cerrar",
    "salí": "cerrar",
    "cancela": "cancelar",
    "anula": "cancelar",
    "para": "detener",
    "detén": "detener",
    "frena": "detener",
    "frená": "detener",
    "alto": "detener",
    "aguas": "detener",
    "cuidado": "detener",
    "explica": "explicar",
    "explicame": "explicar",
    "explícame": "explicar",
    "qué es": "explicar",
    "que es": "explicar",
    "qué significa": "explicar",
    "que significa": "explicar",
    "qué quiere decir": "explicar",
    "que quiere decir": "explicar",
    "ayudame": "ayudar",
    "ayúdame": "ayudar",
    "ayuda": "ayudar",
    "necesito": "quiero",
    "preciso": "quiero",
    "me urge": "quiero",
    "me urge un": "quiero un",
    "ocupo": "quiero",
    "hace falta": "quiero",
    "rebusca": "buscar",
    "buscame": "buscar",
    "búscalos": "buscar",
    "encuéntralos": "buscar",
    "encuentralos": "buscar",
    "encuéntrame": "buscar",
    "buscar": "buscar",
    "encuentra": "buscar",
    "search": "buscar",
    "investiga": "buscar",
    "averigua": "buscar",
    "indaga": "buscar",
    "mira a ver": "buscar",
    "mirá": "observar",
    "fijáte": "observar",
    "fíjate": "observar",
    "escríbeme": "escribir",
    "escribime": "escribir",
    "apuntá": "escribir",
    "anota": "escribir",
    "anotá": "escribir",
    "toma nota": "escribir",
    "ponme": "escribir",
    "escribile": "escribir",
    "ponmelo en": "guardar en",
    "guardamelo": "guardar",
    "guardá": "guardar",
    "guarda": "guardar",
    "almacena": "guardar",
    "almacená": "guardar",
    "metelo": "guardar",
    "mételo": "guardar",
    "pégale": "mover",
    "córrelo a": "mover a",
    "corremelo a": "mover a",
    "trasládate": "mover",
    "mueve": "mover",
    "mover": "mover",
    "move": "mover",
    "llévate": "mover",
    "traslada": "mover",
    "sácame de": "mover desde",
    "sácame a": "mover a",
    "pásalo a": "mover a",
    "renombra": "renombrar",
    "renombrá": "renombrar",
    "cambiale el nombre": "renombrar",
    "bautiza": "renombrar",
    "títulale": "renombrar",
    "abrí": "abrir",
    "abrelo": "abrir",
    "abreme": "abrir",
    "abreme el": "abrir",
    "abreme la": "abrir",
    "mostrame": "mostrar",
    "muéstrame": "mostrar",
    "enseñame": "mostrar",
    "enseñáme": "mostrar",
    "sacame una captura": "tomar captura",
    "capturame": "tomar captura",
    "tirame una captura": "tomar captura",
    "pasame el": "enviar",
    "te paso": "enviar",
    "te mando": "enviar",
    "ahí te va": "enviar",
    "ahí te mando": "enviar",
    "tírame": "enviar",
    "tíramelo": "enviar",
    "lanzame": "enviar",
    "lánzame": "enviar",
    "ponlo en": "subir a",
    "subelo a": "subir a",
    "subila a": "subir a",
    "súbelo a": "subir a",
    "publícalo": "publicar",
    "publicá": "publicar",
    "publicar": "publicar",
    "postear": "publicar",
    "posteá": "publicar",
    "subir": "publicar",
    "comparte": "compartir",
    "compartí": "compartir",
    "compartir": "compartir",
    "share": "compartir",
    "descarga": "descargar",
    "bajá": "descargar",
    "bájate eso": "descargar eso",
    "trae ese": "descargar",
    "traeme": "descargar",
    "tráeme": "descargar",
    "traelo": "descargar",
    "trae esa": "descargar",
    "dame": "descargar",
    "dámelo": "descargar",
    "pasame el link": "enviar link",
    "envíame el": "enviar",
    "ponlo en mi": "guardar en mi",
    "hazme un favor": "ayudar",
    "te encargo": "ayudar",
    "te pido": "ayudar",
    "ayúdenme": "ayudar",
    "ayudame con": "ayudar",
    "échame la mano": "ayudar",
    "echame la mano": "ayudar",
    "help me": "ayudar",
    "necesito que": "quiero",
    "haz que": "ejecutar",
    "que": "",
    "por favor": "",
    "porfa": "",
    "porfis": "",
    "por favo": "",
    "por favorcito": "",
    "plis plis": "",
}


# ---------------------------------------------------------------------------
# Detector de intent (qué quiere el usuario)
# ---------------------------------------------------------------------------
INTENT_KEYWORDS: Dict[str, List[str]] = {
    # Acciones de archivo
    "create_file": [
        "crea un archivo", "crea un fichero", "crea un txt", "crea un documento",
        "escribe un archivo", "escribe un fichero", "hazme un archivo", "hazme un txt",
        "hazme un documento", "armame un archivo", "armame un documento",
        "guarda en", "escribe en", "pon en un archivo", "guardalo en un archivo",
        "dame un archivo", "haz un archivo", "hacé un archivo",
        "guardame un archivo", "guardame un txt", "guardame un documento",
        "guardame un fichero", "guardame una nota", "guarda esto en un archivo",
        "escribime un archivo", "escribime un txt", "escribime un documento",
        "anota en un archivo", "anota esto", "pon en un txt", "pon en un archivo",
        "ponmelo en un archivo", "ponmelo en un txt", "házmelo en un archivo",
        "hazme un txt con", "hazme un documento con", "hazme un archivo con",
        "create file", "write a file", "save a file", "make a txt",
    ],
    "create_directory": [
        "crea una carpeta", "crea un directorio", "hazme una carpeta", "hazme un folder",
        "armame una carpeta", "hacé una carpeta", "crea el directorio",
        "haz una carpeta", "creame una carpeta", "ponme una carpeta",
        "creame el directorio", "hazme el directorio", "nueva carpeta",
        "nuevo directorio", "make a folder", "create folder", "create directory", "new folder",
    ],
    "delete_file": [
        "borra el archivo", "borra la carpeta", "elimina el archivo", "elimina la carpeta",
        "borra ese archivo", "borra esa carpeta", "bórralo", "bórrala",
        "quítalo", "quítala", "sácale", "deshazte de", "delete", "remove file",
    ],
    "read_file": [
        "léeme el archivo", "ábreme el archivo", "muéstrame el archivo",
        "que dice el archivo", "qué hay en el archivo", "enséñame el archivo",
        "ábreme el fichero", "muéstrame el fichero", "dame el contenido",
        "leeme el fichero", "leeme el archivo", "ver el archivo", "ver el contenido",
        "read file", "show file", "cat file",
    ],
    "organize_files": [
        "organiza los archivos", "ordena los archivos", "ordena mi carpeta",
        "organiza mi carpeta", "organiza el escritorio", "ordena el escritorio",
        "ordena las descargas", "organiza las descargas", "limpia mi carpeta",
        "organize files", "sort files", "tidy up", "clean up folder",
    ],
    # Web
    "web_search": [
        "busca en google", "búscalo en google", "googlea", "googlealo",
        "busca en internet", "búscalo en internet", "busca en la web",
        "search google", "google", "busca sobre", "investiga sobre",
        "averigua sobre", "qué sabes de", "qué es", "quién es",
        "información sobre", "info de", "dime sobre",
    ],
    "open_website": [
        "abre la página", "abreme la web", "entra a la página", "entra a la web",
        "anda a", "ve a", "vete a", "navega a", "ábreme el sitio",
        "abrir sitio", "ir a", "entra al sitio", "open website", "go to",
    ],
    "download": [
        "descarga", "descárgalo", "bájalo", "bájame", "bájate eso",
        "tráeme ese", "dame el archivo", "trae ese archivo",
        "download", "get me", "fetch", "descargame",
        "bajame el video", "bajame esa", "bajame ese", "bájame el",
        "descargame el", "descargame esa", "descargame ese",
    ],
    # Multimedia
    "play_video": [
        "reproduce", "ponme", "reproducir", "escuchar", "escucha",
        "pon la canción", "reproduce la canción", "reproduce el video",
        "play", "play music", "play song", "pon youtube", "reproduce youtube",
        "pon un video de youtube", "pon un video", "pon esa canción",
        "reproducir youtube", "reproducir spotify", "reproducir música",
        "reproducir canción",
    ],
    "edit_video": [
        "edita el video", "edita el vídeo", "recorta el video", "córtame el video",
        "hazme un edit", "hazme un tiktok", "haz un edit",
        "trim video", "edit video", "cut video",
    ],
    "edit_image": [
        "edita la imagen", "edita la foto", "retoca la foto", "retocame la foto",
        "cambiale el tamaño", "resize", "edit image", "edit photo",
        "filtro a la foto", "ponle filtro", "blanco y negro",
    ],
    "generate_image": [
        "crea una imagen", "genera una imagen", "dibújame", "dibujame",
        "hazme una imagen", "hazme un dibujo", "create image", "generate image",
        "imagina", "ilustra", "ilustrame", "hazme un poster",
    ],
    "generate_video": [
        "crea un video", "genera un video", "hazme un video", "create video",
        "generate video", "hazme un vídeo",
    ],
    # Sistema
    "open_program": [
        "abre", "abrir", "abreme", "ejecuta", "lánzame", "inicia",
        "arranca", "enciende", "córreme", "ábreme el programa",
        "open", "launch", "run", "start", "abre el", "abrir el",
        "abreme el", "abrime", "abreme chrome", "abreme firefox",
        "abreme el navegador", "abreme la app", "lanza el",
    ],
    "execute_cmd": [
        "ejecuta el comando", "corre el comando", "haz una línea",
        "cmd", "powershell", "terminal", "consola", "shell",
        "run command", "execute command", "run script", "corre el script",
    ],
    "close_program": [
        "cierra", "cierre", "ciérralo", "mátalo", "apágala", "salir de",
        "cierra el", "kill", "close", "quit", "exit",
    ],
    "type_text": [
        "escribe", "escribir", "tipea", "teclea", "tecleá", "type",
        "pon texto", "escribime", "apunta",
    ],
    "screenshot_intent": [
        "screenshot", "toma captura", "toma una captura", "captura de pantalla",
        "captura la pantalla", "captura pantalla", "tómame una captura",
        "tomar captura", "hazme un screenshot", "saca una captura",
    ],
    "press_key": [
        "presiona", "pulsa", "aprieta", "toca", "click", "click en",
        "press", "push", "hit",
    ],
    # Conversación
    "greeting": [
        "hola", "qué tal", "como estás", "cómo estás", "cómo andas",
        "qué onda", "buenas", "buenos días", "buenas tardes", "buenas noches",
        "hi", "hello", "hey", "qué hubo", "que tal", "que onda", "saludos",
        "buen dia", "buenos dias",
        # Coloquialismos latinos / calle
        "ey", "oe", "oiga", "oiga usted", "vea", "ve",
        "ey mano", "oe mano", "mano", "parcero", "parce", "brother", "bro",
        "gonorrea", "no seas gonorrea", "no joda", "ñero", "ñera", "loco",
        "tío", "tia", "tio", "tia", "primo", "prima", "amigo", "amiga",
        "ps", "pss", "pues", "a ver", "ver", "mira", "fíjate", "mire",
        "qué más", "que mas", "qué más pues", "qué hubo", "qué hube",
        "cómo te va", "como te va", "cómo vamos", "como vamos",
        "todo bien", "cómo vas", "que tal todo", "qué tal todo",
        "hi there", "hey there", "yo", "aló", "aló?", "buenas buenas",
    ],
    "help": [
        "ayuda", "ayúdame", "necesito ayuda", "qué puedes hacer", "qué sabes hacer",
        "para qué sirves", "help", "qué haces", "explicame", "explícame",
        "qué funciones tienes", "muéstrame qué puedes hacer", "enséñame",
        "que puedes hacer", "que sabes hacer", "para que sirves", "que haces",
        "muéstrame qué hacer", "mostrame que hacer", "a ver qué haces",
        "mira qué haces", "muestrame", "mostrame", "enséñame a usar",
    ],
    "thanks": [
        "gracias", "muchas gracias", "te lo agradezco", "mil gracias",
        "thanks", "thank you", "ty", "merci",
    ],
    "farewell": [
        "adiós", "chao", "chau", "hasta luego", "nos vemos", "bye",
        "hasta pronto", "me voy", "cuídate",
    ],
    # Configuración de integraciones / canales
    "setup_integration": [
        # Español
        "configurar notion", "configura notion", "conectar notion", "conecta notion",
        "vincular notion", "vincula notion", "activar notion", "activa notion",
        "agregar notion", "añadir notion", "anadir notion",
        "poner mi token de notion", "guardar mi token de notion", "mi api key de notion",
        "configurar github", "configura github", "conectar github", "conecta github",
        "vincular github", "activar github", "mi token de github",
        "configurar telegram", "configura telegram", "conectar telegram",
        "vincular telegram", "activar telegram", "mi bot de telegram",
        "configurar discord", "configura discord", "conectar discord",
        "vincular discord", "activar discord", "mi bot de discord",
        "configurar instagram", "configura instagram", "conectar instagram",
        "vincular instagram", "activar instagram",
        "configurar openai", "configurar anthropic", "configurar elevenlabs",
        "configurar tavily", "configurar gemini",
        "configurar integracion", "configurar integración", "configurar canal",
        "agregar integracion", "agregar integración", "agregar canal",
        "set up notion", "setup notion", "connect notion", "add notion",
        "set up github", "setup github", "connect github", "add github",
        "set up telegram", "setup telegram", "connect telegram",
        "set up discord", "setup discord", "connect discord",
        "link notion", "link github", "link telegram", "link discord",
        "i want to use notion", "i need to set up notion", "let's configure notion",
        "let's connect notion", "help me set up notion", "ayuda a configurar notion",
        "no tengo notion configurado", "quiero usar notion", "quiero conectar notion",
        "agrega notion", "registra notion", "setup integration", "setup channel",
        "add channel", "add integration",
        # Rotar / validar
        "rotar notion", "rotar github", "rotar telegram", "rotar discord",
        "rotar instagram", "rotar openai", "rotar anthropic", "rotar elevenlabs",
        "rotar tavily", "rotar gemini", "rotar groq", "rotar mistral",
        "validar notion", "validar github", "validar telegram", "validar discord",
        "validar instagram", "validar openai", "validar anthropic", "validar elevenlabs",
        "validar tavily", "validar gemini", "validar groq", "validar mistral",
        "rotate notion", "rotate github", "rotate telegram", "rotate discord",
        "validate notion", "validate github", "validate telegram", "validate discord",
        "cambiar token de notion", "cambiar token de github", "cambiar mi token",
        "actualizar token", "refrescar token", "renew notion", "renew github",
    ],
    # Código
    "run_code": [
        "corre el código", "ejecuta el script", "corre el script",
        "ejecuta el código", "lánzame el script", "lánzame el código",
        "run code", "execute script", "run script",
    ],
    "test_code": [
        "corre los tests", "haz tests", "genera tests", "testea",
        "pytest", "ejecuta tests", "run tests", "test the code",
    ],
    "deploy": [
        "despliega", "deploy", "sube a producción", "publica", "deploya",
        "saca a producción", "lanza a producción", "push to prod",
    ],
    # Búsqueda local
    "search_files": [
        "busca el archivo", "encuentra el archivo", "dónde está el archivo",
        "búscalo en mi pc", "búscalo en mi compu", "search files",
        "find file", "locate file",
    ],
    # Conocimiento
    "explain": [
        "explícame", "explícame qué es", "qué significa", "qué quiere decir",
        "explain", "what is", "what does it mean",
    ],
    "summarize": [
        "resúmeme", "hazme un resumen", "resume", "resumen",
        "summarize", "summary", "tldr",
    ],
    "translate": [
        "tradúceme", "traduce", "trádúceme esto", "translate",
        "how do you say", "cómo se dice", "al inglés", "al español",
    ],
    "remember": [
        "recuerda que", "recuerdame", "no olvides", "memoriza",
        "remember", "memorize", "keep in mind",
    ],
    "forget": [
        "olvida", "olvídate", "borra de tu memoria", "reset",
        "forget", "clear memory",
    ],
}


# ---------------------------------------------------------------------------
# Detección de carpetas coloquiales
# ---------------------------------------------------------------------------
FOLDER_SLANG: Dict[str, str] = {
    "escritorio": "Desktop",
    "escritorios": "Desktop",
    "pantalla principal": "Desktop",
    "pantalla de inicio": "Desktop",
    "mesa": "Desktop",
    "descargas": "Downloads",
    "descarga": "Downloads",
    "downloads": "Downloads",
    "download": "Downloads",
    "lo bajado": "Downloads",
    "documentos": "Documents",
    "docs": "Documents",
    "documento": "Documents",
    "archivos": "Documents",
    "papeles": "Documents",
    "fotos": "Pictures",
    "foto": "Pictures",
    "fotos mías": "Pictures",
    "imágenes": "Pictures",
    "imagenes": "Pictures",
    "imagen": "Pictures",
    "galería": "Pictures",
    "galeria": "Pictures",
    "álbum": "Pictures",
    "album": "Pictures",
    "videos": "Videos",
    "vídeos": "Videos",
    "video": "Videos",
    "mis videos": "Videos",
    "grabaciones": "Videos",
    "cancion": "canción",
    "cancioncita": "canción",
    "temita": "canción",
    "temazo": "canción",
    "track": "canción",
    "song": "canción",
    "playlista": "playlist",
    "lista": "playlist",
    "fotovideo": "video",
    "reel": "video",
    "reels": "videos",
    "short": "video",
    "shorts": "videos",
    "peli": "película",
    "movie": "película",
    "film": "película",
    "bookmark": "marcador",
    "favorito": "marcador",
    "foto": "imagen",
    "pics": "imágenes",
    "pict": "imagen",
    "imagen": "imagen",
    "imagencita": "imagen",
    "pic": "imagen",
    "selfie": "foto",
    "selfi": "foto",
    "retocame": "editar imagen",
    "editame": "editar",
    "cortame": "recortar",
    "recortame": "recortar",
    "borrame": "eliminar",
    "bórralo": "eliminar",
    "borralo": "eliminar",
    "quítale": "eliminar",
}


# ---------------------------------------------------------------------------
# Typos comunes en español (letras adyacentes en teclado)
# ---------------------------------------------------------------------------
COMMON_TYPO_MAP: Dict[str, str] = {
    "archico": "archivo",
    "archvos": "archivos",
    "archvio": "archivo",
    "archvio": "archivo",
    "carptea": "carpeta",
    "carpta": "carpeta",
    "carpea": "carpeta",
    "carpea": "carpeta",
    "ventna": "ventana",
    "ventama": "ventana",
    "archico": "archivo",
    "dierección": "dirección",
    "direccón": "dirección",
    "direccin": "dirección",
    "direción": "dirección",
    "apñlicación": "aplicación",
    "aplcación": "aplicación",
    "aplcacion": "aplicación",
    "configración": "configuración",
    "configracion": "configuración",
    "confguracion": "configuración",
    "confgur": "configurar",
    "imgane": "imagen",
    "imganen": "imagen",
    "viudeo": "video",
    "vodeo": "video",
    "vidoe": "video",
    "vido": "video",
    "vcideo": "video",
    "muscia": "música",
    "musca": "música",
    "musca": "música",
    "canción": "canción",
    "cancion": "canción",
    "canciónn": "canción",
    "ejcutar": "ejecutar",
    "ejcutar": "ejecutar",
    "ejcutalo": "ejecútalo",
    "bucar": "buscar",
    "buscr": "buscar",
    "buscame": "búsqueda",
    "informcón": "información",
    "info": "información",
    "informacion": "información",
    "pubicar": "publicar",
    "publciar": "publicar",
    "publiar": "publicar",
    "escribie": "escribe",
    "escribi": "escribe",
    "escribeme": "escríbeme",
    "descaargar": "descargar",
    "descrgar": "descargar",
    "descaragr": "descargar",
    "desca": "descargar",
    "cancelar": "cancelar",
    "cancelr": "cancelar",
    "aborrir": "abrir",
    "abrri": "abrir",
    "abir": "abrir",
    "abr": "abrir",
    "habrir": "abrir",
    "qiero": "quiero",
    "kiero": "quiero",
    "qer": "querer",
    "qero": "quiero",
    "qiero": "quiero",
    "kero": "quiero",
}


# ---------------------------------------------------------------------------
# Función principal: entender mensaje
# ---------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """Limpia y normaliza texto: slang, contracciones, typos."""
    if not text:
        return ""

    s = text.strip().lower()
    # Quitar acentos residuales al comparar
    s_norm = unicodedata.normalize("NFD", s)
    s_no_acc = "".join(c for c in s_norm if unicodedata.category(c) != "Mn")

    # 0. Frases multi-palabra (orden: más largas primero)
    phrase_keys = sorted(
        [k for k in SLANG_NORMALIZER.keys() if " " in k],
        key=len, reverse=True
    )
    for phrase in phrase_keys:
        canon_phrase = SLANG_NORMALIZER[phrase]
        if canon_phrase == "":
            # borrar frase completa
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            s = pattern.sub("", s)
        else:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            s = pattern.sub(canon_phrase, s)

    # 1. Slang → forma canónica (palabra por palabra)
    out_parts = []
    for word in s.split():
        # Quitar puntuación para matchear
        clean = word.strip("¿?¡!.,;:()[]{}\"'")
        if not clean:
            out_parts.append(word)
            continue
        canon = SLANG_NORMALIZER.get(clean)
        if canon is None:
            # match sin acentos
            clean_no_acc = unicodedata.normalize("NFD", clean)
            clean_no_acc = "".join(c for c in clean_no_acc if unicodedata.category(c) != "Mn")
            canon = SLANG_NORMALIZER.get(clean_no_acc)
        if canon is None:
            # typo
            canon = COMMON_TYPO_MAP.get(clean)
        if canon is None:
            out_parts.append(word)
        elif canon == "":
            # palabra vacía (grosería, muletilla)
            out_parts.append("")
        else:
            # mantener puntuación original
            out_parts.append(word.replace(clean, canon))

    return " ".join(p for p in out_parts if p).strip()


def _stem_es(word: str) -> str:
    """Stemmer ultra-simple para español. Quita sufijos comunes."""
    w = word.lower()
    for suf in ["ar", "er", "ir", "ando", "iendo", "ado", "ido", "a", "e", "o",
                "amos", "emos", "imos", "an", "en", "in", "as", "es", "is",
                "ame", "eme", "ime", "ale", "ele", "ile", "arles", "erles", "irles"]:
        if w.endswith(suf) and len(w) - len(suf) >= 4:  # más conservador
            return w[: -len(suf)]
    return w


def _text_contains(text: str, kw: str) -> bool:
    """Match con word boundary + stemming básico (estricto)."""
    kw_lower = kw.lower().strip()
    if not kw_lower:
        return False
    # 1) Match exacto con word boundary
    pattern = r"(?:^|\b)" + re.escape(kw_lower) + r"(?:$|\b)"
    if re.search(pattern, text.lower()):
        return True
    # 2) Match por stems: SOLO si el keyword es multi-palabra o >=5 chars
    kw_words_raw = re.findall(r"\w+", kw_lower)
    text_words = [_stem_es(w) for w in re.findall(r"\w+", text.lower())]
    if len(kw_words_raw) < 1:
        return False
    # Para keywords de una palabra, exigir match exacto (no stemming)
    if len(kw_words_raw) == 1 and len(kw_words_raw[0]) < 6:
        return False
    kw_stems = [_stem_es(w) for w in kw_words_raw if len(w) >= 4]
    if not kw_stems:
        return False
    # Si solo hay 1 stem, exigir que sea largo (>=8) y match exacto
    if len(kw_stems) == 1:
        if len(kw_stems[0]) < 8:
            return False
        return any(t == kw_stems[0] for t in text_words)
    # Multi-stem: requerir todos
    matches = 0
    for k in kw_stems:
        for t in text_words:
            if t == k:
                matches += 1
                break
            if len(t) >= 4 and (t.startswith(k) or k.startswith(t)):
                if abs(len(t) - len(k)) <= 2:
                    matches += 1
                    break
            if len(t) >= 4 and SequenceMatcher(None, t, k).ratio() >= 0.88:
                matches += 1
                break
    return matches >= len(kw_stems)


def _stem_match(a: str, b: str) -> bool:
    """True if two single-word strings share a strong stem relation.

    Used as a fallback when exact substring fails — e.g. "ayudar" vs "ayuda"
    (the stemmer drops the trailing -r, so both should match the help intent).
    """
    aw = re.findall(r"\w+", a.lower())
    bw = re.findall(r"\w+", b.lower())
    if not aw or not bw:
        return False
    a1, b1 = aw[0], bw[0]
    if len(a1) < 4 or len(b1) < 4:
        return False
    if a1 == b1:
        return True
    # 88% similarity is enough for stem-level match
    if SequenceMatcher(None, a1, b1).ratio() >= 0.88:
        return True
    return False


def detect_intent(text: str) -> Dict[str, Any]:
    """
    Detecta el intent del usuario.
    Returns: {
        "intent": "create_file" | "web_search" | ...,
        "confidence": 0.0-1.0,
        "normalized": "texto normalizado",
        "entities": {...}
    }
    """
    norm = normalize_text(text)
    norm_lower = norm.lower()
    text_lower = text.lower()

    best_intent = "unknown"
    best_score = 0.0
    matched_keyword = ""

    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            kw_lower = kw.lower().strip()
            if not kw_lower:
                continue
            # Three match tiers (strong → weak):
            # 1. Exact substring (strong)
            # 2. Normalized-stem match (weak, only for single words)
            # The weak match only counts if no strong match wins, preventing
            # "ayuda" from incorrectly matching "ayuda a configurar notion".
            is_strong = _text_contains(norm, kw_lower) or _text_contains(text, kw_lower)
            is_weak = False
            if not is_strong:
                kw_norm = normalize_text(kw)
                if (
                    _text_contains(norm, kw_norm)
                    or _text_contains(kw_norm, norm)
                    or _stem_match(norm, kw_lower)
                    or _stem_match(kw_norm, norm_lower)
                ):
                    is_weak = True
            if not (is_strong or is_weak):
                continue
            # Score: preferir keywords más largas y multi-palabra
            kw_len = len(kw_lower.split())
            base_score = (len(kw_lower) / 20.0) + (kw_len * 0.15)
            # Weak (stem) matches get a strong penalty. Specifically, if the
            # keyword is much longer than the user's input (i.e. the user typed
            # a subset of a multi-word keyword), we discard the match entirely
            # — this prevents "ayuda" from being mis-classified as
            # "ayuda a configurar notion" via stem match.
            if is_weak:
                input_word_count = len(re.findall(r"\w+", norm))
                if len(kw_lower.split()) > input_word_count:
                    continue  # keyword is longer than input — not a real match
                score = base_score * 0.5
            else:
                score = base_score
            if score > best_score:
                best_score = score
                best_intent = intent
                matched_keyword = kw

    # Boost confianza si el intent es claro
    confidence = min(0.99, 0.5 + best_score)
    if best_intent == "unknown":
        confidence = 0.0

    return {
        "intent": best_intent,
        "confidence": round(confidence, 3),
        "matched_keyword": matched_keyword,
        "normalized": norm,
        "entities": extract_entities(norm),
    }


def extract_entities(text: str) -> Dict[str, Any]:
    """Extrae entidades (carpetas, archivos, URLs, apps, etc.) del texto."""
    if not text:
        return {}

    entities: Dict[str, Any] = {}
    text_lower = text.lower()

    # Detectar carpeta coloquial
    for slang, real_folder in FOLDER_SLANG.items():
        if slang in text_lower:
            entities.setdefault("folders", []).append(real_folder)
            break

    # Detectar URLs
    urls = re.findall(r'https?://[^\s]+', text)
    if urls:
        entities["urls"] = urls

    # Detectar paths tipo C:\ o C:/ 
    paths = re.findall(r"[A-Za-z]:[\\\/][^\s]+", text)
    if paths:
        entities["paths"] = paths

    # Detectar apps mencionadas
    common_apps = [
        "chrome", "firefox", "edge", "brave", "opera", "safari",
        "word", "excel", "powerpoint", "outlook",
        "photoshop", "illustrator", "premiere", "after effects", "davinci",
        "spotify", "netflix", "youtube", "tiktok", "instagram", "facebook",
        "twitch", "discord", "slack", "zoom", "teams", "skype",
        "vscode", "visual studio", "pycharm", "intellij", "sublime",
        "blender", "unity", "unreal", "godot",
        "obs", "streamlabs",
        "calculator", "calculadora", "notepad", "bloc de notas",
        "paint", "terminal", "powershell", "cmd",
        "telegram", "whatsapp", "signal",
        "figma", "canva", "notion", "obsidian",
    ]
    mentioned_apps = [app for app in common_apps if app in text_lower]
    if mentioned_apps:
        entities["apps"] = mentioned_apps

    # Detectar números
    numbers = re.findall(r"\b\d+\b", text)
    if numbers:
        entities["numbers"] = [int(n) for n in numbers]

    # Detectar extensiones de archivo
    exts = re.findall(r"\.\w{2,4}\b", text)
    if exts:
        entities["file_extensions"] = list(set(exts))

    return entities


def understand(user_input: str) -> Dict[str, Any]:
    """
    Punto de entrada principal: tomar lo que dijo el usuario (en cualquier estilo)
    y entregar una interpretación estructurada para el LLM.
    """
    norm = normalize_text(user_input)
    intent_data = detect_intent(norm)
    return {
        "original": user_input,
        "normalized": norm,
        "intent": intent_data["intent"],
        "intent_confidence": intent_data["confidence"],
        "matched_keyword": intent_data["matched_keyword"],
        "entities": intent_data["entities"],
        "interpretation": _compose_interpretation(user_input, intent_data),
    }


def _compose_interpretation(original: str, intent_data: Dict[str, Any]) -> str:
    """Genera una interpretación legible para el LLM en español."""
    intent = intent_data["intent"]
    entities = intent_data["entities"]
    conf = intent_data["confidence"]

    parts = [
        f"[Interpretación de Automyx v2.5]",
        f"Original: \"{original}\"",
        f"Normalizado: \"{intent_data['normalized']}\"",
        f"Intent detectado: {intent} (confianza {conf:.0%})",
    ]
    if intent_data.get("matched_keyword"):
        parts.append(f"Palabra clave: \"{intent_data['matched_keyword']}\"")
    if entities:
        entities_str = ", ".join(f"{k}={v}" for k, v in entities.items())
        parts.append(f"Entidades: {entities_str}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Expansor de aliases de tools (mapeo de nombres coloquiales → nombre canónico)
# ---------------------------------------------------------------------------
TOOL_ALIASES: Dict[str, str] = {
    # Acciones de archivo
    "guardar_archivo": "write_file",
    "crear_archivo": "write_file",
    "escribir_archivo": "write_file",
    "make_file": "write_file",
    "save_file": "write_file",
    "put_file": "write_file",
    "guardar": "write_file",
    "crear_txt": "write_file",
    "crear_documento": "write_file",
    "crear_pdf": "write_file",
    "crear_imagen": "write_file",
    "crear_nota": "write_file",

    "leer_archivo": "read_file",
    "abrir_archivo": "read_file",
    "ver_archivo": "read_file",
    "mostrar_archivo": "read_file",
    "cat": "read_file",
    "open": "read_file",
    "view": "read_file",

    "crear_carpeta": "create_directory",
    "nueva_carpeta": "create_directory",
    "make_dir": "create_directory",
    "mkdir": "create_directory",
    "nuevo_directorio": "create_directory",
    "carpeta_nueva": "create_directory",

    "borrar": "delete_file",
    "eliminar": "delete_file",
    "remove": "delete_file",
    "del": "delete_file",
    "rm": "delete_file",
    "quitar": "delete_file",

    # Multimedia
    "reproducir_musica": "play_youtube_video",
    "play_music": "play_youtube_video",
    "play_song": "play_youtube_video",
    "pon_musica": "play_youtube_video",
    "reproduce_musica": "play_youtube_video",
    "play_youtube": "play_youtube_video",
    "play_video": "play_youtube_video",

    "reproducir_tiktok": "play_tiktok_desktop_video",
    "tiktok_video": "play_tiktok_desktop_video",
    "play_tt": "play_tiktok_desktop_video",
    "ver_tiktok": "play_tiktok_desktop_video",

    "crear_video": "generate_vyrex_video",
    "generar_video": "generate_vyrex_video",
    "make_video": "generate_vyrex_video",
    "video_ia": "generate_vyrex_video",

    "crear_imagen_ia": "generate_gemini_image",
    "generar_imagen": "generate_gemini_image",
    "dibujar": "generate_gemini_image",
    "ilustrar": "generate_gemini_image",
    "ai_image": "generate_gemini_image",

    "crear_pdf_pro": "pdf_create_report",
    "generar_pdf": "pdf_create_report",
    "make_pdf": "pdf_create_report",

    # Sistema
    "abrir_programa": "open_program",
    "lanzar_programa": "open_program",
    "ejecutar_programa": "open_program",
    "abrir_app": "open_program",
    "abrir_aplicacion": "open_program",
    "lanzar_app": "open_program",
    "abrir_software": "open_program",
    "open_app": "open_program",
    "launch_app": "open_program",
    "start_app": "open_program",
    "iniciar_app": "open_program",

    "ejecutar_comando": "execute_cmd",
    "correr_comando": "execute_cmd",
    "cmd_run": "execute_cmd",
    "run_shell": "execute_cmd",
    "shell": "execute_cmd",

    "cerrar_programa": "use_terminal_window",
    "cerrar_app": "use_terminal_window",
    "kill_app": "use_terminal_window",
    "close_app": "use_terminal_window",

    "escribir_texto": "type_text",
    "tipear": "type_text",
    "teclear": "type_text",
    "type": "type_text",

    "presionar_tecla": "press_key",
    "pulsar_tecla": "press_key",
    "click_en": "mouse_click",
    "click_sobre": "mouse_click",
    "mouse": "mouse_click",

    "captura": "screenshot",
    "screenshot_pc": "screenshot",
    "captura_pantalla": "screenshot",
    "toma_captura": "screenshot",
    "tomar_captura": "screenshot",

    "click_imagen": "ui_click_image",
    "click_por_imagen": "ui_click_image",
    "find_click": "ui_click_image",
    "image_click": "ui_click_image",

    # Web
    "abrir_web": "open_website",
    "abrir_pagina": "open_website",
    "ir_a": "open_website",
    "navegar": "open_website",
    "abrir_url": "open_website",
    "open_url": "open_website",
    "goto": "open_website",

    "google": "web_search",
    "buscar_google": "web_search",
    "search": "web_search",
    "search_web": "web_search",
    "investigar": "web_search",

    "scrape": "deep_web_scrape",
    "scrapear": "deep_web_scrape",
    "raspar_web": "deep_web_scrape",

    "descargar_archivo": "download_video",
    "bajar_archivo": "download_video",
    "bajar": "download_video",
    "download_file": "download_video",

    # Conversación
    "saludar": "greeting",
    "despedir": "farewell",
    "agradecer": "thanks",
    "ayudar": "help",

    # Código
    "correr_codigo": "execute_cmd",
    "correr_script": "execute_cmd",
    "test": "test_pytest",
    "pruebas": "test_pytest",
    "tests": "test_pytest",
    "pytest": "test_pytest",

    # Información
    "clima": "web_search",
    "tiempo": "web_search",
    "clima_hoy": "web_search",
    "pronostico": "web_search",
    "que_tal_clima": "web_search",
    "weather": "web_search",

    "traducir": "translate_text",
    "translate": "translate_text",

    "resumir": "doc_summarize",
    "summarize": "doc_summarize",
    "resumen": "doc_summarize",

    "explicar": "opencode_explain",
    "explain": "opencode_explain",
}


def resolve_tool_alias(tool_name: str) -> str:
    """Resuelve alias coloquiales de tools al nombre canónico registrado."""
    if not tool_name:
        return tool_name
    name_lower = tool_name.lower().strip()
    # Sin acentos
    name_norm = unicodedata.normalize("NFD", name_lower)
    name_norm = "".join(c for c in name_norm if unicodedata.category(c) != "Mn")
    return TOOL_ALIASES.get(name_lower) or TOOL_ALIASES.get(name_norm) or tool_name


# ---------------------------------------------------------------------------
# Catálogo de skills para onboard
# ---------------------------------------------------------------------------
SKILLS_CATALOG: Dict[str, List[Dict[str, str]]] = {
    "Productividad y Documentos": [
        {"name": "PDF Professional", "tools": "17", "icon": "📄",
         "desc": "Crear contratos, facturas, propuestas, currículums, NDAs, whitepapers con plantillas profesionales."},
        {"name": "Word/Excel/PowerPoint", "tools": "12", "icon": "📊",
         "desc": "Manipular documentos Office con python-docx, openpyxl, python-pptx."},
        {"name": "Markdown/Notion/Obsidian", "tools": "16", "icon": "📝",
         "desc": "Notas estructuradas, vault de Obsidian, sync con Notion API."},
        {"name": "OCR + Document Intelligence", "tools": "9", "icon": "🔍",
         "desc": "Extraer texto de PDFs/imágenes, NER, clasificar, resumir, comparar docs."},
        {"name": "JSON Tools Pro", "tools": "16", "icon": "🔧",
         "desc": "Validar, reparar, transformar, fusionar, hacer diff, queries JSONPath."},
    ],
    "Sistema y Archivos": [
        {"name": "PC Control", "tools": "20+", "icon": "🖥️",
         "desc": "Abrir apps, escribir, click, teclado, mouse, captura de pantalla."},
        {"name": "Universal App Control", "tools": "18", "icon": "🎛️",
         "desc": "Control TOTAL de cualquier app: mover, cerrar, redimensionar, automatizar."},
        {"name": "File System Pro", "tools": "12", "icon": "📁",
         "desc": "Crear/leer/escribir/organizar archivos, resolver rutas coloquiales."},
        {"name": "Terminal/Shell", "tools": "6", "icon": "⌨️",
         "desc": "Ejecutar comandos cmd/PowerShell/Bash, scripts Python."},
    ],
    "Multimedia": [
        {"name": "Video Editor Pro", "tools": "26", "icon": "🎬",
         "desc": "FFmpeg: trim, concat, transiciones, lower-third, slideshow, export para redes."},
        {"name": "Video Tools 2026", "tools": "16", "icon": "🎥",
         "desc": "Color grading, mastering, intros/outros, transiciones avanzadas."},
        {"name": "Audio Mastering", "tools": "8", "icon": "🎵",
         "desc": "Autotune, mezcla, master, extracción de audio."},
        {"name": "Image Editor Pro", "tools": "12", "icon": "🖼️",
         "desc": "Filtros, redimensión, collage, OCR, optimización."},
        {"name": "3D Studio (Blender)", "tools": "10", "icon": "🎲",
         "desc": "Modelos 3D, animaciones, físicas, entornos cinemáticos, scripts Blender."},
        {"name": "AI Image Generation", "tools": "4", "icon": "🎨",
         "desc": "Generar imágenes con Gemini/SDXL/DALL-E."},
        {"name": "AI Video Generation", "tools": "4", "icon": "🎞️",
         "desc": "Vyrex, Sora, Veo, generación cinemática IA."},
    ],
    "Web y Redes": [
        {"name": "Web Search + Scrape", "tools": "8", "icon": "🌐",
         "desc": "Google, Bing, deep scrape, anti-detección (Stealth Browser)."},
        {"name": "YouTube Player", "tools": "6", "icon": "▶️",
         "desc": "Reproducir, descargar, transcribir, analizar videos."},
        {"name": "TikTok Desktop", "tools": "8", "icon": "🎵",
         "desc": "Subir, programar, analizar trends, edición rápida."},
        {"name": "Social Media", "tools": "20+", "icon": "📱",
         "desc": "WhatsApp, Telegram, Discord, Slack, Teams, Instagram, Facebook, X, LinkedIn."},
    ],
    "Desarrollo": [
        {"name": "Code Review Pro", "tools": "5", "icon": "🔬",
         "desc": "Métricas, seguridad, linters, formateo, full review."},
        {"name": "Test Runner", "tools": "6", "icon": "🧪",
         "desc": "pytest, unittest, jest, go test, cargo test, auto-detect."},
        {"name": "GitHub Pro (gh CLI)", "tools": "14", "icon": "🐙",
         "desc": "Repos, issues, PRs, releases, workflows, clone."},
        {"name": "Git Advanced", "tools": "6", "icon": "🌿",
         "desc": "Merge strategies, conflict resolution, rebase, cherry-pick."},
        {"name": "OpenCode Bridge", "tools": "10", "icon": "🤖",
         "desc": "Code review, refactor, tests, explain, generate from spec."},
    ],
    "DevOps y Deploy": [
        {"name": "Docker + Compose", "tools": "8", "icon": "🐳",
         "desc": "Build, push, run, compose stacks, multi-stage builds."},
        {"name": "Kubernetes", "tools": "4", "icon": "☸️",
         "desc": "Apply manifests, get pods, logs, scale."},
        {"name": "Cloud Deploy", "tools": "6", "icon": "☁️",
         "desc": "Vercel, Netlify, Railway, SSH, SCP, health checks."},
    ],
    "Conocimiento y Datos": [
        {"name": "RAG Memory", "tools": "13", "icon": "🧠",
         "desc": "Vector store, indexar archivos/folders/URLs, query semántico."},
        {"name": "Academic Search", "tools": "6", "icon": "🎓",
         "desc": "arXiv, PubMed, Crossref, Semantic Scholar, citaciones, review."},
        {"name": "Database Pro", "tools": "8", "icon": "🗄️",
         "desc": "SQLite, Postgres, MySQL, Mongo: query, backup, diff."},
        {"name": "Data Science", "tools": "8", "icon": "📈",
         "desc": "Jupyter live kernel, SQL execution, análisis, gráficos."},
        {"name": "Translation", "tools": "4", "icon": "🌍",
         "desc": "Google, MyMemory, DeepL, batch translate, 100+ idiomas."},
    ],
    "Ciberseguridad": [
        {"name": "OSINT", "tools": "4", "icon": "🕵️",
         "desc": "Búsqueda de personas, emails, dominios, breach check."},
        {"name": "Port Scan + Nmap", "tools": "4", "icon": "🔓",
         "desc": "Escaneo de puertos, fingerprint, vulnerabilidades."},
        {"name": "Stealth Browser RPA", "tools": "16", "icon": "🕶️",
         "desc": "Bypass Cloudflare, reCAPTCHA, fingerprinting, proxy pool."},
    ],
    "Negocios y Finanzas": [
        {"name": "Accountant AFIP/SAT/SUNAT", "tools": "12", "icon": "💼",
         "desc": "Parsear facturas, reconciliar, calcular impuestos, validar IDs."},
        {"name": "Crypto Pro", "tools": "9", "icon": "💰",
         "desc": "Precios, conversión, market, history, análisis técnico, wallets."},
        {"name": "Calendar + Google Cal", "tools": "5", "icon": "📅",
         "desc": "iCal local, Google Calendar, find free time."},
    ],
    "Smart Home y Creatividad": [
        {"name": "Home Assistant", "tools": "2", "icon": "🏠",
         "desc": "Luces, persianas, climatización, escenas."},
        {"name": "Creative Studio", "tools": "6", "icon": "🎭",
         "desc": "Mermaid diagrams, ASCII art, generación de ideas."},
        {"name": "Diagram Generator", "tools": "4", "icon": "📊",
         "desc": "Flowcharts, UML, ER, Gantt, arquitectura."},
    ],
    "Productividad Avanzada": [
        {"name": "Project Autopilot", "tools": "8", "icon": "🚀",
         "desc": "Análisis + tests + commits + deploy, modo git pull + auto-improve."},
        {"name": "Skill Forger", "tools": "11", "icon": "⚒️",
         "desc": "Auto-crea skills detectando patrones, valida, promueve, archiva."},
        {"name": "Task Coordinator", "tools": "6", "icon": "🎯",
         "desc": "Resuelve paths, encuentra archivos, parsea intents, genera planes."},
        {"name": "Error Learning", "tools": "6", "icon": "📚",
         "desc": "Aprende de errores pasados, lecciones reutilizables por tool."},
        {"name": "Aumformbring Memory", "tools": "10", "icon": "🧬",
         "desc": "Memoria evolutiva, auto-mejora, búsqueda de patrones."},
        {"name": "Nexus Core", "tools": "6", "icon": "🌌",
         "desc": "Perfil de usuario, compresión de memoria, skill stats."},
    ],
    "OBS y Streaming": [
        {"name": "OBS WebSocket v5", "tools": "18", "icon": "📡",
         "desc": "Conectar OBS, scenes, sources, start/stop stream, bitrate, mod tools."},
    ],
    "Swarm y Multi-Agent": [
        {"name": "Swarm Orchestrator", "tools": "9", "icon": "🐝",
         "desc": "Distribuir tareas a múltiples nodos, map-reduce, pipeline, consensus."},
    ],
    "MCP e Integraciones": [
        {"name": "MCP (Model Context Protocol)", "tools": "8", "icon": "🔌",
         "desc": "Servidor MCP, integración con Claude, GPT, cualquier cliente."},
        {"name": "API Integrations Pro", "tools": "10", "icon": "🔗",
         "desc": "Conectores REST/GraphQL, OAuth, webhooks."},
    ],
    "Avanzadas / Élite": [
        {"name": "Codebase Healing", "tools": "1", "icon": "🩹",
         "desc": "Detecta y repara bugs de forma autónoma."},
        {"name": "Predictive Market", "tools": "1", "icon": "🔮",
         "desc": "Predicción de mercados con análisis técnico + IA."},
        {"name": "Smart Contract Audit", "tools": "1", "icon": "🛡️",
         "desc": "Auditoría de smart contracts (Solidity) y vulnerabilidades."},
        {"name": "Document Intelligence", "tools": "6", "icon": "🧠",
         "desc": "OCR multi-idioma, NER, clasificación, resumen, outline."},
        {"name": "Chain of Thought", "tools": "1", "icon": "🔗",
         "desc": "Razonamiento paso a paso para tareas complejas."},
        {"name": "Advanced Memory", "tools": "1", "icon": "🧩",
         "desc": "Memoria multi-nivel con compresión semántica."},
        {"name": "Workflow Manager", "tools": "1", "icon": "⚙️",
         "desc": "Editor de workflows visuales (DAG)."},
        {"name": "Script Editor Pro", "tools": "1", "icon": "📜",
         "desc": "Editor inteligente de scripts con syntax highlight y ejecución."},
    ],
    "Document Intelligence": [
        {"name": "OCR Multi-idioma", "tools": "3", "icon": "🔤",
         "desc": "Extraer texto de imágenes, PDFs escaneados, 100+ idiomas."},
        {"name": "NER (Entity Recognition)", "tools": "1", "icon": "🏷️",
         "desc": "Detectar personas, organizaciones, lugares, fechas, dinero."},
        {"name": "Document Classifier", "tools": "1", "icon": "📑",
         "desc": "Clasificar documentos por tipo y categoría."},
    ],
    "UI/UX y Diseño": [
        {"name": "Color Palette Generator", "tools": "1", "icon": "🎨",
         "desc": "Paletas armónicas desde imágenes o colores base."},
        {"name": "Logo Generator", "tools": "1", "icon": "✒️",
         "desc": "Logos vectoriales con SVG."},
        {"name": "Icon Set Generator", "tools": "1", "icon": "🖼️",
         "desc": "Conjuntos de iconos consistentes."},
    ],
    "Email y Comunicación": [
        {"name": "Email Pro", "tools": "6", "icon": "📧",
         "desc": "SMTP/IMAP, plantillas, archivos adjuntos, filtros."},
        {"name": "HR Tools", "tools": "4", "icon": "👥",
         "desc": "ATS, screening, generación de ofertas."},
    ],
    "Blockchain": [
        {"name": "Wallet Manager", "tools": "1", "icon": "👛",
         "desc": "Generar wallets multi-chain."},
        {"name": "DeFi Tracker", "tools": "1", "icon": "📊",
         "desc": "Seguir portafolios DeFi."},
    ],
    "Robótica y Hardware": [
        {"name": "Hardware Detector", "tools": "1", "icon": "🖥️",
         "desc": "Detecta GPU, CPU, RAM, OS, backend aceleración."},
        {"name": "Sensor Manager", "tools": "1", "icon": "📡",
         "desc": "Acceso a sensores locales (cámara, mic, GPS)."},
    ],
    "Educación y Salud": [
        {"name": "Quiz Generator", "tools": "1", "icon": "❓",
         "desc": "Genera quizzes desde cualquier contenido."},
        {"name": "Lesson Planner", "tools": "1", "icon": "📚",
         "desc": "Planes de lección personalizados."},
        {"name": "Workout Generator", "tools": "1", "icon": "💪",
         "desc": "Rutinas de ejercicio adaptadas."},
        {"name": "Meal Planner", "tools": "1", "icon": "🥗",
         "desc": "Planes de comidas y recetas."},
    ],
    "Idiomas y Traducción": [
        {"name": "Multi-idioma 100+", "tools": "4", "icon": "🌍",
         "desc": "Traducción con Google/MyMemory/DeepL, batch, detección."},
        {"name": "Language Tutor", "tools": "1", "icon": "🗣️",
         "desc": "Tutor conversacional en cualquier idioma."},
    ],
    "Audio y Música": [
        {"name": "Music Composer IA", "tools": "1", "icon": "🎼",
         "desc": "Composición musical con IA (estilo, tempo, duración)."},
        {"name": "Sound Effects", "tools": "1", "icon": "🔊",
         "desc": "Genera efectos de sonido para video."},
    ],
    "Geolocalización y Mapas": [
        {"name": "Maps Pro", "tools": "1", "icon": "🗺️",
         "desc": "Rutas, lugares cercanos, geocoding."},
        {"name": "Weather Pro", "tools": "1", "icon": "🌤️",
         "desc": "Clima actual, pronóstico 7 días, alertas."},
    ],
}


def count_skills() -> int:
    return sum(len(items) for items in SKILLS_CATALOG.values())


def count_tools_in_catalog() -> int:
    total = 0
    for items in SKILLS_CATALOG.values():
        for item in items:
            try:
                total += int(str(item.get("tools", "0")).replace("+", ""))
            except ValueError:
                pass
    return total


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        "ahorita guardame un txt en descargas",
        "oye, ábreme chrome porfa",
        "qiero crear una carpeta en el escritorio llamada 'proyecto nuevo'",
        "metele a youtube y pon bad bunny",
        "mándale un wspe a Juan diciéndole q llego tarde",
        "bájame el video ese de tiktok",
        "borra la carpeta Downloads vieja",
        "necesito editar el video del cumple, recortame los primeros 5 segundos",
        "hablame en inglés",
        "qué onda carnal, qué tal",
        "tirame un screenshot y mandamelo al correo",
    ]
    for t in tests:
        result = understand(t)
        print("─" * 60)
        print(result["interpretation"])


# ---------------------------------------------------------------------------
# Integration / channel target detection
# ---------------------------------------------------------------------------
# Maps user-friendly names → canonical integration ID + the env var that
# holds the token + the URL where the user can obtain it.
INTEGRATION_REGISTRY: Dict[str, Dict[str, str]] = {
    "notion":     {"id": "notion",     "name": "Notion",     "icon": "📚",
                   "env_var": "NOTION_API_KEY",
                   "help_url": "https://www.notion.so/my-integrations",
                   "validate": "https://api.notion.com/v1/users/me",
                   "format_hint": "Internal Integration Secret (ntn_... or secret_...)"},
    "github":     {"id": "github",     "name": "GitHub",     "icon": "🐙",
                   "env_var": "GITHUB_TOKEN",
                   "help_url": "https://github.com/settings/tokens",
                   "validate": "https://api.github.com/user",
                   "format_hint": "Personal Access Token (ghp_...)"},
    "telegram":   {"id": "telegram",   "name": "Telegram",   "icon": "✈️",
                   "env_var": "TELEGRAM_BOT_TOKEN",
                   "help_url": "https://t.me/BotFather",
                   "validate": "https://api.telegram.org/bot{TOKEN}/getMe",
                   "format_hint": "Bot Token de @BotFather (123456789:ABCdef...)"},
    "discord":    {"id": "discord",    "name": "Discord",    "icon": "💬",
                   "env_var": "DISCORD_BOT_TOKEN",
                   "help_url": "https://discord.com/developers/applications",
                   "validate": None,
                   "format_hint": "Bot Token del portal de Discord"},
    "instagram":  {"id": "instagram",  "name": "Instagram",  "icon": "📷",
                   "env_var": "INSTAGRAM_ACCESS_TOKEN",
                   "help_url": "https://developers.facebook.com/apps",
                   "validate": None,
                   "format_hint": "Page Access Token de Meta Graph API"},
    "whatsapp":   {"id": "whatsapp",   "name": "WhatsApp",   "icon": "🟢",
                   "env_var": None,
                   "help_url": "https://web.whatsapp.com",
                   "validate": None,
                   "format_hint": "Escanea QR con tu teléfono"},
    "openai":     {"id": "openai",     "name": "OpenAI",     "icon": "🅞",
                   "env_var": "OPENAI_API_KEY",
                   "help_url": "https://platform.openai.com/api-keys",
                   "validate": "https://api.openai.com/v1/models",
                   "format_hint": "API Key (sk-...)"},
    "anthropic":  {"id": "anthropic",  "name": "Anthropic",  "icon": "🅐",
                   "env_var": "ANTHROPIC_API_KEY",
                   "help_url": "https://console.anthropic.com/settings/keys",
                   "validate": None,
                   "format_hint": "API Key (sk-ant-...)"},
    "elevenlabs": {"id": "elevenlabs", "name": "ElevenLabs", "icon": "🗣️",
                   "env_var": "ELEVENLABS_API_KEY",
                   "help_url": "https://elevenlabs.io/app/settings/api-keys",
                   "validate": None,
                   "format_hint": "API Key de ElevenLabs"},
    "tavily":     {"id": "tavily",     "name": "Tavily",     "icon": "🔍",
                   "env_var": "TAVILY_API_KEY",
                   "help_url": "https://tavily.com",
                   "validate": None,
                   "format_hint": "API Key de Tavily"},
    "gemini":     {"id": "gemini",     "name": "Google Gemini", "icon": "🅖",
                   "env_var": "GEMINI_API_KEY",
                   "help_url": "https://aistudio.google.com/app/apikey",
                   "validate": None,
                   "format_hint": "API Key de Google AI Studio"},
    "groq":       {"id": "groq",       "name": "Groq",       "icon": "🅖",
                   "env_var": "GROQ_API_KEY",
                   "help_url": "https://console.groq.com/keys",
                   "validate": None,
                   "format_hint": "API Key de Groq"},
    "mistral":    {"id": "mistral",    "name": "Mistral",    "icon": "🅜",
                   "env_var": "MISTRAL_API_KEY",
                   "help_url": "https://console.mistral.ai/",
                   "validate": None,
                   "format_hint": "API Key de Mistral"},
}

# Aliases para que la detección de objetivo sea tolerante a jerga/typos
INTEGRATION_ALIASES: Dict[str, str] = {
    "notion": "notion", "notion app": "notion", "notionapi": "notion",
    "github": "github", "git": "github", "git hub": "github", "github api": "github",
    "telegram": "telegram", "tele": "telegram", "tg": "telegram", "telegram bot": "telegram",
    "discord": "discord", "ds": "discord", "discord bot": "discord",
    "instagram": "instagram", "ig": "instagram", "insta": "instagram", "instagram dm": "instagram",
    "whatsapp": "whatsapp", "wa": "whatsapp", "wpp": "whatsapp", "whats app": "whatsapp",
    "openai": "openai", "gpt": "openai", "chatgpt": "openai",
    "anthropic": "anthropic", "claude": "anthropic",
    "elevenlabs": "elevenlabs", "eleven labs": "elevenlabs", "eleven": "elevenlabs", "tts": "elevenlabs",
    "tavily": "tavily", "search": "tavily", "web search": "tavily",
    "gemini": "gemini", "google": "gemini", "bard": "gemini",
    "groq": "groq",
    "mistral": "mistral", "mixtral": "mistral",
}


def extract_integration_target(text: str) -> Optional[str]:
    """Detect which integration the user wants to configure in a setup_integration
    request. Returns the canonical ID (e.g. 'notion') or None.

    Uses a token-search through INTEGRATION_ALIASES, longest-match first.
    """
    if not text:
        return None
    text_lower = text.lower()
    # Sort by length desc so 'eleven labs' wins over 'eleven'
    for alias in sorted(INTEGRATION_ALIASES.keys(), key=len, reverse=True):
        if alias in text_lower:
            return INTEGRATION_ALIASES[alias]
    return None


def validate_integration_token(integration_id: str, token: str) -> Dict[str, Any]:
    """Best-effort live validation of an API token. Returns:
        {"ok": bool, "detail": str, "user_info": Optional[dict]}
    """
    info = INTEGRATION_REGISTRY.get(integration_id)
    if not info or not info.get("validate"):
        # No validator available — return ok=True (format-check only)
        return {"ok": True, "detail": "no live validator; format check only"}

    url = info["validate"]
    try:
        if integration_id == "notion":
            r = requests.get(
                "https://api.notion.com/v1/users/me",
                headers={"Authorization": f"Bearer {token}",
                         "Notion-Version": "2022-06-28"},
                timeout=10,
            )
            if r.status_code == 200:
                bot = r.json().get("bot", {}) or r.json()
                return {"ok": True, "detail": f"connected as '{bot.get('name', '?')}' ({bot.get('id', '?')[:8]}…)",
                        "user_info": bot}
            return {"ok": False, "detail": f"HTTP {r.status_code}: {r.text[:200]}"}
        if integration_id == "github":
            r = requests.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {token}"},
                timeout=10,
            )
            if r.status_code == 200:
                u = r.json()
                return {"ok": True, "detail": f"connected as '{u.get('login', '?')}'", "user_info": u}
            return {"ok": False, "detail": f"HTTP {r.status_code}: {r.text[:200]}"}
        if integration_id == "openai":
            r = requests.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if r.status_code == 200:
                return {"ok": True, "detail": f"OpenAI OK · {len(r.json().get('data', []))} models available"}
            return {"ok": False, "detail": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "detail": f"validation error: {e}"}
    return {"ok": True, "detail": "no validator; format check only"}
