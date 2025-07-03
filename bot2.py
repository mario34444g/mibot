import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import re
import logging
import requests
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Configuración de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN IMPORTANTE ---
# Configuración del bot de Telegram
API_KEY = '7596820597:AAFnJkKIEV3zbXmvgG80vzAAJsQet59PEmM'
# Pega tu clave de API de The Movie Database (TMDb) aquí. ¡Es crucial!
TMDB_API_KEY = '42090effb6fe9ca05ecdf5cbbee24132' 

# IDs de los chats
GROUP_CHAT_ID = -1002399548246
ADMIN_GROUP_ID = -4634644543
CHANNEL_ID = -1002176864902
ADMIN_USER_ID = 7753923473

# Configuración de Gemini
GEMINI_API_KEY = "AIzaSyAK4dCqDDoXXOK4IoTsjtQT76vZ9nXDRf4"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# Inicializar Firebase
firebase_config = {
    "type": "service_account",
    "project_id": "base-de-datos-elecciones-6e9d5",
    "private_key_id": "fd23142b53ca7b6ae2113e9d5abbb7f2599cef9a",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDnWRO2hmfYinO0\nzLxX7PUnLcM2jImzGGBLkPAwkrYZwGzqMlojimQ+yq/3pO2RUZxX8eoFS4f3uAcm\n7vjFnnA9xo3BZ8geR1OSdbam4G3nJqzwlYIXHu+EuRvppK8rRSJUlomfL3CnLCyC\nNRmCglgxqOzwP+6XXwxd18XhkfFOwpdPjFKe5HDrSTOBPcMLFiBtW/W9QnQJ6tNR\nh8zXM5h7lliLDjwJ48wEGidxY1dlDny7mSP72Z4avmGIJUrJCzwl83njalmsA+fq\nMNqXyk0AOtlWc9yliUb71FxOxyL+ALoiWqKhG3LKnhOrYJ/Ll+J52Sb9US5DEnw6\nEBvXo/vzAgMBAAECggEADTeAq067Bw5EQi61W3z9Nat+uawsv7xJ4BDoz/WWjRqt\nSwuGX8prvYFp4GC3qJovfH/xfTNaXyCDdBap94XjAElKiiNjz1FtQlkSqGHHYmT9\njOvifm/bgjGEstC52zB8OU+CXEN8qmhMWkH7WGizuvgqIfQDei1jCpQ/SPEQ03Pc\n4NH9oxRtXgdETvJylwlxGLvzYr4bm1BDbbb+mXScrCmB/Bm7xV/+wcBSz/GRowdm\naqDG51nURUd1p0N56M51JhrHztxvRBTTztKv3ydos5wDZIXUtCDvLCHyePpCxPIq\nquX+RTfApP8V3uXoOm8/jN9F2t2KU/cpXDaOQSAyUQKBgQD/cz7CV9cvv9CoPD3Y\neq4kue+pFB5Q9xXWcGNRpLra/Ps4izvrcE2hGUiBfgwFkYMwWOi5DK/BxAZNCccQ\nCd8inZwzm301E97QUnpG0KFtd9wXeItLEoOaoQJId+PviE2SqYDjQJcHmDJ0Fr6N\nkbXPUgTV8X01SuXhy/ybN7UNkQKBgQDn2I0l0GQGbPpX2eT5aoERQsszmFzQ3aHM\nyxjZjNkSHcTUf/lhBdpJZvQnAlm8DX7g5jbaXKDg1lLnivXpqbY7gOSYrQkGLGv2\nebz/enAwx9IHfydh29MQBPK0kKa1BYsIAHW7Wxm3as586L3kEFVsV2/PujXDB1Hh\nDjNjN97/QwKBgQDKBuQQoZX/Ho2wMAydg9DsHN1s9AtR70gnEzWJYWWiQceRnZRj\nDKtoiG1udDifwshlWTuc9mqeLSDqlpwHlDcT0mCx8/wfGTrzuPcZwHCa+dtn+J75\nXYgVp9b9Z0wuqbboEgRsNi38BKOKal6D6kRG1dAbP+TNXBHY9RIv0+vt8QKBgQC1\nydOq0cKMU0jcN4rVkpAPM7tXAmHMl+u1Q46BjnHqRZM/N/UXAVrOcT6Bk9M+o6pX\nt8tM3pJ6mTK6QPhfNeYgtAkKOas4vv4MbhomjB+J8DQcErSTg6T0C50uvbkpeWYx\naQLnXCBG9CViRbAXMkN4xvpx+8UJ3iRyfgsHAhkFNwKBgCBPK4LDkiSroXAn8mpb\nWIwwWBJylJuBv2a+1dWB6/NvvdCIHt2y76jXLtEFxNV7Za9Qd33U1C0Q6aW85DBO\nP0N5302OprBT1GLCTScgdhUo7J/zQvR6GmcRA3Z8YkyWyEh/GF5Ev0wLcZggshf2\nWvOrkeGgO7BjLdeHIyE45ER3\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-fbsvc@base-de-datos-elecciones-6e9d5.iam.gserviceaccount.com",
    "client_id": "116973578837058387528",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40base-de-datos-elecciones-6e9d5.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

try:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase inicializado correctamente")
except Exception as e:
    logger.error(f"Error al inicializar Firebase: {e}")
    db = None

bot = telebot.TeleBot(API_KEY)
USER_STATES = {}

def create_keyboard(buttons):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*[KeyboardButton(button) for button in buttons])
    return keyboard

