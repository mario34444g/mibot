
import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from fuzzywuzzy import fuzz
import logging
import sqlite3
from datetime import datetime
from collections import defaultdict

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = '7458928597:AAGAyVvFXJ7QSWuY0-hpBA7xgOqYBtbxxW8'
GROUP_CHAT_ID = -1002199010991
bot = telebot.TeleBot(API_KEY)

# Estados del usuario
USER_STATES = {}

# Configuración de la base de datos
DB_NAME = 'cinepelis_messages.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY,
                  type TEXT,
                  content TEXT,
                  caption TEXT,
                  file_id TEXT,
                  message_id INTEGER,
                  timestamp DATETIME)''')
    conn.commit()
    conn.close()

def add_message_to_db(message_type, content, caption, file_id, message_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO messages (type, content, caption, file_id, message_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
              (message_type, content, caption, file_id, message_id, datetime.now()))
    conn.commit()
    conn.close()

def search_messages(search_term):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM messages")
    all_messages = c.fetchall()
    conn.close()

    results = []
    for msg in all_messages:
        content = msg[2] or msg[3] or ''  # content or caption
        ratio = fuzz.partial_ratio(search_term.lower(), content.lower())
        if ratio > 80:  # Ajusta este umbral según sea necesario
            results.append({
                'type': msg[1],
                'content': msg[2],
                'caption': msg[3],
                'file_id': msg[4],
                'message_id': msg[5]
            })
    
    return results  # Retorna todos los resultados sin límite

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
    results = search_messages(search_term)
    
    if results:
        # Agrupar resultados por título
        title_groups = defaultdict(list)
        for result in results:
            title = result.get('caption', '') or result.get('content', '')[:50]  # Usar los primeros 50 caracteres como título
            title_groups[title].append(result)
        
        for title, group in title_groups.items():
            if len(group) > 3:
                # Más de 3 mensajes con el mismo título, enviar como link (serie)
                link = f"https://t.me/c/{str(GROUP_CHAT_ID)[4:]}/{group[0]['message_id']}"
                bot.send_message(message.chat.id, f"Serie encontrada: {title}\nLink: {link}")
            else:
                # 3 o menos mensajes, enviar como multimedia (película)
                bot.send_message(message.chat.id, f"Película encontrada: {title}")
                for result in group:
                    content_type = result['type']
                    if content_type == 'text':
                        bot.send_message(message.chat.id, result['content'])
                    elif content_type in ['photo', 'video', 'document']:
                        if result['file_id']:
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
            add_message_to_db('text', message.text, None, None, message.message_id)
        elif message.content_type in ['photo', 'video', 'document']:
            caption = message.caption if message.caption else "Sin título"
            file_id = None
            if message.content_type == 'photo':
                file_id = message.photo[-1].file_id
            elif message.content_type == 'video':
                file_id = message.video.file_id
            elif message.content_type == 'document':
                file_id = message.document.file_id
            
            add_message_to_db(message.content_type, None, caption, file_id, message.message_id)

if __name__ == "__main__":
    init_db()
    bot.polling()
