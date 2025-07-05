import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import re
import logging
import requests
import json
from datetime import datetime

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN IMPORTANTE ---
# Configuración del bot de Telegram
API_KEY = '7596820597:AAFnJkKIEV3zbXmvgG80vzAAJsQet59PEmM'
# Pega tu clave de API de The Movie Database (TMDb) aquí. ¡Es crucial!
TMDB_API_KEY = '42090effb6fe9ca05ecdf5cbbee24132'

# IDs de los chats de trabajo
WORK_CHAT_IDS = [-1002399548246, -4634644543, -1002255075991] # GROUP_CHAT_ID, ADMIN_GROUP_ID y el nuevo chat
ADMIN_GROUP_ID = -4634644543
CHANNEL_ID = -1002176864902
ADMIN_USER_ID = 7753923473

# Configuración de Gemini
GEMINI_API_KEY = "AIzaSyAK4dCqDDoXXOK4IoTsjtQT76vZ9nXDRf4"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# --- NUEVO: CONFIGURACIÓN DE BASE DE DATOS LOCAL ---
DB_FILE = 'movies_database.json'

bot = telebot.TeleBot(API_KEY)
USER_STATES = {}

# --- NUEVO: FUNCIONES PARA MANEJAR LA BASE DE DATOS JSON ---
def load_database():
    """Carga la base de datos desde el archivo JSON."""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"El archivo {DB_FILE} no fue encontrado. Se creará uno nuevo.")
        return []
    except json.JSONDecodeError:
        logger.error(f"Error al decodificar el archivo JSON {DB_FILE}. Se creará uno nuevo.")
        return []

def save_database(data):
    """Guarda los datos en el archivo JSON."""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"No se pudo guardar la base de datos en {DB_FILE}: {e}")
        return False

def create_keyboard(buttons):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*[KeyboardButton(button) for button in buttons])
    return keyboard

def create_inline_keyboard(buttons):
    keyboard = InlineKeyboardMarkup()
    for row in buttons:
        keyboard.row(*[InlineKeyboardButton(text, callback_data=data) for text, data in row])
    return keyboard

# --- MODIFICADO: USA LA BASE DE DATOS LOCAL ---
def save_movie_to_database(title_spanish, title_original, year, media_type, plot, poster_url, message_link):
    """Guarda una nueva película en el archivo JSON."""
    logger.info(f"Intentando guardar '{title_spanish}' en la base de datos local.")
    movies_db = load_database()
    
    new_movie = {
        'title_spanish': title_spanish,
        'title_original': title_original,
        'year': year,
        'media_type': media_type,
        'plot': plot,
        'poster_url': poster_url,
        'message_link': message_link,
        'created_at': datetime.now().isoformat(), # Guardar fecha como string
        'status': 'active'
    }
    
    movies_db.append(new_movie)
    
    if save_database(movies_db):
        logger.info(f"Película '{title_spanish}' guardada exitosamente en {DB_FILE}.")
        return True
    else:
        logger.error(f"Fallo al guardar la película '{title_spanish}'.")
        return False

# --- MODIFICADO: USA LA BASE DE DATOS LOCAL ---
def search_movie_in_database(query):
    """Busca en el archivo JSON y devuelve solo resultados únicos."""
    logger.info(f"Buscando '{query}' en la base de datos local.")
    movies_db = load_database()
    query_lower = query.lower()
    
    results = []
    found_movies = set()

    for movie_data in movies_db:
        title_spanish = movie_data.get('title_spanish', '').lower()
        title_original = movie_data.get('title_original', '').lower()
        year = movie_data.get('year', '')

        unique_identifier = (title_spanish, year)

        if (query_lower in title_spanish or
            query_lower in title_original or
            any(word in title_spanish for word in query_lower.split()) or
            any(word in title_original for word in query_lower.split())):
            
            if unique_identifier not in found_movies:
                results.append(movie_data)
                found_movies.add(unique_identifier)
                
    logger.info(f"Se encontraron {len(results)} resultados únicos para '{query}'.")
    return results