def create_inline_keyboard(buttons):
    keyboard = InlineKeyboardMarkup()
    for text, callback_data in buttons:
        keyboard.add(InlineKeyboardButton(text, callback_data=callback_data))
    return keyboard

def save_movie_to_database(title_spanish, title_original, year, media_type, plot, poster_url, message_link):
    try:
        if not db:
            logger.error("Base de datos no inicializada")
            return False
        doc_ref = db.collection('movies').document()
        doc_ref.set({
            'title_spanish': title_spanish,
            'title_original': title_original,
            'year': year,
            'media_type': media_type,
            'plot': plot,
            'poster_url': poster_url,
            'message_link': message_link,
            'created_at': datetime.now(),
            'status': 'active'
        })
        logger.info(f"Película guardada en BD: {title_spanish}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar en BD: {e}")
        return False

# --- FUNCIÓN CORREGIDA ---
def search_movie_in_database(query):
    """Buscar película/serie en la base de datos de Firebase."""
    try:
        if not db:
            return []
            
        movies_ref = db.collection('movies')
        query_lower = query.lower()
        
        results = []
        docs = movies_ref.stream()
        
        for doc in docs:
            movie_data = doc.to_dict()
            
            # **LA SOLUCIÓN ESTÁ AQUÍ**
            # Convertimos el objeto de fecha de Firestore a un string
            # antes de que llegue a la función de Gemini.
            if 'created_at' in movie_data and hasattr(movie_data['created_at'], 'isoformat'):
                movie_data['created_at'] = movie_data['created_at'].isoformat()

            title_spanish = movie_data.get('title_spanish', '').lower()
            title_original = movie_data.get('title_original', '').lower()
            
            if (query_lower in title_spanish or 
                query_lower in title_original or
                any(word in title_spanish for word in query_lower.split()) or
                any(word in title_original for word in query_lower.split())):
                results.append(movie_data)
        
        return results
    except Exception as e:
        logger.error(f"Error al buscar en BD: {e}")
        return []

