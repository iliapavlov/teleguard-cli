import argparse
import os
import time
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest
from telethon.tl.types import UserStatusOnline, UserStatusOffline
from telethon.errors import FloodWaitError

# Налаштування білого списку (можна винести в окремий файл)
ALLOWED_SESSIONS = {
    ("Firefox 149", "Telegram Web")
}

def check_account_status(client):
    me = client.get_me()
    print(f"\n{"="*40}")
    print(f"👤 КОРУСТУВАЧ: {me.first_name} {me.last_name or ''}")
    print(f"📱 Username: @{me.username} | 🆔 ID: {me.id}")
    print(f"💎 Premium: {'Так' if me.premium else 'Ні'}")

    # Перевірка статусу (онлайн/офлайн)
    status = me.status
    if isinstance(status, UserStatusOnline):
        print("🟢 Статус: Online")
    elif isinstance(status, UserStatusOffline):
        print(f"🔘 Востаннє в мережі: {status.was_online}")
    
    # Детальний аналіз сесій
    print(f"\n🔐 АКТИВНІ СЕСІЇ:")
    auths = client(GetAuthorizationsRequest())
    
    for i, auth in enumerate(auths.authorizations, 1):
        current_mark = "⭐ (ПОТОЧНА)" if auth.current else "  "
        print(f"{i}. {current_mark} Пристрій: {auth.device_model}")
        print(f"   Додаток: {auth.app_name}")
        print(f"   IP: {auth.ip} | Локація: {auth.country}")
        print(f"   Дата входу: {auth.date_created.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Параметри для white-list: (\"{auth.device_model}\", \"{auth.app_name}\")")
        print(f"   {'-'*30}")

    print(f"Всього активних сесій: {len(auths.authorizations)}")
    print(f"{"="*40}\n")

def terminate_suspicious_sessions(client):
    auths = client(GetAuthorizationsRequest())
    terminated = 0
    
    for auth in auths.authorizations:
        if auth.current:
            print(f"🛡️ Current session - Skipping.")
            continue
            
        device, app = auth.device_model or "", auth.app_name or ""
        
        if (device, app) in ALLOWED_SESSIONS:
            print(f"✅ Allowed: {device} ({app})")
        else:
            try:
                client(ResetAuthorizationRequest(hash=auth.hash))
                print(f"❌ Terminated: {device} ({app}) | IP: {auth.ip} | {auth.country}")
                terminated += 1
            except FloodWaitError as e:
                print(f"⏳ Flood limit. Waiting {e.seconds}s...")
                time.sleep(e.seconds)
    
    print(f"🔚 Total terminated: {terminated}")

async def manage_unread_messages(client):
    # Отримуємо всі діалоги
    dialogs = await client.get_dialogs()
    # Фільтруємо лише ті, де є непрочитані
    unread_dialogs = [d for d in dialogs if d.unread_count > 0]

    # 1) Вивід заголовка лише якщо є повідомлення
    if not unread_dialogs:
        print("\n✅ Непрочитаних повідомлень немає.")
        return

    print("\n📩 Unread Messages:")

    for dialog in unread_dialogs:
        # 5) Пріоритетність: Спершу питаємо дію, щоб зекономити трафік
        print(f"\n--- 👥 {dialog.name} ({dialog.unread_count} нових) ---")
        
        action = input(f"[R]ead / [A]nswer / [S]kip / [Q]uit: ").lower()

        # 2) Використовуємо return для негайного виходу
        if action == 'q':
            print("🛑 Вихід з перегляду повідомлень.")
            return 

        # 3, 4) Пропуск з візуальним фідбеком
        if action == 's':
            print(f"⏩ Пропущено: {dialog.name}")
            continue

        # Завантажуємо повідомлення тільки якщо користувач обрав Read або Answer
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
                print(f"🚀 Повідомлення надіслано в {dialog.name}.")

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
        if args.unread: manage_unread_messages(client)

if __name__ == '__main__':
    main()