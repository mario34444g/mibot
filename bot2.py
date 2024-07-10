import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from fuzzywuzzy import fuzz
import logging

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = '7458928597:AAGAyVvFXJ7QSWuY0-hpBA7xgOqYBtbxxW8'
GROUP_CHAT_ID = -1002199010991
bot = telebot.TeleBot(API_KEY)
group_messages = []

# Estados del usuario
USER_STATES = {}

def create_keyboard(buttons):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*[KeyboardButton(button) for button in buttons])
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_message = "Hola, bienvenido. Soy tu asistente de cinepelis."
    keyboard = create_keyboard(["Buscar"])
    bot.send_message(message.chat.id, welcome_message, reply_markup=keyboard)
    USER_STATES[message.chat.id] = 'WAITING_FOR_SEARCH'

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'WAITING_FOR_SEARCH')
def handle_search_request(message):
    if message.text == "Buscar":
        bot.send_message(message.chat.id, "Por favor, escribe el nombre de la película o serie que deseas buscar.")
        USER_STATES[message.chat.id] = 'SEARCHING'
    else:
        bot.send_message(message.chat.id, "Por favor, presiona el botón 'Buscar' para iniciar tu búsqueda.")

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'SEARCHING')
def handle_search(message):
    search_term = message.text.lower()
    results = []
    for msg in group_messages:
        content = msg.get('content', '') or msg.get('caption', '')
        ratio = fuzz.partial_ratio(search_term, content.lower())
        if ratio > 80:
            results.append(msg)
    
    if results:
        for result in results[:5]:
            content_type = result['type']
            response_text = f"Película o serie \"{search_term}\" encontrada\nAquí está:"
            bot.send_message(message.chat.id, response_text)
            
            if content_type == 'text':
                bot.send_message(message.chat.id, result['content'])
            elif content_type in ['photo', 'video', 'document']:
                if content_type == 'photo':
                    bot.send_photo(message.chat.id, result['file_id'], caption=result['caption'])
                elif content_type == 'video':
                    bot.send_video(message.chat.id, result['file_id'], caption=result['caption'])
                elif content_type == 'document':
                    bot.send_document(message.chat.id, result['file_id'], caption=result['caption'])
    else:
        bot.send_message(message.chat.id, f"Lo siento, esa película o serie al parecer no está en cinepelis.")
    
    keyboard = create_keyboard(["Sí", "No"])
    bot.send_message(message.chat.id, "¿Quieres buscar otra cosa?", reply_markup=keyboard)
    USER_STATES[message.chat.id] = 'ASKING_FOR_MORE'

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'ASKING_FOR_MORE')
def handle_more_search(message):
    if message.text.lower() == "sí":
        bot.send_message(message.chat.id, "Por favor, escribe el nombre de la película o serie que deseas buscar.")
        USER_STATES[message.chat.id] = 'SEARCHING'
    elif message.text.lower() == "no":
        bot.send_message(message.chat.id, "Adiós, espero verte de nuevo.")
        USER_STATES[message.chat.id] = 'FINISHED'
    else:
        keyboard = create_keyboard(["Sí", "No"])
        bot.send_message(message.chat.id, "Por favor, selecciona 'Sí' o 'No'.", reply_markup=keyboard)

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_group_messages(message):
    if message.chat.id == GROUP_CHAT_ID:
        if message.content_type == 'text':
            group_messages.append({'type': 'text', 'content': message.text, 'message_id': message.message_id})
        elif message.content_type in ['photo', 'video', 'document']:
            caption = message.caption if message.caption else "Sin título"
            file_id = None
            if message.content_type == 'photo':
                file_id = message.photo[-1].file_id
            elif message.content_type == 'video':
                file_id = message.video.file_id
            elif message.content_type == 'document':
                file_id = message.document.file_id
            
            group_messages.append({
                'type': message.content_type,
                'caption': caption,
                'file_id': file_id,
                'message_id': message.message_id
            })

if __name__ == "__main__":
    bot.polling()
