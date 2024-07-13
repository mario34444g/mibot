import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests
from tmdbv3api import TMDb, Movie

# Configuración del bot
API_KEY = '7458928597:AAGAyVvFXJ7QSWuY0-hpBA7xgOqYBtbxxW8'
GROUP_CHAT_ID = -1002199010991
ADMIN_GROUP_ID = -4284232130
CHANNEL_ID = -1002176864902
bot = telebot.TeleBot(API_KEY)

# Configuración de TMDb
tmdb = TMDb()
tmdb.api_key = '061c902ac47748b62bd6717bce1872ff'
tmdb.language = 'es'  # Cambiar el idioma a español
movie = Movie()

# Estados del usuario
USER_STATES = {}

def create_keyboard(buttons):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*[KeyboardButton(button) for button in buttons])
    return keyboard

@bot.message_handler(func=lambda message: message.chat.type == 'supergroup', content_types=['document', 'video'])
def handle_movie_upload(message):
    if message.document:
        file_name = message.document.file_name
    elif message.video:
        file_name = message.video.file_name
    else:
        return

    # Extraer el nombre de la película del nombre del archivo
    movie_name = file_name.split('.')[0].replace('_', ' ').title()

    # Buscar información de la película
    search = movie.search(movie_name)
    if search:
        movie_info = search[0]
        title = movie_info.title
        original_title = movie_info.original_title
        overview = movie_info.overview
        poster_path = movie_info.poster_path

        # Crear el enlace al mensaje original
        message_link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"

        # Crear el texto del mensaje
        caption = (f"{title} | {original_title}\n\n"
                   f"{overview[:200]}...\n\n"
                   f"[VER {title.upper()} AQUÍ]({message_link})\n\n"
                   "CINEPELIS 🍿")

        # Enviar la imagen al canal
        try:
            bot.send_photo(CHANNEL_ID, 
                           f"https://image.tmdb.org/t/p/w500{poster_path}", 
                           caption=caption, 
                           parse_mode='Markdown')
            
            # Se elimina el mensaje de confirmación en el grupo
        except Exception as e:
            print(f"Error al enviar la portada: {e}")
            bot.reply_to(message, "Hubo un error al crear la portada. Por favor, inténtalo de nuevo más tarde.")
    else:
        bot.reply_to(message, "No se pudo encontrar información sobre esta película.")

# El resto del código permanece igual

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
    print("Bot iniciado. Esperando mensajes...")
    bot.polling(none_stop=True)


