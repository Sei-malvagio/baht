from telethon import *
from telethon.tl.functions.messages import EditMessageRequest
from telethon.tl.functions.channels import EditAdminRequest
from telethon.sessions import StringSession
from telethon.errors.rpcerrorlist import SlowModeWaitError, SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from telethon.tl.custom import Button
from telethon.tl.types import Channel, PeerChannel
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, UserDeactivatedBanError, UserDeactivatedError, FloodWaitError

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import json
import os
import re
import random
import string
import logging
import time
import psutil
import platform
import tracemalloc

logging.basicConfig(level=logging.ERROR)

api_id = "27064450"
api_hash = "b6273399b2130286c2b82f659f4d3a7b"

## PROD ##
bot_token = "7626153827:AAH0S1VYnSSYYD2hBGoheiy72vub7Ru8_WE"

## DEVELOPMENT ##
#bot_token = "7575112938:AAE94Lurz8c6PjpobmhZPZ_ed34HHgmlQKQ"


bot = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Cooldown untuk mengirim pesan
message_cooldown = defaultdict(datetime)

# Cooldown untuk grup yang akan dikirim
group_cooldown = defaultdict(datetime)

# Cooldown untuk mengedit pesan
edit_cooldown = defaultdict(datetime)

### KEYS SYSTEM ###
OWNER_ID = [6370385266]

## Error mesage ##
def err(msg, e):
   print(f"\x1b[91m[ERR]\x1b[0m {msg}: \x1b[91m\x1b[1m{e}\x1b[0m")

async def logs(msg, e):
  uid = e.sender_id

  logs_g = await bot.get_entity("t.me/+eXUdSjo8wVgwNzM1")
  await bot.send_message(logs_g, msg)

print("\x1b[96mChecking all function\x1b[0m")
def cl(msg):
  print(f"\x1b[92m[√] {msg} (Success)\x1b[0m")

## Keys db ##
KEYS_PATH = "db/keys.json"

def save_keys(keys):
  avail_keys = {
     'keys': keys
  }

  with open(KEYS_PATH, 'w') as file:
     json.dump(avail_keys, file, indent=4)

def save_key(uid, key):
  keys = load_keys()

  keys_found = False
  for key_ in keys:
     if key_['key'] == key:
        user_found = True
        break

  if not keys_found:
     new_key = {
       'key_id': key['key_id'],
       'key': key['key'],
       'used': key['used'],
       'expired': key['expired']
     }

     keys.append(new_key)

  save_keys(keys)

def load_keys():
  keys = []
  if os.path.exists(KEYS_PATH):
     with open(KEYS_PATH, 'r') as file:
        try:
           keys_data = json.load(file)
           keys = keys_data.get('keys', [])
           cl("load_keys")
        except json.JSONDecodeError:
           return []
  return keys

users_key = load_keys()

def waktu_expired(bulan):
    now = datetime.now()

    return now.replace(month=now.month + bulan)

### SESSIONS SYSTEM ###
SESSIONS_PATH = "sessions.json"