def is_movie_query_with_gemini(text):
    try:
        prompt = f"""
        Analiza el siguiente mensaje de un usuario en un grupo de Telegram.
        Tu única tarea es determinar si el usuario está preguntando por una película o serie.
        Responde SOLAMENTE con la palabra 'BUSCAR' si la intención es encontrar o preguntar por la disponibilidad de una película o serie.
        De lo contrario, responde SOLAMENTE con la palabra 'IGNORAR'.
        Mensaje del usuario: "{text}"
        """
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(GEMINI_URL, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        decision = result['candidates'][0]['content']['parts'][0]['text'].strip().upper()
        logger.info(f"Decisión de Gemini para '{text}': {decision}")
        return decision == 'BUSCAR'
    except Exception as e:
        logger.error(f"Error en is_movie_query_with_gemini: {e}")
        return any(keyword in text.lower() for keyword in ['película', 'serie', 'tienen', 'busco', 'está'])

def ask_gemini(user_question, movie_database=None):
    try:
        if movie_database is None:
            movie_database = search_movie_in_database(user_question)

        context_prompt = f"""
        Eres Lucy, la asistente IA del canal de películas y series CINEPELIS 🍿.
        Tu trabajo es ayudar a los usuarios a encontrar contenido disponible en nuestro canal.
        Base de datos del contenido disponible (ya filtrada para no tener duplicados):
        {json.dumps(movie_database, indent=2, ensure_ascii=False)}

        Pregunta del usuario: {user_question}

        Instrucciones:
        1. Tu tono debe ser siempre amigable, servicial y un poco entusiasta. Preséntate siempre como Lucy de CINEPELIS 🍿.
        2. Analiza la pregunta del usuario y la base de datos.
        3. SI ENCUENTRAS UNO O MÁS RESULTADOS:
           - Responde con un mensaje alegre como "¡Claro que sí! Encontré esto para ti:"
           - Luego, crea una lista con viñetas (usando "-").
           - CADA elemento de la lista DEBE tener el siguiente formato Markdown EXACTO:
             - *Título* (Año): [Ver Aquí](message_link)
           - Ejemplo de lista:
             - *Bad Boys for Life* (2020): [Ver Aquí](https://t.me/c/...)
             - *Dos policías rebeldes II* (2003): [Ver Aquí](https://t.me/c/...)
           - NO incluyas ninguna otra información en la lista, solo los elementos con ese formato.
        4. SI NO ENCUENTRAS NINGÚN RESULTADO:
           - Responde amablemente que por el momento NO está disponible.
           - Sugiere al usuario que puede hacer una petición oficial hablando contigo en privado. Ejemplo: "¡Hola! Soy Lucy 🍿. Busqué '{user_question}' pero no lo encontré en nuestro catálogo por ahora. ¡No te preocupes! Puedes hablar conmigo en privado para hacer una petición oficial."
        5. Responde siempre de forma clara y concisa.
        """
        payload = {"contents": [{"parts": [{"text": context_prompt}]}]}
        response = requests.post(GEMINI_URL, json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()
        ai_response = result['candidates'][0]['content']['parts'][0]['text']
        return ai_response
    except Exception as e:
        logger.error(f"Error al consultar Gemini: {e}")
        return "¡Hola! Soy Lucy 🍿. Parece que mi cerebro de IA está un poco sobrecargado ahora mismo. Por favor, intenta tu consulta de nuevo en un momento."


def search_media_tmdb(query):
    try:
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={query}&language=es-ES&include_adult=false"
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()
        if data['results']:
            for result in data['results']:
                media_type = result.get('media_type')
                if media_type in ['movie', 'tv']:
                    title = result.get('title') or result.get('name', 'Título no encontrado')
                    original_title = result.get('original_title') or result.get('original_name', '')
                    plot = result.get('overview', 'Descripción no disponible.')
                    poster_path = result.get('poster_path')
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                    year = ''
                    if 'release_date' in result and result['release_date']:
                        year = result['release_date'].split('-')[0]
                    elif 'first_air_date' in result and result['first_air_date']:
                        year = result['first_air_date'].split('-')[0]
                    return {
                        'title_spanish': title,
                        'title_original': original_title,
                        'year': year,
                        'plot': plot,
                        'poster_url': poster_url,
                        'media_type': 'PELÍCULA' if media_type == 'movie' else 'SERIE'
                    }
            logger.warning(f"No se encontraron resultados para '{query}', pero ninguno era película o serie.")
            return None
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con la API de TMDb: {e}")
        return None
    except Exception as e:
        logger.error(f"Error procesando datos de TMDb: {e}", exc_info=True)
        return None

def validate_petition_format(text):
    patterns = {
        'Nombre': re.compile(r"Nombre:(.*)", re.IGNORECASE),
        'Año': re.compile(r"Año:(.*)", re.IGNORECASE),
        'Temporadas': re.compile(r"Temporadas:(.*)", re.IGNORECASE),
        'Idioma': re.compile(r"Idioma:(.*)", re.IGNORECASE)
    }
    
    data = {}
    for key, pattern in patterns.items():
        match = pattern.search(text)
        if not match:
            return None
        data[key] = match.group(1).strip()

    if not data['Nombre'] or not data['Año'] or not data['Idioma']:
        return None
        
    return data


@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type != 'private':
        return
    username = message.from_user.first_name
    welcome_message = f"Hola {username}, soy Lucy 🤖 de CINEPELIS 🍿\n\n¿En qué puedo ayudarte hoy?\n\n🎬 También puedes escribirme directamente el nombre de una película o serie para buscarla."
    keyboard = create_keyboard(["Hacer una Petición", "Tengo una Queja/Sugerencia", "Buscar Película/Serie"])
    bot.send_message(message.chat.id, welcome_message, reply_markup=keyboard)
    USER_STATES[message.chat.id] = 'WAITING_FOR_OPTION'

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id, '').startswith('CHATTING_WITH_ADMIN_'), content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice'])
def user_chatting_with_admin(message):
    try:
        admin_chat_id = int(USER_STATES[message.chat.id].split('_')[-1])
        user_info = f"💬 Mensaje de {message.from_user.first_name} (@{message.from_user.username or 'N/A'}):"
        bot.send_message(admin_chat_id, user_info)
        bot.forward_message(admin_chat_id, message.chat.id, message.message_id)
    except Exception as e:
        logger.error(f"Error reenviando mensaje de usuario a admin: {e}")
        bot.send_message(message.chat.id, "Hubo un error al enviar tu mensaje. Por favor, intenta de nuevo.")

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id, '').startswith('CHATTING_WITH_USER_'), content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice'])
def admin_chatting_with_user(message):
    try:
        user_id = int(USER_STATES[message.chat.id].split('_')[-1])
        admin_name = message.from_user.first_name
        
        if message.text:
            bot.send_message(user_id, f"Respuesta del administrador {admin_name}:\n\n{message.text}")
        else:
            bot.send_message(user_id, f"Respuesta del administrador {admin_name}:")
            bot.forward_message(user_id, message.chat.id, message.message_id)

        bot.send_message(message.chat.id, "✅ Mensaje enviado al usuario.")
    except Exception as e:
        logger.error(f"Error enviando mensaje de admin a usuario: {e}")
        bot.send_message(message.chat.id, "Hubo un error al enviar tu respuesta. La conversación podría haberse cerrado.")


