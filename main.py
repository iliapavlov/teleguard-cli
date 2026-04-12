import argparse
import os
import time
import json  # 1. Додано імпорт json
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.tl.types import UserStatusOnline, UserStatusOffline
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
        
        # 2. Виправлено вивід для зручного копіювання в JSON
        # Виводимо готовий рядок, який можна просто вставити в масив
        print(f"   Копіювати в configuration.json: \"{auth.device_model}|{auth.app_name}\"")
        print(f"   {'-'*30}")

    print(f"Всього активних сесій: {len(auths.authorizations)}")
    print(f"{'-'*40}\n")

def terminate_suspicious_sessions(client):
    # 1. Завантажуємо конфігурацію всередині функції
    config = load_config()
    allowed_list = config.get("allowed_sessions", [])
    
    auths = client(GetAuthorizationsRequest())
    terminated = 0
    
    for auth in auths.authorizations:
        if auth.current:
            continue
            
        device, app = auth.device_model or "", auth.app_name or ""
        # Формуємо ключ ідентифікації так само, як у пораді при статусі
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
    dialogs = await client.get_dialogs()
    unread_dialogs = [d for d in dialogs if d.unread_count > 0]

    if not unread_dialogs:
        print("\n✅ Непрочитаних повідомлень немає.")
        return

    print("\n📩 Unread Messages:")

    for dialog in unread_dialogs:
        print(f"\n--- 👥 {dialog.name} ({dialog.unread_count} нових) ---")
        action = input(f"[R]ead / [A]nswer / [S]kip / [Q]uit: ").lower()

        if action == 'q':
            print("🛑 Вихід з перегляду повідомлень.")
            return 

        if action == 's':
            print(f"⏩ Пропущено: {dialog.name}")
            continue

        messages = await client.get_messages(dialog, limit=dialog.unread_count)
        
        print("-" * 30)
        for msg in reversed(messages):
            sender = "Ви" if msg.out else "Співрозмовник"
            text = msg.text.replace('\n', ' ')[:50] if msg.text else "[Медіа/Інше]"
            print(f"[{msg.date.strftime('%H:%M')}] {sender}: {text}")
        print("-" * 30)

        if action == 'r':
            await client.send_read_acknowledge(dialog)
            print(f"✔️ Чат {dialog.name} позначено як прочитаний.")
        elif action == 'a':
            reply = input("Ваша відповідь: ")
            if reply.strip():
                await client.send_message(dialog, reply)
                await client.send_read_acknowledge(dialog)
                print(f"🚀 Повідомлення надіслано.")

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