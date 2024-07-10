import os
import telebot
from fuzzywuzzy import fuzz
import logging

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


API_KEY = '7458928597:AAGAyVvFXJ7QSWuY0-hpBA7xgOqYBtbxxW8'
GROUP_CHAT_ID = -1002199010991
bot = telebot.TeleBot(API_KEY)
group_messages = []

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Bienvenido! ¿Qué deseas buscar?")

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def handle_text(message):
    try:
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
        else:
            search_term = message.text.lower()
            results = []
            for msg in group_messages:
                content = msg.get('content', '') or msg.get('caption', '')
                ratio = fuzz.partial_ratio(search_term, content.lower())
                if ratio > 80:  # Ajusta este umbral según sea necesario
                    results.append((ratio, msg))
            
            results.sort(key=lambda x: x[0], reverse=True)  # Ordena por relevancia
            
            if results:
                for _, result in results[:5]:  # Limita a los 5 mejores resultados
                    link = f"https://t.me/c/{str(GROUP_CHAT_ID)[4:]}/{result['message_id']}"
                    content_type = result['type']
                    if content_type == 'text':
                        bot.send_message(message.chat.id, f"Texto encontrado: {link}\nContenido: {result['content'][:100]}...")
                    elif content_type in ['photo', 'video', 'document']:
                        bot.send_message(message.chat.id, f"{content_type.capitalize()} encontrado: {link}\nTítulo: {result['caption']}")
                        if result['file_id']:
                            if content_type == 'photo':
                                bot.send_photo(message.chat.id, result['file_id'], caption=result['caption'])
                            elif content_type == 'video':
                                bot.send_video(message.chat.id, result['file_id'], caption=result['caption'])
                            elif content_type == 'document':
                                bot.send_document(message.chat.id, result['file_id'], caption=result['caption'])
            else:
                bot.send_message(message.chat.id, "No se encontraron resultados.")
    except Exception as e:
        logger.error(f"Error en handle_text: {str(e)}")

if __name__ == "__main__":
    bot.polling()