@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'], content_types=['document', 'video', 'text'])
def unified_group_handler(message):
    logger.info(f"Manejador unificado de grupos activado para el chat {message.chat.id} con tipo de contenido {message.content_type}")

    if message.chat.id in WORK_CHAT_IDS and message.content_type in ['document', 'video']:
        logger.info(f"Detectada subida de multimedia en grupo de trabajo. Procesando...")
        try:
            if message.caption:
                media_name = message.caption.split('\n')[0]
            elif message.document:
                media_name = message.document.file_name
            elif message.video:
                media_name = message.video.file_name
            else:
                logger.warning("El archivo multimedia no tiene caption ni nombre de archivo.")
                return

            cleaned_name = re.sub(r'\([^)]*\)', '', media_name).split('.')[0].strip()
            logger.info(f"Buscando en TMDb información para: '{cleaned_name}'")
            media_info = search_media_tmdb(cleaned_name)
            
            if media_info:
                logger.info(f"Información encontrada para '{cleaned_name}': {media_info['title_spanish']}")
                title_es = media_info['title_spanish']
                title_original = media_info['title_original']
                year = media_info['year']
                plot_es = media_info['plot']
                poster_url = media_info['poster_url']
                media_type = media_info['media_type']
                message_link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"

                save_movie_to_database(
                    title_spanish=title_es,
                    title_original=title_original,
                    year=year,
                    media_type=media_type,
                    plot=plot_es,
                    poster_url=poster_url,
                    message_link=message_link
                )
                display_title = title_original if title_original and title_original != title_es else title_es
                caption = (f"*{display_title}* ({year})\n\n"
                           f"{plot_es[:200]}...\n\n"
                           f"[VER {media_type} {display_title.upper()} AQUÍ]({message_link})\n\n"
                           "[CINEPELIS �](https://t.me/pelicuilasymasg)")
                try:
                    if poster_url:
                        logger.info(f"Enviando foto al canal {CHANNEL_ID}")
                        bot.send_photo(CHANNEL_ID, poster_url, caption=caption, parse_mode='Markdown')
                    else:
                        logger.warning("No se encontró poster, enviando solo texto.")
                        bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                    logger.info("Publicación enviada al canal exitosamente.")
                except Exception as e:
                    logger.error(f"Error al enviar la portada al canal: {e}")
                    bot.reply_to(message, "Hubo un error al crear la portada para el canal.")
            else:
                logger.warning(f"No se encontró información en TMDb para: '{cleaned_name}'")
                bot.reply_to(message, "No se pudo encontrar información sobre esta película o serie. Por favor, asegúrate de que el nombre en el subtítulo es correcto.")
        except Exception as e:
            logger.error(f"Error en handle_media_upload: {e}", exc_info=True)
            bot.reply_to(message, "Ocurrió un error general al procesar el archivo.")
        return

    if message.chat.id not in WORK_CHAT_IDS and message.content_type == 'text':
        logger.info(f"Detectado mensaje de texto en grupo público. Consultando a Gemini...")
        if is_movie_query_with_gemini(message.text):
            try:
                bot.send_chat_action(message.chat.id, 'typing')
                ai_response = ask_gemini(message.text)
                bot.reply_to(message, ai_response, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error al procesar consulta con Gemini en grupo: {e}")
                bot.reply_to(message, "Lo siento, tuve un problema para procesar tu búsqueda. ¡Pero no te rindas! Inténtalo de nuevo.")
        else:
            logger.info("Gemini determinó que el mensaje no es una consulta de película. Ignorando.")
        return
    
    logger.info(f"El mensaje en el chat {message.chat.id} no cumple ninguna condición del manejador unificado. Ignorando.")


@bot.message_handler(func=lambda message: message.chat.type == 'private' and USER_STATES.get(message.chat.id) == 'WAITING_FOR_OPTION')
def handle_option(message):
    if message.text == "Tengo una Queja/Sugerencia":
        bot.send_message(message.chat.id, "Entendido. Por favor, describe tu queja o sugerencia en un solo mensaje. Sé lo más detallado posible.")
        USER_STATES[message.chat.id] = 'WAITING_FOR_COMPLAINT'
    elif message.text == "Hacer una Petición":
        bot.send_message(message.chat.id, "¡Claro! Pero primero, asegúrate de haber buscado bien en el canal. ¿Estás seguro/a de que lo que pides NO está ya disponible?", reply_markup=create_keyboard(["Sí, estoy seguro", "No, déjame revisar"]))
        USER_STATES[message.chat.id] = 'CONFIRMING_REQUEST'
    elif message.text == "Buscar Película/Serie":
        bot.send_message(message.chat.id, "🎬 ¡Perfecto! Escribe el nombre de la película o serie que buscas:")
        USER_STATES[message.chat.id] = 'SEARCHING_MOVIE'
    else: 
        handle_movie_search(message)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    try:
        action, user_id_str = call.data.split('_', 1)
        user_id = int(user_id_str)
        admin_chat_id = call.message.chat.id
        admin_user = call.from_user

        if action == "talk" or action == "info":
            bot.answer_callback_query(call.id, "Conectando con el usuario...")
            USER_STATES[user_id] = f'CHATTING_WITH_ADMIN_{admin_chat_id}'
            USER_STATES[admin_chat_id] = f'CHATTING_WITH_USER_{user_id}'

            bot.send_message(user_id, "✅ Un administrador se ha conectado para hablar contigo. Puedes escribir tu respuesta aquí.")
            
            end_chat_button = create_inline_keyboard([[("Finalizar Chat", f"endchat_{user_id}")]])
            bot.edit_message_text(f"✅ Conectado con el usuario. Ahora puedes chatear directamente.",
                                  chat_id=admin_chat_id, message_id=call.message.message_id, reply_markup=None)
            bot.send_message(admin_chat_id, f"Conversación activa con el usuario {user_id}. Para terminar, pulsa el botón.", reply_markup=end_chat_button)

        elif action == "endchat":
            bot.answer_callback_query(call.id, "Finalizando chat...")
            
            bot.send_message(user_id, f"El administrador {admin_user.first_name} ha finalizado esta conversación. Si necesitas algo más, puedes iniciar una nueva consulta con /start.")
            
            bot.edit_message_text(f"Conversación con {user_id} finalizada por {admin_user.first_name}.",
                                  chat_id=admin_chat_id, message_id=call.message.message_id, reply_markup=None)
            
            if user_id in USER_STATES:
                USER_STATES.pop(user_id)
            if admin_chat_id in USER_STATES:
                USER_STATES.pop(admin_chat_id)
        
        elif action == "reject":
            bot.answer_callback_query(call.id, "Has rechazado la consulta")
            bot.send_message(user_id, "Lo sentimos, en este momento los administradores no pueden atender tu consulta. Por favor, intenta más tarde.")
            bot.edit_message_text(f"Consulta rechazada por {admin_user.first_name}.",
                                  chat_id=admin_chat_id, message_id=call.message.message_id, reply_markup=None)
            USER_STATES.pop(user_id, None)

        elif action == "taken":
            bot.answer_callback_query(call.id, "Petición marcada como 'en proceso'")
            bot.send_message(user_id, f"¡Buenas noticias! El administrador {admin_user.first_name} ha tomado tu petición y la está buscando. ¡Mantente atento al canal!")
            bot.edit_message_text(f"Petición marcada como 'en proceso' por {admin_user.first_name}.",
                                  chat_id=admin_chat_id, message_id=call.message.message_id, reply_markup=None)
        elif action == "exists":
            bot.answer_callback_query(call.id, "Notificando al usuario")
            bot.send_message(user_id, "Un administrador ha revisado tu petición y nos informa que lo que buscas ¡ya está disponible en el grupo! Por favor, usa la lupa 🔍 para buscarlo. También puedes preguntarme directamente a mí.")
            bot.edit_message_text(f"Notificación de 'ya existe' enviada por {admin_user.first_name}.",
                                  chat_id=admin_chat_id, message_id=call.message.message_id, reply_markup=None)

    except ValueError:
        logger.error(f"Error al procesar callback_data: {call.data}")
        bot.answer_callback_query(call.id, "Error: Callback inválido.")
    except Exception as e:
        logger.error(f"Error en handle_query: {e}", exc_info=True)


@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_COMPLAINT', content_types=['text'])
def handle_complaint(message):
    user_info = f"Nueva queja/sugerencia de {message.from_user.first_name} (@{message.from_user.username or 'N/A'}):"
    keyboard = create_inline_keyboard([[
        ("Hablar con el usuario", f"talk_{message.chat.id}"),
        ("Rechazar", f"reject_{message.chat.id}")
    ]])
    bot.send_message(ADMIN_GROUP_ID, f"{user_info}\n\n_{message.text}_", reply_markup=keyboard, parse_mode='Markdown')
    bot.send_message(message.chat.id, "Gracias. Tu mensaje ha sido enviado a los administradores. Si es necesario, se pondrán en contacto contigo.")
    ask_for_more(message.chat.id)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_REQUEST', content_types=['text', 'photo'])
def handle_request(message):
    petition_text = message.text if message.content_type == 'text' else message.caption
    
    if not petition_text:
        bot.send_message(message.chat.id, "Por favor, envía tu petición como texto o como una foto con el texto en la descripción.")
        return

    validated_data = validate_petition_format(petition_text)

    if validated_data:
        user_info = f"Petición de {message.from_user.first_name} (@{message.from_user.username or 'N/A'}):"
        keyboard = create_inline_keyboard([
            [("Marcar como 'en proceso'", f"taken_{message.chat.id}"), ("Notificar que ya existe", f"exists_{message.chat.id}")],
            [("Pedir más información", f"info_{message.chat.id}")]
        ])
        
        if message.content_type == 'photo':
            bot.forward_message(ADMIN_GROUP_ID, message.chat.id, message.message_id)
        
        bot.send_message(ADMIN_GROUP_ID, f"{user_info}\n\n_{petition_text}_", reply_markup=keyboard, parse_mode='Markdown')
        bot.send_message(message.chat.id, "✅ ¡Petición recibida y validada! Ha sido enviada a los administradores. Te notificaremos sobre su estado.")
        ask_for_more(message.chat.id)
    else:
        error_message = """
        ❌ **Formato de petición incorrecto.**

        Por favor, asegúrate de que tu mensaje sigue este formato exacto (puedes copiar y pegar):

        ```
        Nombre: [Nombre de la película o serie]
        Año: [Año de estreno]
        Temporadas: [Número de temporadas, o déjalo en blanco si es una película]
        Idioma: [Idioma que solicitas, ej: Castellano]
        ```

        Inténtalo de nuevo.
        """
        bot.send_message(message.chat.id, error_message, parse_mode='Markdown')

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'SEARCHING_MOVIE')
def handle_movie_search(message):
    try:
        query = message.text
        bot.send_message(message.chat.id, "🔍 Un momento, estoy buscando en la base de datos de CINEPELIS...")
        bot.send_chat_action(message.chat.id, 'typing')
        ai_response = ask_gemini(message.text)
        bot.send_message(message.chat.id, ai_response, parse_mode='Markdown')
        ask_for_more(message.chat.id)
    except Exception as e:
        logger.error(f"Error en búsqueda privada: {e}")
        bot.send_message(message.chat.id, "Lo siento, hubo un error al buscar. Intenta de nuevo más tarde.")
        ask_for_more(message.chat.id)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'CONFIRMING_REQUEST')
