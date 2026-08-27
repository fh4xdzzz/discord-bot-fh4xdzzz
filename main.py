import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime, timedelta
import requests
import re
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
TOKEN = os.getenv('DISCORD_TOKEN')
DATA_FILE = 'bot_data.json'

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
# intents.presences = True  # Desactivado para optimizar rendimiento (no se usa)
intents.guilds = True
intents.moderation = True
intents.invites = True
intents.messages = True
intents.reactions = True

# Bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Cargar datos
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f'[Error] Error al decodificar JSON: {e}. Creando datos por defecto.')
            return create_default_data()
        except Exception as e:
            print(f'[Error] Error al cargar datos: {e}. Creando datos por defecto.')
            return create_default_data()
    return create_default_data()

def create_default_data():
    return {
        'users': {},
        'warns': {},
        'tickets': {},
        'banned_words': ['palabra1', 'palabra2'],
        'config': {
            'level_channel': None,
            'ticket_category': None,
            'welcome_channel': None,
            'ranking_channel': None,
            'ranking_message_id': None,
            'stream_channel': None,
            'streamers': [],
            'auto_roles': [],
            'verification_channel': None,
            'verification_message_id': None,
            'verification_role': None,
            'verified_users': [],
            'giveaway_channel': None,
            'giveaway_announcement_channel': None,
            'notifications_channel': None,
            'log_channel': None,
            'notification_roles': {
                'streams': None,
                'giveaways': None,
                'announcements': None,
                'events': None
            }
        },
        'giveaways': {},
        'user_notifications': {}
    }

def validate_data():
    """Asegura que los datos tengan la estructura correcta"""
    required_keys = {
        'users': dict,
        'warns': dict,
        'tickets': dict,
        'banned_words': list,
        'config': dict,
        'giveaways': dict,
        'user_notifications': dict,
        'servers': dict
    }

    required_config_keys = {
        'level_channel': (int, type(None)),
        'ticket_category': (int, type(None)),
        'welcome_channel': (int, type(None)),
        'ranking_channel': (int, type(None)),
        'ranking_message_id': (int, type(None)),
        'stream_channel': (int, type(None)),
        'streamers': list,
        'auto_roles': list,
        'verification_channel': (int, type(None)),
        'verification_message_id': (int, type(None)),
        'verification_role': (int, type(None)),
        'verified_users': list,
        'giveaway_channel': (int, type(None)),
        'giveaway_announcement_channel': (int, type(None)),
        'notifications_channel': (int, type(None)),
        'log_channel': (int, type(None)),
        'notification_roles': dict
    }

    # Validar estructura principal
    for key, expected_type in required_keys.items():
        if key not in data:
            print(f'[Validación] Campo faltante: {key}, agregando valor por defecto')
            data[key] = required_keys[key]() if callable(required_keys[key]) else required_keys[key]
        elif not isinstance(data[key], expected_type):
            print(f'[Validación] Campo {key} tiene tipo incorrecto, corrigiendo')
            data[key] = required_keys[key]() if callable(required_keys[key]) else required_keys[key]

    # Validar configuración
    if 'config' not in data:
        data['config'] = {}

    for key, expected_types in required_config_keys.items():
        if key not in data['config']:
            print(f'[Validación] Campo de configuración faltante: {key}, agregando valor por defecto')
            if isinstance(expected_types, type):
                data['config'][key] = expected_types() if expected_types != type(None) else None
            else:
                data['config'][key] = expected_types[0]() if expected_types[0] != type(None) else None
        elif not isinstance(data['config'][key], expected_types):
            print(f'[Validación] Campo de configuración {key} tiene tipo incorrecto, corrigiendo')
            if isinstance(expected_types, type):
                data['config'][key] = expected_types() if expected_types != type(None) else None
            else:
                data['config'][key] = expected_types[0]() if expected_types[0] != type(None) else None

    # Validar notification_roles
    if 'notification_roles' in data['config']:
        required_notification_roles = ['streams', 'giveaways', 'announcements', 'events']
        for role_type in required_notification_roles:
            if role_type not in data['config']['notification_roles']:
                data['config']['notification_roles'][role_type] = None

    # Validar estructura de servidores
    if 'servers' not in data:
        data['servers'] = {}

    save_data()
    print('[Validación] Datos validados y corregidos correctamente')

# Sistema de caché y guardado optimizado
_data_needs_save = False
_save_interval = 60  # Guardar cada 60 segundos como máximo

def save_data():
    """Guarda datos con sistema de caché para optimizar rendimiento"""
    global _data_needs_save
    _data_needs_save = True

async def _auto_save():
    """Tarea en background para guardar datos automáticamente"""
    global _data_needs_save
    while True:
        await asyncio.sleep(_save_interval)
        if _data_needs_save:
            try:
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                _data_needs_save = False
                print('[Optimización] Datos guardados automáticamente')
            except Exception as e:
                print(f'[Error] Error al guardar datos: {e}')

