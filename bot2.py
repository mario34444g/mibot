import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import re
from imdb import Cinemagoer
from googletrans import Translator
import logging


# Configuración de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


API_KEY = '7600046039:AAGIWIlILfBdKl0qt4gLE8UTN0L_qGJIbB4'
GROUP_CHAT_ID = -1002271682346
ADMIN_GROUP_ID = -4634644543
CHANNEL_ID = -1002176864902
ADMIN_USER_ID = 7753923473
bot = telebot.TeleBot(API_KEY)

ia = Cinemagoer()
translator = Translator()

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

def search_media(media_name):
    try:
        cleaned_name = re.sub(r'\(\d{4}\)', '', media_name).strip()
        results = ia.search_movie(cleaned_name)
        if results:
            for result in results:
                try:
                    media_id = result.movieID
                    media = ia.get_movie(media_id)
                    if media.get('kind') in ['movie', 'tv series']:
                        return media
                except Exception as e:
                    logger.error(f"Error al obtener detalles del medio: {e}")
        return None
    except Exception as e:
        logger.error(f"Error en la búsqueda de medios: {e}")
        return None

@bot.message_handler(func=lambda message: message.chat.type == 'supergroup', content_types=['document', 'video'])
def handle_media_upload(message):
    try:
        logger.info(f"Nuevo mensaje recibido. Tipo: {message.content_type}")
        
        # Usar el texto del mensaje (subtítulo) si está disponible
        if message.caption:
            media_name = message.caption.split('\n')[0]  # Tomar la primera línea del subtítulo
            logger.info(f"Subtítulo encontrado: {media_name}")
        else:
            # Si no hay subtítulo, usar el nombre del archivo como respaldo
            if message.document:
                media_name = message.document.file_name
                logger.info(f"Usando nombre de documento: {media_name}")
            elif message.video:
                media_name = message.video.file_name
                logger.info(f"Usando nombre de video: {media_name}")
            else:
                logger.warning("Mensaje recibido sin documento, video ni subtítulo")
                return

        # Limpiar el nombre del medio
        media_name = re.sub(r'\([^)]*\)', '', media_name)  # Eliminar cualquier cosa entre paréntesis
        media_name = media_name.split('.')[0].strip()  # Eliminar la extensión del archivo si existe
        logger.info(f"Nombre del medio limpio: {media_name}")

        logger.info(f"Buscando información para: {media_name}")
        media_info = search_media(media_name)
        
        if media_info:
            logger.info(f"Información encontrada para {media_name}")
            title = media_info.get('title', 'Sin título')
            year = media_info.get('year', 'Año desconocido')
            plot = media_info.get('plot outline', 'Sin descripción disponible')
            if isinstance(plot, list):
                plot = plot[0] if plot else 'Sin descripción disponible'
            
            logger.info("Intentando traducir la descripción")
            try:
                plot_es = translator.translate(plot, dest='es').text
                logger.info("Traducción exitosa")
            except Exception as e:
                logger.error(f"Error en la traducción: {e}")
                plot_es = plot
            
            poster_url = media_info.get('full-size cover url') or media_info.get('cover url')
            logger.info(f"URL del póster: {poster_url}")

            message_link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"
            logger.info(f"Enlace del mensaje: {message_link}")

            media_type = "PELÍCULA" if media_info.get('kind') == 'movie' else "SERIE"
            logger.info(f"Tipo de medio: {media_type}")

            caption = (f"*{title}* ({year})\n\n"
                       f"{plot_es[:200]}...\n\n"
                       f"[VER {media_type} {title.upper()} AQUÍ]({message_link})\n\n"
                       "[CINEPELIS 🍿](https://t.me/peliculasymasg)")
            
            logger.info("Intentando enviar el mensaje al canal")
            try:
                if poster_url:
                    bot.send_photo(CHANNEL_ID, 
                                   poster_url, 
                                   caption=caption, 
                                   parse_mode='Markdown')
                    logger.info("Foto con caption enviada exitosamente")
                else:
                    bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
                    logger.info("Mensaje de texto enviado exitosamente")
            except Exception as e:
                logger.error(f"Error al enviar la portada: {e}")
                bot.reply_to(message, "Hubo un error al crear la portada. Por favor, inténtalo de nuevo más tarde.")
        else:
            logger.warning(f"No se encontró información para: {media_name}")
            bot.reply_to(message, "No se pudo encontrar información sobre esta película o serie. Por favor, asegúrate de incluir el nombre correcto en el subtítulo del mensaje.")
    except Exception as e:
        logger.error(f"Error en handle_media_upload: {e}", exc_info=True)
        bot.reply_to(message, "Ocurrió un error al procesar el archivo. Por favor, inténtalo de nuevo más tarde.")

