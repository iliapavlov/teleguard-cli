import argparse
import os
import time
import json
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.errors import FloodWaitError

def load_config():
    config_path = 'configuration.json'
    default_config = {"allowed_sessions": []}
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Помилка читання configuration.json. Використовую порожній список.")
                return default_config
    return default_config

def check_account_status(client):
    me = client.get_me()
    print(f"\n{'-'*40}")
    print(f"👤 КОРУСТУВАЧ: {me.first_name} {me.last_name or ''}")
    print(f"📱 Username: @{me.username} | 🆔 ID: {me.id}")
    
    # Детальний аналіз сесій
    print(f"\n🔐 АКТИВНІ СЕСІЇ:")
    auths = client(GetAuthorizationsRequest())
    
    for i, auth in enumerate(auths.authorizations, 1):
        current_mark = "⭐ (ПОТОЧНА)" if auth.current else "  "
        print(f"{i}. {current_mark} Пристрій: {auth.device_model}")
        print(f"   Додаток: {auth.app_name}")
        print(f"   IP: {auth.ip} | Локація: {auth.country}")
        
        # Виводимо готовий рядок, який можна просто вставити в масив в configuration.json
        print(f"   Копіювати в configuration.json: \"{auth.device_model}|{auth.app_name}\"")
        print(f"   {'-'*30}")

    print(f"Всього активних сесій: {len(auths.authorizations)}")
    print(f"{'-'*40}\n")

def terminate_suspicious_sessions(client):
    # Завантажуємо конфігурацію та отримуємо список дозволених сесій
    config = load_config()
    allowed_list = config.get("allowed_sessions", [])
    
    auths = client(GetAuthorizationsRequest())
    terminated = 0
    
    for auth in auths.authorizations:
        if auth.current:
            continue
            
        device, app = auth.device_model or "", auth.app_name or ""
        # Формуємо ключ ідентифікації сесії для порівняння з дозволеним списком
        session_key = f"{device}|{app}"
        
        if session_key in allowed_list:
            print(f"✅ Дозволено: {device} ({app})")
        else:
            try:
                print(f"❌ Спроба завершення: {device} ({app})...")
                client(ResetAuthorizationRequest(hash=auth.hash))
                print(f"🗑️ Сесію завершено! IP: {auth.ip}")
                terminated += 1
            except FloodWaitError as e:
                print(f"⏳ Ліміт запитів. Чекаємо {e.seconds}с...")
                time.sleep(e.seconds)
            except Exception as e:
                print(f"⚠️ Помилка: {e}")
    
    print(f"\n🔚 Всього видалено сесій: {terminated}")

async def manage_unread_messages(client):
    async for dialog in client.iter_dialogs():
        if dialog.unread_count > 0:
            print(f"\n--- 👥 {dialog.name} ({dialog.unread_count} нових) ---")
            
            async for message in client.iter_messages(dialog, limit=dialog.unread_count):
                if message.text:
                    print(f"[{message.date.strftime('%H:%M')}] Співрозмовник: {message.text}")
            
            choice = input("[R]ead / [A]nswer / [S]kip / [Q]uit: ").lower()
            
            if choice == 'r':
                await client.send_read_acknowledge(dialog)
                print(f"✔️ Чат {dialog.name} позначено як прочитаний.")
            elif choice == 'a':
                reply_text = input("Ваша відповідь: ")
                
                # Очищаємо текст від можливих проблемних символів, 
                # які ламають utf-16-le кодек у Telethon
                safe_reply = reply_text.encode('utf-8', 'ignore').decode('utf-8')
                
                try:
                    await client.send_message(dialog, safe_reply)
                    await client.send_read_acknowledge(dialog)
                    print(f"🚀 Відповідь надіслана.")
                except Exception as e:
                    print(f"❌ Помилка при відправці: {e}")
            elif choice == 'q':
                return
    print("\n✅ Непрочитані повідомлення відсутні.")

def main():
    load_dotenv()
    api_id = os.getenv('TG_API_ID')
    api_hash = os.getenv('TG_API_HASH')
    phone = os.getenv('TG_PHONE')

    if not all([api_id, api_hash, phone]):
        print("❌ Error: Missing environment variables in .env file.")
        return

    parser = argparse.ArgumentParser(description='Telegram Diagnostic CLI')
    parser.add_argument('--status', action='store_true', help='Check account status')
    parser.add_argument('--clean', action='store_true', help='Terminate suspicious sessions')
    parser.add_argument('--unread', action='store_true', help='Manage unread messages')
    args = parser.parse_args()

    with TelegramClient('diag_session', int(api_id), api_hash) as client:
        if args.status: check_account_status(client)
        if args.clean: terminate_suspicious_sessions(client)
        if args.unread:
            client.loop.run_until_complete(manage_unread_messages(client))

if __name__ == '__main__':
    main()