def confirm_request(message):
    if message.text == "Sí, estoy seguro":
        instruction_message = """
        De acuerdo. Por favor, envía tu petición en un solo mensaje usando el siguiente formato estricto. Puedes adjuntar una foto si lo deseas.

        *Formato obligatorio:*
        ```
        Nombre: [Nombre de la película o serie]
        Año: [Año de estreno]
        Temporadas: [Número de temporadas, o déjalo en blanco si es una película]
        Idioma: [Idioma que solicitas, ej: Castellano]
        ```
        """
        bot.send_message(message.chat.id, instruction_message, parse_mode='Markdown')
        USER_STATES[message.chat.id] = 'WAITING_FOR_REQUEST'
    elif message.text == "No, déjame revisar":
        bot.send_message(message.chat.id, "¡Excelente! Tómate tu tiempo para buscar. Puedes usar la lupa 🔍 en el canal o preguntarme directamente aquí. Si no lo encuentras, vuelve a iniciar el proceso de petición.")
        ask_for_more(message.chat.id)
    else:
        bot.send_message(message.chat.id, "Por favor, responde con una de las opciones del teclado.", reply_markup=create_keyboard(["Sí, estoy seguro", "No, déjame revisar"]))

def ask_for_more(chat_id):
    keyboard = create_keyboard(["Hacer una Petición", "Tengo una Queja/Sugerencia", "Buscar Película/Serie", "No, gracias"])
    bot.send_message(chat_id, "¿Puedo ayudarte en algo más?", reply_markup=keyboard)
    USER_STATES[chat_id] = 'WAITING_FOR_MORE'

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_MORE')
def handle_more(message):
    if message.text == "No, gracias":
        bot.send_message(message.chat.id, "¡De acuerdo! Ha sido un placer ayudarte. ¡Que disfrutes de CINEPELIS 🍿!")
        USER_STATES.pop(message.chat.id, None)
    else:
        USER_STATES[message.chat.id] = 'WAITING_FOR_OPTION'
        handle_option(message)


if __name__ == '__main__':
    if TMDB_API_KEY == 'TU_API_KEY_DE_TMDB_AQUÍ':
        logger.error("LA CLAVE DE API DE TMDB NO HA SIDO CONFIGURADA. Por favor, edita el script y añade tu clave.")
    else:
        # Bucle guardián para reiniciar el bot en caso de fallo
        while True:
            try:
                logger.info("Iniciando el bot con funcionalidades mejoradas y bucle guardián...")
                # Aumentar el timeout para hacer la conexión más robusta
                bot.infinity_polling(skip_pending=True, timeout=40, long_polling_timeout=60)
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                logger.error(f"Error de red detectado: {e}", exc_info=True)
                logger.info("Pausa de 15 segundos antes de reiniciar debido a error de red...")
                time.sleep(15)
            except Exception as e:
                logger.error(f"El bot se ha detenido debido a un error inesperado: {e}", exc_info=True)
                logger.info("Reiniciando el bot en 20 segundos...")
                time.sleep(20)