def load_sessions():
    if os.path.exists(SESSIONS_PATH):
        with open(SESSIONS_PATH, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {e}")
                return {}
    return {}
def save_sessions(sessions):
    with open(SESSIONS_PATH, 'w') as file:
        json.dump(sessions, file, indent= 4)

session_lock = asyncio.Lock()

async def save_session(user_id, session_data):
    async with session_lock:
        sessions = load_sessions()
        sessions[str(user_id)] = session_data
        save_sessions(sessions)

### SAVE ID FOR BC ###
IDS_PATH = "db/userids.json"

def save_ids(ids):
  save_ids = {
     'ids': ids
    }

  with open(IDS_PATH, 'w') as file:
     json.dump(save_ids, file, indent=4)

def save_id(uid):
  ids = load_ids()
  ids_found = False

  for id in ids:
     if id['uid'] == uid:
        ids_found = True
        break

  if not ids_found:
     new_id = {
       'uid': uid
     }

     ids.append(new_id)

  save_ids(ids)

def load_ids():
  ids = []
  if os.path.exists(IDS_PATH):
     with open(IDS_PATH, 'r') as file:
        try:
           ids_data = json.load(file)
           ids = ids_data.get('ids', [])
        except json.JSONDecodeError:
           return []
  return ids

users_tg_id = load_ids()

if users_tg_id:
   cl("load_ids")

async def is_valid_session(session_data):
    try:
        session = session_data['session']
        client = TelegramClient(StringSession(session), api_id, api_hash)
        await client.connect()
        if await client.is_user_authorized():
            await client.disconnect()
            return True
    except (UserDeactivatedBanError, UserDeactivatedError):
        return False
    except Exception as e:
        print(f"Error checking session: {str(e)}")
    return False

async def remove_invalid_sessions():
    sessions = load_sessions()
    valid_sessions = {}

    for user_id, session_data in sessions.items():
        if await is_valid_session(session_data):
            valid_sessions[user_id] = session_data
        else:
            print(f"Removing invalid session for user ID: {user_id}")

    save_sessions(valid_sessions)

print("Update sesi sudah tersimpan.")

def parse_duration(duration_str):
    units = {
        'jam': 'hours',
        'hari': 'days',
        'bulan': 'months'
        #'tahun': 'years'
    }

    parts = duration_str.split()
    if len(parts) != 2 or parts[1] not in units:
        return None, None

    amount = int(parts[0])
    unit = units[parts[1]]

    return amount, unit

def calculate_expiry_time(amount, unit):
    now = datetime.now()

    if unit == 'hours':
        return now + timedelta(hours=amount)
    elif unit == 'days':
        return now + timedelta(days=amount)
    elif unit == 'months':
        return now.replace(month=now.month + amount)
    elif unit == 'years':
        return now.replace(year=now.year + amount)
    return now

user_sessions = load_sessions()
if user_sessions: cl("load_sessions")

groups_session = {}
status_send = {}
sended = {}
group_cooldown = {}
usage = "**[!] Usage: **"
resume = {}

log_txt = "**[X] Kamu belum membuat userbot, Harap buat userbot dahulu!**"

g_logs = "logsforbahtubotbro"

@bot.on(events.NewMessage)
async def logs(event):
    uid = event.sender_id
    message_hist = event.raw_text
    userf = await bot.get_entity(uid)

    if uid not in OWNER_ID and event.is_private:
       save_id(uid)
       await bot.send_message(g_logs, f"**Pesan baru dari**\n\nUsername: {userf.username}\nId: {userf.id}\nMesage: {message_hist}")

### OWNER COMMANDS ###
channel_username = 'AltairssUserbot'

async def get_all_subscribers(channel):
    subscribers = []
    async for user in bot.iter_participants(channel):
        if not user.bot:
            subscribers.append(user.id)
    return subscribers

async def can_send_message(user_id):
    try:
        msg = await bot.send_message(user_id, '.')
        await msg.delete()
        return True
    except:
        return False

async def forward_to_subscribers(event, message):
    subscribers = await get_all_subscribers(channel_username)
    from_peer = await bot.get_input_entity(event.chat_id)

    success_count = 0
    failure_count = 0

    for subscriber in subscribers:
        if await can_send_message(subscriber):
            try:
                await bot.forward_messages(subscriber, message, from_peer)
                success_count += 1
                await asyncio.sleep(2)
            except errors.FloodWaitError as e:
                await bot.send_message(OWNER_ID[0], f"**Rate limit terlampaui. Menunggu {e.seconds} detik.**")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                failure_count += 1
                await bot.send_message(OWNER_ID[0], f"**Gagal forward ke {subscriber}**\n**nReason: {e}**")
        else:
            failure_count += 1
          #  await bot.send_message(OWNER_ID[0], f"**User {subscriber} belum memulai conv kepada Altair bot :( **")

    return success_count, failure_count

@bot.on(events.NewMessage(pattern="/info"))
async def server_info_handler(event):
    uid = event.input_sender

    start_time = time.time()
    server_info_msg = await event.respond("**Loading...**")
    end_time = time.time()
    ping_time = (end_time - start_time) * 1000

    # MEM INFO #
    mem = psutil.virtual_memory()
    total_mem = mem.total / (1024 ** 3)
    avail_mem = mem.available / (1024 ** 3)
    os_name = platform.system()

    # MEM USAGE #
    tracemalloc.start()

    process = psutil.Process(os.getpid())

    rss = process.memory_info().rss / (1024 ** 2)

    snapshot = tracemalloc.take_snapshot()
    stats = snapshot.statistics('filename')

    heap_total = sum(stat.size for stat in stats) / (1024 ** 2)  # Convert to MB
    heap_used = heap_total

    mem_usages = {
        "rss": round(rss, 2),
        "heapTotal": round(heap_total, 2),
        "heapUsed": round(heap_used, 2),
    }

    # INFORMASI CPU #
    #cpu_temp1 = psutil.sensors_temperatures()
    cpu_name = platform.processor() or "Tidak diketahui"
    cpu_physical_core = psutil.cpu_count(logical=False)
    cpu_logical_core = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    cpu_usage_per_core = psutil.cpu_percent(interval=1, percpu=True)
    cpu_usage_overall = psutil.cpu_percent(interval=1)

    #cpu_temprature_message = ""

    cpu_per_core = []
    for i, usage in enumerate(cpu_usage_per_core):
      cpu_per_core.append({
         "core": i + 1,
         "usage": usage
      })


    cpu_temp = []

    """
    if "coretemp" in cpu_temp1:
      for ent in cpu_temp1["coretemp"]:
        cpu_temp.append({
           "label": ent.label,
           "curr": ent.current,
           "high": ent.high,
           "critical": ent.critical
        })
    else:
      await bot.send_message(uid, "**[X] Server ini tidak mendukung cpu sensor tempratur!")
    """

    cpu_temperature_message = ""
    for temp in cpu_temp:
        cpu_temperature_message += (
            f"`{temp['label']}` - Current: {temp['current']}°C, "
            f"High: {temp['high']}°C, Critical: {temp['critical']}°C\n"
        )

    cpu_msg = f"""
𝗣𝗜𝗡𝗚
`{ping_time:.2f}ms`

𝗦𝗘𝗥𝗩𝗘𝗥
`Memory : {avail_mem:.2f}GB / {total_mem:.2f}GB`
`OS : {os_name}`

𝗠𝗘𝗠𝗢𝗥𝗬 𝗨𝗦𝗔𝗚𝗘
`RSS          : {mem_usages['rss']} MB`
`heapTotal    : {mem_usages['heapTotal']} MB`
`heapUsed     : {mem_usagea['heapUsed']} MB`

𝗖𝗣𝗨 𝗜𝗡𝗙𝗢
`Processor : {cpu_name}`
`Physical Cores : {cpu_physical_core}`
`Logical Cores  : {cpu_logical_core}`
`Max Frequency  : {cpu_freq.max:.2f} MHz`
`Min Frequency  : {cpu_freq.min:.2f} MHz`
`Current Frequency : {cpu_freq.current:.2f} Mhz`
`Overall CPU usage : {cpu_usage_overall}%`

**CPU Core(s) Usage ({cpu_logical_core} Core CPU):**
""" + "\n".join([f"  `Core {core['core']}`: {core['usage']}%" for core in cpu_per_core]) + f"""
    """

    await server_info_msg.edit(cpu_msg)

@bot.on(events.NewMessage(pattern="/chfw"))
async def chfw_command(event):
    uid = event.input_sender
    print(uid.access_hash)

    if uid and event.is_channel:
        if event.raw_text == "/chfw":
            if event.is_reply:
                message_id = event.reply_to_msg_id
                success_count, failure_count = await forward_to_subscribers(event, message_id)
                for own_id in OWNER_ID:
                  try:
                     await bot.send_message(own_id, f"**Forward berhasil ke {success_count} users, Gagal {failure_count} users.**")
                  except:
                     print('ok')
            else:
                gg = await event.respond("**Reply pesan yang mau di forward**")
                await asyncio.sleep(2)
                await gg.delete()
                return

            await bot.delete_messages(event.chat_id, [event.id])

bot_start_time=time.time()

@bot.on(events.NewMessage(pattern='ping'))
async def ping_handler(event):
    start_time = time.time()
    pong = await event.respond("**🏓 Pong:**")
    end_time = time.time()
    ping_time = (end_time - start_time) * 1000
    await pong.edit(f'**🏓 Pong:** `{ping_time:.2f}ms`', parse_mode="md")

@bot.on(events.NewMessage(pattern='uptime'))
async def uptime_handler(event):
    current_time = time.time()
    uptime_seconds = current_time - bot_start_time
    uptime_days = int(uptime_seconds // (24 * 3600))
    uptime_seconds %= 24 * 3600
    uptime_hours = int(uptime_seconds // 3600)
    uptime_seconds %= 3600
    uptime_minutes = int(uptime_seconds // 60)
    uptime_seconds = int(uptime_seconds % 60)

    uptime_str = f"{uptime_days}hari {uptime_hours}jam {uptime_minutes}m {uptime_seconds}detik"
    await event.respond(f"**Uptime**: __{uptime_str}__")
    
@bot.on(events.NewMessage(pattern='/setpesan (\S+)'))
async def setpesan_owner(event):
    uid = str(event.sender_id)
    user_sessions = load_sessions()
    
    if int(uid) in OWNER_ID:
        user_id = event.pattern_match.group(1)
        await event.respond("**Masukkan pesannya ownerku sayang**")
        
        @bot.on(events.NewMessage())
        async def handle_setpesan(ev):
            pesan = ev.raw_text.strip()
            
            if "/setpesan" not in pesan:
                try:
                    replacements = {
                       r'b:(.*?):b': r'<strong>\1</strong>',
                       r'k:(.*?):k': r'<blockquote>\1</blockquote>',
                       r'i:(.*?):i': r'<i>\1</i>',
                       r's:(.*?):s': r'<del>\1</del>',
                       r'h:(.*?):h': r'<details>\1</details>',
                       r'm:(.*?):m': r'<code>\1</code>',
                       r'p:(.*?):p': r'<pre>\1</pre>'
                    }
                    for pattern, replacement in replacements.items():
                        pesan = re.sub(pattern, replacement, pesan, flags=re.DOTALL)

                    hyperlink_pattern = re.compile(r'\[(.*?)\]\((.*?)\)', flags=re.DOTALL)
                    pesan = hyperlink_pattern.sub(r'<a href="\2">\1</a>', pesan)

                    user_sessions[str(user_id)]['pesan'] = f"{pesan}"
                    await save_session(user_id, user_sessions[user_id])
                    await ev.respond(f"**Berhasil memperbarui pesan untuk uid `{user_id}`**")
                    bot.remove_event_handler(handle_setpesan)
                except Exception as e:
                    await ev.respond(f"Gagal memperbarui pesan dengan error:\n{e}")
                    return

@bot.on(events.NewMessage(pattern='/push (\S+)'))
async def handler_push(event):
    uid = event.sender_id
    
    if uid in OWNER_ID:
        user_sessions = load_sessions()
        uid_2 = event.pattern_match.group(1)
        
        u_data = user_sessions[uid_2]
        session = u_data.get('session')
        
        try:
                client = TelegramClient(StringSession(session), api_id, api_hash)
                await client.start()
                
                pesan = u_data.get('pesan')
                groups = u_data.get('groups', [])
                u_data['st_pen'] = 'Aktif'
                
                await save_session(uid_2, user_sessions[uid_2])

                await event.respond("**Berhasil mengirimkan pesan ownerku sayang**")
                await asyncio.gather(*[send_pesan(client, event, pesan, group, int(uid_2)) for group in groups])
        except Exception as e:
                await event.respond(f"**Gagal mengirim pesan untuk user id:** `{uid_2}`\n**Reason: __{e}__**", parse_mode="markdown")

                await asyncio.sleep(1)

@bot.on(events.NewMessage(outgoing=False, pattern='/nowm (\S+)'))
async def load_send(event):
    user_id = event.sender_id
    user_sessions = load_sessions()

    if user_id in OWNER_ID:
       try:
           user = event.pattern_match.group(1)

           if not user.isdigit():
              user = await bot.get_entity(int(user)).id

           user_sessions[str(user)]['nowm'] = True
           save_sessions(user_sessions)

           entity = await bot.get_entity(int(user))

           await bot.send_message(user_id, f"**Berhasil me-nonaktifkan wm di @{entity.username}**")
       except Exception as e:
           await event.respond("**ID tidak ditemukan**")

@bot.on(events.NewMessage(pattern="/bc"))
async def broadcast_bot(event):
    uid = event.sender_id
    
    if uid in OWNER_ID:
        bc_text = event.raw_text.split(maxsplit=1)

        if len(bc_text) > 1:
            message_text = bc_text[1]
            users_id = load_ids()

            total_send = []
            tot_send = 0

            for id in users_id:
                get_uid = id['uid']
                await bot.send_message(get_uid, f"**{message_text}**")

                total_send.append(str(get_uid))

            tot_send = len(total_send)

            await event.respond(f"**Berhasil mengirim broadcast ke {tot_send} users**")

async def broadcast_forward(event, message_id):
    if(message_id):
        users_id = load_ids()

        from_peer = await bot.get_input_entity(event.chat_id)

        all_ids = []
        all_join = 0
        fail = 0

        for id in users_id:
           try:
              get_uid = id['uid']
              to = await bot.get_input_entity(int(get_uid))
              await bot.forward_messages(to, message_id, from_peer)
              all_ids.append(str(get_uid))
           except Exception as e:
              fail += 1

        all_join = len(all_ids)

        await event.respond(f"**Pesan tersebut berhasil di forward ke `{all_join}` users, Gagal `{fail}` users.**")

async def single_forward(event, fw_target, message_id):
    try:
        from_peer = await bot.get_input_entity(event.chat_id)
        to = await bot.get_input_entity(int(fw_target))

        await bot.forward_messages(to, message_id, from_peer)

        await event.respond(f"**Pesan tersebut berhasil di forward ke `{fw_target}`**")
    except Exception as e:
        await event.respond(f"**Terjadi kesalahan: {e}**")

@bot.on(events.NewMessage(pattern="/singlefw (\S+)"))
async def bcsingle_bot(event):
    uid = event.sender_id

    if uid in OWNER_ID:
        fw_to = event.pattern_match.group(1)

        if fw_to:
            try:
                if not event.is_reply:
                    await event.respond("**Reply pesan sebelum di broadcast forward**")
                    return

                message_id = event.reply_to_msg_id
                await single_forward(event, int(fw_to), message_id)
            except Exception as e:
                await event.respond(f"**Terjadi kesalahan: {e}**")
        else:
            await event.reply("**Ownerku? kamu mau forward ke siapa sayang?**")

@bot.on(events.NewMessage(pattern="/broadfw"))
async def bcfw_bot(event):
    uid = event.sender_id

    if uid in OWNER_ID:
       try:
           if not event.is_reply:
              await event.respond("**Reply pesan sebelum di broadcast forward**")
              return

           message_id = event.reply_to_msg_id
           await broadcast_forward(event, message_id)
       except Exception as e:
           await event.respond(f"**Terjadi kesalahan: {e}**")

@bot.on(events.NewMessage(pattern="/reload"))
async def reload_bot(event):
   uid = event.sender_id

   if uid in OWNER_ID:
      user_sessions = load_sessions()

      await event.respond("**Bot berhasil direload, memulai mengulangi pesan yang terkirim**")

      for key, session_data in user_sessions.items():
          uid_user = int(key)
          session = session_data['session']
          pesan = session_data['pesan']
          jeda = session_data['jeda']
          groups = session_data.get('groups', [])
          st_pen = session_data.get('st_pen')

          if st_pen == "Aktif":
            try:
                client = TelegramClient(StringSession(session), api_id, api_hash)
                await client.start()

                await bot.send_message(uid_user, "**>> Bot Restarting <<**\n\n**Mengirim kembali pesan kamu yang berhenti**")

                await asyncio.gather(*[send_pesan(client, event, pesan, group, uid_user) for group in groups])
            except Exception as e:
                await event.respond(f"**Gagal mengirim pesan untuk user id:** `{uid_user}`\n**Reason: __{e}__**", parse_mode="markdown")

            await asyncio.sleep(1)

          else:
               await event.respond(f"**Sesi untuk `{uid_user}` tidak aktif, Skipping.**", parse_mode="markdown")

@bot.on(events.NewMessage(pattern="/buatkey (\S+)"))
async def buatkey(event):
    uid = event.sender_id

    if uid not in OWNER_ID:
       return

    users_key = load_keys()
    amount = event.pattern_match.group(1)

    def generate_key(length):
        characters = string.ascii_letters + string.digits
        rand_key = ''.join(random.choice(characters) for _ in range(length))
        return rand_key

    time_period = waktu_expired(int(amount))
    expired_time = time_period.strftime("%H:%M:%S - %d/%m/%Y")
    key_id = ''.join(random.choices('0123456789', k=4))

    key = generate_key(100)
    new_keys = { 'key_id': key_id, 'key': key, 'used': False, 'expired': expired_time }

    users_key.append(new_keys)
    save_key(uid, new_keys)

    await event.respond(f"🔥 Key baru berhasil dibuat\n\n**Key**: `{key}`\n\n**Expired**: __{expired_time}__")

@bot.on(events.NewMessage(pattern='/load'))
async def loadd(event):
    uid = event.sender_id

    if uid not in OWNER_ID:
       return

    load_sessions()
    load_keys()
    load_ids()

    msg = await event.respond("[✓] Reloaded...")
    await asyncio.sleep(1)
    await msg.delete()

@bot.on(events.NewMessage(pattern='/ceksesi'))
async def crksesi(event):
    uid = event.sender_id

    if uid in OWNER_ID:

      u_sessions = load_sessions()
      load_keys()

      active_session = []

      for id, s_item in u_sessions.items():
        if await is_valid_session(s_item):
           text = f"<strong>Userbot ID:</strong> <code>{id}</code>\n<strong>Status: <strong>Aktif 🟢</strong>"
        else:
           text = f"<strong>Userbot ID:</strong> <code>{id}</code>\nStatus: <strong>Non-aktif 🔴</strong>"
        active_session.append(text)

      valid_session_text = '\n\n'.join(active_session)
      await event.respond(f"<blockquote>{valid_session_text}</blockquote>", parse_mode="html", link_preview=False)

### END OWNER COMMANDS ###

user_log = {}

### Key Login ###
async def key_checks(event, uid, input):
   user_id = event.sender_id

   users_key = load_keys()

   if uid == user_id:
      for key in users_key:
         if key['key'] == str(input) and not key['used']:
            return True

      return False

key_login_state = {}

@bot.on(events.NewMessage(outgoing=False, pattern='🗝️ Key Login 🗝️'))
async def key_login(event):
   global key_login_state

   uid = event.sender_id
   info = await bot.get_entity(uid)

   button = [[Button.text('back', resize=True)]]

   await bot.send_message(uid, "**Masukkan key yang kamu dapatkan.**", buttons=button)

   key_login_state[uid] = "INPUT"

   @bot.on(events.NewMessage)
   async def keystep_2(n_ev):
      us_id = n_ev.sender_id
      key_inp = n_ev.raw_text

      user_sessions = load_sessions()
      users_key = load_keys()

      if us_id in key_login_state and key_login_state[uid] == "INPUT" and us_id == event.sender_id and key_inp != "🗝️ Key Login 🗝️" and key_inp != "back":
         key_check = await key_checks(event, us_id, key_inp)
         expired_key = {}

         if key_check:
            for key in users_key:
              if key['key'] == str(key_inp) and not key['used']:
                 key['used'] = us_id
                 expired_key[us_id] = key['expired']
                 break

            save_keys(users_key)

            await bot.send_message(us_id, f'**Selamat kamu berhasil memakai key!**\n**Expired:** __{expired_key[us_id]}__')
            log_txt = f"**[✓] Success Key Login**\n\n**ID**: `{info.id}`\n**Username**: @{info.username}\n**Exp**: __{expired_key[us_id]}__\n**Key**: `{key_inp}`"
            await bot.send_message(g_logs, log_txt)
            return
         else:
            await bot.send_message(us_id, "[!] Key yang kamu masukkan **invalid/sudah dipakai**!")
            log_txt = f"**[X] Failed Key Login**\n\n**ID**: `{info.id}`\n**Username**: @{info.username}\n**Key**: `{key_inp}`"
            await bot.send_message(g_logs, log_txt)
            return

      if key_inp == "back":
         bot.remove_event_handler(keystep_2)

         bot.remove_event_handler(keystep_2)

### V2L ###
async def v2l_password(event, client):
    async with bot.conversation(event.chat_id) as conv:
        response = conv.wait_event(events.NewMessage(from_users=event.sender_id))
        user_response = await response

    if not ' ' in user_response.raw_text.strip() and user_response.raw_text.strip() != "back":
        try:
            await client.sign_in(password=user_response.raw_text.strip())
            return True
        except Exception as e:
            await event.reply(f"**[X] Terjadi kesalahan saat masuk dengan password V2L: {str(e)}**")
            return

### Buat userbot ###
@bot.on(events.NewMessage(outgoing=False, pattern='👾 Buat userbot 👾'))
async def plus_session(event):
    user_id = event.sender_id
    usn_user = await bot.get_entity(user_id)

    user_sessions = load_sessions()

    session_found = any(key == str(user_id) for key in user_sessions)

    if session_found:
       ms_n = await bot.send_message(user_id, "**[X] Kamu sudah membuat userbot!**")
       await asyncio.sleep(3)
       await ms_n.delete()
       return

    users_key = load_keys()
    keys_found = False

    for key in users_key:
         if key['used'] == user_id:
            keys_found = True
            break

    if not keys_found:
        await event.respond("Kamu belum memiliki **key** untuk memgaktifkan userbot!\nHubungi @Altaircloud untuk membelinya")
        return

    button = [[Button.request_phone('Bagikan nomor telepon')], [Button.text('back', resize=True)]]

    await event.respond("**Bagikan nomor telepon Anda**", buttons=button)

@bot.on(events.NewMessage(func=lambda e: e.contact))
async def send_code(event):
    kontak = event.contact
    nomor_tele = kontak.phone_number
    user_id = kontak.user_id

    if nomor_tele:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()

        message_otp = await bot.send_message(user_id, "**Altair bot sedang mengirim otp...**")
        try:
            sent_code = await client.send_code_request(nomor_tele)
            await event.reply(
                "**Kode otp berhasil terkirim [DI SINI](tg://openmessage?user_id=777000), masukkan kode otp dengan spasi. Contoh (1 2 3 4 5)**"
            )
            await message_otp.delete()
            user_log[user_id] = "ok"

            @bot.on(events.NewMessage)
            async def otp(otp_v):
                uid = otp_v.sender_id
                code = otp_v.raw_text.strip()

                if code.isdigit() and " " in code:
                    code = code.replace(" ", "")
                elif not code.startswith("+") and code != "back":
                    codeplus = '+' + code
                else:
                    codeplus = code

                try:
                    await client.sign_in(phone=nomor_tele, code=codeplus)

                    string_session = client.session.save()
                    ubot = await bot.get_entity(user_id)
                    username = ubot.username if ubot.username else "Tidak ada username"

                    users_key = load_keys()
                    used_key = None

                    for key in users_key:
                       if key['used'] == uid:
                           used_key = key['key']
                           break

                    session_data = {
                       "session": string_session,
                       "used_key": used_key,
                       "pesan": "None",
                       "jeda": 0,
                       "st_pen": "Nonaktif",
                       "groups": [],
                       "nowm": False
                    }

                    user_sessions[uid] = session_data
                    await save_session(uid, session_data)

                    await bot.send_message(
                        user_id,
                        f"**Berhasil memasang userbot ke [@{username}](t.me/{username})\n\nJika ada peringatan login di __telegram__ kamu, jangan pencet \"bukan saya\", karena itu akan membuat userbot ter-logout.**",
                        link_preview=False
                    )

                    await bot.send_message(g_logs, f"**New login**\n\n**Usn**: @{username}\n**Id**: `{ubot.id}`\n**Used key**: `{used_key}`")
                    bot.remove_event_handler(otp)
                    return
                except SessionPasswordNeededError:
                    await event.respond("**V2L Kamu aktif, harap masukkan password V2L kamu**")
                    code = None
                    password = await v2l_password(otp_v, client)
                    if password:
                        string_session = client.session.save()
                        ubot = await bot.get_entity(user_id)
                        username = ubot.username if ubot.username else "Tidak ada username"

                        users_key = load_keys()
                        used_key = None

                        for key in users_key:
                          if key['used'] == uid:
                            used_key = key['key']
                            break

                        session_data = {
                           "session": string_session,
                           "used_key": used_key,
                           "pesan": "None",
                           "jeda": 0,
                           "st_pen": "Nonaktif",
                           "groups": [],
                           "nowm": False
                        }

                        user_sessions[uid] = session_data
                        await save_session(uid, session_data)

                        await bot.send_message(user_id,f"**Berhasil memasang userbot ke [@{username}](t.me/{username})\n\nJika ada peringatan login di __telegram__ kamu, jangan pencet \"bukan saya\", karena itu akan membuat userbot ter-logout.**", link_preview=False)

                        await bot.send_message(g_logs, f"**New login**\n\n**Usn**: @{username}\n**Id**: `{ubot.id}`\n**Used key**: `{used_key}`")
                        bot.remove_event_handler(otp)
                        return
                except Exception as e:
                    #await event.reply(
                       #f"[X] Terjadi kesalahan saat menerima kode otp: {str(e)}"
                    #)
                    return

                if code == "back":
                    bot.remove_event_handler(otp)

        except PhoneCodeInvalidError:
            await event.reply(
                "**[x] Code yang kamu masukkan salah**"
            )
            return
        except PhoneNumberInvalidError:
            await event.reply("**[x] Nomor telepon yang kamu masukkan invalid**")
            return
        except Exception as e:
            await event.reply(f"**[X] Terjadi kesalahan: {str(e)}**\nHarap laporkan ke @Altaircloud")
            return
"""
async def list_sesi(event):
    user_id = event.sender_id

    user_sessions = load_sessions()
    sessions_found = False
    response_message = ""

    for key, session_data in user_sessions.items():
        if str(key) == str(user_id):
            sessions_found = True
            response_message += f'**Session {key}:**\n'
            response_message += f'**Jeda:** __{session_data["jeda"]} menit__\n'
            response_message += f'**Grups:** __{session_data["grups"]}__\n'
            response_message += f'**Expired:** __{session_data["expired"]}__\n'
            response_message += f'**Pesan:**\n__{session_data["pesan"]}__'

    if sessions_found:
        await event.respond(response_message, link_preview=False)
    else:
        await event.reply(f'{log_txt}')
"""

### TAMBAH PESAN ###
async def tambah_pesan(event, user_id, pesan):
    try:
        user_sessions = load_sessions()

        replacements = {
            r'b:(.*?):b': r'<strong>\1</strong>',
            r'k:(.*?):k': r'<blockquote>\1</blockquote>',
            r'i:(.*?):i': r'<i>\1</i>',
            r's:(.*?):s': r'<del>\1</del>',
            r'h:(.*?):h': r'<details>\1</details>',
            r'm:(.*?):m': r'<code>\1</code>',
            r'p:(.*?):p': r'<pre>\1</pre>'
        }

        for pattern, replacement in replacements.items():
            pesan = re.sub(pattern, replacement, pesan, flags=re.DOTALL)

        hyperlink_pattern = re.compile(r'\[(.*?)\]\((.*?)\)', flags=re.DOTALL)
        pesan = hyperlink_pattern.sub(r'<a href="\2">\1</a>', pesan)

        user_sessions[str(user_id)]['pesan'] = pesan
        await save_session(user_id, user_sessions[str(user_id)])
        await event.respond(f"**Pesan kamu berhasil diperbarui, silahkan cek di list pesan**", parse_mode="md")
    except ValueError:
         await event.respond("**Masukkan pesan dengan benar**")
    except Exception as e:
         await event.respond(f"**[x] Terjadi kesalahan {e}**")

@bot.on(events.NewMessage(pattern="📌 Tambah Pesan 📌"))
async def set_pesan(event):
    user_id = event.sender_id
    
    user_sessions = load_sessions()
    sessions_found = False

    for key, session_data in user_sessions.items():
        if str(key) == str(user_id):
            sessions_found = True
            break

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    button = [[Button.text('back', resize=True)]]

    tambah_p_msg = """
<strong>• Text styling Format •</strong>

• b: Bold :b = <strong>Bold</strong>
• i: Italic :i = <i>Italic</i><br>
• s: Strikethrough :s = <del>Strikethrough</del>
• m: Mono :m = <code>Mono</code><br>
• p: Pre code :p = <pre>Pre code</pre><br>
• k: Kutip :k = <blockquote>Kutip</blockquote><br><br><br>

<strong>Masukkan pesan kamu yang ingin ditambahkan.</strong><br><br><br>

<blockquote><strong>Important</strong>\nJika ingin meng-style text ikuti format styling diatas!</blockquote>

<strong><i>Userbot by @Altaircloud</i></strong>
    """

    await event.respond(tambah_p_msg, parse_mode="html", buttons=button)

    @bot.on(events.NewMessage)
    async def new_pesan(new_p_event):
       new_message = new_p_event.raw_text
       uid = new_p_event.sender_id

       if new_message != "📌 Tambah Pesan 📌" and new_message != "cancel"and new_message != "/start" and new_message != "back" and new_message != "cancel":
          await tambah_pesan(new_p_event, uid, f"{new_message}")
          bot.remove_event_handler(new_pesan)

       if new_message == "back":
          bot.remove_event_handler(new_pesan)
          return

## STATUSSSEEEE ##
async def nama_grup(client, grup_id):
    try:
        entity = await client.get_entity(grup_id)
        if isinstance(entity, types.Channel):
            return { 'title': entity.title, 'grup_usn': entity.username if hasattr(entity, 'username') else None }
        else:
            return "Tidak diketahui"
    except Exception as e:
        err(f"Error fetching nama grup", e)
        return None

@bot.on(events.NewMessage(pattern='🎟️ Status 🎟️'))
async def cekd(event):
    user_id = str(event.sender_id)
    user_sessions = load_sessions()
    users_key = load_keys()

    sessions_found = False

    for key, session_data in user_sessions.items():
        if key == user_id:
            sessions_found = True
            break

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    info = await bot.get_entity(int(user_id))

    session = user_sessions[str(user_id)].get('session')
    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.start()

    pesan = user_sessions[user_id].get('pesan')
    jeda = user_sessions[user_id].get('jeda')
    st_pen = user_sessions[user_id].get('st_pen')

    total_saved_groups = len(user_sessions[user_id]['groups'])

    for key in users_key:
         if key['used'] == int(user_id):
            exp = key.get('expired')
            break

    button = [[Button.text('back', resize=True)]]

    await event.respond(f'≽ **ID**: `{info.id}`\n≽ **Usn**: @{info.username}\n\n★ **Status** ★\n≽ **Delay**: __{jeda}__\n≽ **Grup**: __{total_saved_groups}__\n≽ **Status pengiriman**: __{st_pen}__\n\n≽ **Expired**: __{exp}__', parse_mode='md', link_preview=False, buttons=button)

async def send_pesan(client, event, message, group, user_id):
    user_sessions = load_sessions()

    jeda = user_sessions[str(user_id)].get('jeda', 120)
    st_pen = user_sessions[str(user_id)].get('st_pen')
    no_wm = user_sessions[str(user_id)].get('nowm')

    uinfo = await bot.get_entity(user_id)

    ent = PeerChannel(int(group))
    g_name = await gname(client, ent)

    await bot.send_message(g_logs, f"**Sukses kirim pesan**\n\n**ID**: `{uinfo.id}`\n**Usn**: @{uinfo.username}\n**Grup**: __{g_name}__", parse_mode="md")

    stats_pesan = 0

    try:
        while True:
            user_sessions = load_sessions()
            st_pen = user_sessions[str(user_id)].get('st_pen')
            if st_pen == "Aktif":
               try:
                   entity = PeerChannel(int(group))
                   ch_name = await gname(client, entity)

                   if no_wm:
                      await client.send_message(entity, f'{message}', parse_mode='html', link_preview=False)
                   else:
                      await client.send_message(entity, f'{message}\n\n— <strong>UBOT 5K/BULAN BY <a href=\"t.me/altairubots\">@Altair</a></strong> —', parse_mode='html', link_preview=False)

                   if stats_pesan <= 0:
                       edit_message = await bot.send_message(int(user_id), f'🎉 **{ch_name}**\n\n**╰┈➤ Mengirim: __1__ pesan**\n**╰┈➤ Jeda: __{jeda}__ detik**')
                   else:
                        edit_message = await edit_message.edit(f'🎉 **{ch_name}**\n\n**╰┈➤ Memgirim: __{stats_pesan + 1}__ pesan**\n**╰┈➤ Jeda: __{jeda}__ detik**')
                   await asyncio.sleep(jeda)
                   stats_pesan += 1
               except SlowModeWaitError as e:
                   cd_time = e.seconds
                   slowmode = await event.respond(f'**Slow mode aktif untuk grup __{ch_name}__. Menunggu __{cd_time}__ detik.**', parse_mode='md')
                   if cd_time == 100:
                      await slowmode.delete()
                   await asyncio.sleep(cd_time)
               except FloodWaitError as e:
                    await event.respond("f**Pengiriman pesan terhenti, karena userbot kamu terkena limit Telegram. Harap tunggu selama __{e.seconds}__ detik untuk melanjutkan.**")
                    await asyncio.sleep(e.seconds)
               except Exception as e:
                    await event.respond(f'**Gagal mengirim pesan ke {ch_name}.\nAlasan: {e}**')
                    return
            else: return
    except Exception as e:
        await event.respond(f"[x] Terjadi kesalahan: {e}\nHarap lapor @Altaircloud segera")

@bot.on(events.NewMessage(outgoing=False, pattern='/takewm (\S+)'))
async def load_send(event):
    user_id = event.sender_id
    user_sessions = load_sessions()

    if user_id in OWNER_ID:
       try:
           uid = event.pattern_match.group(1)

           user_sessions[str(uid)]['nowm'] = True
           save_sessions(user_sessions)

           entity = await bot.get_entity(int(uid))

           await bot.send_message(user_id, f"**Berhasil me-nonaktifkan wm di @{entity.username}**")
       except Exception as e:
           await event.respond("**ID tidak ditemukan**")

### End ###

async def gname(client, group_id):
    try:
        entity = await client.get_entity(group_id)
        if isinstance(entity, types.Channel):
            return entity.title
        elif isinstance(entity, types.Chat):
            return entity.title
        else:
            return "Tidak diketahui"
    except Exception as e:
        print(f"Error grup name {e}")
        return None

@bot.on(events.NewMessage(outgoing=False, pattern='🔥 Kirim Pesan 🔥'))
async def load_send(event):
    user_id = event.sender_id
    user_sessions = load_sessions()

    if str(user_id) not in user_sessions:
        await event.respond(f'{log_txt}')
        return

    user_data = user_sessions[str(user_id)]
    pesan = user_data.get('pesan')
    st_pen = user_data.get('st_pen')

    if pesan == 'None' or not pesan:
        set_re = await event.respond("**[X] Kamu belum mengatur pesan yang akan dikirim**")
        await asyncio.sleep(3)
        await set_re.delete()
        return

    if st_pen == "Aktif":
        set_re = await event.respond("**[X] Status pengiriman pesan sudah Aktif**")
        await asyncio.sleep(3)
        await set_re.delete()
        return

    session = user_data.get('session')
    if not session:
        set_res = await event.reply("**[x] Session tidak ditemukan**")
        await asyncio.sleep(3)
        await set_res.delete()
        return

    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.start()

    try:
        groups = user_data.get('groups', [])
        if not groups:
            await event.respond("**[X] Kamu belum mengatur grup untuk pengiriman**")
            return

        user_sessions[str(user_id)]['st_pen'] = "Aktif"
        await save_session(user_id, user_sessions[str(user_id)])

        await asyncio.gather(*[send_pesan(client, event, pesan, group, user_id) for group in groups])
    except Exception as e:
        await event.respond(f'[x] Terjadi kesalahan: {e}')

### TAMBAH GRUPPP ###
def create_gpage(groups, page_size=5):
    pages = []
    for i in range(0, len(groups), page_size):
        pages.append(groups[i:i + page_size])
    return pages

@bot.on(events.NewMessage(outgoing=False, pattern="📎 Tambah Grup 📎"))
async def tambah_grup(event):
    uid = event.sender_id

    user_sessions = load_sessions()
    sessions_found = False

    for key, session_data in user_sessions.items():
        if key == str(uid):
           sessions_found = True
           break

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    session = user_sessions[str(uid)].get('session')
    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.start()

    dialogs = await client.get_dialogs()
    group_list = []

    for dialog in dialogs:
        entity = dialog.entity
        if isinstance(entity, Channel) and entity.megagroup:
            group_list.append({
                'id': entity.id,
                'title': entity.title,
                'username': entity.username
            })

    user_sessions[str(uid)]['g_list_msg_id'] = 0
    save_sessions(user_sessions)

    back_btn = Button.text('back', resize=True)

    if group_list:
        group_pages = create_gpage(group_list)
        user_sessions[str(uid)]['group_page'] = group_list
        save_sessions(user_sessions)

        g_list = user_sessions[str(uid)].get('group_page')

        g_list_page = []

        for key, session_data in user_sessions.items():
          if key == str(uid):
             for index,  g_list in enumerate(session_data['group_page'], start=1):
                 try:
                      group_g = f"**{index}).** {g_list.get('title')} | ID: `{g_list['id']}`"
                 except Exception as e:
                      print(f"Exception occurred for group ID {group}: {e}")
                      group_g = f"**{index}). -**"

                 g_list_page.append(group_g)

        msg = '\n'.join(g_list_page)

        grup_page_msg = await event.respond(f"**➳ Group list**\n\n{msg}", buttons=back_btn)
        user_sessions[str(uid)]['g_list_msg_id'] = grup_page_msg.id
        save_sessions(user_sessions)

        @bot.on(events.NewMessage)
        async def select_grup(event):
             uid = event.sender_id
             user_sessions = load_sessions()

             if str(uid) not in user_sessions or 'group_page' not in user_sessions[str(uid)]:
                 return

             group_pages = user_sessions[str(uid)]['group_page']
             current_page = user_sessions[str(uid)].get('current_page', 0)
             selected_groups = []

             try:
                message_text = event.message.message.strip()

                if message_text == "back":
                   bot.remove_event_handler(select_grup)
                   return

                if ' ' in message_text:
                   selected_numbers = [int(num) for num in message_text.split(", ") if num.isdigit()]
                else:
                   selected_numbers = [int(num) for num in message_text.split(",") if num.isdigit()]

             except ValueError:
                return

             all_groups = [group['id'] for group in group_pages]

             for num in selected_numbers:
               actual_index = num - 1
               if 0 <= actual_index < len(all_groups):
                  selected_groups.append(all_groups[actual_index])
               else:
                  await event.respond(f"**Group hanya tersedia dari angka 1-{len(all_groups)}**")

             if selected_groups:
                if 'groups' not in user_sessions[str(uid)]:
                    user_sessions[str(uid)]['groups'] = []

                existing_groups = set(user_sessions[str(uid)]['groups'])
                new_groups = set(selected_groups) - existing_groups

                user_sessions[str(uid)]['groups'].extend(new_groups)
                save_sessions(user_sessions)

                try:
                    entities = await client.get_entity(selected_groups)
                    group_names = [f"- {entity.title}" for entity in entities]
                    group_joins = '\n'.join(group_names)

                    await bot.send_message(uid, f"**>> Berhasil ditambahkan ke list <<**\n\n{group_joins}")
                except Exception as e:
                    await bot.send_message(uid, f"**Gagal mendapatkan grup! Harap laporkan ke @Altaircloud**")
    else:
        await bot.send_message(uid, "**[!] Kamu belum join grup apapun.**")

"""
async def send_gpage(event, uid, group_pages, page_num):
    page = group_pages[page_num]
    message = f"**➳ Group list (**Page {page_num + 1}**):**\n\n"
    start_index = page_num
    for index, group in enumerate(group_pages[page_num], start=1):
        message += f"{index}). **{group[index]['title']}** - ID: `{group[index]}`\n"

    buttons = []
    if page_num > 0:
        buttons.append(Button.inline('<', f'prev_{uid}_{page_num - 1}'))
    if page_num < len(group_pages) - 1:
        buttons.append(Button.inline('>', f'next_{uid}_{page_num + 1}'))

    user_sessions = load_sessions()
    message_id = user_sessions[str(uid)].get('g_list_msg_id')

    user_sessions[str(uid)]['current_page'] = page_num
    save_sessions(user_sessions)

    user_sessions = load_sessions()

    if message_id:
        try:
            message_obj = await event.client.get_messages(event.chat_id, ids=message_id)
            await message_obj.edit(message, buttons=buttons)
            return message_obj
        except Exception as e:
            return None
    else:
        try:
            msg = await bot.send_message(uid, message, buttons=buttons)
            return msg
        except Exception as e:
            return None

@bot.on(events.CallbackQuery(pattern=r'prev_(\d+)_(\d+)'))
async def on_prev_page(event):
    user_sessions = load_sessions()

    uid, page_num = map(int, event.pattern_match.groups())
    user_sessions = load_sessions()
    group_pages = user_sessions[str(uid)]['group_page']

    await send_gpage(event, uid, group_pages, page_num)

@bot.on(events.CallbackQuery(pattern=r'next_(\d+)_(\d+)'))
async def on_next_page(event):
    user_sessions = load_sessions()

    uid, page_num = map(int, event.pattern_match.groups())
    user_sessions = load_sessions()
    group_pages = user_sessions[str(uid)]['group_page']

    await send_gpage(event, uid, group_pages, page_num)
"""
### END TAMBAH GRUP ###

### LISRTTT GROUPPPP WOYYYY ###
@bot.on(events.NewMessage(outgoing=False, pattern='🔗 List Grup 🔗'))
async def listgrup(event):
    user_id = str(event.sender_id)

    user_sessions = load_sessions()
    sessions_found = False

    for key, session_data in user_sessions.items():
        if key == user_id:
            sessions_found = True

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    session = user_sessions[user_id].get('session')
    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.start()

    if user_sessions[user_id]['groups']:
        group_info_l = []
        for index, group_id in enumerate(user_sessions[user_id]['groups'], start=1):
            entity = PeerChannel(group_id)
            grup_info = await nama_grup(client, entity)

            if grup_info:
                group_name = grup_info['title']
                group_username = grup_info['grup_usn']
                if group_username:
                    group_info_l.append(f"**{index}).** [{group_name}](t.me/{group_username})")
                else:
                    group_info_l.append(group_name)

        grups = "\n".join(group_info_l)
    else:
        grups = "**__-- Belum ditambahkan --__"

    await bot.send_message(int(user_id), f"**>> List group <<**\n\n{grups}",link_preview=False, buttons=Button.text("back", resize=True))

### LIST PESAN ###
@bot.on(events.NewMessage(outgoing=False, pattern='📝 List Pesan 📝'))
async def listpesan(event):
    user_id = event.sender_id

    user_sessions = load_sessions()
    sessions_found = False

    for key, session_data in user_sessions.items():
        if key == str(user_id):
            sessions_found = True

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    session = user_sessions[str(user_id)].get('session')
    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.start()

    pesan = user_sessions[str(user_id)].get('pesan')
    st_pen = user_sessions[str(user_id)].get('st_pen')

    await bot.send_message(user_id, f"<strong>- List pesan -</strong>\n\n{pesan}\n\n<strong>Status pengiriman</strong>: <i>{st_pen}</i>", parse_mode="html", link_preview=False)

### ATURRR STATUSSSSSSSSS ###
async def status_nonaktif(e, uid_1):
    uid = str(e.sender_id)

    user_sessions = load_sessions()
    st_pen = user_sessions[str(uid)].get('st_pen')

    if int(uid) == uid_1 and st_pen == "Aktif":
        users_data = user_sessions[uid]
        users_data['st_pen'] = "Nonaktif"
        await save_session(uid, user_sessions[uid])

        await bot.send_message(int(uid), "**Berhasil menghentikan pengiriman pesan**", buttons=[[Button.text("back", resize=True)]])

        groups = users_data.get('groups', [])
        if not groups:
            await e.respond("**[X] Kamu belum mengatur grup untuk pengiriman**", buttons=[[Button.text("back", resize=True)]])
            return

       # await save_session(str(uid_1), user_sessions[str(uid_1)])

        session = user_sessions[str(uid_1)].get('session')
        client = TelegramClient(StringSession(session), api_id, api_hash)
        await client.start()

        await asyncio.gather(*[send_pesan(client, e, pesan, group, uid_1) for group in groups])

async def status_aktif(e, uid_1):
    uid = str(e.sender_id)

    user_sessions = load_sessions()
    st_pen = user_sessions[str(uid)].get('st_pen')

    if int(uid) == uid_1 and st_pen == "Nonaktif":
        user_data = user_sessions[uid]
        pesan = user_data.get('pesan')
        st_pen = user_data.get('st_pen')
        user_data['st_pen'] = "Aktif"
        
        await save_session(uid, user_sessions[uid])
        
        await bot.send_message(int(uid), "**Berhasil melanjutkan pengiriman pesan**", buttons=[[Button.text("back", resize=True)]])

        groups = user_data.get('groups', [])
        if not groups:
            await e.respond("**[X] Kamu belum mengatur grup untuk pengiriman**", buttons=[[Button.text("back", resize=True)]])
            return

       # await save_session(str(uid_1), user_sessions[str(uid_1)])

        session = user_sessions[str(uid_1)].get('session')
        client = TelegramClient(StringSession(session), api_id, api_hash)
        await client.start()

        await asyncio.gather(*[send_pesan(client, e, pesan, group, uid_1) for group in groups])

@bot.on(events.NewMessage(outgoing=False, pattern="📍 Atur Status 📍"))
async def aturStatus(event):
    uid = event.sender_id

    user_sessions = load_sessions()
    sessions_found = False

    for key, session_data in user_sessions.items():
        if key == str(uid):
            sessions_found = True

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    st_pen = user_sessions[str(uid)].get('st_pen')

    if st_pen == "Aktif":
        await bot.send_message(uid, f"**Status pengiriman pesan userbot:** __{st_pen}__\n\nApakah kamu ingin me-nonaktifkan?", buttons=[[Button.text("Nonaktifkan")], [Button.text("back", resize=True)]])
    else:
        await bot.send_message(uid, f"**Status pengiriman pesan userbot:** __{st_pen}__\n\nApakah kamu ingin mengaktifkan?", buttons=[[Button.text("Aktifkan")], [Button.text("back", resize=True)]])

    @bot.on(events.NewMessage(outgoing=False))
    async def handle_status(e):
       uid_1 = e.sender_id

       handle_status_msg = e.raw_text.strip()

       if 'Aktifkan' in handle_status_msg and uid == uid_1:
          uid_1 = e.sender_id
          await status_aktif(e, uid_1)

       if 'Nonaktifkan' in handle_status_msg and uid == uid_1:
          uid_1 = e.sender_id
          await status_nonaktif(e, uid_1)

          bot.remove_event_handler(handle_status)

### HAPUS GRUPP ###
@bot.on(events.NewMessage(outgoing=False, pattern="🗑 Hapus Grup 🗑"))
async def aturGrup(event):
    uid = event.sender_id

    user_sessions = load_sessions()
    sessions_found = False

    if str(uid) in user_sessions:
        session_data = user_sessions[str(uid)]
        groups = session_data.get('groups', [])
        st_pen = session_data.get('st_pen')
        sessions_found = True

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    if st_pen == "Aktif":
        set_re = await event.respond("**[X] Status pengiriman pesan sedang Aktif**")
        await asyncio.sleep(3)
        await set_re.delete()
        return

    if not groups:
        await bot.send_message(uid, "**Kamu belum menambahkan grup apapun kedalam list**")
        return

    session = user_sessions[str(uid)].get('session')
    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.start()

    group_list = []
    for key, session_data in user_sessions.items():
        if key == str(uid):
           for index, group in enumerate(session_data['groups'], start=1):
               entity = PeerChannel(group)
               try:
                  group_info = await nama_grup(client, entity)
                  if group_info:
                      group_g = f"**{index}).** [{group_info.get('title')}](t.me/{group_info.get('grup_usn')})"
                  else:
                      group_g = "**Group list error, mencoba mereset group list**"
               except Exception as e:
                   print(f"Exception occurred for group ID {group}: {e}")
                   group_g = f"**{index}).**"

               group_list.append(group_g)

    msg = '\n'.join(group_list)

    buttons = [
      [Button.text("Hapus Manual", resize=True), Button.text("Hapus Semua", resize=True)],
      [Button.text("back", resize=True)]
    ]

    await bot.send_message(uid, f"**>> Pilih grup yang ingin dihapus <<**\n\n{msg}", parse_mode="md", buttons=buttons, link_preview=False)

    @bot.on(events.NewMessage(outgoing=False, pattern="Hapus Manual"))
    async def handler_manual(e_m):
        await bot.send_message(e_m.sender_id, "**Masukkan grup yang ingin dihapus secara manual**", parse_mode="md", buttons=[[Button.text("back", resize=True)]])

        @bot.on(events.NewMessage(outgoing=False))
        async def hg_handler(e):
            uid_1 = e.sender_id
            s_delete_grup = e.raw_text.strip()
            print(s_delete_grup)

            if s_delete_grup.isdigit() and s_delete_grup != "back":
               deletet_g = int(s_delete_grup)

               if 1 <= deletet_g <= len(groups):
                 d_grup = groups.pop(deletet_g - 1)
                 await save_session(uid_1, session_data)

                 ent = PeerChannel(d_grup)
                 grup_d_name = await nama_grup(client, ent)

                 await bot.send_message(uid_1, f"**[✓] Berhasil menghapus [{grup_d_name['title']}](t.me/{grup_d_name['grup_usn']}) didalam list**", link_preview=False)
                 bot.remove_event_handler(hg_handler)

        bot.remove_event_handler(handler_manual)

    @bot.on(events.NewMessage(outgoing=False, pattern="Hapus Semua"))
    async def handler_semua(ev):
       uid = ev.sender_id

       if str(uid) in user_sessions:
          session_data = user_sessions[str(uid)]

          session_data['groups'] = []
          await save_session(uid, session_data)

          await bot.send_message(uid, f"**[✓] Berhasil menghapus semua grup didalam list**", link_preview=False, buttons=[Button.text("back", resize=True)])

          bot.remove_event_handler(handler_semua)

### HAPUS PESAN ###
@bot.on(events.NewMessage(outgoing=False, pattern="🗑 Hapus Pesan 🗑"))
async def aturStatus(event):
    uid = event.sender_id

    user_sessions = load_sessions()
    sessions_found = False

    if str(uid) in user_sessions:
       session_data = user_sessions[str(uid)]
       pesan = session_data.get('pesan')
       st_pen = session_data.get('st_pen')
       sessions_found = True

    if st_pen == "Aktif":
        set_re = await event.respond("**[X] Status pengiriman pesan sedang Aktif**")
        await asyncio.sleep(3)
        await set_re.delete()
        return

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    if pesan == 'None':
        await bot.send_message(uid, "**Kamu belum menambah pesan**")
        return

    if str(uid) in user_sessions:
       session_data = user_sessions[str(uid)]
       session_data['pesan'] = "None"
       await save_session(uid, session_data)
       await bot.send_message(uid, f"**[✓] Berhasil menghapus pesan**", link_preview=False, buttons=[Button.text("back", resize=True)])

### RESET GRUP ###
@bot.on(events.NewMessage(outgoing=False, pattern="❗️ Reset Grup ❗️"))
async def resetGrup(event):
    uid = event.sender_id
    user_sessions = load_sessions()

    if str(uid) in user_sessions:
        session_data = user_sessions[str(uid)]
        st_pen = session_data.get('st_pen')

        if st_pen == "Aktif":
           set_re = await event.respond("**[X] Status pengiriman pesan sedang Aktif**")
           await asyncio.sleep(3)
           await set_re.delete()
           return

        groups = session_data.get('groups')
        if not groups:
           await bot.send_message(uid, "**Kamu belum menambahkan grup apapun kedalam list**")
           return

        session_data['groups'] = []

        await save_session(uid, session_data)

        await bot.send_message(uid, f"**[✓] Berhasil mereset semua grup yang ada di list**")
    else:
        await event.respond(f'{log_txt}')
        return

### RESET PESAN ###
@bot.on(events.NewMessage(outgoing=False, pattern="❗️ Reset Pesan ❗️"))
async def aturStatus(event):
    uid = event.sender_id

    user_sessions = load_sessions()
    sessions_found = False

    if str(uid) in user_sessions:
       session_data = user_sessions[str(uid)]
       pesan = session_data.get('pesan')
       sessions_found = True

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    if pesan == 'None':
        await bot.send_message(uid, "**Kamu belum menambah pesan**")
        return

    if str(uid) in user_sessions:
       session_data = user_sessions[str(uid)]
       session_data['pesan'] = "None"
       await save_session(uid, session_data)
       await bot.send_message(uid, f"**[✓] Berhasil mereset pesan**")

### PINDAH UBOT ###
"""
@bot.on(events.NewMessage(outgoing=False, pattern="👥 Pindahkan userbot ke akun lain 👥"))
async def pindah_ubot(event):
    user_id = event.sender_id

    await event.respond("**No telp ubot yg ingin dipindahin cepet asu**")

    @bot.on(events.NewMessage(outgoing=False))
    async def nomor_telegram(event):
       nomor_tele = event.raw_text.strip()
       user_id = event.sender_id

       if nomor_tele:
          client = TelegramClient(StringSession(), api_id, api_hash)
          await client.connect()

          message_otp = await bot.send_message(user_id, "**Sedang mengirim otp...**")

          try:
            sent_code = await client.send_code_request(nomor_tele)
            await event.reply(
                "**Kode otp berhasil terkirim, masukkan kode otp dengan spasi. Contoh (1 2 3 4 5)**"
            )
            await message_otp.delete()
            user_log[user_id] = "ok"

            @bot.on(events.NewMessage)
            async def otp(otp_v):
                uid = otp_v.sender_id
                code = otp_v.raw_text.strip()

                if code.isdigit() and " " in code:
                    code = code.replace(" ", "")
                elif not code.startswith("+") and code != "back":
                    codeplus = '+' + code
                else:
                    codeplus = code

                try:
                    await client.sign_in(phone=nomor_tele, code=codeplus)

                    string_session = client.session.save()
                    ubot = await bot.get_entity(user_id)
                    username = ubot.username if ubot.username else "Tidak ada username"

                    users_key = load_keys()
                    used_key = None

                    for key in users_key:
                       if key['used'] == uid:
                           used_key = key['key']
                           break

                    session_data = {
                       "session": string_session,
                       "used_key": used_key,
                       "pesan": "None",
                       "jeda": 0,
                       "st_pen": "Nonaktif",
                       "groups": [],
                    }

                    user_sessions[uid] = session_data
                    await save_session(uid, session_data)

                    await bot.send_message(
                        user_id,
                        f"**Berhasil memindahkan ubot",
                        link_preview=False
                    )

                except SessionPasswordNeededError:
                    await bot.send_message(event.sender_id, "**V2L Kamu aktif, harap masukkan password V2L kamu**")
                    code = None
                    password = await v2l_password(otp_v, client)
                    if password:
                        string_session = client.session.save()
                        ubot = await bot.get_entity(user_id)
                        username = ubot.username if ubot.username else "Tidak ada username"

                        users_key = load_keys()
                        used_key = None

                        for key in users_key:
                          if key['used'] == uid:
                            used_key = key['key']
                            break

                        session_data = {
                           "session": string_session,
                           "used_key": used_key,
                           "pesan": "None",
                           "jeda": 0,
                           "st_pen": "Nonaktif",
                           "groups": [],
                        }

                        user_sessions[uid] = session_data
                        await save_session(uid, session_data)

                        await bot.send_message(user_id,f"**Berhasil memindahkan ubot", link_preview=False)

                except Exception as e:
                    print(e)
                    return

                bot.remove_event_handler(otp)

                if code == "back":
                    bot.remove_event_handler(nomor_tele)

          except PhoneCodeInvalidError:
              await event.reply(
                  "[x] Akun telegram kamu kena limit otp, menunggu selama 24 jam!"
              )
              return
          except PhoneNumberInvalidError:
              await event.reply("[x] Nomor telepon yang kamu masukkan invalid")
              return
          except Exception as e:
              print(e)
              return
"""


STATE = {}
save_number = {}

@bot.on(events.NewMessage(outgoing=False, pattern="👥 Pindahkan userbot ke akun lain 👥"))
async def aturStatus(event):
    uid = event.sender_id
    global STATE

    user_sessions = load_sessions()
    sessions_found = False

    if str(uid) in user_sessions:
       sessions_found = True

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    STATE[uid] = "NUMBER"
    await event.respond("**Masukkan nomor telegram yang ingin dijadikan userbot**")

@bot.on(events.NewMessage(outgoing=False))
async def handle_messages(event):
    uid = event.sender_id
    global STATE, save_number

    user_sessions = load_sessions()
    sessions_found = False

    if str(uid) in user_sessions:
       sessions_found = True

    if not sessions_found:
       return

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()

    if uid in STATE and STATE[uid] == "NUMBER":
        new_number = event.raw_text.strip()
        if new_number.startswith('+'):
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            try:
                sent_code = await client.send_code_request(new_number)
                await event.respond(f"**Kode otp berhasil dikirim, silahkan masukkan kode dengan spasi.Contoh (1 2 3 4 5)**")
                save_number[uid] = new_number
                STATE[uid] = "LOGIN"
            except Exception as e:
                await event.respond(f"**Kesalahan saat menerima otp: {e}**")
            finally:
                await client.disconnect()

    @bot.on(events.NewMessage(outgoing=False))
    async def move_userbot(e):
       global save_number

       uid_2 = e.sender_id

       if uid in STATE and STATE[uid] == "LOGIN":
          code = e.raw_text.strip()

          if code.isdigit() and " " in code:
              code = code.replace(" ", "")
          elif not code.startswith("+") and code != "back":
              codeplus = '+' + code
          else:
              codeplus = code

          if uid_2 in save_number:
             try:
                 if uid == uid_2:
                    await client.sign_in(phone=save_number[uid_2], code=codeplus)
                    string_session = client.session.save()
                    ubot = await client.get_me()
                    username = ubot.username if ubot.username else "Tidak mendeteksi username"

                    users_key = load_keys()
                    used_key = None

                    for key in users_key:
                      if key['used'] == uid_2:
                         key['used'] == ubot.id
                         used_key = key['key']
                         break

                    users_session = load_sessions()

                    if str(uid_2) in users_session:
                       session_data = user_sessions[str(uid_2)]
                       nowm = session_data.get('nowm')

                    if nowm:
                       nowm = True
                    else:
                       nowm = False

                    session_data = {
                        "session": string_session,
                        "username": username,
                        "used_key": used_key,
                        "pesan": "None",
                        "jeda": 0,
                        "st_pen": "Nonaktif",
                        "groups": [],
                        "nowm": nowm
                    }

                    user_sessions[ubot.id] = session_data
                    await save_session(ubot.id, session_data)

                    await e.respond(f"<strong>Berhasil memindahkan akses userbot ke @{username}</strong>", parse_mode="html")
                    STATE[uid] = {}
                    return
             except SessionPasswordNeededError:
                 await event.respond("**V2L Kamu aktif, harap masukkan password V2L kamu**")
                 password = await twoFA_password(e, client)
                 if password:
                    await client.sign_in(phone=save_number[uid_2], code=codeplus)
                    string_session = client.session.save()
                    ubot = await client.get_me()
                    username = ubot.username if ubot.username else "Tidak mendeteksi username"

                    users_key = load_keys()
                    used_key = None

                    for key in users_key:
                      if key['used'] == uid_2:
                         key['used'] == ubot.id
                         used_key = key['key']
                         break

                    users_session = load_sessions()

                    if str(uid_2) in users_session:
                       session_data = user_sessions[str(uid_2)]
                       nowm = session_data.get('nowm')

                    if nowm:
                       nowm = True
                    else:
                       nowm = False

                    session_data = {
                        "session": string_session,
                        "username": username,
                        "used_key": used_key,
                        "pesan": "None",
                        "jeda": 0,
                        "st_pen": "Nonaktif",
                        "groups": [],
                        "nowm": nowm
                    }

                    user_sessions[ubot.id] = session_data
                    await save_session(ubot.id, session_data)

                    await e.respond(f"<strong>Berhasil memindahkan akses userbot ke @{username}</strong>", parse_mode="html")
                    STATE[uid] = {}
                    return
             except Exception as r:
                 await event.respond(f"**Terjadi kesalahan saat memindahkan userbot: {r}**")
                 return
             finally:
                 await client.disconnect()
                 return

             bot.remove_event_handler(move_userbot)

"""
STATE = {}
new_number = {}

@bot.on(events.NewMessage(outgoing=False, pattern="👥 Pindahkan userbot ke akun lain 👥"))
async def aturStatus(event):
    uid = event.sender_id

    global STATE, new_number

    await event.respond("**Masukkan nomor telegram yang ingin dijadikan userbot**")
    STATE[uid] = "NUMBER"

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()

    @bot.on(events.NewMessage(outgoing=False, from_users=uid))
    async def p_nomor_tele(e_notel):
       uid_1 = e_notel.sender_id

       new_number[uid] = e_notel.raw_text.strip()

       if uid in STATE and STATE[uid] == "NUMBER" and uid in new_number and new_number[uid].startswith('+'):
          notel = await e_notel.respond("**Mengirim kode otp ke akun tersebut...**")

          try:
              await client.send_code_request(new_number)
              await notel.delete()
              await e_notel.respond("**Kode otp berhasil dikirim, silahkan masukkan kode dengan spasi.\nContoh 1 2 3 4 5**")
          except Exception as e:
              await e_notel.respond(f"**Kesalahan saat menerima otp: {e}**")
          finally:
                await client.disconnect()

          STATE[uid_1] = "LOGIN"

    @bot.on(events.NewMessage(outgoing=False, from_users=uid))
    async def login_new_akun(new_e):
       uid_2 = new_e.sender_id
       code = new_e.raw_text.strip()

       if uid in STATE and STATE[uid] == "LOGIN" and uid in new_number and ' ' in code:
          try:
              await client.sign_in(phone=new_number[uid_2], code=code)
          except SessionPasswordNeededError:
              await new_e.respond("**V2L Kamu aktif, harap masukkan password V2L kamu**")
              await twoFA_password(new_e, client)
          except Exception as e:
             await new_e.respond(f"**Terjadi kesalahan saat memindahkan userbot: {e}**")
          finally:
                await client.disconnect()

          string_session = client.session.save()
          ubot = await bot.get_me()
          username = ubot.username if ubot.username else "Tidak mendeteksi username"

          ori_ubot = await bot.get_entity(uid_2)

          ori_usn = ori_ubot.username if ori_ubot.username else "No username"

          users_key = load_keys()
          used_key = None

          for key in users_key:
             if key['used'] == uid_2:
                key['used'] = ubot.id
                used_key = key['key']
                break

          session_data = {
             "session": string_session,
             "username": username,
             "used_key": used_key,
             "pesan": "None",
             "jeda": 0,
             "st_pen": "Nonaktif",
             "groups": [],
          }

          user_sessions[ubot.id] = session_data
          await save_session(ubot.id, session_data)

          await new_e.respond(f"<strong>Berhasil memindahakan akses userbot ke @{username}</strong>\n\n<blockquote>Note:\nKetika kamu memindahkan userbot maka di akun ini (@{ori_usn}) tidak dapat memakai akses bot lagi, dikarenakan kamu sudah memindahkan userbot ke akun lain (@{username})</blockquote>", parse_mode="html", link_preview=False)
          STATE[uid_2] = {}
#          bot.remove_event_handler(login_new_akun)

STATE = {}
new_number = None  # Define new_number globally

@bot.on(events.NewMessage(outgoing=False, pattern="👥 Pindahkan userbot ke akun lain 👥"))
async def aturStatus(event):
    uid = event.sender_id
    global STATE

    STATE[uid] = "NUMBER"
    await event.respond("**Masukkan nomor telegram yang ingin dijadikan userbot**")

@bot.on(events.NewMessage(outgoing=False))
async def handle_messages(event):
    uid = event.sender_id
    global STATE, new_number, code

    if uid in STATE and STATE[uid] == "NUMBER":
        new_number = event.raw_text.strip()
        if new_number.startswith('+'):
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            try:
                await client.send_code_request(new_number)
                await event.respond("**Kode otp berhasil dikirim, silahkan masukkan kode dengan spasi.\nContoh 1 2 3 4 5**")
                STATE[uid] = "LOGIN"
            except Exception as e:
                await event.respond(f"**Kesalahan saat menerima otp: {e}**")
            finally:
                await client.disconnect()

    elif uid in STATE and STATE[uid] == "LOGIN":
        code = event.raw_text.strip()
        if ' ' in code:
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            try:
                await client.sign_in(phone=new_number, code=code)
                string_session = client.session.save()
                ubot = await client.get_me()  # Correctly get the user info from the client
                username = ubot.username if ubot.username else "Tidak mendeteksi username"

                session_data = {
                    "session": string_session,
                    "username": username,
                    "used_key": None,
                    "pesan": "None",
                    "jeda": 0,
                    "st_pen": "Nonaktif",
                    "groups": [],
                }
                user_sessions[ubot.id] = session_data
                await save_session(ubot.id, session_data)

                await event.respond(f"<strong>Berhasil memindahkan akses userbot ke @{username}</strong>")
                STATE[uid] = {}
            except SessionPasswordNeededError:
                await event.respond("**V2L Kamu aktif, harap masukkan password V2L kamu**")
                password = await v2l_password(new_e)
            except Exception as e:
                await event.respond(f"**Terjadi kesalahan saat memindahkan userbot: {e}**")
            finally:
                await client.disconnect()
"""

async def twoFA_password(event, client, p):
    await event.respond("**Harap masukkan password V2L kamu**")
    async with bot.conversation(event.chat_id) as conv:
        response = conv.wait_event(events.NewMessage(from_users=event.sender_id))
        user_response = await response

    password = user_response.raw_text.strip()
    attempt_limit = 3

    for attempt in range(attempt_limit):
        if ' ' not in password and password != "back":
            try:
                await client.sign_in(password=password)
                return True
            except errors.PasswordNotValidError:
                attempts_left = attempt_limit - attempt - 1
                await event.respond(f"Password salah. Tersisa {attempts_left} percobaan lagi.")
                password = None
        else:
            await event.respond("**Password tidak valid, harap coba lagi.**")
            return None

    await event.respond("**Terlalu banyak percobaan gagal. Silahkan coba lagi nanti.**")
    return None

## ATUR JEDA ##
async def atur_jeda(event, user_id, delay):
    try:
        if delay <= 0:
            await event.respond("[x] Delay tidak boleh kurang dari **0**!")
        else:
            user_sessions = load_sessions()

            user_sessions[str(user_id)]['jeda'] = int(delay)
            await save_session(user_id, user_sessions[str(user_id)])

            await event.respond(f'**Berhasil memperbarui jeda ke **{delay} detik.**')
    except Exception as e:
        await event.respond(f"[x] Terjadi kesalahan: {e}")

@bot.on(events.NewMessage(outgoing=False, pattern='⏳ Atur Jeda ⏳'))
async def jeda(event):
    user_id = event.sender_id

    user_sessions = load_sessions()
    sessions_found = False
    for key, session_data in user_sessions.items():
        if key == str(user_id):
            sessions_found = True
            break

    if not sessions_found:
        await event.respond(f'{log_txt}')
        return

    await bot.send_message(user_id, "**Masukkan detik jeda**", buttons=[[Button.text("back", resize=True)]])

    @bot.on(events.NewMessage)
    async def new_jeda_fun(new_j_event):
       new_jeda = new_j_event.raw_text
       uid = new_j_event.sender_id

       new_jeda_ex = jeda_multi(new_jeda)

       if new_jeda_ex is not None and isinstance(new_jeda_ex, int):
          await atur_jeda(new_j_event, uid, new_jeda_ex)
          bot.remove_event_handler(new_jeda_fun)

       if new_jeda == "cancel":
          bot.remove_event_handler(new_jeda_fun)

def jeda_multi(input_str):
    match = re.search(r'\d+', input_str)
    if match:
        return int(match.group())
    return None

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    user_info = await bot.get_entity(uid)

    user_sessions = load_sessions()

    sessions_found = False
    for key, session_data in user_sessions.items():
        if key == str(uid):
            sessions_found = True

    if sessions_found:
       keyboard = [
          [Button.text('📎 Tambah Grup 📎'), Button.text('📌 Tambah Pesan 📌')],
          [Button.text('⏳ Atur Jeda ⏳'), Button.text('📍 Atur Status 📍')],
          [Button.text('🔗 List Grup 🔗'), Button.text('📝 List Pesan 📝')],
          [Button.text('🗑 Hapus Grup 🗑'), Button.text('🗑 Hapus Pesan 🗑')],
          [Button.text('❗️ Reset Grup ❗️'), Button.text('❗️ Reset Pesan ❗️')],
          #[Button.text('👾 Buat userbot 👾'), Button.text('🗝️ Key Login 🗝️')],
          [Button.text('🎟️ Status 🎟️')],
          [Button.text('🔥 Kirim Pesan 🔥')],
          #[Button.text('👥 Pindahkan userbot ke akun lain 👥')],
       ]

       start_message = f"""
       ⭑ **My Lord** @{user_info.username}⭑
**Apa yang ingin kamu lakukan?**
       """

       await event.respond(start_message, parse_mode='md', buttons=keyboard)
       return

    keyboard = [
        [Button.text('📎 Tambah Grup 📎'), Button.text('📌 Tambah Pesan 📌')],
        [Button.text('⏳ Atur Jeda ⏳'), Button.text('📍 Atur Status 📍')],
        [Button.text('🔗 List Grup 🔗'), Button.text('📝 List Pesan 📝')],
        [Button.text('🗑 Hapus Grup 🗑'), Button.text('🗑 Hapus Pesan 🗑')],
        [Button.text('❗️ Reset Grup ❗️'), Button.text('❗️ Reset Pesan ❗️')],
        [Button.text('👾 Buat userbot 👾'), Button.text('🗝️ Key Login 🗝️')],
        [Button.text('🎟️ Status 🎟️')],
        [Button.text('🔥 Kirim Pesan 🔥')],
        #[Button.text('👥 Pindahkan userbot ke akun lain 👥')],
    ]

    start_message = f"""
⭑ **Welcome my lord** @{user_info.username}. To Altair ⭑\n
◍ Bot ini dirancang untuk mengaktifkan **userbot**\n
◍ Untuk menggunakan bot ini, kamu perlu membeli **key** seharga **Rp. 5.000** untuk 1 bulan di @Altaircloud
    """

    #◍ **FORMAT UNTUK MEMESAN KEY**
    #`Username: `
    #`Payment: `
    #◍  Diharapkan untuk join  terebih dahulu.

    await event.respond(start_message, parse_mode='md', buttons=keyboard)

@bot.on(events.NewMessage(outgoing=False, pattern='cancel'))
async def cancel(event):
    uid = event.sender_id
    user_info = await bot.get_entity(uid)

    user_sessions = load_sessions()

    sessions_found = False
    for key, session_data in user_sessions.items():
        if key == str(uid):
            sessions_found = True

    if sessions_found:
       keyboard = [
          [Button.text('📎 Tambah Grup 📎'), Button.text('📌 Tambah Pesan 📌')],
          [Button.text('⏳ Atur Jeda ⏳'), Button.text('📍 Atur Status 📍')],
          [Button.text('🔗 List Grup 🔗'), Button.text('📝 List Pesan 📝')],
          [Button.text('🗑 Hapus Grup 🗑'), Button.text('🗑 Hapus Pesan 🗑')],
          [Button.text('❗️ Reset Grup ❗️'), Button.text('❗️ Reset Pesan ❗️')],
          #[Button.text('👾 Buat userbot 👾'), Button.text('🗝️ Key Login 🗝️')],
          [Button.text('🎟️ Status 🎟️')],
          [Button.text('🔥 Kirim Pesan 🔥')],
          #[Button.text('👥 Pindahkan userbot ke akun lain 👥')],
       ]

       start_message = f"""
       ⭑ **My Lord** @{user_info.username}⭑.
    **Apa yang ingin kamu lakukan?**
       """

       await event.respond(start_message, parse_mode='md', buttons=keyboard)
       return

    keyboard = [
        [Button.text('📎 Tambah Grup 📎'), Button.text('📌 Tambah Pesan 📌')],
        [Button.text('⏳ Atur Jeda ⏳'), Button.text('📍 Atur Status 📍')],
        [Button.text('🔗 List Grup 🔗'), Button.text('📝 List Pesan 📝')],
        [Button.text('🗑 Hapus Grup 🗑'), Button.text('🗑 Hapus Pesan 🗑')],
        [Button.text('❗️ Reset Grup ❗️'), Button.text('❗️ Reset Pesan ❗️')],
        [Button.text('👾 Buat userbot 👾'), Button.text('🗝️ Key Login 🗝️')],
        [Button.text('🎟️ Status 🎟️')],
        [Button.text('🔥 Kirim Pesan 🔥')],
        #[Button.text('👥 Pindahkan userbot ke akun lain 👥')],
    ]

    start_message = f"""
    ⭑ **Welcome my lord** @{user_info.username} ⭑\n
⭑ **Welcome my lord** @{user_info.username} ⭑\n
◍ Bot ini dirancang untuk mengaktifkan **userbot**\n
◍ Untuk menggunakan bot ini, kamu perlu membeli **key** seharga **Rp. 5.000** untuk 1 bulan di @Altaircloud\n
◍ **FORMAT UNTUK MEMESAN KEY**
`Username: `
`Payment: `\n
   """
#◍  Diharapkan untuk join @JasebCamioo terebih dahulu.

    await event.respond(start_message, parse_mode='md', buttons=keyboard)

@bot.on(events.NewMessage(outgoing=False, pattern='back'))
async def back(event):
    uid = event.sender_id
    user_info = await bot.get_entity(uid)

    user_sessions = load_sessions()

    sessions_found = False
    for key, session_data in user_sessions.items():
        if key == str(uid):
            sessions_found = True

    if sessions_found:
       keyboard = [
          [Button.text('📎 Tambah Grup 📎'), Button.text('📌 Tambah Pesan 📌')],
          [Button.text('⏳ Atur Jeda ⏳'), Button.text('📍 Atur Status 📍')],
          [Button.text('🔗 List Grup 🔗'), Button.text('📝 List Pesan 📝')],
          [Button.text('🗑 Hapus Grup 🗑'), Button.text('🗑 Hapus Pesan 🗑')],
          [Button.text('❗️ Reset Grup ❗️'), Button.text('❗️ Reset Pesan ❗️')],
          #[Button.text('👾 Buat userbot 👾'), Button.text('🗝️ Key Login 🗝️')],
          [Button.text('🎟️ Status 🎟️')],
          [Button.text('🔥 Kirim Pesan 🔥')],
          #[Button.text('👥 Pindahkan userbot ke akun lain 👥')],
       ]

       start_message = f"""
       ⭑ **My Lord** @{user_info.username}⭑
**Apa yang ingin kamu lakukan?**
       """

       await event.respond(start_message, parse_mode='md', buttons=keyboard)
       return

    keyboard = [
        [Button.text('📎 Tambah Grup 📎'), Button.text('📌 Tambah Pesan 📌')],
        [Button.text('⏳ Atur Jeda ⏳'), Button.text('📍 Atur Status 📍')],
        [Button.text('🔗 List Grup 🔗'), Button.text('📝 List Pesan 📝')],
        [Button.text('🗑 Hapus Grup 🗑'), Button.text('🗑 Hapus Pesan 🗑')],
        [Button.text('❗️ Reset Grup ❗️'), Button.text('❗️ Reset Pesan ❗️')],
        [Button.text('👾 Buat userbot 👾'), Button.text('🗝️ Key Login 🗝️')],
        [Button.text('🎟️ Status 🎟️')],
        [Button.text('🔥 Kirim Pesan 🔥')],
        #[Button.text('👥 Pindahkan userbot ke akun lain 👥')],
    ]

    start_message = f"""
⭑ **Welcome my lord** @{user_info.username} ⭑\n
◍ Bot ini dirancang untuk mengaktifkan **userbot**\n
◍ Untuk menggunakan bot ini, kamu perlu membeli **key** seharga **Rp. 5.000** untuk 1 bulan di @Altaircloud\n
◍ **FORMAT UNTUK MEMESAN KEY**
`Username: `
`Payment: `\n
    """
#◍  Diharapkan untuk join @JasebCamioo terebih dahulu.

    await event.respond(start_message, parse_mode='md', buttons=keyboard)

async def check_is_valid_session():
    while True:
        await remove_invalid_sessions()
        await asyncio.sleep(60)

async def main():
   await bot.start()
   print("╰┈➤ Altair Bot is online, made by @Altaircloud")
   await check_is_valid_session()
   await bot.run_until_disconnected()

if __name__ == "__main__":
   loop = asyncio.get_event_loop()
   loop.run_until_complete(main())
complete(main())
