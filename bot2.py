import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import re
from imdb import Cinemagoer
from googletrans import Translator
import logging

# Configuración del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración del bot
API_KEY = '7458928597:AAGAyVvFXJ7QSWuY0-hpBA7xgOqYBtbxxW8'
GROUP_CHAT_ID = -1002199010991
ADMIN_GROUP_ID = -4284232130
CHANNEL_ID = -1002176864902
bot = telebot.TeleBot(API_KEY)

# Configuración de IMDb y Traductor
ia = Cinemagoer()
translator = Translator()

# Estados del usuario
USER_STATES = {}

def create_keyboard(buttons):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*[KeyboardButton(button) for button in buttons])
    return keyboard

def search_media(media_name):
    try:
        cleaned_name = re.sub(r'\(\d{4}\)', '', media_name).strip()
        
        # Intentar buscar sin especificar idioma
        results = ia.search_movie(cleaned_name)
        
        if results:
            for result in results:
                try:
                    media_id = result.movieID
                    media = ia.get_movie(media_id)
                    
                    # Aceptar tanto películas como series de TV
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
        if message.document:
            file_name = message.document.file_name
        elif message.video:
            file_name = message.video.file_name
        else:
            logger.warning("Mensaje recibido sin documento ni video")
            return

        if not file_name:
            logger.warning("Nombre de archivo no disponible")
            return

        media_name = file_name.split('.')[0].replace('_', ' ').title()

        media_info = search_media(media_name)
        if media_info:
            title = media_info.get('title', 'Sin título')
            year = media_info.get('year', 'Año desconocido')
            plot = media_info.get('plot outline', 'Sin descripción disponible')
            if isinstance(plot, list):
                plot = plot[0] if plot else 'Sin descripción disponible'
            
            # Traducir la sinopsis al español
            try:
                plot_es = translator.translate(plot, dest='es').text
            except Exception as e:
                logger.error(f"Error en la traducción: {e}")
                plot_es = plot  # Si falla la traducción, usamos el texto original
            
            poster_url = media_info.get('full-size cover url') or media_info.get('cover url')

            message_link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"

            # Determinar si es una película o una serie
            media_type = "PELÍCULA" if media_info.get('kind') == 'movie' else "SERIE"

            # Crear el texto del mensaje con el formato solicitado
            caption = (f"*{title}* ({year})\n\n"
                       f"{plot_es[:200]}...\n\n"
                       f"[VER {media_type} {title.upper()} AQUÍ]({message_link})\n\n"
                       "[CINEPELIS 🍿](https://t.me/peliculasymasg)")

            try:
                if poster_url:
                    bot.send_photo(CHANNEL_ID, 
                                   poster_url, 
                                   caption=caption, 
                                   parse_mode='Markdown')
                else:
                    bot.send_message(CHANNEL_ID, caption, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error al enviar la portada: {e}")
                bot.reply_to(message, "Hubo un error al crear la portada. Por favor, inténtalo de nuevo más tarde.")
        else:
            bot.reply_to(message, "No se pudo encontrar información sobre esta película o serie.")
    except Exception as e:
        logger.error(f"Error en handle_media_upload: {e}")
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
        bot.send_message(message.chat.id, "Asegúrate de que lo que pides no está en el grupo. Recuerda usar la barra superior derecha para buscar. ¿Qué quieres pedir?")
        USER_STATES[message.chat.id] = 'WAITING_FOR_REQUEST'
    elif message.text == "Sugerencia":
        bot.send_message(message.chat.id, "Por favor, deja tu sugerencia:")
        USER_STATES[message.chat.id] = 'WAITING_FOR_SUGGESTION'
    else:
        keyboard = create_keyboard(["Queja", "Petición", "Sugerencia"])
        bot.send_message(message.chat.id, "Por favor, selecciona una opción válida.", reply_markup=keyboard)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_COMPLAINT')
def handle_complaint(message):
    bot.forward_message(ADMIN_GROUP_ID, message.chat.id, message.message_id)
    bot.send_message(ADMIN_GROUP_ID, f"Nueva queja de {message.from_user.first_name} (@{message.from_user.username}):")
    bot.send_message(message.chat.id, "Gracias por tu queja. ¿Quieres hablar con un administrador?", reply_markup=create_keyboard(["Sí", "No"]))
    USER_STATES[message.chat.id] = 'WAITING_FOR_ADMIN_DECISION'

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_ADMIN_DECISION')
def handle_admin_decision(message):
    if message.text == "Sí":
        bot.send_message(ADMIN_GROUP_ID, f"@admin El usuario {message.from_user.first_name} (@{message.from_user.username}) quiere hablar con un administrador.")
        bot.send_message(message.chat.id, "Un administrador se pondrá en contacto contigo pronto.")
    elif message.text == "No":
        bot.send_message(message.chat.id, "Entendido. Gracias por tu queja.")
    else:
        bot.send_message(message.chat.id, "Por favor, selecciona 'Sí' o 'No'.", reply_markup=create_keyboard(["Sí", "No"]))
        return
    ask_for_more(message.chat.id)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_REQUEST')
def handle_request(message):
    bot.forward_message(ADMIN_GROUP_ID, message.chat.id, message.message_id)
    bot.send_message(ADMIN_GROUP_ID, f"Nueva petición de {message.from_user.first_name} (@{message.from_user.username}):")
    bot.send_message(message.chat.id, "Petición tomada. Pronto estará disponible.")
    ask_for_more(message.chat.id)

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_SUGGESTION')
def handle_suggestion(message):
    bot.forward_message(ADMIN_GROUP_ID, message.chat.id, message.message_id)
    bot.send_message(ADMIN_GROUP_ID, f"Nueva sugerencia de {message.from_user.first_name} (@{message.from_user.username}):")
    bot.send_message(message.chat.id, "Gracias por tu sugerencia. La tendremos en cuenta.")
    ask_for_more(message.chat.id)

def ask_for_more(chat_id):
    keyboard = create_keyboard(["Queja", "Petición", "Sugerencia", "Salir"])
    bot.send_message(chat_id, "¿Quieres hacer algo más?", reply_markup=keyboard)
    USER_STATES[chat_id] = 'ASKING_FOR_MORE'

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'ASKING_FOR_MORE')
def handle_more(message):
    if message.text == "Salir":
        bot.send_message(message.chat.id, "Gracias por usar nuestro servicio. ¡Hasta pronto!")
        USER_STATES[message.chat.id] = 'FINISHED'
    else:
        handle_option(message)

if __name__ == "__main__":
    logger.info("Bot iniciado. Esperando mensajes...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logger.error(f"Error en el polling del bot: {e}")
            time.sleep(10)