def save_data_immediate():
    """Guarda datos inmediatamente (sin caché) para operaciones críticas"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f'[Error] Error al guardar datos: {e}')
        raise

# Caché de usuarios para evitar llamadas repetitivas a la API
_user_cache = {}
_cache_expiry = 300  # 5 minutos

def get_cached_user(user_id):
    """Obtiene usuario del caché o lo busca"""
    current_time = datetime.now().timestamp()
    if user_id in _user_cache:
        cached_data = _user_cache[user_id]
        if current_time - cached_data['timestamp'] < _cache_expiry:
            return cached_data['user']
    return None

def cache_user(user_id, user):
    """Guarda usuario en caché"""
    _user_cache[user_id] = {
        'user': user,
        'timestamp': datetime.now().timestamp()
    }

# Funciones helper para configuración por servidor
def get_server_config(guild_id):
    """Obtiene la configuración específica de un servidor"""
    server_id = str(guild_id)
    if 'servers' not in data:
        data['servers'] = {}
    if server_id not in data['servers']:
        data['servers'][server_id] = {}
    return data['servers'][server_id]

def get_server_setting(guild_id, key, default=None):
    """Obtiene un valor de configuración específico del servidor"""
    config = get_server_config(guild_id)
    return config.get(key, default)

def set_server_setting(guild_id, key, value):
    """Establece un valor de configuración específico del servidor"""
    config = get_server_config(guild_id)
    config[key] = value
    save_data()

data = load_data()
validate_data()  # Validar y corregir estructura de datos

# Inicializar variables globales desde data['config'] para compatibilidad
log_channel_id = data['config'].get('log_channel')
ranking_channel_id = data['config'].get('ranking_channel')
ranking_message_id = data['config'].get('ranking_message_id')
stream_channel_id = data['config'].get('stream_channel')
streamers_to_monitor = data['config'].get('streamers', [])
giveaway_channel_id = data['config'].get('giveaway_channel')
giveaway_announcement_channel_id = data['config'].get('giveaway_announcement_channel')
notifications_channel_id = data['config'].get('notifications_channel')
notification_roles = data['config'].get('notification_roles', {})
user_notifications = data.get('user_notifications', {})
auto_roles = data['config'].get('auto_roles', [])
verification_channel_id = data['config'].get('verification_channel')
verification_message_id = data['config'].get('verification_message_id')
verification_role_id = data['config'].get('verification_role')
verified_users = data['config'].get('verified_users', [])
giveaways = data.get('giveaways', {})
stream_notifications = {}  # Para rastrear notificaciones de streams enviadas

# Sistema de rate limiting mejorado
log_rate_limit = {}  # {user_id: {last_log_time}}
LOG_RATE_LIMIT_SECONDS = 5  # Máximo 1 log por usuario cada 5 segundos

# Cooldowns para comandos frecuentes
command_cooldowns = {}  # {user_id: {command_name: last_used_time}}
COOLDOWN_PERIODS = {
    'ping': 10,  # 10 segundos
    'level': 30,  # 30 segundos
    'top': 60,  # 1 minuto
    'server_stats': 60,  # 1 minuto
    'info': 30  # 30 segundos
}

def check_cooldown(user_id, command_name):
    """Verifica si un usuario está en cooldown para un comando"""
    current_time = datetime.now().timestamp()
    if user_id not in command_cooldowns:
        command_cooldowns[user_id] = {}

    if command_name in command_cooldowns[user_id]:
        last_used = command_cooldowns[user_id][command_name]
        cooldown_period = COOLDOWN_PERIODS.get(command_name, 0)
        if current_time - last_used < cooldown_period:
            remaining = int(cooldown_period - (current_time - last_used))
            return False, remaining

    command_cooldowns[user_id][command_name] = current_time
    return True, 0

# Función para enviar logs
async def send_log(guild, title, description, color=0x3498db, fields=None, author=None, thumbnail=None):
    if not guild:
        print(f'[Logs] No se proporcionó guild. Evento: {title}')
        return

    # Obtener log_channel específico del servidor con fallback a global
    log_channel_id = get_server_setting(guild.id, 'log_channel', data['config'].get('log_channel'))
    
    if not log_channel_id:
        print(f'[Logs] Canal de logs no configurado para servidor {guild.name}. Evento: {title}')
        return

    try:
        log_channel = bot.get_channel(log_channel_id)
        if not log_channel:
            print(f'[Logs] Canal de logs no encontrado. ID: {log_channel_id}. Evento: {title}')
            return

        # Verificar permisos del bot en el canal
        bot_permissions = log_channel.permissions_for(guild.me)
        if not bot_permissions.send_messages or not bot_permissions.embed_links:
            print(f'[Logs] El bot no tiene permisos para enviar mensajes en el canal de logs. Evento: {title}')
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )

        if fields:
            for field in fields:
                embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', False))

        if author:
            embed.set_author(name=author['name'], icon_url=author.get('icon_url'))

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        embed.set_footer(text=f'Sistema de Logs - {guild.name}')

        await log_channel.send(embed=embed)
        print(f'[Logs] Log enviado exitosamente: {title}')
    except discord.errors.Forbidden as e:
        print(f'[Logs] Error de permisos al enviar log: {e}. Evento: {title}')
    except discord.errors.NotFound as e:
        print(f'[Logs] Canal de logs no encontrado (404): {e}. Evento: {title}')
    except Exception as e:
        print(f'[Logs] Error al enviar log: {e}. Evento: {title}')

# Función para enviar notificaciones
async def send_notification(guild, notification_type, message, color=0x3498db, mention_role=True):
    if not guild:
        return

    # Obtener configuración específica del servidor con fallback a global
    notifications_channel_id = get_server_setting(guild.id, 'notifications_channel', data['config'].get('notifications_channel'))
    notification_roles = get_server_setting(guild.id, 'notification_roles', data['config'].get('notification_roles', {}))
    
    if not notifications_channel_id:
        return
    
    try:
        notifications_channel = bot.get_channel(notifications_channel_id)
        if not notifications_channel:
            return
        
        role_id = notification_roles.get(notification_type)
        role_mention = ''
        
        if mention_role and role_id:
            role = guild.get_role(role_id)
            if role:
                role_mention = role.mention
        
        embed = discord.Embed(
            title=f'🔔 {notification_type.upper()}',
            description=message,
            color=color,
            timestamp=datetime.now()
        )
        
        embed.set_footer(text=f'Sistema de Notificaciones - {guild.name}')
        
        await notifications_channel.send(content=role_mention, embed=embed)
        print(f'[Notificaciones] Notificación enviada: {notification_type}')
    except Exception as e:
        print(f'[Notificaciones] Error al enviar notificación: {e}')

# Listas de protección
DANGEROUS_DOMAINS = [
    'mrbeast.com', 'mrbeast.io', 'mrbeast.org',
    'mrbeastgiveaway.com', 'mrbeastgift.com',
    'free-gift.com', 'free-reward.com',
    'steam-gift.com', 'steam-reward.com',
    'discord-gift.com', 'discord-reward.com',
    'free-discord.com', 'free-nitro.com',
    'nitro-free.com', 'discord-nitro-free.com',
    'free-games.com', 'free-game.com',
    'robux-free.com', 'free-robux.com',
    'bitcoin-giveaway.com', 'crypto-gift.com',
    'phishing.com', 'scam.com', 'hack.com',
    'malware.com', 'virus.com', 'trojan.com'
]

DANGEROUS_PATTERNS = [
    r'(http[s]?://)?(www\.)?mrbeast.*?(com|io|org|net|xyz|tk|ml)',
    r'(http[s]?://)?(www\.)?.*?gift.*?(com|io|org|net|xyz|tk|ml)',
    r'(http[s]?://)?(www\.)?.*?free.*?(nitro|discord|steam|robux)',
    r'(http[s]?://)?(www\.)?.*?scam.*?(com|io|org|net)',
    r'(http[s]?://)?(www\.)?.*?phishing.*?(com|io|org|net)',
    r'discord\.com/gifts/\w+',
    r'nitro\.discord\.com/gifts/\w+',
]

SUSPICIOUS_PATTERNS = [
    r'¡Urgente!', r'¡Activa ahora!', r'¡Reclama tu premio!',
    r'100% gratis', r'ganaste un premio', r'tu cuenta está comprometida',
    r'verifica tu cuenta', r'confirmar identidad', r'urgente seguridad',
    r'¡Suscripción cancelada!', r'¡Tu cuenta será eliminada!',
    r'confirma tu pago', r'pago pendiente', r'factura vencida'
]

# Evento ready
@bot.event
async def on_ready():
    print(f'Bot conectado: {bot.user.name}')
    print(f'ID: {bot.user.id}')
    print(f'Servidores: {len(bot.guilds)}')

    # Iniciar tarea de auto-save optimizado
    bot.loop.create_task(_auto_save())
    print('[Optimización] Sistema de auto-save iniciado')

    # Sincronizar comandos automáticamente con mejor manejo de errores
    try:
        synced = await bot.tree.sync()
        print(f'Sincronizados {len(synced)} comandos globales')
    except discord.app_commands.CommandSyncFailure as e:
        print(f'Error de sincronización de comandos: {e}')
        print('Intentando sincronización forzada...')
        try:
            synced = await bot.tree.sync(guild=None)
            print(f'Sincronizados {len(synced)} comandos globales (forzado)')
        except Exception as e2:
            print(f'Error en sincronización forzada: {e2}')
    except Exception as e:
        print(f'Error general al sincronizar comandos: {e}')

    # Sincronizar comandos por servidor si es necesario
    for guild in bot.guilds:
        try:
            guild_synced = await bot.tree.sync(guild=guild)
            print(f'Sincronizados {len(guild_synced)} comandos en servidor {guild.name}')
        except Exception as e:
            print(f'Error al sincronizar comandos en servidor {guild.name}: {e}')

    # Iniciar actualización automática del ranking
    bot.loop.create_task(update_ranking_periodically())

    # Iniciar monitoreo de streams
    bot.loop.create_task(check_streams_periodically())

    # Iniciar actualización de temporizadores de sorteos
    bot.loop.create_task(update_giveaway_timers())

# Actualización periódica del ranking
async def update_ranking_periodically():
    while True:
        try:
            await asyncio.sleep(60)
            # Actualizar ranking para cada servidor que tiene configuración
            if 'servers' in data:
                for server_id, server_config in data['servers'].items():
                    if server_config.get('ranking_channel') and server_config.get('ranking_message_id'):
                        await update_ranking(int(server_id))
            # También actualizar el ranking global para compatibilidad
            await update_ranking()
        except Exception as e:
            print(f'[Ranking] Error en actualización periódica: {e}')
            await asyncio.sleep(60)  # Esperar antes de reintentar

# Monitoreo periódico de streams
async def check_streams_periodically():
    while True:
        try:
            await asyncio.sleep(120)
            await check_all_streamers()
        except Exception as e:
            print(f'[Streams] Error en monitoreo periódico: {e}')
            await asyncio.sleep(120)  # Esperar antes de reintentar

# Actualización de temporizadores de sorteos
async def update_giveaway_timers():
    while True:
        try:
            await asyncio.sleep(300)  # Actualizar cada 5 minutos (reducido de 30s para evitar spam)
            
            # Procesar sorteos de cada servidor
            if 'servers' in data:
                for server_id, server_config in data['servers'].items():
                    if 'giveaways' not in server_config:
                        continue
                    
                    server_giveaways = server_config['giveaways']
                    giveaway_announcement_channel_id = server_config.get('giveaway_announcement_channel')
                    
                    for giveaway_id, giveaway in server_giveaways.items():
                        try:
                            end_time = datetime.fromisoformat(giveaway['end_time'])
                            time_left = end_time - datetime.now()
                            
                            if time_left.total_seconds() > 0:
                                # Actualizar el embed con el tiempo restante
                                channel = bot.get_channel(giveaway['channel_id'])
                                if channel:
                                    try:
                                        message = await channel.fetch_message(giveaway['message_id'])
                                        embed = message.embeds[0]
                                        
                                        # Formatear el tiempo restante
                                        hours = int(time_left.total_seconds() // 3600)
                                        minutes = int((time_left.total_seconds() % 3600) // 60)
                                        seconds = int(time_left.total_seconds() % 60)
                                        
                                        if hours > 0:
                                            time_str = f'{hours}h {minutes}m {seconds}s'
                                        elif minutes > 0:
                                            time_str = f'{minutes}m {seconds}s'
                                        else:
                                            time_str = f'{seconds}s'
                                        
                                        # Actualizar el campo de tiempo
                                        for i, field in enumerate(embed.fields):
                                            if field.name == '⏰ Tiempo restante' or field.name == '⏰ Termina en':
                                                embed.set_field_at(i, name='⏰ Tiempo restante', value=time_str, inline=True)
                                                break
                                        
                                        await message.edit(embed=embed)
                                        print(f'[Sorteo] Temporizador actualizado para "{giveaway["prize"]}": {time_str}')
                                    except Exception as e:
                                        print(f'[Sorteo] Error al actualizar mensaje: {e}')
                                
                                # Enviar recordatorio en el canal de anuncios
                                if giveaway_announcement_channel_id:
                                    try:
                                        announcement_channel = bot.get_channel(giveaway_announcement_channel_id)
                                        if announcement_channel:
                                            reminder_embed = discord.Embed(
                                                title='🎉 ¡Sorteo en curso!',
                                                description=f'**{giveaway["prize"]}**\n\nTiempo restante: {time_str}\n\n🎯 Participa en {channel.mention} reaccionando con 🎉',
                                                color=0xFFD700
                                            )
                                            reminder_embed.add_field(name='👥 Participantes', value=str(len(giveaway['participants'])), inline=True)
                                            reminder_embed.add_field(name='🏆 Ganadores', value=str(giveaway['winners']), inline=True)
                                            reminder_embed.set_footer(text='¡Reacciona con 🎉 para participar!')
                                            reminder_embed.set_thumbnail(url=bot.user.display_avatar.url)
                                            
                                            # Enviar mensaje con @everyone
                                            reminder_message = await announcement_channel.send(content='@everyone', embed=reminder_embed)
                                            
                                            # Guardar el ID del mensaje para eliminarlo después
                                            if 'announcement_messages' not in giveaway:
                                                giveaway['announcement_messages'] = []
                                            giveaway['announcement_messages'].append(reminder_message.id)
                                            data['servers'][server_id]['giveaways'][giveaway_id] = giveaway
                                            save_data()
                                            
                                            print(f'[Sorteo] Recordatorio enviado para "{giveaway["prize"]}"')
                                    except Exception as e:
                                        print(f'[Sorteo] Error al enviar recordatorio: {e}')
                        except Exception as e:
                            print(f'[Sorteo] Error en actualización del sorteo {giveaway_id}: {e}')
            
            # Fallback a sorteos globales para compatibilidad
            for giveaway_id, giveaway in giveaways.items():
                try:
                    end_time = datetime.fromisoformat(giveaway['end_time'])
                    time_left = end_time - datetime.now()
                    
                    if time_left.total_seconds() > 0:
                        # Actualizar el embed con el tiempo restante
                        channel = bot.get_channel(giveaway['channel_id'])
                        if channel:
                            try:
                                message = await channel.fetch_message(giveaway['message_id'])
                                embed = message.embeds[0]
                                
                                # Formatear el tiempo restante
                                hours = int(time_left.total_seconds() // 3600)
                                minutes = int((time_left.total_seconds() % 3600) // 60)
                                seconds = int(time_left.total_seconds() % 60)
                                
                                if hours > 0:
                                    time_str = f'{hours}h {minutes}m {seconds}s'
                                elif minutes > 0:
                                    time_str = f'{minutes}m {seconds}s'
                                else:
                                    time_str = f'{seconds}s'
                                
                                # Actualizar el campo de tiempo
                                for i, field in enumerate(embed.fields):
                                    if field.name == '⏰ Tiempo restante' or field.name == '⏰ Termina en':
                                        embed.set_field_at(i, name='⏰ Tiempo restante', value=time_str, inline=True)
                                        break
                                
                                await message.edit(embed=embed)
                                print(f'[Sorteo] Temporizador actualizado para "{giveaway["prize"]}": {time_str}')
                            except:
                                pass  # Mensaje ya no existe, puede que fue eliminado
                        
                        # Enviar recordatorio en el canal de anuncios
                        if giveaway_announcement_channel_id:
                            try:
                                announcement_channel = bot.get_channel(giveaway_announcement_channel_id)
                                if announcement_channel:
                                    reminder_embed = discord.Embed(
                                        title='🎉 ¡Sorteo en curso!',
                                        description=f'**{giveaway["prize"]}**\n\nTiempo restante: {time_str}\n\n🎯 Participa en {channel.mention} reaccionando con 🎉',
                                        color=0xFFD700
                                    )
                                    reminder_embed.add_field(name='👥 Participantes', value=str(len(giveaway['participants'])), inline=True)
                                    reminder_embed.add_field(name='🏆 Ganadores', value=str(giveaway['winners']), inline=True)
                                    reminder_embed.set_footer(text='¡Reacciona con 🎉 para participar!')
                                    reminder_embed.set_thumbnail(url=bot.user.display_avatar.url)
                                    
                                    # Enviar mensaje con @everyone
                                    reminder_message = await announcement_channel.send(content='@everyone', embed=reminder_embed)
                                    
                                    # Guardar el ID del mensaje para eliminarlo después
                                    if 'announcement_messages' not in giveaway:
                                        giveaway['announcement_messages'] = []
                                    giveaway['announcement_messages'].append(reminder_message.id)
                                    data['giveaways'][giveaway_id] = giveaway
                                    save_data()
                                    
                                    print(f'[Sorteo] Recordatorio enviado para "{giveaway["prize"]}"')
                            except Exception as e:
                                print(f'[Sorteo] Error al enviar recordatorio: {e}')
                except Exception as e:
                    print(f'[Sorteo] Error en actualización: {e}')
        except Exception as e:
            print(f'[Sorteo] Error general en actualización de temporizadores: {e}')

# Actualizar ranking
async def update_ranking(guild_id=None):
    if guild_id:
        # Actualizar ranking específico del servidor
        ranking_channel_id = get_server_setting(guild_id, 'ranking_channel', data['config'].get('ranking_channel'))
        ranking_message_id = get_server_setting(guild_id, 'ranking_message_id', data['config'].get('ranking_message_id'))
    else:
        # Fallback a global (para compatibilidad)
        ranking_channel_id = data['config'].get('ranking_channel')
        ranking_message_id = data['config'].get('ranking_message_id')
    
    if not ranking_channel_id or not ranking_message_id:
        return
    
    try:
        channel = bot.get_channel(ranking_channel_id)
        if not channel:
            return
        
        message = await channel.fetch_message(ranking_message_id)
        embed = create_ranking_embed(channel.guild.id)
        await message.edit(embed=embed)
        print('Ranking actualizado')
    except Exception as e:
        print(f'Error al actualizar ranking: {e}')

# Crear embed de ranking
def create_ranking_embed(guild_id):
    server_id = str(guild_id)
    
    # Obtener usuarios del servidor específico
    if 'servers' in data and server_id in data['servers'] and 'users' in data['servers'][server_id]:
        users = data['servers'][server_id]['users']
    else:
        users = data.get('users', {})  # Fallback a global
    
    sorted_users = sorted(users.items(), key=lambda x: (x[1]['level'], x[1]['xp']), reverse=True)[:15]
    
    embed = discord.Embed(
        title='🏆 Ranking de Niveles',
        description='🔄 Actualizado cada 1 minuto',
        color=0xFFD700
    )
    
    if not sorted_users:
        embed.add_field(name='Sin usuarios', value='Aún no hay usuarios en el ranking', inline=False)
    else:
        description = ''
        for i, (user_id, user_data) in enumerate(sorted_users):
            user = bot.get_user(int(user_id))
            username = user.name if user else 'Usuario desconocido'
            medal = '🥇' if i == 0 else '🥈' if i == 1 else '🥉' if i == 2 else f'#{i + 1}'
            description += f'{medal} **{username}** - Nivel {user_data["level"]} ({user_data["xp"]} XP)\n'
        
        embed.add_field(name='Top 15 Usuarios', value=description, inline=False)
    
    embed.set_footer(text=f'Última actualización: {datetime.now().strftime("%H:%M:%S")}')
    return embed

# Verificar streams
async def check_all_streamers():
    # Verificar streams para cada servidor configurado
    if 'servers' in data:
        for server_id, server_config in data['servers'].items():
            stream_channel_id = server_config.get('stream_channel')
            streamers = server_config.get('streamers', [])
            
            if not stream_channel_id or not streamers:
                continue
            
            channel = bot.get_channel(stream_channel_id)
            if not channel:
                continue
            
            guild = channel.guild
            
            for streamer in streamers:
                try:
                    is_live = await check_streamer_live(streamer['platform'], streamer['username'])
                    key = f"{server_id}-{streamer['platform']}-{streamer['username']}"
                    
                    if is_live and key not in stream_notifications:
                        await send_stream_notification(channel, streamer, guild)
                        stream_notifications[key] = datetime.now().timestamp()
                    elif not is_live and key in stream_notifications:
                        del stream_notifications[key]
                except Exception as e:
                    print(f'Error checking streamer {streamer["username"]}: {e}')
    
    # Fallback a configuración global para compatibilidad
    if data['config'].get('stream_channel') and data['config'].get('streamers'):
        channel = bot.get_channel(data['config']['stream_channel'])
        if channel:
            guild = channel.guild
            for streamer in data['config']['streamers']:
                try:
                    is_live = await check_streamer_live(streamer['platform'], streamer['username'])
                    key = f"global-{streamer['platform']}-{streamer['username']}"
                    
                    if is_live and key not in stream_notifications:
                        await send_stream_notification(channel, streamer, guild)
                        stream_notifications[key] = datetime.now().timestamp()
                    elif not is_live and key in stream_notifications:
                        del stream_notifications[key]
                except Exception as e:
                    print(f'Error checking streamer {streamer["username"]}: {e}')

# Verificar si streamer está en live
async def check_streamer_live(platform, username):
    try:
        if platform == 'kick':
            response = requests.get(f'https://kick.com/api/v2/channels/{username}')
            return response.json().get('livestream', {}).get('is_live', False)
        elif platform == 'tiktok':
            return False
        elif platform == 'twitch':
            response = requests.get(f'https://twitch.tv/{username}')
            return 'isLiveBroadcasting' in response.text or 'live-channel-card' in response.text
        elif platform == 'youtube':
            response = requests.get(f'https://www.youtube.com/@{username}/live')
            return 'isLive' in response.text or 'live-stream' in response.text
        return False
    except:
        return False

# Enviar notificación de stream
async def send_stream_notification(channel, streamer, guild):
    urls = {
        'tiktok': f'https://www.tiktok.com/@{streamer["username"]}/live',
        'kick': f'https://kick.com/{streamer["username"]}',
        'twitch': f'https://twitch.tv/{streamer["username"]}',
        'youtube': f'https://www.youtube.com/@{streamer["username"]}/live'
    }
    
    url = urls.get(streamer['platform'], '')
    
    embed = discord.Embed(
        title='🔴 ¡STREAM EN VIVO!',
        description=f'**{streamer["username"]}** está ahora en live en **{streamer["platform"].upper()}**!',
        color=0xFF0000,
        url=url
    )
    
    embed.add_field(name='Plataforma', value=streamer['platform'].upper(), inline=True)
    embed.add_field(name='Streamer', value=streamer['username'], inline=True)
    embed.add_field(name='🔗 Enlace', value=f'[Ir al stream]({url})', inline=False)
    embed.set_footer(text='Notificación automática del bot')
    
    await channel.send(content='@everyone', embed=embed)
    
    # Enviar notificación al canal de notificaciones
    await send_notification(
        guild=guild,
        notification_type='streams',
        message=f'**{streamer["username"]}** está en live en {streamer["platform"].upper()}! [Ir al stream]({url})',
        color=0xFF0000
    )

# Evento message_create
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Auto-protección (siempre activa)
    if message.guild:
        if await check_dangerous_content(message):
            return
        
        # Anti-spam (siempre activo)
        if await check_spam(message):
            return
    
    # Dar XP por mensajes (solo en servidores)
    if message.guild:
        server_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        # Inicializar estructura del servidor si no existe
        if 'servers' not in data:
            data['servers'] = {}
        if server_id not in data['servers']:
            data['servers'][server_id] = {}
        if 'users' not in data['servers'][server_id]:
            data['servers'][server_id]['users'] = {}
        
        if user_id not in data['servers'][server_id]['users']:
            data['servers'][server_id]['users'][user_id] = {'level': 1, 'xp': 0}
        
        data['servers'][server_id]['users'][user_id]['xp'] += 10
        
        # Subir de nivel
        xp_needed = data['servers'][server_id]['users'][user_id]['level'] * 100
        if data['servers'][server_id]['users'][user_id]['xp'] >= xp_needed:
            data['servers'][server_id]['users'][user_id]['level'] += 1
            data['servers'][server_id]['users'][user_id]['xp'] = 0
            new_level = data['servers'][server_id]['users'][user_id]['level']

            # Asignar roles por nivel
            level_roles = data['servers'][server_id].get('level_roles', {})
            if new_level in level_roles:
                role_id = level_roles[new_level]
                role = message.guild.get_role(role_id)
                if role:
                    try:
                        await message.author.add_roles(role)
                        print(f'[Level Roles] Rol {role.name} asignado a {message.author.name} por alcanzar nivel {new_level}')
                    except discord.errors.Forbidden:
                        print(f'[Level Roles] Error: El bot no tiene permisos para asignar roles (Manage Roles)')

            level_channel_id = get_server_setting(message.guild.id, 'level_channel', data['config'].get('level_channel'))
            level_channel = message.channel

            if level_channel_id:
                try:
                    level_channel = bot.get_channel(level_channel_id)
                    if level_channel:
                        level_channel = level_channel
                except:
                    pass

            embed = discord.Embed(
                title='¡SUBIDA DE NIVEL!',
                description=f'¡Felicidades {message.author.mention} has subido al nivel **{new_level}**!',
                color=0xFFD700
            )

            embed.add_field(name='Nuevo Nivel', value=f'**{new_level}**', inline=True)
            embed.add_field(name='XP Total', value=str(new_level * 100 - 100), inline=True)
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_footer(text=f'Usuario: {message.author.name} | ID: {message.author.id}')

            await level_channel.send(embed=embed)

            # Log de subida de nivel
            await send_log(
                guild=message.guild,
                title='Subida de Nivel',
                description=f'{message.author.mention} ha subido al nivel **{new_level}**',
                color=0xFFD700,
                fields=[
                    {'name': 'Usuario', 'value': message.author.name, 'inline': True},
                    {'name': 'Nuevo nivel', 'value': str(new_level), 'inline': True},
                    {'name': 'XP total', 'value': str(new_level * 100 - 100), 'inline': True}
                ],
                author={'name': message.author.name, 'icon_url': message.author.display_avatar.url}
            )

            if level_channel.id != message.channel.id:
                await message.channel.send(f'{message.author.mention} subió al nivel {new_level}!')

        save_data()
    
    # Automoderación manual
    if message.guild:
        for word in data['banned_words']:
            if word.lower() in message.content.lower():
                await message.delete()
                await message.channel.send(f'⚠️ {message.author.mention}, tu mensaje contiene una palabra prohibida.')
                return
    
    await bot.process_commands(message)

    # Log de mensaje enviado (nuevo) con rate limiting
    if not message.author.bot:
        user_id = str(message.author.id)
        current_time = datetime.now().timestamp()

        # Rate limiting para logs de mensajes
        if user_id in log_rate_limit:
            if current_time - log_rate_limit[user_id] < LOG_RATE_LIMIT_SECONDS:
                return  # Saltar log si muy reciente
        log_rate_limit[user_id] = current_time

        await send_log(
            guild=message.guild,
            title='💬 Mensaje Enviado',
            description=f'{message.author.mention} envió un mensaje en {message.channel.mention}',
            color=0x2ecc71,
            fields=[
                {'name': 'Usuario', 'value': message.author.name, 'inline': True},
                {'name': 'Canal', 'value': message.channel.name, 'inline': True},
                {'name': 'Contenido', 'value': message.content[:200] + '...' if len(message.content) > 200 else message.content, 'inline': False}
            ],
            author={'name': message.author.name, 'icon_url': message.author.display_avatar.url}
        )

# Sistema de auto-protección
async def check_dangerous_content(message):
    content = message.content.lower()
    
    for domain in DANGEROUS_DOMAINS:
        if domain in content:
            await delete_and_warn(message, f'⛔ Enlace peligroso detectado ({domain}). Mensaje eliminado por seguridad.')
            return True
    
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            await delete_and_warn(message, '⛔ Patrón peligroso detectado. Mensaje eliminado por seguridad.')
            return True
    
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            await delete_and_warn(message, '⚠️ Contenido sospechoso detectado. Mensaje eliminado por seguridad.')
            return True
    
    if 'discord.com/gifts/' in content or 'nitro.discord.com/gifts/' in content:
        if not message.author.guild_permissions.administrator:
            await delete_and_warn(message, '⛔ Link de gift falso detectado. Los gifts reales solo vienen de Discord oficial.')
            return True
    
    link_count = len(re.findall(r'http[s]?://[^\s]+', content))
    if link_count > 3:
        await delete_and_warn(message, '⚠️ Demasiados links en un solo mensaje. Posible spam/phishing.')
        return True
    
    if message.attachments:
        for attachment in message.attachments:
            if attachment.size > 10 * 1024 * 1024:
                await delete_and_warn(message, '⚠️ Archivo muy grande detectado. Posible malware.')
                return True
            
            dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com', '.vbs', '.js', '.jar']
            for ext in dangerous_extensions:
                if attachment.filename.lower().endswith(ext):
                    await delete_and_warn(message, '⛔ Archivo ejecutable peligroso detectado. Mensaje eliminado.')
                    return True
    
    return False

# Sistema anti-spam
spam_detection = {}  # Para detectar spam rápido
spam_cleanup = {}  # Para limpiar mensajes viejos

# Sistema de tracking de tiempo en canales de voz
voice_join_times = {}  # {user_id: {guild_id: {channel_id: join_time}}}

async def check_spam(message):
    user_id = str(message.author.id)
    current_time = datetime.now().timestamp()
    
    # Ignorar administradores
    if message.author.guild_permissions.administrator:
        return False
    
    # Inicializar usuario si no existe
    if user_id not in spam_detection:
        spam_detection[user_id] = {
            'messages': [],
            'warnings': 0,
            'last_warning': 0
        }
    
    user_data = spam_detection[user_id]
    
    # Limpiar mensajes viejos (más de 10 segundos)
    user_data['messages'] = [msg_time for msg_time in user_data['messages'] if current_time - msg_time < 10]
    
    # Agregar mensaje actual
    user_data['messages'].append(current_time)
    
    # Detectar spam rápido (más de 5 mensajes en 10 segundos)
    if len(user_data['messages']) > 5:
        await handle_spam_violation(message, 'spam_rápido')
        return True
    
    # Detectar mensajes duplicados (mismo contenido 3 veces en 30 segundos)
    if user_id not in spam_cleanup:
        spam_cleanup[user_id] = {'content_history': []}
    
    spam_cleanup[user_id]['content_history'] = [
        (content, time) for content, time in spam_cleanup[user_id]['content_history'] 
        if current_time - time < 30
    ]
    
    spam_cleanup[user_id]['content_history'].append((message.content, current_time))
    
    # Contar mensajes duplicados
    content_count = sum(1 for content, _ in spam_cleanup[user_id]['content_history'] if content == message.content)
    if content_count > 3:
        await handle_spam_violation(message, 'mensajes_duplicados')
        return True
    
    # Detectar spam de menciones (más de 5 menciones en un mensaje)
    mention_count = len(message.mentions) + len(message.role_mentions)
    if mention_count > 5:
        await handle_spam_violation(message, 'spam_menciones')
        return True
    
    # Detectar spam de emojis (más de 10 emojis en un mensaje)
    emoji_count = len(re.findall(r'<a?:\w+:\d+>|[\U0001F600-\U0001F64F]', message.content))
    if emoji_count > 10:
        await handle_spam_violation(message, 'spam_emojis')
        return True
    
    # Detectar mensaje muy largo (más de 2000 caracteres)
    if len(message.content) > 2000:
        await handle_spam_violation(message, 'mensaje_largo')
        return True
    
    return False

async def handle_spam_violation(message, violation_type):
    user_id = str(message.author.id)
    user_data = spam_detection[user_id]
    
    # Incrementar advertencias
    user_data['warnings'] += 1
    user_data['last_warning'] = datetime.now().timestamp()
    
    violation_messages = {
        'spam_rápido': '⚠️ Has enviado demasiados mensajes muy rápido. Por favor reduce la velocidad.',
        'mensajes_duplicados': '⚠️ Has enviado el mismo mensaje varias veces. Por favor evita el spam.',
        'spam_menciones': '⚠️ Has enviado demasiadas menciones en un solo mensaje. Por favor evita el spam.',
        'spam_emojis': '⚠️ Has enviado demasiados emojis en un solo mensaje. Por favor evita el spam.',
        'mensaje_largo': '⚠️ Has enviado un mensaje muy largo. Por favor reduce el tamaño.'
    }
    
    # Acciones basadas en advertencias
    if user_data['warnings'] == 1:
        await message.delete()
        await message.channel.send(f'⚠️ {message.author.mention}: {violation_messages[violation_type]} Advertencia 1/3')
    elif user_data['warnings'] == 2:
        await message.delete()
        await message.channel.send(f'⚠️ {message.author.mention}: {violation_messages[violation_type]} Advertencia 2/3. Próxima vez: Timeout de 5 minutos')
    elif user_data['warnings'] >= 3:
        await message.delete()
        # Aplicar timeout de 5 minutos
        try:
            await message.author.timeout(timedelta(minutes=5), reason='Spam detectado')
            await message.channel.send(f'⛔ {message.author.mention} ha recibido un timeout de 5 minutos por spam continuo.')
            user_data['warnings'] = 0  # Reset advertencias después de timeout
        except Exception as e:
            print(f'Error al aplicar timeout: {e}')
    
    # Log de spam
    await send_log(
        guild=message.guild,
        title='🚨 Anti-Spam Activado',
        description=f'{message.author.mention} fue detectado por spam',
        color=0xFF0000,
        fields=[
            {'name': '👤 Usuario', 'value': message.author.name, 'inline': True},
            {'name': '🚨 Tipo', 'value': violation_type, 'inline': True},
            {'name': '⚠️ Advertencias', 'value': str(user_data['warnings']), 'inline': True},
            {'name': '📝 Contenido', 'value': message.content[:100] + '...' if len(message.content) > 100 else message.content, 'inline': False}
        ],
        author={'name': message.author.name, 'icon_url': message.author.display_avatar.url}
    )
    
    print(f'[Anti-Spam] {message.author.name} detectado por {violation_type}. Advertencias: {user_data["warnings"]}')

async def delete_and_warn(message, reason):
    try:
        await message.delete()
        
        embed = discord.Embed(
            title='🛡️ Protección Automática Activada',
            description=f'{message.author.mention}: {reason}',
            color=0xFF0000
        )
        
        embed.add_field(name='👤 Usuario', value=message.author.name, inline=True)
        embed.add_field(name='📅 Fecha', value=datetime.now().strftime('%d/%m/%Y %H:%M:%S'), inline=True)
        embed.add_field(name='📝 Mensaje', value=message.content[:100] + '...' if len(message.content) > 100 else message.content, inline=False)
        
        await message.channel.send(embed=embed)
        
        # Usar log_channel específico del servidor
        if message.guild:
            log_channel_id = get_server_setting(message.guild.id, 'log_channel', data['config'].get('log_channel'))
            if log_channel_id:
                try:
                    log_channel = bot.get_channel(log_channel_id)
                    if log_channel:
                        await log_channel.send(embed=embed)
                except:
                    pass
        
        print(f'[Auto-Protección] Mensaje eliminado de {message.author.name}: {reason}')
        
    except Exception as e:
        print(f'Error en auto-protección: {e}')

# Evento guild_member_add
@bot.event
async def on_member_join(member):
    server_id = str(member.guild.id)
    
    # Inicializar estructura del servidor si no existe
    if 'servers' not in data:
        data['servers'] = {}
    if server_id not in data['servers']:
        data['servers'][server_id] = {}
    if 'users' not in data['servers'][server_id]:
        data['servers'][server_id]['users'] = {}
    
    # Log de nuevo miembro
    await send_log(
        guild=member.guild,
        title='Nuevo Miembro',
        description=f'{member.mention} se ha unido al servidor',
        color=0x2ecc71,
        fields=[
            {'name': 'Usuario', 'value': f'{member.name}#{member.discriminator}', 'inline': True},
            {'name': 'ID', 'value': str(member.id), 'inline': True},
            {'name': 'Cuenta creada', 'value': member.created_at.strftime('%d/%m/%Y'), 'inline': True},
            {'name': 'Total miembros', 'value': str(member.guild.member_count), 'inline': True}
        ],
        author={'name': member.name, 'icon_url': member.display_avatar.url},
        thumbnail=member.display_avatar.url
    )
    
    # Verificar si ya está verificado (usar configuración del servidor)
    server_verified_users = data['servers'][server_id].get('verified_users', [])
    if str(member.id) in server_verified_users:
        server_auto_roles = data['servers'][server_id].get('auto_roles', [])
        if server_auto_roles:
            for role_id in server_auto_roles:
                auto_role = member.guild.get_role(role_id)
                if auto_role:
                    await member.add_roles(auto_role)
    else:
        verification_channel_id = get_server_setting(member.guild.id, 'verification_channel', data['config'].get('verification_channel'))
        if verification_channel_id:
            try:
                verification_channel = bot.get_channel(verification_channel_id)
                if verification_channel:
                    embed = discord.Embed(
                        title='🔒 Verificación Requerida',
                        description=f'{member.mention}, por favor reacciona al mensaje de verificación para obtener acceso completo al servidor.',
                        color=0xFF6B6B
                    )
                    embed.add_field(name='📋 Beneficios', value='✅ Acceso a canales\n✅ Participar en chats\n✅ Sorteos y eventos\n✅ Acceso completo', inline=False)
                    embed.add_field(name='🚀 Cómo verificar', value='Reacciona al mensaje ✅ en este canal', inline=False)
                    embed.set_footer(text='Sistema de verificación automática')
                    
                    await verification_channel.send(embed=embed)
            except:
                pass
    
    welcome_channel_id = get_server_setting(member.guild.id, 'welcome_channel', data['config'].get('welcome_channel'))
    channel = member.guild.system_channel
    
    if welcome_channel_id:
        try:
            welcome_channel = bot.get_channel(welcome_channel_id)
            if welcome_channel:
                channel = welcome_channel
        except:
            pass
    
    if channel:
        member_count = member.guild.member_count
        server_name = member.guild.name

        embed = discord.Embed(
            title=f'🎉 ¡Bienvenido a la Comunidad de {server_name}!',
            description=f'¡Hola {member.mention}! Gracias por unirte a la comunidad de **{server_name}**, contigo somos **{member_count} miembros**',
            color=0xFFD700
        )

        embed.add_field(name='👤 Usuario', value=member.name, inline=True)
        embed.add_field(name='📊 Miembros', value=str(member_count), inline=True)
        embed.add_field(name='🏠 Comunidad', value=server_name, inline=True)
        embed.add_field(name='📌 Información', value='Lee las reglas del servidor', inline=False)
        embed.add_field(name='🎮 Comandos', value='Usa /ayuda para ver los comandos del bot', inline=False)
        embed.add_field(name='👋 ¡Disfruta!', value='No dudes en preguntar si necesitas ayuda', inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=member.display_avatar.url)

        await channel.send(embed=embed)
    
    user_id = str(member.id)
    if user_id not in data['servers'][server_id]['users']:
        data['servers'][server_id]['users'][user_id] = {'level': 1, 'xp': 0}
        save_data()  # Guardar solo para nuevos usuarios (operación crítica)

# Evento de reacción para verificación
@bot.event
async def on_raw_reaction_add(payload):
    # Verificación - usar configuración específica del servidor
    server_id = str(payload.guild_id)
    if 'servers' in data and server_id in data['servers']:
        server_verification_message_id = data['servers'][server_id].get('verification_message_id')
        server_verification_role_id = data['servers'][server_id].get('verification_role')
        server_verified_users = data['servers'][server_id].get('verified_users', [])

        if payload.message_id == server_verification_message_id and str(payload.emoji) == '✅':
            try:
                guild = bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)

                if member and str(member.id) not in server_verified_users:
                    # Dar rol de verificación del servidor
                    role = guild.get_role(server_verification_role_id)
                    if role:
                        await member.add_roles(role)
                        print(f'[Verificación] Rol {role.name} asignado a {member.name} en servidor {guild.name}')

                        # Log de verificación
                        await send_log(
                            guild=guild,
                            title='Usuario Verificado',
                            description=f'{member.mention} ha sido verificado correctamente',
                            color=0x2ecc71,
                            fields=[
                                {'name': 'Usuario', 'value': member.name, 'inline': True},
                                {'name': 'Rol asignado', 'value': role.name, 'inline': True}
                            ],
                            author={'name': member.name, 'icon_url': member.display_avatar.url}
                        )
                    else:
                        print(f'[Verificación] Rol de verificación no encontrado en servidor {guild.name}: {server_verification_role_id}')
                        return

                    # Marcar como verificado en el servidor específico
                    server_verified_users.append(str(member.id))
                    data['servers'][server_id]['verified_users'] = server_verified_users
                    save_data()

                    # Asignar auto-roles del servidor
                    server_auto_roles = data['servers'][server_id].get('auto_roles', [])
                    if server_auto_roles:
                        for role_id in server_auto_roles:
                            auto_role = guild.get_role(role_id)
                            if auto_role:
                                await member.add_roles(auto_role)
                                print(f'[Auto-Roles] Auto-rol {auto_role.name} asignado a {member.name} en servidor {guild.name}')

                    # Enviar confirmación por mensaje privado (DM)
                    try:
                        await member.send(f'✅ ¡Has sido verificado exitosamente en **{guild.name}**! Ahora tienes acceso completo al servidor.')
                        print(f'[Verificación] Mensaje privado enviado a {member.name} en servidor {guild.name}')
                    except discord.errors.Forbidden:
                        # Si no se puede enviar DM, no enviar nada
                        print(f'[Verificación] No se pudo enviar DM a {member.name} (DMs desactivados)')
                    print(f'[Verificación] {member.name} verificado exitosamente en servidor {guild.name}')
                else:
                    print(f'[Verificación] {member.name} ya está verificado en servidor {guild.name}')
            except discord.errors.Forbidden as e:
                print(f'[Verificación] Error de permisos en servidor {guild.name}: {e}')
                print(f'[Verificación] El bot necesita permisos: Manage Roles, Send Messages')
            except Exception as e:
                print(f'Error en verificación: {e}')

    # Roles Reaccionables
    server_id = str(payload.guild_id)
    if 'servers' in data and server_id in data['servers'] and 'reaction_roles' in data['servers'][server_id]:
        panel_message_id = data['servers'][server_id]['reaction_roles'].get('panel_message_id')
        reaction_roles = data['servers'][server_id]['reaction_roles'].get('roles', {})

        if payload.message_id == panel_message_id and str(payload.emoji) in reaction_roles:
            try:
                guild = bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)

                if member and not member.bot:
                    role_id = reaction_roles[str(payload.emoji)]['role_id']
                    role = guild.get_role(role_id)

                    if role:
                        if role in member.roles:
                            # Quitar el rol
                            await member.remove_roles(role)
                            print(f'[Reaction Roles] Rol {role.name} quitado de {member.name} en servidor {guild.name}')
                        else:
                            # Agregar el rol
                            await member.add_roles(role)
                            print(f'[Reaction Roles] Rol {role.name} asignado a {member.name} en servidor {guild.name}')
            except discord.errors.Forbidden:
                print(f'[Reaction Roles] Error de permisos en servidor {guild.name}')
            except Exception as e:
                print(f'[Reaction Roles] Error: {e}')

# Evento de reacción removida para roles reaccionables
@bot.event
async def on_raw_reaction_remove(payload):
    # Roles Reaccionables
    server_id = str(payload.guild_id)
    if 'servers' in data and server_id in data['servers'] and 'reaction_roles' in data['servers'][server_id]:
        panel_message_id = data['servers'][server_id]['reaction_roles'].get('panel_message_id')
        reaction_roles = data['servers'][server_id]['reaction_roles'].get('roles', {})

        if payload.message_id == panel_message_id and str(payload.emoji) in reaction_roles:
            try:
                guild = bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)

                if member and not member.bot:
                    role_id = reaction_roles[str(payload.emoji)]['role_id']
                    role = guild.get_role(role_id)

                    if role and role in member.roles:
                        # Quitar el rol
                        await member.remove_roles(role)
                        print(f'[Reaction Roles] Rol {role.name} quitado de {member.name} (reacción removida) en servidor {guild.name}')
            except discord.errors.Forbidden:
                print(f'[Reaction Roles] Error de permisos en servidor {guild.name}')
            except Exception as e:
                print(f'[Reaction Roles] Error: {e}')

    # Sorteos (verificar en todos los servidores)
    server_id = str(payload.guild_id)
    if 'servers' in data and server_id in data['servers'] and 'giveaways' in data['servers'][server_id]:
        if str(payload.message_id) in data['servers'][server_id]['giveaways']:
            try:
                giveaway = data['servers'][server_id]['giveaways'][str(payload.message_id)]
                if str(payload.emoji) == '🎉':
                    guild = bot.get_guild(payload.guild_id)
                    member = guild.get_member(payload.user_id)
                    
                    if member and not member.bot:
                        user_id = str(member.id)
                        if user_id not in giveaway['participants']:
                            giveaway['participants'].append(user_id)
                            data['servers'][server_id]['giveaways'][str(payload.message_id)] = giveaway
                            save_data()
                            print(f'[Sorteo] {member.name} se unió al sorteo {giveaway["prize"]}')
                            
                            # Actualizar el embed del sorteo con el nuevo contador
                            try:
                                channel = bot.get_channel(giveaway['channel_id'])
                                if channel:
                                    message = await channel.fetch_message(giveaway['message_id'])
                                    embed = message.embeds[0]
                                    
                                    # Actualizar el campo de participantes
                                    for i, field in enumerate(embed.fields):
                                        if field.name == '👥 Participantes':
                                            embed.set_field_at(i, name='👥 Participantes', value=str(len(giveaway['participants'])), inline=True)
                                            break
                                    
                                    await message.edit(embed=embed)
                                    print(f'[Sorteo] Contador actualizado: {len(giveaway["participants"])} participantes')
                            except Exception as e:
                                print(f'[Sorteo] Error al actualizar embed: {e}')
                            
                            # Log de participación en sorteo
                            await send_log(
                                guild=guild,
                                title='Participación en Sorteo',
                                description=f'{member.mention} se ha unido al sorteo',
                                color=0xFFD700,
                                fields=[
                                    {'name': 'Usuario', 'value': member.name, 'inline': True},
                                    {'name': 'Premio', 'value': giveaway['prize'], 'inline': True},
                                    {'name': 'Total participantes', 'value': str(len(giveaway['participants'])), 'inline': True}
                                ],
                                author={'name': member.name, 'icon_url': member.display_avatar.url}
                            )
            except Exception as e:
                print(f'Error en sorteo: {e}')
    
    # Fallback a sorteos globales para compatibilidad
    if str(payload.message_id) in giveaways:
        try:
            giveaway = giveaways[str(payload.message_id)]
            if str(payload.emoji) == '🎉':
                guild = bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                
                if member and not member.bot:
                    user_id = str(member.id)
                    if user_id not in giveaway['participants']:
                        giveaway['participants'].append(user_id)
                        data['giveaways'][str(payload.message_id)] = giveaway
                        save_data()
                        print(f'[Sorteo] {member.name} se unió al sorteo {giveaway["prize"]}')
                        
                        # Actualizar el embed del sorteo con el nuevo contador
                        try:
                            channel = bot.get_channel(giveaway['channel_id'])
                            if channel:
                                message = await channel.fetch_message(giveaway['message_id'])
                                embed = message.embeds[0]
                                
                                # Actualizar el campo de participantes
                                for i, field in enumerate(embed.fields):
                                    if field.name == '👥 Participantes':
                                        embed.set_field_at(i, name='👥 Participantes', value=str(len(giveaway['participants'])), inline=True)
                                        break
                                
                                await message.edit(embed=embed)
                                print(f'[Sorteo] Contador actualizado: {len(giveaway["participants"])} participantes')
                        except Exception as e:
                            print(f'[Sorteo] Error al actualizar embed: {e}')
                        
                        # Log de participación en sorteo
                        await send_log(
                            guild=guild,
                            title='Participación en Sorteo',
                            description=f'{member.mention} se ha unido al sorteo',
                            color=0xFFD700,
                            fields=[
                                {'name': 'Usuario', 'value': member.name, 'inline': True},
                                {'name': 'Premio', 'value': giveaway['prize'], 'inline': True},
                                {'name': 'Total participantes', 'value': str(len(giveaway['participants'])), 'inline': True}
                            ],
                            author={'name': member.name, 'icon_url': member.display_avatar.url}
                        )
        except Exception as e:
            print(f'Error en sorteo: {e}')

# Evento miembro salió
@bot.event
async def on_member_remove(member):
    await send_log(
        guild=member.guild,
        title='Miembro Salió',
        description=f'{member.mention} ha abandonado el servidor',
        color=0xE74C3C,
        fields=[
            {'name': 'Usuario', 'value': f'{member.name}#{member.discriminator}', 'inline': True},
            {'name': 'ID', 'value': str(member.id), 'inline': True},
            {'name': 'Miembros restantes', 'value': str(member.guild.member_count), 'inline': True}
        ],
        author={'name': member.name, 'icon_url': member.display_avatar.url}
    )

# Evento mensaje eliminado
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    await send_log(
        guild=message.guild,
        title='Mensaje Eliminado',
        description=f'Mensaje de {message.author.mention} eliminado en {message.channel.mention}',
        color=0xE74C3C,
        fields=[
            {'name': 'Autor', 'value': message.author.name, 'inline': True},
            {'name': 'Contenido', 'value': message.content[:500] if message.content else 'Sin contenido', 'inline': False},
            {'name': 'Canal', 'value': message.channel.name, 'inline': True}
        ],
        author={'name': message.author.name, 'icon_url': message.author.display_avatar.url}
    )

# Evento rol asignado
@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        new_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        
        if new_roles:
            await send_log(
                guild=after.guild,
                title='Rol Asignado',
                description=f'Roles agregados a {after.mention}',
                color=0x2ecc71,
                fields=[
                    {'name': 'Usuario', 'value': after.name, 'inline': True},
                    {'name': 'Roles agregados', 'value': ', '.join([role.name for role in new_roles]), 'inline': False}
                ],
                author={'name': after.name, 'icon_url': after.display_avatar.url}
            )
        
        if removed_roles:
            await send_log(
                guild=after.guild,
                title='Rol Removido',
                description=f'Roles removidos de {after.mention}',
                color=0xE74C3C,
                fields=[
                    {'name': 'Usuario', 'value': after.name, 'inline': True},
                    {'name': 'Roles removidos', 'value': ', '.join([role.name for role in removed_roles]), 'inline': False}
                ],
                author={'name': after.name, 'icon_url': after.display_avatar.url}
            )

# Evento cambios en el servidor
@bot.event
async def on_guild_channel_create(channel):
    await send_log(
        guild=channel.guild,
        title='Canal Creado',
        description=f'Nuevo canal creado: {channel.mention}',
        color=0x2ecc71,
        fields=[
            {'name': 'Nombre', 'value': channel.name, 'inline': True},
            {'name': 'Tipo', 'value': str(channel.type), 'inline': True},
            {'name': 'Categoría', 'value': channel.category.name if channel.category else 'Sin categoría', 'inline': True}
        ]
    )

@bot.event
async def on_guild_channel_delete(channel):
    await send_log(
        guild=channel.guild,
        title='Canal Eliminado',
        description=f'Canal eliminado: {channel.name}',
        color=0xE74C3C,
        fields=[
            {'name': 'Nombre', 'value': channel.name, 'inline': True},
            {'name': 'Tipo', 'value': str(channel.type), 'inline': True}
        ]
    )

# Evento rol creado
@bot.event
async def on_guild_role_create(role):
    await send_log(
        guild=role.guild,
        title='Rol Creado',
        description=f'Nuevo rol creado: {role.mention}',
        color=0x2ecc71,
        fields=[
            {'name': 'Nombre', 'value': role.name, 'inline': True},
            {'name': 'Color', 'value': str(role.color), 'inline': True},
            {'name': 'Permisos', 'value': str(role.permissions.value), 'inline': True}
        ]
    )

# Evento rol eliminado
@bot.event
async def on_guild_role_delete(role):
    await send_log(
        guild=role.guild,
        title='Rol Eliminado',
        description=f'Rol eliminado: {role.name}',
        color=0xE74C3C,
        fields=[
            {'name': 'Nombre', 'value': role.name, 'inline': True},
            {'name': 'Color', 'value': str(role.color), 'inline': True}
        ]
    )

# Evento invitación creada
@bot.event
async def on_invite_create(invite):
    await send_log(
        guild=invite.guild,
        title='Invitación Creada',
        description=f'Nueva invitación creada por {invite.inviter.mention if invite.inviter else "Desconocido"}',
        color=0x2ecc71,
        fields=[
            {'name': 'Creador', 'value': invite.inviter.name if invite.inviter else 'Desconocido', 'inline': True},
            {'name': 'Código', 'value': invite.code, 'inline': True},
            {'name': 'Usos máximos', 'value': str(invite.max_uses) if invite.max_uses else 'Ilimitado', 'inline': True},
            {'name': 'Expira en', 'value': str(invite.expires_at) if invite.expires_at else 'Nunca', 'inline': True}
        ],
        author={'name': invite.inviter.name, 'icon_url': invite.inviter.display_avatar.url} if invite.inviter else None
    )

# Evento invitación usada
@bot.event
async def on_invite_use(invite):
    await send_log(
        guild=invite.guild,
        title='Invitación Usada',
        description=f'Invitación usada para unirse al servidor',
        color=0x3498db,
        fields=[
            {'name': 'Código', 'value': invite.code, 'inline': True},
            {'name': 'Usos totales', 'value': str(invite.uses), 'inline': True},
            {'name': 'Creador', 'value': invite.inviter.name if invite.inviter else 'Desconocido', 'inline': True}
        ],
        author={'name': invite.inviter.name, 'icon_url': invite.inviter.display_avatar.url} if invite.inviter else None
    )

# Evento de movimiento de voz (extremadamente detallado con tiempo)
@bot.event
async def on_voice_state_update(member, before, after):
    # Usuario se une a un canal de voz
    if after.channel and not before.channel:
        # Registrar tiempo de entrada
        user_id = str(member.id)
        guild_id = str(member.guild.id)
        channel_id = str(after.channel.id)

        if user_id not in voice_join_times:
            voice_join_times[user_id] = {}
        if guild_id not in voice_join_times[user_id]:
            voice_join_times[user_id][guild_id] = {}

        voice_join_times[user_id][guild_id][channel_id] = datetime.now()

        await send_log(
            guild=member.guild,
            title='🎤 Usuario se unió a canal de voz',
            description=f'{member.mention} se unió a {after.channel.mention}',
            color=0x2ecc71,
            fields=[
                {'name': 'Usuario', 'value': member.name, 'inline': True},
                {'name': 'Canal', 'value': after.channel.name, 'inline': True},
                {'name': 'Miembros en canal', 'value': str(len(after.channel.members)), 'inline': True},
                {'name': 'Hora de entrada', 'value': datetime.now().strftime('%H:%M:%S'), 'inline': True}
            ],
            author={'name': member.name, 'icon_url': member.display_avatar.url}
        )

    # Usuario sale de un canal de voz
    elif before.channel and not after.channel:
        # Calcular tiempo en el canal
        user_id = str(member.id)
        guild_id = str(member.guild.id)
        channel_id = str(before.channel.id)

        time_in_channel = "N/A"
        if user_id in voice_join_times and guild_id in voice_join_times[user_id] and channel_id in voice_join_times[user_id][guild_id]:
            join_time = voice_join_times[user_id][guild_id][channel_id]
            time_spent = datetime.now() - join_time

            # Formatear el tiempo
            hours = int(time_spent.total_seconds() // 3600)
            minutes = int((time_spent.total_seconds() % 3600) // 60)
            seconds = int(time_spent.total_seconds() % 60)

            if hours > 0:
                time_in_channel = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                time_in_channel = f"{minutes}m {seconds}s"
            else:
                time_in_channel = f"{seconds}s"

            # Limpiar el registro
            del voice_join_times[user_id][guild_id][channel_id]

        await send_log(
            guild=member.guild,
            title='🎤 Usuario salió de canal de voz',
            description=f'{member.mention} salió de {before.channel.mention}',
            color=0xe74c3c,
            fields=[
                {'name': 'Usuario', 'value': member.name, 'inline': True},
                {'name': 'Canal anterior', 'value': before.channel.name, 'inline': True},
                {'name': 'Tiempo en canal', 'value': time_in_channel, 'inline': True}
            ],
            author={'name': member.name, 'icon_url': member.display_avatar.url}
        )

    # Usuario cambia de canal de voz
    elif before.channel and after.channel and before.channel != after.channel:
        # Calcular tiempo en el canal anterior
        user_id = str(member.id)
        guild_id = str(member.guild.id)
        old_channel_id = str(before.channel.id)
        new_channel_id = str(after.channel.id)

        time_in_old_channel = "N/A"
        if user_id in voice_join_times and guild_id in voice_join_times[user_id] and old_channel_id in voice_join_times[user_id][guild_id]:
            join_time = voice_join_times[user_id][guild_id][old_channel_id]
            time_spent = datetime.now() - join_time

            # Formatear el tiempo
            hours = int(time_spent.total_seconds() // 3600)
            minutes = int((time_spent.total_seconds() % 3600) // 60)
            seconds = int(time_spent.total_seconds() % 60)

            if hours > 0:
                time_in_old_channel = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                time_in_old_channel = f"{minutes}m {seconds}s"
            else:
                time_in_old_channel = f"{seconds}s"

            # Limpiar el registro del canal anterior
            del voice_join_times[user_id][guild_id][old_channel_id]

        # Registrar tiempo de entrada al nuevo canal
        if user_id not in voice_join_times:
            voice_join_times[user_id] = {}
        if guild_id not in voice_join_times[user_id]:
            voice_join_times[user_id][guild_id] = {}

        voice_join_times[user_id][guild_id][new_channel_id] = datetime.now()

        await send_log(
            guild=member.guild,
            title='🎤 Usuario cambió de canal de voz',
            description=f'{member.mention} se movió de {before.channel.mention} a {after.channel.mention}',
            color=0xf39c12,
            fields=[
                {'name': 'Usuario', 'value': member.name, 'inline': True},
                {'name': 'Canal anterior', 'value': before.channel.name, 'inline': True},
                {'name': 'Canal nuevo', 'value': after.channel.name, 'inline': True},
                {'name': 'Tiempo en canal anterior', 'value': time_in_old_channel, 'inline': True}
            ],
            author={'name': member.name, 'icon_url': member.display_avatar.url}
        )

    # Usuario activa/desactiva micrófono
    elif before.self_mute != after.self_mute:
        status = 'activó' if after.self_mute else 'desactivó'
        await send_log(
            guild=member.guild,
            title='🎤 Micrófono cambiado',
            description=f'{member.mention} {status} su micrófono en {after.channel.mention if after.channel else "fuera de canal"}',
            color=0x95a5a6,
            fields=[
                {'name': 'Usuario', 'value': member.name, 'inline': True},
                {'name': 'Estado', 'value': 'Muteado' if after.self_mute else 'Desmuteado', 'inline': True}
            ],
            author={'name': member.name, 'icon_url': member.display_avatar.url}
        )

    # Usuario activa/desactiva sonido
    elif before.self_deaf != after.self_deaf:
        status = 'activó' if after.self_deaf else 'desactivó'
        await send_log(
            guild=member.guild,
            title='🎤 Sonido cambiado',
            description=f'{member.mention} {status} su sonido en {after.channel.mention if after.channel else "fuera de canal"}',
            color=0x95a5a6,
            fields=[
                {'name': 'Usuario', 'value': member.name, 'inline': True},
                {'name': 'Estado', 'value': 'Sordo' if after.self_deaf else 'Escuchando', 'inline': True}
            ],
            author={'name': member.name, 'icon_url': member.display_avatar.url}
        )

# Evento de mensaje editado
@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return

    await send_log(
        guild=after.guild,
        title='✏️ Mensaje Editado',
        description=f'{before.author.mention} editó un mensaje en {before.channel.mention}',
        color=0xf39c12,
        fields=[
            {'name': 'Usuario', 'value': before.author.name, 'inline': True},
            {'name': 'Canal', 'value': before.channel.name, 'inline': True},
            {'name': 'Antes', 'value': before.content[:200] + '...' if len(before.content) > 200 else before.content, 'inline': False},
            {'name': 'Después', 'value': after.content[:200] + '...' if len(after.content) > 200 else after.content, 'inline': False}
        ],
        author={'name': before.author.name, 'icon_url': before.author.display_avatar.url}
    )

# Evento de reacción agregada
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    await send_log(
        guild=reaction.message.guild,
        title='👍 Reacción Agregada',
        description=f'{user.mention} reaccionó con {reaction.emoji} a un mensaje en {reaction.message.channel.mention}',
        color=0x2ecc71,
        fields=[
            {'name': 'Usuario', 'value': user.name, 'inline': True},
            {'name': 'Emoji', 'value': str(reaction.emoji), 'inline': True},
            {'name': 'Canal', 'value': reaction.message.channel.name, 'inline': True},
            {'name': 'Mensaje', 'value': reaction.message.content[:100] + '...' if len(reaction.message.content) > 100 else reaction.message.content, 'inline': False}
        ],
        author={'name': user.name, 'icon_url': user.display_avatar.url}
    )

# Evento de reacción removida
@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return

    await send_log(
        guild=reaction.message.guild,
        title='👎 Reacción Removida',
        description=f'{user.mention} removió su reacción {reaction.emoji} de un mensaje en {reaction.message.channel.mention}',
        color=0xe74c3c,
        fields=[
            {'name': 'Usuario', 'value': user.name, 'inline': True},
            {'name': 'Emoji', 'value': str(reaction.emoji), 'inline': True},
            {'name': 'Canal', 'value': reaction.message.channel.name, 'inline': True}
        ],
        author={'name': user.name, 'icon_url': user.display_avatar.url}
    )

# Evento de usuario escribiendo (ELIMINADO SEGÚN SOLICITUD)
# @bot.event
# async def on_typing(channel, user, when):
#     if user.bot:
#         return
#
#     await send_log(
#         guild=channel.guild,
#         title='⌨️ Usuario Escribiendo',
#         description=f'{user.mention} está escribiendo en {channel.mention}',
#         color=0x95a5a6,
#         fields=[
#             {'name': 'Usuario', 'value': user.name, 'inline': True},
#             {'name': 'Canal', 'value': channel.name, 'inline': True},
#             {'name': 'Hora', 'value': when.strftime('%H:%M:%S'), 'inline': True}
#         ],
#         author={'name': user.name, 'icon_url': user.display_avatar.url}
#     )

# Evento de cambio de presencia (estado/juego) - DESACTIVADO para reducir spam en logs
# @bot.event
# async def on_presence_update(before, after):
#     if before.bot or after.bot:
#         return
#
#     # Cambio de estado (online, idle, dnd, offline)
#     if before.status != after.status:
#         await send_log(
#             guild=after.guild if after.guild else before.guild,
#             title='🟢 Cambio de Estado',
#             description=f'{after.mention} cambió su estado a {str(after.status)}',
#             color=0x95a5a6,
#             fields=[
#                 {'name': 'Usuario', 'value': after.name, 'inline': True},
#                 {'name': 'Estado anterior', 'value': str(before.status), 'inline': True},
#                 {'name': 'Estado nuevo', 'value': str(after.status), 'inline': True}
#             ],
#             author={'name': after.name, 'icon_url': after.display_avatar.url}
#         )
#
#     # Cambio de actividad (juego, streaming, etc.)
#     if before.activity != after.activity:
#         if after.activity:
#             await send_log(
#                 guild=after.guild if after.guild else before.guild,
#                 title='🎮 Cambio de Actividad',
#                 description=f'{after.mention} cambió su actividad',
#                 color=0x3498db,
#                 fields=[
#                     {'name': 'Usuario', 'value': after.name, 'inline': True},
#                     {'name': 'Actividad', 'value': f'{after.activity.type.name}: {after.activity.name}', 'inline': True}
#                 ],
#                 author={'name': after.name, 'icon_url': after.display_avatar.url}
#             )

# Evento de cambio de perfil de usuario
@bot.event
async def on_user_update(before, after):
    if before.bot or after.bot:
        return

    # Cambio de nombre
    if before.name != after.name:
        await send_log(
            guild=None,  # No tiene guild específico
            title='👤 Cambio de Nombre',
            description=f'Usuario cambió su nombre de {before.name} a {after.name}',
            color=0xf39c12,
            fields=[
                {'name': 'Nombre anterior', 'value': before.name, 'inline': True},
                {'name': 'Nombre nuevo', 'value': after.name, 'inline': True},
                {'name': 'ID', 'value': str(after.id), 'inline': True}
            ],
            author={'name': after.name, 'icon_url': after.display_avatar.url}
        )

    # Cambio de avatar
    if before.avatar != after.avatar:
        await send_log(
            guild=None,
            title='🖼️ Cambio de Avatar',
            description=f'{after.mention} cambió su avatar',
            color=0x3498db,
            fields=[
                {'name': 'Usuario', 'value': after.name, 'inline': True},
                {'name': 'ID', 'value': str(after.id), 'inline': True}
            ],
            author={'name': after.name, 'icon_url': after.display_avatar.url},
            thumbnail=after.display_avatar.url
        )

# Evento de baneo de usuario
@bot.event
async def on_member_ban(guild, user):
    await send_log(
        guild=guild,
        title='🔨 Usuario Baneado',
        description=f'{user.mention} ha sido baneado del servidor',
        color=0xe74c3c,
        fields=[
            {'name': 'Usuario', 'value': user.name, 'inline': True},
            {'name': 'ID', 'value': str(user.id), 'inline': True}
        ],
        author={'name': user.name, 'icon_url': user.display_avatar.url if user.display_avatar else None}
    )

# Evento de desbaneo de usuario
@bot.event
async def on_member_unban(guild, user):
    await send_log(
        guild=guild,
        title='🔓 Usuario Desbaneado',
        description=f'{user.mention} ha sido desbaneado del servidor',
        color=0x2ecc71,
        fields=[
            {'name': 'Usuario', 'value': user.name, 'inline': True},
            {'name': 'ID', 'value': str(user.id), 'inline': True}
        ],
        author={'name': user.name, 'icon_url': user.display_avatar.url if user.display_avatar else None}
    )

# Evento de actualización del servidor
@bot.event
async def on_guild_update(before, after):
    # Cambio de nombre del servidor
    if before.name != after.name:
        await send_log(
            guild=after,
            title='🏷️ Cambio de Nombre del Servidor',
            description=f'El servidor cambió de nombre',
            color=0xf39c12,
            fields=[
                {'name': 'Nombre anterior', 'value': before.name, 'inline': True},
                {'name': 'Nombre nuevo', 'value': after.name, 'inline': True}
            ]
        )

    # Cambio de icono del servidor
    if before.icon != after.icon:
        await send_log(
            guild=after,
            title='🖼️ Cambio de Icono del Servidor',
            description=f'El servidor cambió su icono',
            color=0x3498db,
            thumbnail=after.icon.url if after.icon else None
        )

# Evento de creación de hilo
@bot.event
async def on_thread_create(thread):
    await send_log(
        guild=thread.guild,
        title='🧵 Hilo Creado',
        description=f'Nuevo hilo creado: {thread.mention}',
        color=0x2ecc71,
        fields=[
            {'name': 'Nombre', 'value': thread.name, 'inline': True},
            {'name': 'Creador', 'value': thread.owner.mention if thread.owner else 'Desconocido', 'inline': True},
            {'name': 'Canal padre', 'value': thread.parent.mention, 'inline': True}
        ]
    )

# Evento de eliminación de hilo
@bot.event
async def on_thread_delete(thread):
    await send_log(
        guild=thread.guild,
        title='🧵 Hilo Eliminado',
        description=f'Hilo eliminado: {thread.name}',
        color=0xe74c3c,
        fields=[
            {'name': 'Nombre', 'value': thread.name, 'inline': True},
            {'name': 'Canal padre', 'value': thread.parent.mention, 'inline': True}
        ]
    )

# Función para asignar auto-roles
async def assign_auto_roles(member):
    if not auto_roles:
        return

    try:
        bot_role = member.guild.me.top_role
        print(f'[Auto-Roles] Rol del bot: {bot_role.name} (posición: {bot_role.position})')

        for role_id in auto_roles:
            role = member.guild.get_role(role_id)
            if role:
                print(f'[Auto-Roles] Intentando asignar rol: {role.name} (posición: {role.position})')
                if role.position >= bot_role.position:
                    print(f'[Auto-Roles] ERROR: Rol {role.name} está por encima o al mismo nivel que el rol del bot')
                else:
                    await member.add_roles(role)
                    print(f'[Auto-Roles] Asignado rol {role.name} a {member.name}')
    except Exception as e:
        print(f'Error al asignar auto-roles a {member.name}: {e}')

# Comandos slash
@bot.tree.command(name='ping', description='Comprueba la latencia del bot')
async def ping(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    can_execute, remaining = check_cooldown(user_id, 'ping')

    if not can_execute:
        await interaction.response.send_message(f'⏱️ Debes esperar {remaining} segundos antes de usar este comando nuevamente.', ephemeral=True)
        return

    try:
        await interaction.response.send_message(f'🏓 Pong! {round(bot.latency * 1000)}ms')
    except discord.errors.NotFound:
        # La interacción expiró o el bot se reinició
        pass

# Sistema de paginación para ayuda
class HelpView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.current_page = 0
        self.pages = self.create_pages()
    
    def create_pages(self):
        pages = [
            {
                'title': '📊 Sistema de Niveles',
                'emoji': '📊',
                'color': 0x3498db,
                'commands': [
                    {'name': '/level', 'desc': 'Muestra tu nivel y XP actual'},
                    {'name': '/top', 'desc': 'Muestra el top 10 usuarios por nivel'},
                    {'name': '/server_stats', 'desc': 'Muestra estadísticas del servidor'}
                ]
            },
            {
                'title': '🏆 Ranking Automático',
                'emoji': '🏆',
                'color': 0xFFD700,
                'commands': [
                    {'name': '/config_ranking_channel', 'desc': 'Configura el canal para el ranking'},
                    {'name': '/create_ranking', 'desc': 'Crea el mensaje de ranking'},
                    {'name': '/update_ranking', 'desc': 'Actualiza manualmente el ranking'}
                ]
            },
            {
                'title': '🎭 Auto-Roles',
                'emoji': '🎭',
                'color': 0x9b59b6,
                'commands': [
                    {'name': '/add_auto_role', 'desc': 'Agrega un rol automático'},
                    {'name': '/remove_auto_role', 'desc': 'Elimina un rol automático'},
                    {'name': '/list_auto_roles', 'desc': 'Lista los roles automáticos'}
                ]
            },
            {
                'title': '⭐ Roles por Nivel',
                'emoji': '⭐',
                'color': 0xFFD700,
                'commands': [
                    {'name': '/add_level_role', 'desc': 'Agrega un rol por nivel'},
                    {'name': '/remove_level_role', 'desc': 'Elimina un rol por nivel'},
                    {'name': '/list_level_roles', 'desc': 'Lista roles por nivel'}
                ]
            },
            {
                'title': '🎭 Roles Reaccionables',
                'emoji': '🎭',
                'color': 0x9b59b6,
                'commands': [
                    {'name': '/create_role_panel', 'desc': 'Crea panel de roles reaccionables'},
                    {'name': '/add_reaction_role', 'desc': 'Agrega rol reaccionable'},
                    {'name': '/list_reaction_roles', 'desc': 'Lista roles reaccionables'}
                ]
            },
            {
                'title': '🔒 Verificación',
                'emoji': '🔒',
                'color': 0xFF6B6B,
                'commands': [
                    {'name': '/config_verification', 'desc': 'Configura el sistema de verificación'},
                    {'name': '/create_verification_message', 'desc': 'Crea el mensaje de verificación'},
                    {'name': '/manual_verify', 'desc': 'Verifica manualmente a un usuario'},
                    {'name': '/check_verification_status', 'desc': 'Verifica el estado del sistema'}
                ]
            },
            {
                'title': '🎉 Sorteos',
                'emoji': '🎉',
                'color': 0xFFD700,
                'commands': [
                    {'name': '/config_giveaway_channel', 'desc': 'Configura el canal de sorteos'},
                    {'name': '/config_announce_channel', 'desc': 'Configura el canal de anuncios'},
                    {'name': '/create_giveaway', 'desc': 'Crea un nuevo sorteo'},
                    {'name': '/end_giveaway', 'desc': 'Finaliza manualmente un sorteo'},
                    {'name': '/list_giveaways', 'desc': 'Lista los sorteos activos'},
                    {'name': '/reroll_giveaway', 'desc': 'Vuelve a elegir ganadores'}
                ]
            },
            {
                'title': '� Notificaciones',
                'emoji': '🔔',
                'color': 0x9b59b6,
                'commands': [
                    {'name': '/config_notifications_channel', 'desc': 'Configura el canal de notificaciones'},
                    {'name': '/config_notification_role', 'desc': 'Configura rol por tipo de notificación'},
                    {'name': '/subscribe', 'desc': 'Suscríbete a notificaciones específicas'},
                    {'name': '/unsubscribe', 'desc': 'Cancela suscripción a notificaciones'},
                    {'name': '/my_subscriptions', 'desc': 'Muestra tus suscripciones actuales'},
                    {'name': '/send_announcement', 'desc': 'Envía un anuncio al canal de notificaciones'},
                    {'name': '/send_event', 'desc': 'Envía una notificación de evento'}
                ]
            },
            {
                'title': '�📺 Notificaciones de Streams',
                'emoji': '📺',
                'color': 0x9b59b6,
                'commands': [
                    {'name': '/config_stream_channel', 'desc': 'Configura el canal de streams'},
                    {'name': '/add_streamer', 'desc': 'Agrega un streamer al monitoreo'},
                    {'name': '/remove_streamer', 'desc': 'Elimina un streamer del monitoreo'},
                    {'name': '/list_streamers', 'desc': 'Lista los streamers monitoreados'},
                    {'name': '/check_stream', 'desc': 'Verifica si un streamer está en live'}
                ]
            },
            {
                'title': '🛡️ Moderación',
                'emoji': '🛡️',
                'color': 0xE74C3C,
                'commands': [
                    {'name': '/warn', 'desc': 'Advierte a un usuario'},
                    {'name': '/kick', 'desc': 'Expulsa a un usuario'},
                    {'name': '/ban', 'desc': 'Banea a un usuario'}
                ]
            },
            {
                'title': '🎫 Tickets',
                'emoji': '🎫',
                'color': 0x3498db,
                'commands': [
                    {'name': '/ticket', 'desc': 'Crea un ticket de soporte'},
                    {'name': '/close', 'desc': 'Cierra el ticket actual'}
                ]
            },
            {
                'title': '⚙️ Configuración',
                'emoji': '⚙️',
                'color': 0x95a5a6,
                'commands': [
                    {'name': '/config_level_channel', 'desc': 'Configura el canal de nivel'},
                    {'name': '/config_welcome_channel', 'desc': 'Configura el canal de bienvenida'},
                    {'name': '/config_ticket_category', 'desc': 'Configura la categoría de tickets'},
                    {'name': '/config_show', 'desc': 'Muestra la configuración actual'},
                    {'name': '/config_log_channel', 'desc': 'Configura el canal de logs'},
                    {'name': '/send_message', 'desc': 'Envía mensaje anónimo a un canal'},
                    {'name': '/sync_commands', 'desc': 'Fuerza sincronización de comandos'},
                    {'name': '/bot_servers', 'desc': 'Muestra servidores donde está el bot'}
                ]
            },
            {
                'title': '🔒 Filtro de Palabras',
                'emoji': '🔒',
                'color': 0x2ecc71,
                'commands': [
                    {'name': '/config_add_banned_word', 'desc': 'Agrega una palabra prohibida'},
                    {'name': '/config_remove_banned_word', 'desc': 'Elimina una palabra prohibida'}
                ]
            },
            {
                'title': '📜 Logs Avanzados',
                'emoji': '📜',
                'color': 0x9b59b6,
                'commands': [
                    {'name': 'Logs de Voz', 'desc': 'Registra movimientos de voz con tiempo'},
                    {'name': 'Logs de Mensajes', 'desc': 'Registra mensajes enviados, editados y eliminados'},
                    {'name': 'Logs de Reacciones', 'desc': 'Registra todas las reacciones'},
                    {'name': 'Logs de Estados', 'desc': 'Registra cambios de estado y actividad'},
                    {'name': 'Logs de Perfil', 'desc': 'Registra cambios de nombre y avatar'},
                    {'name': 'Logs de Servidor', 'desc': 'Registra cambios en el servidor'},
                    {'name': 'Logs de Ban/Unban', 'desc': 'Registra baneos y desbaneos'},
                    {'name': 'Logs de Hilos', 'desc': 'Registra creación y eliminación de hilos'}
                ]
            },
            {
                'title': 'ℹ️ Información',
                'emoji': 'ℹ️',
                'color': 0x3498db,
                'commands': [
                    {'name': '/ping', 'desc': 'Comprueba la latencia del bot'},
                    {'name': '/info', 'desc': 'Muestra información del servidor'},
                    {'name': '/ayuda', 'desc': 'Muestra este panel de ayuda'}
                ]
            }
        ]
        return pages
    
    def create_embed(self):
        page = self.pages[self.current_page]
        embed = discord.Embed(
            title=f'{page["emoji"]} {page["title"]}',
            description='Lista de comandos disponibles en esta categoría:',
            color=page['color']
        )
        
        for cmd in page['commands']:
            embed.add_field(name=cmd['name'], value=cmd['desc'], inline=False)
        
        embed.set_footer(text=f'Página {self.current_page + 1}/{len(self.pages)} | Sistema de Ayuda v2.0')
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        
        return embed
    
    @discord.ui.button(label='FIRST', style=discord.ButtonStyle.primary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label='PREVIOUS', style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label='NEXT', style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label='LAST', style=discord.ButtonStyle.primary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = len(self.pages) - 1
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

@bot.tree.command(name='bot_servers', description='Muestra en qué servidores está el bot')
@discord.app_commands.checks.has_permissions(administrator=True)
async def bot_servers(interaction: discord.Interaction):
    servers = []
    for guild in bot.guilds:
        servers.append(f"🏠 **{guild.name}** (ID: {guild.id}) - {guild.member_count} miembros")
    
    if not servers:
        await interaction.response.send_message("El bot no está en ningún servidor.", ephemeral=True)
    else:
        message = f"🤖 **Bot en {len(servers)} servidor(es):**\n\n" + "\n".join(servers)
        await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name='ayuda', description='Muestra el panel de comandos del bot')
async def ayuda(interaction: discord.Interaction):
    view = HelpView(interaction)
    await interaction.response.send_message(embed=view.create_embed(), view=view, ephemeral=True)

@bot.tree.command(name='info', description='Muestra información del servidor')
async def info(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message('Este comando solo funciona en servidores.', ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f'ℹ️ Información de {interaction.guild.name}',
        color=0x2ecc71
    )
    
    embed.add_field(name='👥 Miembros', value=str(interaction.guild.member_count), inline=True)
    embed.add_field(name='📁 Canales', value=str(len(interaction.guild.channels)), inline=True)
    embed.add_field(name='👑 Dueño', value=interaction.guild.owner.name if interaction.guild.owner else 'Desconocido', inline=True)
    embed.add_field(name='📅 Creado', value=interaction.guild.created_at.strftime('%d/%m/%Y'), inline=True)
    
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='level', description='Muestra tu nivel y XP actual')
async def level(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message('Este comando solo funciona en servidores.', ephemeral=True)
        return

    user_id = str(interaction.user.id)
    can_execute, remaining = check_cooldown(user_id, 'level')

    if not can_execute:
        await interaction.response.send_message(f'⏱️ Debes esperar {remaining} segundos antes de usar este comando nuevamente.', ephemeral=True)
        return

    server_id = str(interaction.guild.id)

    # Obtener usuarios del servidor específico
    if 'servers' in data and server_id in data['servers'] and 'users' in data['servers'][server_id]:
        users = data['servers'][server_id]['users']
    else:
        users = data.get('users', {})  # Fallback a global

    if user_id in users:
        user_data = users[user_id]
        level = user_data['level']
        xp = user_data['xp']
        xp_needed = level * 100
        
        embed = discord.Embed(
            title=f'📊 Nivel de {interaction.user.name}',
            color=0xFFD700
        )
        
        embed.add_field(name='Nivel', value=str(level), inline=True)
        embed.add_field(name='XP', value=f'{xp}/{xp_needed}', inline=True)
        embed.add_field(name='Progreso', value=f'{(xp/xp_needed)*100:.1f}%', inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message('Aún no tienes nivel. ¡Envía mensajes para ganar XP!', ephemeral=True)

@bot.tree.command(name='top', description='Muestra el top 10 usuarios por nivel')
async def top(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message('Este comando solo funciona en servidores.', ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    
    # Obtener usuarios del servidor específico
    if 'servers' in data and server_id in data['servers'] and 'users' in data['servers'][server_id]:
        users = data['servers'][server_id]['users']
    else:
        users = data.get('users', {})  # Fallback a global
    
    sorted_users = sorted(users.items(), key=lambda x: (x[1]['level'], x[1]['xp']), reverse=True)[:10]
    
    embed = discord.Embed(
        title='🏆 Top 10 Usuarios por Nivel',
        color=0xFFD700
    )
    
    for i, (user_id, user_data) in enumerate(sorted_users):
        try:
            user = await bot.fetch_user(int(user_id))
            embed.add_field(name=f'#{i + 1} {user.name}', value=f'Nivel {user_data["level"]}', inline=False)
        except:
            embed.add_field(name=f'#{i + 1} Usuario desconocido', value=f'Nivel {user_data["level"]}', inline=False)
    
    await interaction.response.send_message(embed=embed)

# Configuración
@bot.tree.command(name='config_level_channel', description='Configura el canal para notificaciones de nivel')
@discord.app_commands.describe(channel='Canal para notificaciones de nivel')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_level_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_server_setting(interaction.guild.id, 'level_channel', channel.id)
    data['config']['level_channel'] = channel.id  # Guardar en global para compatibilidad
    save_data()
    await interaction.response.send_message(f'✅ Canal de nivel configurado: {channel.mention}')
    print(f'[Config] Canal de nivel configurado en servidor {interaction.guild.name}: {channel.name} (ID: {channel.id})')

@bot.tree.command(name='config_welcome_channel', description='Configura el canal para bienvenida de nuevos miembros')
@discord.app_commands.describe(channel='Canal para bienvenida')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_welcome_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_server_setting(interaction.guild.id, 'welcome_channel', channel.id)
    data['config']['welcome_channel'] = channel.id  # Guardar en global para compatibilidad
    save_data()
    await interaction.response.send_message(f'✅ Canal de bienvenida configurado: {channel.mention}')
    print(f'[Config] Canal de bienvenida configurado en servidor {interaction.guild.name}: {channel.name} (ID: {channel.id})')

# Sistema de Roles por Nivel
@bot.tree.command(name='add_level_role', description='Agrega un rol que se asigna al alcanzar un nivel específico')
@discord.app_commands.describe(level='Nivel requerido', role='Rol a asignar')
@discord.app_commands.checks.has_permissions(administrator=True)
async def add_level_role(interaction: discord.Interaction, level: int, role: discord.Role):
    server_id = str(interaction.guild.id)

    # Inicializar estructura si no existe
    if 'servers' not in data:
        data['servers'] = {}
    if server_id not in data['servers']:
        data['servers'][server_id] = {}
    if 'level_roles' not in data['servers'][server_id]:
        data['servers'][server_id]['level_roles'] = {}

    data['servers'][server_id]['level_roles'][level] = role.id
    save_data()

    await interaction.response.send_message(f'✅ Rol {role.mention} configurado para el nivel **{level}**')
    print(f'[Level Roles] Rol {role.name} configurado para nivel {level} en servidor {interaction.guild.name}')

@bot.tree.command(name='remove_level_role', description='Elimina un rol de un nivel específico')
@discord.app_commands.describe(level='Nivel a eliminar')
@discord.app_commands.checks.has_permissions(administrator=True)
async def remove_level_role(interaction: discord.Interaction, level: int):
    server_id = str(interaction.guild.id)

    if 'servers' not in data or server_id not in data['servers'] or 'level_roles' not in data['servers'][server_id]:
        await interaction.response.send_message('❌ No hay roles por nivel configurados', ephemeral=True)
        return

    if level not in data['servers'][server_id]['level_roles']:
        await interaction.response.send_message(f'❌ No hay rol configurado para el nivel {level}', ephemeral=True)
        return

    del data['servers'][server_id]['level_roles'][level]
    save_data()

    await interaction.response.send_message(f'✅ Rol del nivel **{level}** eliminado')
    print(f'[Level Roles] Rol del nivel {level} eliminado en servidor {interaction.guild.name}')

@bot.tree.command(name='list_level_roles', description='Lista todos los roles configurados por nivel')
async def list_level_roles(interaction: discord.Interaction):
    server_id = str(interaction.guild.id)

    if 'servers' not in data or server_id not in data['servers'] or 'level_roles' not in data['servers'][server_id]:
        await interaction.response.send_message('❌ No hay roles por nivel configurados', ephemeral=True)
        return

    level_roles = data['servers'][server_id]['level_roles']

    if not level_roles:
        await interaction.response.send_message('❌ No hay roles por nivel configurados', ephemeral=True)
        return

    # Ordenar por nivel
    sorted_levels = sorted(level_roles.keys())

    embed = discord.Embed(
        title='🎭 Roles por Nivel',
        description=f'Configuración de roles por nivel en {interaction.guild.name}',
        color=0x9b59b6
    )

    for level in sorted_levels:
        role_id = level_roles[level]
        role = interaction.guild.get_role(role_id)
        if role:
            embed.add_field(name=f'Nivel {level}', value=role.mention, inline=False)

    await interaction.response.send_message(embed=embed)

# Sistema de Estadísticas del Servidor
@bot.tree.command(name='server_stats', description='Muestra estadísticas detalladas del servidor')
async def server_stats(interaction: discord.Interaction):
    guild = interaction.guild
    server_id = str(guild.id)

    # Obtener datos del servidor
    server_users = data['servers'][server_id].get('users', {}) if 'servers' in data and server_id in data['servers'] else {}

    # Calcular estadísticas
    total_members = guild.member_count
    online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
    total_text_channels = len(guild.text_channels)
    total_voice_channels = len(guild.voice_channels)
    total_roles = len(guild.roles)
    total_categories = len(guild.categories)

    # Calcular niveles promedio
    if server_users:
        total_levels = sum(user_data['level'] for user_data in server_users.values())
        avg_level = total_levels / len(server_users) if server_users else 0
    else:
        avg_level = 0

    # Obtener usuario con mayor nivel (usando caché)
    if server_users:
        top_user = max(server_users.items(), key=lambda x: x[1]['level'])
        top_user_id, top_user_data = top_user
        try:
            # Intentar obtener del caché primero
            cached_user = get_cached_user(int(top_user_id))
            if cached_user:
                top_user_name = cached_user.name
            else:
                top_user_obj = await bot.fetch_user(int(top_user_id))
                cache_user(int(top_user_id), top_user_obj)
                top_user_name = top_user_obj.name
        except:
            top_user_name = "Usuario desconocido"
    else:
        top_user_name = "N/A"
        top_user_data = {'level': 0}

    # Fecha de creación del servidor
    server_age = (datetime.now() - guild.created_at).days

    embed = discord.Embed(
        title=f'📊 Estadísticas de {guild.name}',
        description=f'Información detallada del servidor',
        color=0x3498db
    )

    embed.add_field(name='👥 Miembros', value=f'**{total_members}** total\n**{online_members}** en línea', inline=True)
    embed.add_field(name='💬 Canales', value=f'**{total_text_channels}** texto\n**{total_voice_channels}** voz', inline=True)
    embed.add_field(name='🎭 Roles', value=f'**{total_roles}** roles', inline=True)
    embed.add_field(name='📁 Categorías', value=f'**{total_categories}** categorías', inline=True)
    embed.add_field(name='⭐ Nivel Promedio', value=f'**{avg_level:.1f}**', inline=True)
    embed.add_field(name='🏆 Top Nivel', value=f'**{top_user_name}** (Nivel {top_user_data["level"]})', inline=True)
    embed.add_field(name='📅 Edad del Servidor', value=f'**{server_age}** días', inline=True)
    embed.add_field(name='🆔 ID del Servidor', value=f'`{guild.id}`', inline=True)
    embed.add_field(name='👑 Propietario', value=guild.owner.mention if guild.owner else 'Desconocido', inline=True)

    embed.set_thumbnail(url=guild.icon.url if guild.icon else guild.me.display_avatar.url)
    embed.set_footer(text=f'Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M")}')

    await interaction.response.send_message(embed=embed)

# Sistema de Roles Reaccionables
@bot.tree.command(name='create_role_panel', description='Crea un panel de roles reaccionables')
@discord.app_commands.describe(channel='Canal donde crear el panel', title='Título del panel')
@discord.app_commands.checks.has_permissions(administrator=True)
async def create_role_panel(interaction: discord.Interaction, channel: discord.TextChannel, title: str = "🎭 Roles Reaccionables"):
    server_id = str(interaction.guild.id)

    # Inicializar estructura si no existe
    if 'servers' not in data:
        data['servers'] = {}
    if server_id not in data['servers']:
        data['servers'][server_id] = {}
    if 'reaction_roles' not in data['servers'][server_id]:
        data['servers'][server_id]['reaction_roles'] = {}

    embed = discord.Embed(
        title=title,
        description='Reacciona a los emojis para obtener los roles correspondientes. ¡Click para agregar, click de nuevo para quitar!',
        color=0x9b59b6
    )

    embed.add_field(name='📋 Instrucciones', value='• Reacciona para obtener el rol\n• Reacciona de nuevo para quitarlo\n• Los roles se asignan automáticamente', inline=False)
    embed.set_footer(text='Sistema de roles reaccionables')

    message = await channel.send(embed=embed)

    # Guardar el mensaje del panel
    data['servers'][server_id]['reaction_roles']['panel_message_id'] = message.id
    data['servers'][server_id]['reaction_roles']['panel_channel_id'] = channel.id
    data['servers'][server_id]['reaction_roles']['roles'] = {}
    save_data()

    await interaction.response.send_message(f'✅ Panel de roles creado en {channel.mention}. Usa /add_reaction_role para agregar roles.')
    print(f'[Reaction Roles] Panel creado en servidor {interaction.guild.name} (ID: {message.id})')

@bot.tree.command(name='add_reaction_role', description='Agrega un rol reaccionable al panel')
@discord.app_commands.describe(emoji='Emoji a usar', role='Rol a asignar', description='Descripción del rol')
@discord.app_commands.checks.has_permissions(administrator=True)
async def add_reaction_role(interaction: discord.Interaction, emoji: str, role: discord.Role, description: str = ""):
    server_id = str(interaction.guild.id)

    if 'servers' not in data or server_id not in data['servers'] or 'reaction_roles' not in data['servers'][server_id]:
        await interaction.response.send_message('❌ Primero crea un panel con /create_role_panel', ephemeral=True)
        return

    panel_message_id = data['servers'][server_id]['reaction_roles'].get('panel_message_id')
    panel_channel_id = data['servers'][server_id]['reaction_roles'].get('panel_channel_id')

    if not panel_message_id or not panel_channel_id:
        await interaction.response.send_message('❌ Panel no encontrado. Crea uno nuevo con /create_role_panel', ephemeral=True)
        return

    # Agregar el rol a la configuración
    if 'roles' not in data['servers'][server_id]['reaction_roles']:
        data['servers'][server_id]['reaction_roles']['roles'] = {}

    data['servers'][server_id]['reaction_roles']['roles'][emoji] = {
        'role_id': role.id,
        'description': description
    }
    save_data()

    # Actualizar el panel
    try:
        channel = bot.get_channel(panel_channel_id)
        if channel:
            message = await channel.fetch_message(panel_message_id)
            embed = message.embeds[0] if message.embeds else None

            if embed:
                # Agregar el nuevo rol al embed
                role_text = f"{emoji} - {role.mention}"
                if description:
                    role_text += f"\n*{description}*"
                embed.add_field(name=role.name, value=role_text, inline=False)

                await message.edit(embed=embed)

                # Agregar la reacción al mensaje
                try:
                    await message.add_reaction(emoji)
                except:
                    pass

    except Exception as e:
        print(f'[Reaction Roles] Error al actualizar panel: {e}')

    await interaction.response.send_message(f'✅ Rol {role.mention} agregado con emoji {emoji}')
    print(f'[Reaction Roles] Rol {role.name} agregado con emoji {emoji} en servidor {interaction.guild.name}')

@bot.tree.command(name='list_reaction_roles', description='Lista todos los roles reaccionables configurados')
async def list_reaction_roles(interaction: discord.Interaction):
    server_id = str(interaction.guild.id)

    if 'servers' not in data or server_id not in data['servers'] or 'reaction_roles' not in data['servers'][server_id]:
        await interaction.response.send_message('❌ No hay panel de roles reaccionables configurado', ephemeral=True)
        return

    reaction_roles = data['servers'][server_id]['reaction_roles'].get('roles', {})

    if not reaction_roles:
        await interaction.response.send_message('❌ No hay roles reaccionables configurados', ephemeral=True)
        return

    embed = discord.Embed(
        title='🎭 Roles Reaccionables',
        description=f'Configuración de roles reaccionables en {interaction.guild.name}',
        color=0x9b59b6
    )

    for emoji, role_data in reaction_roles.items():
        role_id = role_data['role_id']
        description = role_data.get('description', '')
        role = interaction.guild.get_role(role_id)
        if role:
            role_text = role.mention
            if description:
                role_text += f"\n*{description}*"
            embed.add_field(name=emoji, value=role_text, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='config_ticket_category', description='Configura la categoría para tickets')
@discord.app_commands.describe(category='Categoría para tickets')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_ticket_category(interaction: discord.Interaction, category: discord.CategoryChannel):
    set_server_setting(interaction.guild.id, 'ticket_category', category.id)
    data['config']['ticket_category'] = category.id  # Guardar en global para compatibilidad
    save_data()
    await interaction.response.send_message(f'✅ Categoría de tickets configurada: {category.name}')
    print(f'[Config] Categoría de tickets configurada en servidor {interaction.guild.name}: {category.name} (ID: {category.id})')

@bot.tree.command(name='config_ranking_channel', description='Configura el canal para el ranking de niveles')
@discord.app_commands.describe(channel='Canal para el ranking')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_ranking_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_server_setting(interaction.guild.id, 'ranking_channel', channel.id)
    data['config']['ranking_channel'] = channel.id  # Guardar en global para compatibilidad
    global ranking_channel_id
    ranking_channel_id = channel.id
    save_data()
    await interaction.response.send_message(f'✅ Canal de ranking configurado: {channel.mention}')
    print(f'[Config] Canal de ranking configurado en servidor {interaction.guild.name}: {channel.name} (ID: {channel.id})')

@bot.tree.command(name='create_ranking', description='Crea el mensaje de ranking en el canal configurado')
async def create_ranking(interaction: discord.Interaction):
    ranking_channel_id = get_server_setting(interaction.guild.id, 'ranking_channel', data['config'].get('ranking_channel'))
    
    if not ranking_channel_id:
        await interaction.response.send_message('❌ Primero configura el canal de ranking con /config_ranking_channel', ephemeral=True)
        return
    
    channel = bot.get_channel(ranking_channel_id)
    if not channel:
        await interaction.response.send_message('❌ Canal de ranking no encontrado', ephemeral=True)
        return
    
    try:
        embed = create_ranking_embed(interaction.guild.id)
        message = await channel.send(embed=embed)
        
        set_server_setting(interaction.guild.id, 'ranking_message_id', message.id)
        data['config']['ranking_message_id'] = message.id  # Guardar en global para compatibilidad
        global ranking_message_id
        ranking_message_id = message.id
        save_data()
        
        await interaction.response.send_message(f'✅ Ranking creado en {channel.mention}')
    except Exception as e:
        await interaction.response.send_message(f'❌ Error al crear ranking: {e}', ephemeral=True)

@bot.tree.command(name='update_ranking', description='Actualiza manualmente el ranking')
async def update_ranking_command(interaction: discord.Interaction):
    await update_ranking()
    await interaction.response.send_message('✅ Ranking actualizado manualmente')

@bot.tree.command(name='config_stream_channel', description='Configura el canal para notificaciones de streams')
@discord.app_commands.describe(channel='Canal para notificaciones de streams')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_stream_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_server_setting(interaction.guild.id, 'stream_channel', channel.id)
    data['config']['stream_channel'] = channel.id  # Guardar en global para compatibilidad
    global stream_channel_id
    stream_channel_id = channel.id
    save_data()
    await interaction.response.send_message(f'✅ Canal de notificaciones de streams configurado: {channel.mention}')
    print(f'[Config] Canal de streams configurado en servidor {interaction.guild.name}: {channel.name} (ID: {channel.id})')

@bot.tree.command(name='add_streamer', description='Agrega un streamer al monitoreo')
@discord.app_commands.describe(platform='Plataforma del streamer', username='Nombre de usuario del streamer')
@discord.app_commands.checks.has_permissions(administrator=True)
async def add_streamer(interaction: discord.Interaction, platform: str, username: str):
    if platform not in ['tiktok', 'kick', 'twitch', 'youtube']:
        await interaction.response.send_message('❌ Plataforma no válida. Usa: tiktok, kick, twitch, youtube', ephemeral=True)
        return
    
    streamers = get_server_setting(interaction.guild.id, 'streamers', data['config'].get('streamers', []))
    
    if not streamers:
        streamers = []
    
    for s in streamers:
        if s['platform'] == platform and s['username'] == username:
            await interaction.response.send_message('⚠️ Este streamer ya está siendo monitoreado.', ephemeral=True)
            return
    
    streamers.append({'platform': platform, 'username': username})
    set_server_setting(interaction.guild.id, 'streamers', streamers)
    data['config']['streamers'] = streamers  # Guardar en global para compatibilidad
    save_data()
    
    await interaction.response.send_message(f'✅ Streamer agregado: {username} ({platform})')

@bot.tree.command(name='remove_streamer', description='Elimina un streamer del monitoreo')
@discord.app_commands.describe(username='Nombre de usuario del streamer')
@discord.app_commands.checks.has_permissions(administrator=True)
async def remove_streamer(interaction: discord.Interaction, username: str):
    streamers = get_server_setting(interaction.guild.id, 'streamers', data['config'].get('streamers', []))
    
    if not streamers:
        await interaction.response.send_message('❌ No hay streamers monitoreados.', ephemeral=True)
        return
    
    for i, s in enumerate(streamers):
        if s['username'] == username:
            removed = streamers.pop(i)
            set_server_setting(interaction.guild.id, 'streamers', streamers)
            data['config']['streamers'] = streamers  # Guardar en global para compatibilidad
            save_data()
            await interaction.response.send_message(f'✅ Streamer eliminado: {removed["username"]} ({removed["platform"]})')
            return
    
    await interaction.response.send_message('❌ Streamer no encontrado en la lista.', ephemeral=True)

@bot.tree.command(name='list_streamers', description='Lista los streamers monitoreados')
async def list_streamers(interaction: discord.Interaction):
    streamers = get_server_setting(interaction.guild.id, 'streamers', data['config'].get('streamers', []))
    
    if not streamers:
        await interaction.response.send_message('❌ No hay streamers monitoreados.', ephemeral=True)
        return
    
    description = '\n'.join([f'• {s["username"]} ({s["platform"]})' for s in streamers])
    
    embed = discord.Embed(
        title='📺 Streamers Monitoreados',
        description=description,
        color=0x9b59b6
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='check_stream', description='Verifica manualmente si un streamer está en live')
@discord.app_commands.describe(platform='Plataforma del streamer', username='Nombre de usuario del streamer')
async def check_stream(interaction: discord.Interaction, platform: str, username: str):
    try:
        is_live = await check_streamer_live(platform, username)
        
        if is_live:
            await interaction.response.send_message(f'✅ {username} está en live en {platform}!')
        else:
            await interaction.response.send_message(f'❌ {username} no está en live en {platform}.')
    except Exception as e:
        await interaction.response.send_message(f'❌ Error al verificar stream: {e}')

@bot.tree.command(name='config_add_banned_word', description='Agrega una palabra prohibida')
@discord.app_commands.describe(word='Palabra a prohibir')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_add_banned_word(interaction: discord.Interaction, word: str):
    if word.lower() not in data['banned_words']:
        data['banned_words'].append(word.lower())
        save_data()
        await interaction.response.send_message(f'✅ Palabra "{word}" agregada a la lista de prohibidas.')
    else:
        await interaction.response.send_message(f'⚠️ La palabra "{word}" ya está en la lista.')

@bot.tree.command(name='config_remove_banned_word', description='Elimina una palabra prohibida')
@discord.app_commands.describe(word='Palabra a eliminar')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_remove_banned_word(interaction: discord.Interaction, word: str):
    if word.lower() in data['banned_words']:
        data['banned_words'].remove(word.lower())
        save_data()
        await interaction.response.send_message(f'✅ Palabra "{word}" eliminada de la lista de prohibidas.')
    else:
        await interaction.response.send_message(f'⚠️ La palabra "{word}" no está en la lista.')

@bot.tree.command(name='config_show', description='Muestra la configuración actual')
async def config_show(interaction: discord.Interaction):
    server_id = str(interaction.guild.id)
    
    # Obtener configuración específica del servidor con fallback a global
    level_channel_id = get_server_setting(interaction.guild.id, 'level_channel', data['config'].get('level_channel'))
    welcome_channel_id = get_server_setting(interaction.guild.id, 'welcome_channel', data['config'].get('welcome_channel'))
    ticket_category_id = get_server_setting(interaction.guild.id, 'ticket_category', data['config'].get('ticket_category'))
    ranking_channel_id = get_server_setting(interaction.guild.id, 'ranking_channel', data['config'].get('ranking_channel'))
    stream_channel_id = get_server_setting(interaction.guild.id, 'stream_channel', data['config'].get('stream_channel'))
    log_channel_id = get_server_setting(interaction.guild.id, 'log_channel', data['config'].get('log_channel'))
    auto_roles = get_server_setting(interaction.guild.id, 'auto_roles', data['config'].get('auto_roles', []))
    streamers = get_server_setting(interaction.guild.id, 'streamers', data['config'].get('streamers', []))
    
    embed = discord.Embed(
        title=f'⚙️ Configuración del Bot - {interaction.guild.name}',
        color=0x3498db
    )
    
    if level_channel_id:
        level_channel = bot.get_channel(level_channel_id)
        embed.add_field(name='Canal de Nivel', value=level_channel.mention if level_channel else 'No encontrado', inline=False)
    else:
        embed.add_field(name='Canal de Nivel', value='No configurado', inline=False)
    
    if welcome_channel_id:
        welcome_channel = bot.get_channel(welcome_channel_id)
        embed.add_field(name='Canal de Bienvenida', value=welcome_channel.mention if welcome_channel else 'No encontrado', inline=False)
    else:
        embed.add_field(name='Canal de Bienvenida', value='No configurado', inline=False)
    
    if ticket_category_id:
        ticket_category = bot.get_channel(ticket_category_id)
        embed.add_field(name='Categoría de Tickets', value=ticket_category.name if ticket_category else 'No encontrada', inline=False)
    else:
        embed.add_field(name='Categoría de Tickets', value='No configurada', inline=False)
    
    if ranking_channel_id:
        ranking_channel = bot.get_channel(ranking_channel_id)
        embed.add_field(name='Canal de Ranking', value=ranking_channel.mention if ranking_channel else 'No encontrado', inline=False)
    else:
        embed.add_field(name='Canal de Ranking', value='No configurado', inline=False)
    
    if stream_channel_id:
        stream_channel = bot.get_channel(stream_channel_id)
        embed.add_field(name='Canal de Streams', value=stream_channel.mention if stream_channel else 'No encontrado', inline=False)
        embed.add_field(name='Streamers Monitoreados', value=f'{len(streamers)} streamers', inline=False)
    else:
        embed.add_field(name='Canal de Streams', value='No configurado', inline=False)
    
    if log_channel_id:
        log_channel = bot.get_channel(log_channel_id)
        embed.add_field(name='Canal de Logs', value=log_channel.mention if log_channel else 'No encontrado', inline=False)
    else:
        embed.add_field(name='Canal de Logs', value='No configurado', inline=False)
    
    embed.add_field(name='Auto-Roles', value=f'{len(auto_roles)} roles configurados', inline=False)
    embed.add_field(name='Palabras Prohibidas', value=f'{len(data["banned_words"])} palabras', inline=False)
    embed.add_field(name='🛡️ Auto-Protección', value='✅ ACTIVA (siempre)', inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='config_log_channel', description='Configura el canal para logs de auto-protección')
@discord.app_commands.describe(channel='Canal para logs de seguridad')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_server_setting(interaction.guild.id, 'log_channel', channel.id)
    data['config']['log_channel'] = channel.id  # Guardar en global para compatibilidad
    save_data()

    # Actualizar la variable global
    global log_channel_id
    log_channel_id = channel.id

    await interaction.response.send_message(f'✅ Canal de logs configurado: {channel.mention}')
    print(f'[Logs] Canal de logs configurado en servidor {interaction.guild.name}: {channel.name} (ID: {channel.id})')

@bot.tree.command(name='add_auto_role', description='Agrega un rol que se asignará automáticamente a nuevos miembros')
@discord.app_commands.describe(role='Rol a asignar automáticamente')
@discord.app_commands.checks.has_permissions(administrator=True)
async def add_auto_role(interaction: discord.Interaction, role: discord.Role):
    auto_roles = get_server_setting(interaction.guild.id, 'auto_roles', data['config'].get('auto_roles', []))
    
    if not auto_roles:
        auto_roles = []
    
    if role.id in auto_roles:
        await interaction.response.send_message('⚠️ Este rol ya está configurado como auto-rol.', ephemeral=True)
        return
    
    auto_roles.append(role.id)
    set_server_setting(interaction.guild.id, 'auto_roles', auto_roles)
    data['config']['auto_roles'] = auto_roles  # Guardar en global para compatibilidad
    save_data()
    
    await interaction.response.send_message(f'✅ Auto-rol agregado: {role.mention}')

@bot.tree.command(name='remove_auto_role', description='Elimina un rol de los auto-roles')
@discord.app_commands.describe(role='Rol a eliminar de auto-roles')
@discord.app_commands.checks.has_permissions(administrator=True)
async def remove_auto_role(interaction: discord.Interaction, role: discord.Role):
    auto_roles = get_server_setting(interaction.guild.id, 'auto_roles', data['config'].get('auto_roles', []))
    
    if not auto_roles:
        await interaction.response.send_message('❌ No hay auto-roles configurados.', ephemeral=True)
        return
    
    if role.id not in auto_roles:
        await interaction.response.send_message('❌ Este rol no está configurado como auto-rol.', ephemeral=True)
        return
    
    auto_roles.remove(role.id)
    set_server_setting(interaction.guild.id, 'auto_roles', auto_roles)
    data['config']['auto_roles'] = auto_roles  # Guardar en global para compatibilidad
    save_data()
    
    await interaction.response.send_message(f'✅ Auto-rol eliminado: {role.mention}')

@bot.tree.command(name='list_auto_roles', description='Lista los roles que se asignan automáticamente')
async def list_auto_roles(interaction: discord.Interaction):
    auto_roles = get_server_setting(interaction.guild.id, 'auto_roles', data['config'].get('auto_roles', []))
    
    if not auto_roles:
        await interaction.response.send_message('❌ No hay auto-roles configurados.', ephemeral=True)
        return
    
    description = '\n'.join([f'• {interaction.guild.get_role(role_id).name}' for role_id in auto_roles if interaction.guild.get_role(role_id)])
    
    embed = discord.Embed(
        title='🎭 Auto-Roles Configurados',
        description=description,
        color=0x9b59b6
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='config_verification', description='Configura el sistema de verificación')
@discord.app_commands.describe(channel='Canal de verificación', role='Rol que se dará al verificar')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_verification(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role):
    # Guardar configuración específica del servidor
    if 'servers' not in data:
        data['servers'] = {}
    server_id = str(interaction.guild.id)
    if server_id not in data['servers']:
        data['servers'][server_id] = {}

    data['servers'][server_id]['verification_channel'] = channel.id
    data['servers'][server_id]['verification_role'] = role.id
    data['servers'][server_id]['verified_users'] = data['servers'][server_id].get('verified_users', [])

    # También guardar en config global para compatibilidad
    data['config']['verification_channel'] = channel.id
    data['config']['verification_role'] = role.id

    save_data()

    await interaction.response.send_message(f'✅ Sistema de verificación configurado en servidor {interaction.guild.name}: {channel.mention} con rol {role.mention}')
    print(f'[Verificación] Configuración actualizada en servidor {interaction.guild.name} - Canal: {channel.name}, Rol: {role.name}')

@bot.tree.command(name='create_verification_message', description='Crea el mensaje de verificación en el canal configurado')
@discord.app_commands.checks.has_permissions(administrator=True)
async def create_verification_message(interaction: discord.Interaction):
    # Usar configuración específica del servidor actual
    server_id = str(interaction.guild.id)
    if 'servers' not in data or server_id not in data['servers']:
        await interaction.response.send_message('❌ Primero configura el sistema de verificación con /config_verification', ephemeral=True)
        return

    server_verification_channel = data['servers'][server_id].get('verification_channel')
    server_verification_role = data['servers'][server_id].get('verification_role')

    if not server_verification_channel or not server_verification_role:
        await interaction.response.send_message('❌ Primero configura el sistema de verificación con /config_verification', ephemeral=True)
        return

    channel = bot.get_channel(server_verification_channel)
    if not channel:
        await interaction.response.send_message('❌ Canal de verificación no encontrado', ephemeral=True)
        return

    try:
        embed = discord.Embed(
            title='🔒 VERIFICACIÓN REQUERIDA',
            description='Reacciona con ✅ para obtener acceso completo al servidor',
            color=0xFF6B6B
        )

        embed.add_field(name='📋 Beneficios', value='✅ Acceso a canales\n✅ Participar en chats\n✅ Sorteos y eventos\n✅ Acceso completo', inline=False)
        embed.add_field(name='🚀 Cómo verificar', value='Reacciona al mensaje ✅ para obtener acceso', inline=False)
        embed.add_field(name='📅 Fecha', value=datetime.now().strftime('%d/%m/%Y'), inline=True)
        embed.add_field(name='⏰ Hora', value=datetime.now().strftime('%H:%M'), inline=True)
        embed.set_footer(text='Sistema de verificación automática - Reacciona para verificar')
        embed.set_thumbnail(url=bot.user.display_avatar.url)

        message = await channel.send(embed=embed)
        await message.add_reaction('✅')

        # Guardar el message_id específico del servidor
        data['servers'][server_id]['verification_message_id'] = message.id
        save_data()

        await interaction.response.send_message(f'✅ Mensaje de verificación creado en {channel.mention}')
        print(f'[Verificación] Mensaje creado en servidor {interaction.guild.name} (ID: {message.id})')
    except Exception as e:
        await interaction.response.send_message(f'❌ Error al crear mensaje de verificación: {e}', ephemeral=True)
        print(f'[Verificación] Error al crear mensaje: {e}')

@bot.tree.command(name='manual_verify', description='Verifica manualmente a un usuario')
@discord.app_commands.describe(member='Usuario a verificar')
@discord.app_commands.checks.has_permissions(administrator=True)
async def manual_verify(interaction: discord.Interaction, member: discord.Member):
    # Usar configuración específica del servidor
    server_id = str(interaction.guild.id)
    if 'servers' not in data or server_id not in data['servers']:
        await interaction.response.send_message('❌ Sistema de verificación no configurado', ephemeral=True)
        return

    server_verification_role_id = data['servers'][server_id].get('verification_role')
    server_verified_users = data['servers'][server_id].get('verified_users', [])

    if not server_verification_role_id:
        await interaction.response.send_message('❌ Sistema de verificación no configurado', ephemeral=True)
        return

    try:
        role = interaction.guild.get_role(server_verification_role_id)
        if role:
            await member.add_roles(role)
            print(f'[Manual Verify] Rol {role.name} asignado a {member.name} en servidor {interaction.guild.name}')

            if str(member.id) not in server_verified_users:
                server_verified_users.append(str(member.id))
                data['servers'][server_id]['verified_users'] = server_verified_users
                save_data()
                print(f'[Manual Verify] {member.name} marcado como verificado en servidor {interaction.guild.name}')

            # Asignar auto-roles del servidor
            server_auto_roles = data['servers'][server_id].get('auto_roles', [])
            if server_auto_roles:
                for role_id in server_auto_roles:
                    auto_role = interaction.guild.get_role(role_id)
                    if auto_role:
                        await member.add_roles(auto_role)
                        print(f'[Manual Verify] Auto-rol {auto_role.name} asignado a {member.name} en servidor {interaction.guild.name}')

            # Enviar confirmación por mensaje privado (DM)
            try:
                await member.send(f'✅ ¡Has sido verificado manualmente en **{interaction.guild.name}**! Ahora tienes acceso completo al servidor.')
                print(f'[Manual Verify] Mensaje privado enviado a {member.name} en servidor {interaction.guild.name}')
            except discord.errors.Forbidden:
                # Si no se puede enviar DM, no enviar nada al usuario
                print(f'[Manual Verify] No se pudo enviar DM a {member.name} (DMs desactivados)')

            await interaction.response.send_message(f'✅ {member.mention} ha sido verificado manualmente', ephemeral=True)
        else:
            await interaction.response.send_message('❌ Rol de verificación no encontrado', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Error: {e}', ephemeral=True)

@bot.tree.command(name='check_verification_status', description='Verifica el estado del sistema de verificación')
async def check_verification_status(interaction: discord.Interaction):
    server_id = str(interaction.guild.id)
    
    verification_channel_id = get_server_setting(interaction.guild.id, 'verification_channel', data['config'].get('verification_channel'))
    verification_role_id = get_server_setting(interaction.guild.id, 'verification_role', data['config'].get('verification_role'))
    verification_message_id = get_server_setting(interaction.guild.id, 'verification_message_id', data['config'].get('verification_message_id'))
    verified_users = get_server_setting(interaction.guild.id, 'verified_users', data['config'].get('verified_users', []))
    auto_roles = get_server_setting(interaction.guild.id, 'auto_roles', data['config'].get('auto_roles', []))
    
    if not verification_channel_id or not verification_role_id:
        await interaction.response.send_message('❌ Sistema de verificación no configurado', ephemeral=True)
        return
    
    channel = bot.get_channel(verification_channel_id)
    role = interaction.guild.get_role(verification_role_id)
    
    embed = discord.Embed(
        title='🔒 Estado del Sistema de Verificación',
        color=0x3498db
    )
    
    embed.add_field(name='Canal de Verificación', value=channel.mention if channel else 'No encontrado', inline=False)
    embed.add_field(name='Rol de Verificación', value=role.mention if role else 'No encontrado', inline=False)
    embed.add_field(name='Mensaje de Verificación ID', value=str(verification_message_id) if verification_message_id else 'No configurado', inline=False)
    embed.add_field(name='Usuarios Verificados', value=str(len(verified_users)), inline=False)
    embed.add_field(name='Auto-Roles', value=f'{len(auto_roles)} roles configurados', inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Sistema de Sorteos
@bot.tree.command(name='config_giveaway_channel', description='Configura el canal para sorteos')
@discord.app_commands.describe(channel='Canal para sorteos')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_giveaway_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_server_setting(interaction.guild.id, 'giveaway_channel', channel.id)
    data['config']['giveaway_channel'] = channel.id  # Guardar en global para compatibilidad
    global giveaway_channel_id
    giveaway_channel_id = channel.id
    save_data()
    await interaction.response.send_message(f'✅ Canal de sorteos configurado: {channel.mention}')
    print(f'[Config] Canal de sorteos configurado en servidor {interaction.guild.name}: {channel.name} (ID: {channel.id})')

@bot.tree.command(name='config_announce_channel', description='Configura el canal para anuncios de sorteos')
@discord.app_commands.describe(channel='Canal para anuncios de sorteos')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_announce_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_server_setting(interaction.guild.id, 'giveaway_announcement_channel', channel.id)
    data['config']['giveaway_announcement_channel'] = channel.id  # Guardar en global para compatibilidad
    global giveaway_announcement_channel_id
    giveaway_announcement_channel_id = channel.id
    save_data()
    await interaction.response.send_message(f'✅ Canal de anuncios de sorteos configurado: {channel.mention}')
    print(f'[Config] Canal de anuncios configurado en servidor {interaction.guild.name}: {channel.name} (ID: {channel.id})')

@bot.tree.command(name='create_giveaway', description='Crea un nuevo sorteo')
@discord.app_commands.describe(
    prize='Premio del sorteo',
    duration='Duración en minutos',
    winners='Cantidad de ganadores'
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def create_giveaway(interaction: discord.Interaction, prize: str, duration: int, winners: int = 1):
    server_id = str(interaction.guild.id)
    giveaway_channel_id = get_server_setting(interaction.guild.id, 'giveaway_channel', data['config'].get('giveaway_channel'))
    giveaway_announcement_channel_id = get_server_setting(interaction.guild.id, 'giveaway_announcement_channel', data['config'].get('giveaway_announcement_channel'))
    
    if not giveaway_channel_id:
        await interaction.response.send_message('❌ Primero configura el canal de sorteos con /config_giveaway_channel', ephemeral=True)
        return
    
    channel = bot.get_channel(giveaway_channel_id)
    if not channel:
        await interaction.response.send_message('❌ Canal de sorteos no encontrado', ephemeral=True)
        return
    
    try:
        # Inicializar estructura de sorteos del servidor
        if 'servers' not in data:
            data['servers'] = {}
        if server_id not in data['servers']:
            data['servers'][server_id] = {}
        if 'giveaways' not in data['servers'][server_id]:
            data['servers'][server_id]['giveaways'] = {}
        
        # Calcular fecha de finalización
        end_time = datetime.now() + timedelta(minutes=duration)
        
        # Crear embed del sorteo
        embed = discord.Embed(
            title='🎉 ¡SORTEO!',
            description=f'**Premio:** {prize}\n\nReacciona con 🎉 para participar',
            color=0xFFD700
        )
        
        embed.add_field(name='🏆 Ganadores', value=str(winners), inline=True)
        embed.add_field(name='⏰ Tiempo restante', value=f'{duration} minutos', inline=True)
        embed.add_field(name='👥 Participantes', value='0', inline=True)
        embed.add_field(name='📅 Finaliza', value=end_time.strftime('%d/%m/%Y %H:%M'), inline=False)
        embed.set_footer(text=f'Organizado por {interaction.user.name}')
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        
        # Enviar mensaje del sorteo
        message = await channel.send(embed=embed)
        await message.add_reaction('🎉')
        
        # Guardar sorteo en el servidor específico
        giveaway_id = str(message.id)
        data['servers'][server_id]['giveaways'][giveaway_id] = {
            'prize': prize,
            'end_time': end_time.isoformat(),
            'winners': winners,
            'participants': [],
            'organizer': str(interaction.user.id),
            'channel_id': channel.id,
            'message_id': message.id,
            'announcement_messages': []  # Guardar IDs de mensajes de anuncios
        }
        # También guardar en global para compatibilidad
        giveaways[giveaway_id] = data['servers'][server_id]['giveaways'][giveaway_id]
        data['giveaways'] = giveaways
        save_data()
        
        await interaction.response.send_message(f'✅ Sorteo creado en {channel.mention}. Terminará a las {end_time.strftime("%H:%M")}')
        
        # Enviar notificación al canal de anuncios si está configurado
        if giveaway_announcement_channel_id:
            try:
                announcement_channel = bot.get_channel(giveaway_announcement_channel_id)
                if announcement_channel:
                    announcement_embed = discord.Embed(
                        title='🎉 ¡Nuevo Sorteo Creado!',
                        description=f'{interaction.user.mention} ha iniciado un nuevo sorteo de **{prize}**',
                        color=0xFFD700
                    )
                    announcement_embed.add_field(name='🎁 Premio', value=prize, inline=True)
                    announcement_embed.add_field(name='⏰ Duración', value=f'{duration} minutos', inline=True)
                    announcement_embed.add_field(name='👥 Ganadores', value=str(winners), inline=True)
                    announcement_embed.add_field(name='📁 Canal', value=channel.mention, inline=False)
                    announcement_embed.add_field(name='🎯 Cómo participar', value=f'Reacciona con 🎉 en {channel.mention}', inline=False)
                    announcement_embed.set_footer(text=f'Organizado por {interaction.user.name}')
                    announcement_embed.set_thumbnail(url=bot.user.display_avatar.url)
                    
                    await announcement_channel.send(embed=announcement_embed)
                    print(f'[Sorteo] Anuncio enviado al canal de anuncios')
            except Exception as e:
                print(f'[Sorteo] Error al enviar anuncio: {e}')
        
        # Iniciar tarea para finalizar sorteo
        bot.loop.create_task(end_giveaway_after_delay(giveaway_id, duration * 60, server_id))
        
    except Exception as e:
        await interaction.response.send_message(f'❌ Error al crear sorteo: {e}', ephemeral=True)

async def end_giveaway_after_delay(giveaway_id, delay, server_id=None):
    await asyncio.sleep(delay)
    await end_giveaway(giveaway_id, server_id)

async def end_giveaway(giveaway_id, server_id=None):
    # Buscar el sorteo en el servidor específico o en global
    giveaway = None
    giveaway_source = None
    
    if server_id and 'servers' in data and server_id in data['servers'] and 'giveaways' in data['servers'][server_id]:
        if giveaway_id in data['servers'][server_id]['giveaways']:
            giveaway = data['servers'][server_id]['giveaways'][giveaway_id]
            giveaway_source = 'server'
    
    if not giveaway and giveaway_id in giveaways:
        giveaway = giveaways[giveaway_id]
        giveaway_source = 'global'
    
    if not giveaway:
        return
    
    try:
        channel = bot.get_channel(giveaway['channel_id'])
        if not channel:
            return
        
        message = await channel.fetch_message(giveaway['message_id'])
        
        if not giveaway['participants']:
            # Actualizar embed mostrando que no hubo participantes
            embed = message.embeds[0]
            embed.description = f'**Premio:** {giveaway["prize"]}\n\n**❌ SORTEO CANCELADO - No hubo participantes**'
            embed.color = 0xE74C3C
            embed.set_field_at(1, name='⏰ Tiempo restante', value='Finalizado', inline=True)
            embed.set_field_at(2, name='👥 Participantes', value='0', inline=True)
            await message.edit(embed=embed)
            
            # Eliminar del servidor o global
            if giveaway_source == 'server' and server_id:
                del data['servers'][server_id]['giveaways'][giveaway_id]
            elif giveaway_id in giveaways:
                del giveaways[giveaway_id]
                data['giveaways'] = giveaways
            save_data()
            return
        
        # Elegir ganadores
        import random
        winners_count = min(giveaway['winners'], len(giveaway['participants']))
        winner_ids = random.sample(giveaway['participants'], winners_count)
        
        # Actualizar embed del mensaje original con los ganadores
        embed = message.embeds[0]
        embed.description = f'**Premio:** {giveaway["prize"]}\n\n**🎉 ¡SORTEO FINALIZADO!**'
        embed.color = 0x2ecc71  # Verde para indicar éxito
        embed.set_field_at(1, name='⏰ Tiempo restante', value='Finalizado', inline=True)
        embed.set_field_at(2, name='👥 Participantes', value=str(len(giveaway['participants'])), inline=True)
        
        winners_mentions = []
        winners_names = []
        for winner_id in winner_ids:
            try:
                winner = await bot.fetch_user(int(winner_id))
                winners_mentions.append(winner.mention)
                winners_names.append(winner.name)
            except:
                pass
        
        if winners_mentions:
            # Agregar campo de ganadores al embed
            embed.add_field(name=f'🏆 Ganador{"es" if len(winners_mentions) > 1 else ""} ({len(winners_mentions)})', 
                          value=', '.join(winners_mentions), inline=False)
            
            await message.edit(embed=embed)
            
            # Enviar mensaje adicional en el canal
            await channel.send(f'🎉 ¡Felicidades {", ".join(winners_mentions)} ganaron el sorteo de **{giveaway["prize"]}**!')
            
            # Enviar mensaje privado a cada ganador
            for winner_id in winner_ids:
                try:
                    winner = await bot.fetch_user(int(winner_id))
                    dm_embed = discord.Embed(
                        title='🎉 ¡Felicidades! ¡Has ganado un sorteo!',
                        description=f'Has ganado el sorteo de **{giveaway["prize"]}**!\n\nPor favor contacta al administrador para reclamar tu premio.',
                        color=0xFFD700
                    )
                    dm_embed.add_field(name='🎁 Premio', value=giveaway['prize'], inline=True)
                    dm_embed.add_field(name='📁 Servidor', value=channel.guild.name, inline=True)
                    dm_embed.set_footer(text='¡Felicidades por tu premio!')
                    dm_embed.set_thumbnail(url=bot.user.display_avatar.url)
                    
                    await winner.send(embed=dm_embed)
                    print(f'[Sorteo] Mensaje enviado a {winner.name}')
                except Exception as e:
                    print(f'[Sorteo] Error al enviar DM a {winner_id}: {e}')
            
            # Enviar notificación al canal de notificaciones
            await send_notification(
                guild=channel.guild,
                notification_type='giveaways',
                message=f'¡Ganadores del sorteo **{giveaway["prize"]}**: {", ".join(winners_mentions)}',
                color=0xFFD700
            )
        else:
            embed.add_field(name='🏆 Ganadores', value='No se pudieron determinar', inline=False)
            await message.edit(embed=embed)
        
        # Eliminar mensajes de anuncios del canal de anuncios
        giveaway_announcement_channel_id = get_server_setting(channel.guild.id, 'giveaway_announcement_channel', data['config'].get('giveaway_announcement_channel'))
        if giveaway_announcement_channel_id and 'announcement_messages' in giveaway:
            try:
                announcement_channel = bot.get_channel(giveaway_announcement_channel_id)
                if announcement_channel:
                    for message_id in giveaway['announcement_messages']:
                        try:
                            message = await announcement_channel.fetch_message(message_id)
                            await message.delete()
                            print(f'[Sorteo] Mensaje de anuncio eliminado: {message_id}')
                        except:
                            pass  # Mensaje ya no existe
            except Exception as e:
                print(f'[Sorteo] Error al eliminar mensajes de anuncio: {e}')
        
        # Eliminar sorteo de la lista
        if giveaway_source == 'server' and server_id:
            del data['servers'][server_id]['giveaways'][giveaway_id]
        elif giveaway_id in giveaways:
            del giveaways[giveaway_id]
            data['giveaways'] = giveaways
        save_data()
        
        print(f'[Sorteo] Sorteo "{giveaway["prize"]}" finalizado. Ganadores: {len(winners_mentions)}')
        
    except Exception as e:
        print(f'Error al finalizar sorteo: {e}')

@bot.tree.command(name='end_giveaway', description='Finaliza manualmente un sorteo')
@discord.app_commands.describe(message_id='ID del mensaje del sorteo')
@discord.app_commands.checks.has_permissions(administrator=True)
async def end_giveaway_command(interaction: discord.Interaction, message_id: str):
    try:
        message_id_int = int(message_id)
        server_id = str(interaction.guild.id)
        
        # Buscar en el servidor específico
        found = False
        if 'servers' in data and server_id in data['servers'] and 'giveaways' in data['servers'][server_id]:
            if str(message_id_int) in data['servers'][server_id]['giveaways']:
                await end_giveaway(str(message_id_int), server_id)
                found = True
        
        # Fallback a global
        if not found and str(message_id_int) in giveaways:
            await end_giveaway(str(message_id_int))
            found = True
        
        if found:
            await interaction.response.send_message('✅ Sorteo finalizado manualmente')
        else:
            await interaction.response.send_message('❌ Sorteo no encontrado', ephemeral=True)
    except ValueError:
        await interaction.response.send_message('❌ ID de mensaje inválido', ephemeral=True)

@bot.tree.command(name='list_giveaways', description='Lista los sorteos activos')
async def list_giveaways(interaction: discord.Interaction):
    if not giveaways:
        await interaction.response.send_message('❌ No hay sorteos activos', ephemeral=True)
        return
    
    embed = discord.Embed(
        title='🎉 Sorteos Activos',
        color=0xFFD700
    )
    
    for giveaway_id, giveaway in giveaways.items():
        end_time = datetime.fromisoformat(giveaway['end_time'])
        time_left = end_time - datetime.now()
        
        embed.add_field(
            name=f'🎁 {giveaway["prize"]}',
            value=f'Participantes: {len(giveaway["participants"])} | Termina en: {time_left}',
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='reroll_giveaway', description='Vuelve a elegir ganadores de un sorteo terminado')
@discord.app_commands.describe(message_id='ID del mensaje del sorteo terminado')
async def reroll_giveaway(interaction: discord.Interaction, message_id: str):
    try:
        message_id_int = int(message_id)
        channel = bot.get_channel(giveaway_channel_id)
        if not channel:
            await interaction.response.send_message('❌ Canal de sorteos no configurado', ephemeral=True)
            return
        
        message = await channel.fetch_message(message_id_int)
        
        # Buscar participantes antiguos (guardados en embed o metadata)
        participants = []
        for reaction in message.reactions:
            if str(reaction.emoji) == '🎉':
                async for user in reaction.users():
                    if not user.bot:
                        participants.append(str(user.id))
        
        if not participants:
            await interaction.response.send_message('❌ No hay participantes para reroll', ephemeral=True)
            return
        
        import random
        winner_id = random.choice(participants)
        winner = await bot.fetch_user(int(winner_id))
        
        await channel.send(f'🎉 ¡Nuevo ganador del sorteo: {winner.mention}!')
        await interaction.response.send_message(f'✅ Nuevo ganador elegido: {winner.mention}')
        
    except Exception as e:
        await interaction.response.send_message(f'❌ Error: {e}', ephemeral=True)

@bot.tree.command(name='test_log', description='Prueba el sistema de logs')
async def test_log(interaction: discord.Interaction):
    await send_log(
        guild=interaction.guild,
        title='Prueba de Logs',
        description=f'Prueba del sistema de logs por {interaction.user.mention}',
        color=0x3498db,
        fields=[
            {'name': 'Usuario', 'value': interaction.user.name, 'inline': True},
            {'name': 'Hora', 'value': datetime.now().strftime('%H:%M:%S'), 'inline': True}
        ],
        author={'name': interaction.user.name, 'icon_url': interaction.user.display_avatar.url}
    )
    await interaction.response.send_message('✅ Prueba de log enviada. Revisa el canal de logs.', ephemeral=True)

# Sistema de Notificaciones
@bot.tree.command(name='config_notifications_channel', description='Configura el canal de notificaciones')
@discord.app_commands.describe(channel='Canal para notificaciones')
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_notifications_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    set_server_setting(interaction.guild.id, 'notifications_channel', channel.id)
    data['config']['notifications_channel'] = channel.id  # Guardar en global para compatibilidad
    global notifications_channel_id
    notifications_channel_id = channel.id
    save_data()
    await interaction.response.send_message(f'✅ Canal de notificaciones configurado: {channel.mention}')
    print(f'[Config] Canal de notificaciones configurado en servidor {interaction.guild.name}: {channel.name} (ID: {channel.id})')

@bot.tree.command(name='config_notification_role', description='Configura el rol para un tipo de notificación')
@discord.app_commands.describe(
    notification_type='Tipo de notificación',
    role='Rol a asignar'
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def config_notification_role(interaction: discord.Interaction, notification_type: str, role: discord.Role):
    valid_types = ['streams', 'giveaways', 'announcements', 'events']
    
    if notification_type not in valid_types:
        await interaction.response.send_message(f'❌ Tipo inválido. Usa: {", ".join(valid_types)}', ephemeral=True)
        return
    
    notification_roles = get_server_setting(interaction.guild.id, 'notification_roles', data['config'].get('notification_roles', {}))
    
    if not notification_roles:
        notification_roles = {}
    
    notification_roles[notification_type] = role.id
    set_server_setting(interaction.guild.id, 'notification_roles', notification_roles)
    data['config']['notification_roles'] = notification_roles  # Guardar en global para compatibilidad
    save_data()
    
    await interaction.response.send_message(f'✅ Rol de notificación para {notification_type} configurado: {role.mention}')

@bot.tree.command(name='subscribe', description='Suscríbete a notificaciones específicas')
@discord.app_commands.describe(
    notification_type='Tipo de notificación'
)
async def subscribe(interaction: discord.Interaction, notification_type: str):
    valid_types = ['streams', 'giveaways', 'announcements', 'events']
    
    if notification_type not in valid_types:
        await interaction.response.send_message(f'❌ Tipo inválido. Usa: {", ".join(valid_types)}', ephemeral=True)
        return
    
    user_id = str(interaction.user.id)
    notification_roles = get_server_setting(interaction.guild.id, 'notification_roles', data['config'].get('notification_roles', {}))
    
    if not data['user_notifications']:
        data['user_notifications'] = {}
    
    if user_id not in data['user_notifications']:
        data['user_notifications'][user_id] = []
    
    if notification_type not in data['user_notifications'][user_id]:
        data['user_notifications'][user_id].append(notification_type)
        save_data()
        
        # Asignar rol si existe
        role_id = notification_roles.get(notification_type)
        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                await interaction.user.add_roles(role)
        
        await interaction.response.send_message(f'✅ Te has suscrito a notificaciones de {notification_type}')
    else:
        await interaction.response.send_message(f'⚠️ Ya estás suscrito a {notification_type}', ephemeral=True)

@bot.tree.command(name='unsubscribe', description='Cancela tu suscripción a notificaciones')
@discord.app_commands.describe(
    notification_type='Tipo de notificación'
)
async def unsubscribe(interaction: discord.Interaction, notification_type: str):
    valid_types = ['streams', 'giveaways', 'announcements', 'events']
    
    if notification_type not in valid_types:
        await interaction.response.send_message(f'❌ Tipo inválido. Usa: {", ".join(valid_types)}', ephemeral=True)
        return
    
    user_id = str(interaction.user.id)
    notification_roles = get_server_setting(interaction.guild.id, 'notification_roles', data['config'].get('notification_roles', {}))
    
    if user_id in data['user_notifications'] and notification_type in data['user_notifications'][user_id]:
        data['user_notifications'][user_id].remove(notification_type)
        global user_notifications
        user_notifications = data['user_notifications']
        save_data()
        
        # Remover rol si existe
        role_id = notification_roles.get(notification_type)
        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                await interaction.user.remove_roles(role)
        
        await interaction.response.send_message(f'✅ Has cancelado tu suscripción a {notification_type}')
    else:
        await interaction.response.send_message(f'⚠️ No estás suscrito a {notification_type}', ephemeral=True)

@bot.tree.command(name='my_subscriptions', description='Muestra tus suscripciones actuales')
async def my_subscriptions(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    notification_roles = get_server_setting(interaction.guild.id, 'notification_roles', data['config'].get('notification_roles', {}))
    
    valid_types = ['streams', 'giveaways', 'announcements', 'events']
    
    if user_id not in data['user_notifications'] or not data['user_notifications'][user_id]:
        user_subs = []
    else:
        user_subs = data['user_notifications'][user_id]
    
    embed = discord.Embed(
        title='🔔 Mis Suscripciones',
        description='Tipos de notificaciones a los que estás suscrito:',
        color=0x3498db
    )
    
    for notif_type in valid_types:
        status = '✅ Suscrito' if notif_type in user_subs else '❌ No suscrito'
        role_id = notification_roles.get(notif_type)
        role_mention = f' ({interaction.guild.get_role(role_id).mention if role_id and interaction.guild.get_role(role_id) else "Sin rol"})'
        embed.add_field(name=notif_type.upper(), value=f'{status}{role_mention}', inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='send_message', description='Envía un mensaje anónimo a un canal específico')
@discord.app_commands.describe(
    channel='Canal donde enviar el mensaje',
    message='Mensaje a enviar',
    mention_everyone='¿Mencionar @everyone?'
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def send_message(interaction: discord.Interaction, channel: discord.TextChannel, message: str, mention_everyone: bool = False):
    try:
        # Verificar que el bot tenga permisos en el canal
        bot_permissions = channel.permissions_for(interaction.guild.me)
        if not bot_permissions.send_messages:
            await interaction.response.send_message('❌ El bot no tiene permisos para enviar mensajes en ese canal', ephemeral=True)
            return

        # Enviar mensaje anónimo
        if mention_everyone:
            await channel.send(f'@everyone {message}')
        else:
            await channel.send(message)

        await interaction.response.send_message(f'✅ Mensaje enviado anónimamente a {channel.mention}', ephemeral=True)
        print(f'[Mensaje Anónimo] Mensaje enviado a {channel.name} por {interaction.user.name}')
    except Exception as e:
        await interaction.response.send_message(f'❌ Error: {e}', ephemeral=True)

@bot.tree.command(name='send_announcement', description='Envía un anuncio al canal de notificaciones')
@discord.app_commands.describe(
    message='Mensaje del anuncio',
    important='¿Es importante? (mencionará @everyone)'
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def send_announcement(interaction: discord.Interaction, message: str, important: bool = False):
    notifications_channel_id = get_server_setting(interaction.guild.id, 'notifications_channel', data['config'].get('notifications_channel'))
    
    if not notifications_channel_id:
        await interaction.response.send_message('❌ Canal de notificaciones no configurado', ephemeral=True)
        return
    
    await send_notification(
        guild=interaction.guild,
        notification_type='announcements',
        message=message,
        color=0xFFD700,
        mention_role=not important
    )
    
    await interaction.response.send_message('✅ Anuncio enviado al canal de notificaciones')

@bot.tree.command(name='send_event', description='Envía una notificación de evento')
@discord.app_commands.describe(
    event_name='Nombre del evento',
    description='Descripción del evento',
    date='Fecha del evento (DD/MM/YYYY)'
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def send_event(interaction: discord.Interaction, event_name: str, description: str, date: str):
    notifications_channel_id = get_server_setting(interaction.guild.id, 'notifications_channel', data['config'].get('notifications_channel'))
    
    if not notifications_channel_id:
        await interaction.response.send_message('❌ Canal de notificaciones no configurado', ephemeral=True)
        return
    
    message = f'**{event_name}**\n{description}\n📅 Fecha: {date}'
    
    await send_notification(
        guild=interaction.guild,
        notification_type='events',
        message=message,
        color=0x9b59b6
    )
    
    await interaction.response.send_message('✅ Evento enviado al canal de notificaciones')

# Tickets
@bot.tree.command(name='ticket', description='Crea un ticket de soporte')
async def ticket(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message('Este comando solo funciona en servidores.', ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    category_id = get_server_setting(interaction.guild.id, 'ticket_category', data['config'].get('ticket_category'))
    category = bot.get_channel(category_id) if category_id else None
    
    # Inicializar estructura de tickets del servidor
    if 'servers' not in data:
        data['servers'] = {}
    if server_id not in data['servers']:
        data['servers'][server_id] = {}
    if 'tickets' not in data['servers'][server_id]:
        data['servers'][server_id]['tickets'] = {}
    
    ticket_num = len(data['servers'][server_id]['tickets']) + 1
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    
    channel = await interaction.guild.create_text_channel(
        name=f'ticket-{ticket_num}',
        category=category,
        overwrites=overwrites
    )
    
    data['servers'][server_id]['tickets'][str(channel.id)] = {
        'user_id': str(interaction.user.id),
        'created_at': datetime.now().isoformat()
    }
    # También guardar en global para compatibilidad
    data['tickets'][str(channel.id)] = data['servers'][server_id]['tickets'][str(channel.id)]
    save_data()
    
    # Log de ticket creado
    await send_log(
        guild=interaction.guild,
        title='Ticket Creado',
        description=f'{interaction.user.mention} ha creado un ticket de soporte',
        color=0x3498db,
        fields=[
            {'name': 'Usuario', 'value': interaction.user.name, 'inline': True},
            {'name': 'Canal', 'value': channel.mention, 'inline': True},
            {'name': 'Fecha', 'value': datetime.now().strftime('%d/%m/%Y %H:%M'), 'inline': True}
        ],
        author={'name': interaction.user.name, 'icon_url': interaction.user.display_avatar.url}
    )
    
    embed = discord.Embed(
        title='🎫 Ticket de Soporte',
        description=f'Ticket creado por {interaction.user.mention}\n\nUsa /close para cerrar este ticket.',
        color=0x3498db
    )
    
    await channel.send(embed=embed)
    await interaction.response.send_message(f'✅ Ticket creado: {channel.mention}')

@bot.tree.command(name='close', description='Cierra el ticket actual')
async def close(interaction: discord.Interaction):
    if not interaction.channel or 'ticket-' not in interaction.channel.name:
        await interaction.response.send_message('Este comando solo funciona en canales de tickets.', ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    
    # Eliminar del servidor específico
    if 'servers' in data and server_id in data['servers'] and 'tickets' in data['servers'][server_id]:
        if str(interaction.channel.id) in data['servers'][server_id]['tickets']:
            del data['servers'][server_id]['tickets'][str(interaction.channel.id)]
    
    # También eliminar de global para compatibilidad
    if str(interaction.channel.id) in data['tickets']:
        del data['tickets'][str(interaction.channel.id)]
    
    save_data()
    
    await interaction.response.send_message('🔒 Cerrando ticket en 5 segundos...')
    await asyncio.sleep(5)
    await interaction.channel.delete()

# Sistema de Gestión de Roles
@bot.tree.command(name='create_role', description='Crea un nuevo rol')
@discord.app_commands.describe(
    name='Nombre del rol',
    color='Color del rol (hexadecimal)',
    permissions='¿Rol administrador?'
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def create_role(interaction: discord.Interaction, name: str, color: str = '0x3498db', permissions: bool = False):
    try:
        # Convertir color hex a entero
        if color.startswith('0x'):
            color_int = int(color, 16)
        else:
            color_int = int(color, 16)
        
        # Crear permisos
        role_permissions = discord.Permissions(administrator=permissions)
        
        role = await interaction.guild.create_role(
            name=name,
            color=discord.Color(color_int),
            permissions=role_permissions
        )
        
        await interaction.response.send_message(f'✅ Rol {role.mention} creado exitosamente')
        
        # Log de creación de rol
        await send_log(
            guild=interaction.guild,
            title='🎭 Rol Creado',
            description=f'{interaction.user.mention} creó el rol {role.mention}',
            color=0x2ecc71,
            fields=[
                {'name': 'Nombre', 'value': role.name, 'inline': True},
                {'name': 'Color', 'value': str(role.color), 'inline': True},
                {'name': 'Administrador', 'value': 'Sí' if permissions else 'No', 'inline': True}
            ],
            author={'name': interaction.user.name, 'icon_url': interaction.user.display_avatar.url}
        )
    except Exception as e:
        await interaction.response.send_message(f'❌ Error al crear rol: {e}', ephemeral=True)

@bot.tree.command(name='add_role_to_user', description='Agrega un rol a un usuario')
@discord.app_commands.describe(
    user='Usuario',
    role='Rol a agregar'
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def add_role_to_user(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    try:
        await user.add_roles(role)
        await interaction.response.send_message(f'✅ Rol {role.mention} agregado a {user.mention}')
        
        # Log de rol asignado
        await send_log(
            guild=interaction.guild,
            title='🎭 Rol Asignado Manualmente',
            description=f'{interaction.user.mention} asignó {role.mention} a {user.mention}',
            color=0x2ecc71,
            fields=[
                {'name': 'Moderador', 'value': interaction.user.name, 'inline': True},
                {'name': 'Usuario', 'value': user.name, 'inline': True},
                {'name': 'Rol', 'value': role.name, 'inline': True}
            ],
            author={'name': interaction.user.name, 'icon_url': interaction.user.display_avatar.url}
        )
    except Exception as e:
        await interaction.response.send_message(f'❌ Error: {e}', ephemeral=True)

@bot.tree.command(name='remove_role_from_user', description='Elimina un rol de un usuario')
@discord.app_commands.describe(
    user='Usuario',
    role='Rol a eliminar'
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def remove_role_from_user(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    try:
        await user.remove_roles(role)
        await interaction.response.send_message(f'✅ Rol {role.mention} eliminado de {user.mention}')
        
        # Log de rol removido
        await send_log(
            guild=interaction.guild,
            title='🎭 Rol Removido Manualmente',
            description=f'{interaction.user.mention} eliminó {role.mention} de {user.mention}',
            color=0xE74C3C,
            fields=[
                {'name': 'Moderador', 'value': interaction.user.name, 'inline': True},
                {'name': 'Usuario', 'value': user.name, 'inline': True},
                {'name': 'Rol', 'value': role.name, 'inline': True}
            ],
            author={'name': interaction.user.name, 'icon_url': interaction.user.display_avatar.url}
        )
    except Exception as e:
        await interaction.response.send_message(f'❌ Error: {e}', ephemeral=True)

@bot.tree.command(name='list_roles', description='Lista todos los roles del servidor')
async def list_roles(interaction: discord.Interaction):
    roles_list = []
    for role in interaction.guild.roles:
        if role.name != '@everyone':
            roles_list.append(f'{role.mention} - {"Admin" if role.permissions.administrator else "Miembro"}')
    
    embed = discord.Embed(
        title='🎭 Roles del Servidor',
        description=f'Total: {len(roles_list)} roles',
        color=0x3498db
    )
    
    for i, role_info in enumerate(roles_list[:10], 1):
        embed.add_field(name=f'Rol {i}', value=role_info, inline=False)
    
    if len(roles_list) > 10:
        embed.add_field(name='...', value=f'y {len(roles_list) - 10} roles más', inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='member_info', description='Muestra información detallada de un usuario')
@discord.app_commands.describe(user='Usuario (vacío para ver tu propia info)')
async def member_info(interaction: discord.Interaction, user: discord.Member = None):
    target = user if user else interaction.user
    
    embed = discord.Embed(
        title=f'👤 Información de {target.name}',
        color=0x3498db
    )
    
    embed.add_field(name='🆔 ID', value=str(target.id), inline=True)
    embed.add_field(name='📅 Cuenta creada', value=target.created_at.strftime('%d/%m/%Y'), inline=True)
    embed.add_field(name='📅 Se unió', value=target.joined_at.strftime('%d/%m/%Y') if target.joined_at else 'Desconocido', inline=True)
    embed.add_field(name='🎭 Roles', value=str(len(target.roles)), inline=True)
    embed.add_field(name='🔥 Boost', value='Sí' if target.premium_since else 'No', inline=True)
    
    if target.roles:
        roles_text = ', '.join([role.mention for role in target.roles if role.name != '@everyone'])[:5]
        if len(target.roles) > 6:
            roles_text += f' y {len(target.roles) - 6} más'
        embed.add_field(name='🎭 Roles principales', value=roles_text, inline=False)
    
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text=f'Solicitado por {interaction.user.name}')
    
    await interaction.response.send_message(embed=embed)

# Moderación
@bot.tree.command(name='warn', description='Advierte a un usuario')
@discord.app_commands.describe(member='Usuario a advertir')
@discord.app_commands.checks.has_permissions(kick_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member):
    server_id = str(interaction.guild.id)
    user_id = str(member.id)
    
    # Inicializar estructura de warns del servidor
    if 'servers' not in data:
        data['servers'] = {}
    if server_id not in data['servers']:
        data['servers'][server_id] = {}
    if 'warns' not in data['servers'][server_id]:
        data['servers'][server_id]['warns'] = {}
    
    if user_id not in data['servers'][server_id]['warns']:
        data['servers'][server_id]['warns'][user_id] = []
    
    data['servers'][server_id]['warns'][user_id].append({
        'reason': 'Advertencia',
        'moderator': str(interaction.user.id),
        'date': datetime.now().isoformat()
    })
    # También guardar en global para compatibilidad
    if user_id not in data['warns']:
        data['warns'][user_id] = []
    data['warns'][user_id] = data['servers'][server_id]['warns'][user_id]
    save_data()
    
    # Log de advertencia
    await send_log(
        guild=interaction.guild,
        title='Advertencia Emitida',
        description=f'{interaction.user.mention} ha advertido a {member.mention}',
        color=0xFFA500,
        fields=[
            {'name': 'Moderador', 'value': interaction.user.name, 'inline': True},
            {'name': 'Usuario advertido', 'value': member.name, 'inline': True},
            {'name': 'Total advertencias', 'value': str(len(data['servers'][server_id]['warns'][user_id])), 'inline': True}
        ],
        author={'name': interaction.user.name, 'icon_url': interaction.user.display_avatar.url}
    )
    
    await interaction.response.send_message(f'⚠️ {member.mention} ha sido advertido. Total: {len(data["servers"][server_id]["warns"][user_id])}')

@bot.tree.command(name='kick', description='Expulsa a un usuario')
@discord.app_commands.describe(member='Usuario a expulsar')
@discord.app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.kick(reason='Kick por moderador')
        
        # Log de kick
        await send_log(
            guild=interaction.guild,
            title='Usuario Expulsado',
            description=f'{interaction.user.mention} ha expulsado a {member.mention}',
            color=0xE74C3C,
            fields=[
                {'name': 'Moderador', 'value': interaction.user.name, 'inline': True},
                {'name': 'Usuario expulsado', 'value': member.name, 'inline': True},
                {'name': 'ID', 'value': str(member.id), 'inline': True}
            ],
            author={'name': interaction.user.name, 'icon_url': interaction.user.display_avatar.url}
        )
        
        await interaction.response.send_message(f'👢 {member.name} ha sido expulsado.')
    except Exception as e:
        await interaction.response.send_message(f'❌ Error: {e}')

@bot.tree.command(name='ban', description='Banea a un usuario')
@discord.app_commands.describe(member='Usuario a banear')
@discord.app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.ban(reason='Ban por moderador')
        
        # Log de ban
        await send_log(
            guild=interaction.guild,
            title='Usuario Baneado',
            description=f'{interaction.user.mention} ha baneado a {member.mention}',
            color=0xE74C3C,
            fields=[
                {'name': 'Moderador', 'value': interaction.user.name, 'inline': True},
                {'name': 'Usuario baneado', 'value': member.name, 'inline': True},
                {'name': 'ID', 'value': str(member.id), 'inline': True}
            ],
            author={'name': interaction.user.name, 'icon_url': interaction.user.display_avatar.url}
        )
        
        await interaction.response.send_message(f'🔨 {member.name} ha sido baneado.')
    except Exception as e:
        await interaction.response.send_message(f'❌ Error: {e}')

@bot.tree.command(name='sync_commands', description='Fuerza la sincronización de comandos')
@discord.app_commands.checks.has_permissions(administrator=True)
async def sync_commands(interaction: discord.Interaction):
    try:
        # Sincronizar comandos globalmente
        synced = await bot.tree.sync()
        await interaction.response.send_message(f'✅ Sincronizados {len(synced)} comandos globalmente', ephemeral=True)
        print(f'[Sincronización] Comandos sincronizados: {len(synced)}')
    except Exception as e:
        await interaction.response.send_message(f'❌ Error al sincronizar: {e}', ephemeral=True)
        print(f'[Sincronización] Error: {e}')


# Manejador de errores global para comandos
@bot.tree.error
async def on_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(f'[Error Global] Error en comando: {type(error).__name__}: {error}')

    if isinstance(error, discord.app_commands.MissingPermissions):
        missing_perms = ", ".join(error.missing_permissions)
        try:
            await interaction.response.send_message(f'❌ No tienes permisos. Necesitas: {missing_perms}', ephemeral=True)
        except discord.errors.NotFound:
            pass  # La interacción expiró
        except Exception as e:
            print(f'[Error Global] Error al responder sobre permisos: {e}')
    elif isinstance(error, discord.app_commands.CommandNotFound):
        try:
            await interaction.response.send_message('❌ Comando no encontrado.', ephemeral=True)
        except discord.errors.NotFound:
            pass
        except Exception as e:
            print(f'[Error Global] Error al responder sobre comando no encontrado: {e}')
    elif isinstance(error, discord.app_commands.CommandInvokeError):
        try:
            await interaction.response.send_message(f'❌ Error al ejecutar el comando: {str(error.original)}', ephemeral=True)
        except discord.errors.NotFound:
            pass
        except Exception as e:
            print(f'[Error Global] Error al responder sobre error de comando: {e}')
    else:
        try:
            await interaction.response.send_message(f'❌ Error: {str(error)}', ephemeral=True)
        except discord.errors.NotFound:
            pass
        except Exception as e:
            print(f'[Error Global] Error al responder sobre error general: {e}')

# Iniciar el bot
bot.run(TOKEN)