def ask_gemini(user_question, movie_database=None):
    """Consultar a Gemini con contexto de la base de datos."""
    try:
        if movie_database is None:
            movie_database = search_movie_in_database(user_question)

        context_prompt = f"""
        Eres Lucy, la asistente del canal de películas y series CINEPELIS 🍿. 
        Tu trabajo es ayudar a los usuarios a encontrar contenido disponible en nuestro canal.
        Base de datos de películas y series disponibles:
        {json.dumps(movie_database, indent=2, ensure_ascii=False)}
        
        Pregunta del usuario: {user_question}
        
        Instrucciones:
        1. Si el usuario pregunta por una película/serie específica, busca en la base de datos.
        2. Si la encuentras, responde que SÍ está disponible y proporciona el enlace ('message_link').
        3. Si no la encuentras, responde amablemente que NO está disponible y sugiere que haga una petición.
        4. Si la pregunta es general o una recomendación, usa la base de datos para sugerir contenido.
        5. Mantén un tono amigable y útil. Siempre menciona que eres Lucy de CINEPELIS 🍿.
        Responde de forma clara y concisa.
        """
        
        payload = {
            "contents": [{"parts": [{"text": context_prompt}]}]
        }
        
        response = requests.post(GEMINI_URL, json=payload, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        ai_response = result['candidates'][0]['content']['parts'][0]['text']
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error al consultar Gemini: {e}")
        return "Lo siento, mi inteligencia artificial está ocupada. Por favor, intenta más tarde."

def search_media_tmdb(query):
    """Busca información de medios usando la API de TMDb."""
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
            logger.warning(f"Se encontraron resultados para '{query}', pero ninguno era película o serie.")
            return None
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al conectar con la API de TMDb: {e}")
        return None
    except Exception as e:
        logger.error(f"Error procesando datos de TMDb: {e}", exc_info=True)
        return None

@bot.message_handler(func=lambda message: message.chat.type == 'supergroup', content_types=['document', 'video'])
def handle_media_upload(message):
    try:
        logger.info(f"Nuevo mensaje recibido. Tipo: {message.content_type}")
        
        if message.caption:
            media_name = message.caption.split('\n')[0]
        elif message.document:
            media_name = message.document.file_name
        elif message.video:
            media_name = message.video.file_name
        else:
            logger.warning("Mensaje sin documento, video ni subtítulo.")
            return

        cleaned_name = re.sub(r'\([^)]*\)', '', media_name).split('.')[0].strip()
        logger.info(f"Buscando en TMDb información para: {cleaned_name}")
        
        media_info = search_media_tmdb(cleaned_name)
        
        if media_info:
            logger.info(f"Información encontrada para {cleaned_name}")
            
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
                       "[CINEPELIS 🍿](https://t.me/pelicuilasymasg)")
            
            try:
                if poster_url:
                    bot.send_photo(CHANNEL_ID, poster_url, caption=caption, parse_mode='Markdown')
                else:
                    bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                logger.info("Publicación enviada al canal exitosamente.")
            except Exception as e:
                logger.error(f"Error al enviar la portada al canal: {e}")
                bot.reply_to(message, "Hubo un error al crear la portada para el canal.")
        else:
            logger.warning(f"No se encontró información en TMDb para: {cleaned_name}")
            bot.reply_to(message, "No se pudo encontrar información sobre esta película o serie. Por favor, asegúrate de que el nombre en el subtítulo es correcto.")
    except Exception as e:
        logger.error(f"Error en handle_media_upload: {e}", exc_info=True)
        bot.reply_to(message, "Ocurrió un error general al procesar el archivo.")