@bot.message_handler(func=lambda message: message.chat.type == 'supergroup')
def handle_group_message(message):
    username = message.from_user.first_name
    chat_button = InlineKeyboardButton("Hablar con Lucy", url=f"https://t.me/{bot.get_me().username}")
    markup = InlineKeyboardMarkup().add(chat_button)
    try:
        bot.reply_to(message, f"Hola {username}, soy Lucy. Para hacer tu petición, queja o sugerencia, escríbeme al privado.", reply_markup=markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "message to be replied not found" in str(e):
            bot.send_message(message.chat.id, f"Hola {username}, soy Lucy. Para hacer tu petición, queja o sugerencia, escríbeme al privado.", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    username = message.from_user.first_name
    welcome_message = f"Hola {username}, ¿qué quieres hacer?"
    keyboard = create_keyboard(["Queja", "Petición", "Sugerencia"])
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
    else:
        keyboard = create_keyboard(["Queja", "Petición", "Sugerencia"])
        bot.send_message(message.chat.id, "Por favor, selecciona una opción válida.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'CONFIRMING_REQUEST')
def confirm_request(message):
    if message.text == "Sí":
        bot.send_message(message.chat.id, "Bien. Deja el nombre de lo que pides de manera clara, indicando si es serie o película. Puedes adjuntar una foto o video si lo deseas.")
        USER_STATES[message.chat.id] = 'WAITING_FOR_REQUEST'
    elif message.text == "No":
        bot.send_message(message.chat.id, "Por favor, busca bien en el grupo usando la barra de búsqueda. Si no lo encuentras, puedes hacer una nueva petición.")
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
    action, user_id = call.data.split('_')
    user_id = int(user_id)
    
    if action == "taken":
        bot.answer_callback_query(call.id, "Petición tomada")
        bot.send_message(user_id, "Tu petición ha sido tomada por un administrador. Está atento/a en los próximos minutos en Cinepelis.")
        bot.send_message(call.message.chat.id, f"Has tomado la petición. ¿Qué quieres responder al usuario?")
        USER_STATES[call.message.chat.id] = f'ADMIN_RESPONDING_{user_id}'
    elif action == "exists":
        bot.answer_callback_query(call.id, "Ya existe")
        bot.send_message(user_id, "Lo que buscas ya está disponible en el grupo. Por favor, usa la barra de búsqueda para encontrarlo.")
    elif action == "take":
        bot.answer_callback_query(call.id, "Has tomado la queja")
        bot.send_message(user_id, "Un administrador ha tomado tu queja y te responderá pronto.")
        bot.send_message(call.message.chat.id, f"Has tomado la queja. ¿Qué quieres responder al usuario?")
        USER_STATES[call.message.chat.id] = f'ADMIN_RESPONDING_{user_id}'
    elif action == "reject":
        bot.answer_callback_query(call.id, "Has rechazado la queja")
        bot.send_message(user_id, "Lo sentimos, en este momento no podemos atender tu queja. Por favor, intenta más tarde.")
        USER_STATES[user_id] = 'IDLE'
        ask_for_more(user_id)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id, '').startswith('ADMIN_RESPONDING_'))
def admin_response(message):
    user_id = int(USER_STATES[message.chat.id].split('_')[-1])
    bot.send_message(user_id, f"Respuesta del administrador: {message.text}")
    bot.send_message(message.chat.id, "Tu respuesta ha sido enviada al usuario.")
    USER_STATES[message.chat.id] = 'IDLE'
    ask_for_more(user_id)

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

bot.infinity_polling()