@bot.message_handler(func=lambda message: message.chat.type == 'supergroup')
def handle_group_message(message):
    username = message.from_user.first_name
    
    if message.text and any(keyword in message.text.lower() for keyword in ['está', 'tienen', 'busco', 'película', 'serie', 'film', 'movie']):
        try:
            ai_response = ask_gemini(message.text)
            bot.reply_to(message, ai_response)
            return
        except Exception as e:
            logger.error(f"Error al procesar consulta con Gemini: {e}")
    
    chat_button = InlineKeyboardButton("Hablar con Lucy", url=f"https://t.me/{bot.get_me().username}")
    markup = InlineKeyboardMarkup().add(chat_button)
    try:
        if message.content_type == 'text':
            bot.reply_to(message, f"Hola {username}, soy Lucy. Para hacer tu petición, queja o sugerencia, escríbeme al privado.", reply_markup=markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "message to be replied not found" in str(e):
            bot.send_message(message.chat.id, f"Hola {username}, soy Lucy. Para hacer tu petición, queja o sugerencia, escríbeme al privado.", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    username = message.from_user.first_name
    welcome_message = f"Hola {username}, soy Lucy 🤖 de CINEPELIS 🍿\n\n¿Qué quieres hacer?\n\n🎬 También puedes preguntarme si tenemos alguna película o serie específica"
    keyboard = create_keyboard(["Queja", "Petición", "Sugerencia", "Buscar película/serie"])
    bot.send_message(message.chat.id, welcome_message, reply_markup=keyboard)
    USER_STATES[message.chat.id] = 'WAITING_FOR_OPTION'

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_OPTION')
def handle_option(message):
    if message.text == "Queja":
        bot.send_message(message.chat.id, "Por favor, deja tu queja:")
        USER_STATES[message.chat.id] = 'WAITING_FOR_COMPLAINT'
    elif message.text == "Petición":
        bot.send_message(message.chat.id, "Asegúrate de que lo que pides no está en el grupo. ¿Estás seguro/a de que NO está en el grupo?", reply_markup=create_keyboard(["Sí", "No"]))
        USER_STATES[message.chat.id] = 'CONFIRMING_REQUEST'
    elif message.text == "Sugerencia":
        bot.send_message(message.chat.id, "Por favor, deja tu sugerencia:")
        USER_STATES[message.chat.id] = 'WAITING_FOR_SUGGESTION'
    elif message.text == "Buscar película/serie":
        bot.send_message(message.chat.id, "🎬 ¿Qué película o serie estás buscando? Escribe el nombre:")
        USER_STATES[message.chat.id] = 'SEARCHING_MOVIE'
    else:
        keyboard = create_keyboard(["Queja", "Petición", "Sugerencia", "Buscar película/serie"])
        bot.send_message(message.chat.id, "Por favor, selecciona una opción válida.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'SEARCHING_MOVIE')
def handle_movie_search(message):
    try:
        query = message.text
        bot.send_message(message.chat.id, "🔍 Buscando en nuestra base de datos...")
        
        ai_response = ask_gemini(f"¿Tienen la película o serie: {query}?")
        bot.send_message(message.chat.id, ai_response)
        
        ask_for_more(message.chat.id)
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        bot.send_message(message.chat.id, "Lo siento, hubo un error al buscar. Intenta de nuevo más tarde.")
        ask_for_more(message.chat.id)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'CONFIRMING_REQUEST')
def confirm_request(message):
    if message.text == "Sí":
        bot.send_message(message.chat.id, "Bien. Deja el nombre de lo que pides de manera clara, indicando si es serie o película. Puedes adjuntar una foto o video si lo deseas.")
        USER_STATES[message.chat.id] = 'WAITING_FOR_REQUEST'
    elif message.text == "No":
        bot.send_message(message.chat.id, "Por favor, busca bien en el grupo usando la barra de búsqueda. También puedes usar mi función de búsqueda. Si no lo encuentras, puedes hacer una nueva petición.")
        ask_for_more(message.chat.id)
    else:
        bot.send_message(message.chat.id, "Por favor, responde 'Sí' o 'No'.", reply_markup=create_keyboard(["Sí", "No"]))

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_REQUEST', content_types=['text', 'photo', 'video'])
def handle_request(message):
    user_info = f"Petición de {message.from_user.first_name} (@{message.from_user.username}):"
    if message.content_type == 'text':
        request_text = message.text
        bot.send_message(ADMIN_GROUP_ID, f"{user_info}\n{request_text}", reply_markup=create_inline_keyboard([("Petición tomada", f"taken_{message.chat.id}"), ("Lo que buscas ya está", f"exists_{message.chat.id}")]))
    else:
        bot.forward_message(ADMIN_GROUP_ID, message.chat.id, message.message_id)
        bot.send_message(ADMIN_GROUP_ID, user_info, reply_markup=create_inline_keyboard([("Petición tomada", f"taken_{message.chat.id}"), ("Lo que buscas ya está", f"exists_{message.chat.id}")]))
    
    bot.send_message(message.chat.id, "Tu petición ha sido enviada a los administradores. Te notificaremos cuando sea procesada.")
    ask_for_more(message.chat.id)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    try:
        action, user_id_str = call.data.split('_', 1)
        user_id = int(user_id_str)
        
        if action == "taken":
            bot.answer_callback_query(call.id, "Petición tomada")
            bot.send_message(user_id, "Tu petición ha sido tomada por un administrador. Está atento/a en los próximos minutos en Cinepelis.")
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, f"Has tomado la petición de @{call.from_user.username}. Responde a este mensaje para contactar al usuario.")
            USER_STATES[call.message.chat.id] = f'ADMIN_RESPONDING_{user_id}'
        elif action == "exists":
            bot.answer_callback_query(call.id, "Ya existe")
            bot.send_message(user_id, "Un administrador ha indicado que lo que buscas ya está disponible en el grupo. Por favor, usa la barra de búsqueda para encontrarlo o pregúntame directamente.")
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        elif action == "take":
            bot.answer_callback_query(call.id, "Has tomado la queja")
            bot.send_message(user_id, "Un administrador ha tomado tu queja y te responderá pronto.")
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            bot.send_message(call.message.chat.id, f"Has tomado la queja de @{call.from_user.username}. Responde a este mensaje para contactar al usuario.")
            USER_STATES[call.message.chat.id] = f'ADMIN_RESPONDING_{user_id}'
        elif action == "reject":
            bot.answer_callback_query(call.id, "Has rechazado la queja")
            bot.send_message(user_id, "Lo sentimos, en este momento no podemos atender tu queja. Por favor, intenta más tarde.")
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            USER_STATES.pop(user_id, None)
            ask_for_more(user_id)
            
    except ValueError:
        logger.error(f"Error al procesar callback_data: {call.data}")
        bot.answer_callback_query(call.id, "Error: Callback inválido.")
    except Exception as e:
        logger.error(f"Error en handle_query: {e}", exc_info=True)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id, '').startswith('ADMIN_RESPONDING_'))
def admin_response(message):
    try:
        user_id_str = USER_STATES[message.chat.id].split('_')[-1]
        user_id = int(user_id_str)
        bot.send_message(user_id, f"Respuesta del administrador: {message.text}")
        bot.send_message(message.chat.id, "Tu respuesta ha sido enviada al usuario.")
        USER_STATES.pop(message.chat.id, None)
        ask_for_more(user_id)
    except Exception as e:
        logger.error(f"Error en admin_response: {e}")
        bot.send_message(message.chat.id, "Ocurrió un error al enviar la respuesta.")

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_COMPLAINT')
def handle_complaint(message):
    bot.forward_message(ADMIN_GROUP_ID, message.chat.id, message.message_id)
    bot.send_message(ADMIN_GROUP_ID, f"Nueva queja de {message.from_user.first_name} (@{message.from_user.username}):", 
                     reply_markup=create_inline_keyboard([("Tomar", f"take_{message.chat.id}"), ("Rechazar", f"reject_{message.chat.id}")]))
    bot.send_message(message.chat.id, "Gracias por tu queja. Un administrador la revisará pronto.")
    ask_for_more(message.chat.id)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_SUGGESTION')
def handle_suggestion(message):
    bot.forward_message(ADMIN_GROUP_ID, message.chat.id, message.message_id)
    bot.send_message(ADMIN_GROUP_ID, f"Nueva sugerencia de {message.from_user.first_name} (@{message.from_user.username}):")
    bot.send_message(message.chat.id, "Gracias por tu sugerencia. La tendremos en cuenta.")
    ask_for_more(message.chat.id)

def ask_for_more(chat_id):
    keyboard = create_keyboard(["Queja", "Petición", "Sugerencia", "Nada"])
    bot.send_message(chat_id, "¿Hay algo más que quieras hacer?", reply_markup=keyboard)
    USER_STATES[chat_id] = 'WAITING_FOR_MORE'

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_MORE')
def handle_more(message):
    if message.text == "Nada":
        bot.send_message(message.chat.id, "Gracias por comunicarte. ¡Hasta la próxima!")
        USER_STATES[message.chat.id] = 'IDLE'
    else:
        handle_option(message)

def delete_group_notifications(message):
    if message.content_type == 'new_chat_members':
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            logger.error(f"Error al eliminar notificación de nuevos miembros: {e}")

@bot.message_handler(func=lambda message: True, content_types=['new_chat_members'])
def handle_new_chat_members(message):
    delete_group_notifications(message)

if __name__ == '__main__':
    if TMDB_API_KEY == 'TU_API_KEY_DE_TMDB_AQUÍ':
        logger.error("LA CLAVE DE API DE TMDB NO HA SIDO CONFIGURADA. Por favor, edita el script y añade tu clave.")
    else:
        logger.info("Iniciando el bot...")
        bot.infinity_polling()
        logger.info("El bot se ha detenido.")
