# 🤖 Discord Bot FH4XDZzz

Bot de Discord completo con múltiples funcionalidades para gestión de comunidades.

## ✨ Características

### 📊 Sistema de Niveles y XP
- Sistema de experiencia por mensajes
- Subida de niveles automáticos
- Top de usuarios por nivel
- Ranking automático actualizado cada 60 segundos

### 🎉 Sistema de Sorteos
- Creación de sorteos con premios personalizados
- Temporizadores en tiempo real
- Participación mediante reacciones
- Ganadores múltiples
- Mensajes privados a ganadores
- Recordatorios automáticos en canal de anuncios

### 🎭 Auto-Roles
- Configuración de roles automáticos para nuevos miembros
- Asignación automática al unirse al servidor
- Lista y gestión de auto-roles

### 🔒 Sistema de Verificación
- Sistema de verificación por reacción
- Mensaje de verificación personalizable
- Verificación manual disponible
- Configuración de canal y rol de verificación

### 📺 Notificaciones de Streams
- Monitoreo de streamers (TikTok, Kick, Twitch, YouTube)
- Notificaciones automáticas cuando un streamer está en vivo
- Configuración de múltiples streamers

### 🛡️ Anti-Spam y Protección
- Detección automática de spam rápido
- Detección de mensajes duplicados
- Detección de spam de menciones y emojis
- Sistema de advertencias progresivas
- Timeout automático para spammers
- Protección contra links peligrosos
- Detección de malware y archivos ejecutables

### 🎫 Sistema de Tickets
- Creación de tickets de soporte
- Categorías personalizadas
- Cierre automático de tickets

### 🔔 Sistema de Notificaciones
- Suscripción a notificaciones por tipo
- Roles de notificaciones configurables
- Anuncios y eventos personalizados

### 📜 Sistema de Logs
- Registro completo de eventos del servidor
- Logs de entradas/salidas de miembros
- Logs de cambios de roles
- Logs de mensajes eliminados
- Logs de acciones de moderación

### 🏆 Moderación
- Sistema de advertencias
- Expulsión de usuarios
- Baneo de usuarios
- Control de permisos por comandos

## 🚀 Instalación

### Requisitos
- Python 3.14+
- Cuenta de Discord Bot

### Pasos

1. **Clonar el repositorio:**
```bash
git clone https://github.com/FH4XDZzz/discord-bot.git
cd discord-bot
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar el bot:**
   - Crea un archivo `.env` con el siguiente contenido:
```
DISCORD_TOKEN=tu_token_aqui
```

4. **Obtener el token:**
   - Ve a [Discord Developer Portal](https://discord.com/developers/applications)
   - Crea una nueva aplicación
   - Ve a la sección "Bot" y crea un bot
   - Copia el token y ponlo en el archivo `.env`

5. **Configurar Intents Privilegiados:**
   - En Discord Developer Portal, activa:
     - ✅ Server Members Intent
     - ✅ Message Content Intent
     - ✅ Presence Intent
     - ✅ Voice States Intent

6. **Invitar el bot al servidor:**
   - Usa el enlace de OAuth2 con permisos de administrador
   - Asegúrate de incluir el scope `bot` y `applications.commands`

7. **Iniciar el bot:**
```bash
python bot.py
```

## 📋 Comandos Principales

### Comandos Públicos
- `/ping` - Verificar latencia
- `/ayuda` - Panel de comandos del bot
- `/info` - Información del servidor
- `/level` - Ver tu nivel y XP
- `/top` - Top usuarios por nivel
- `/subscribe` - Suscribirse a notificaciones
- `/unsubscribe` - Desuscribirse de notificaciones
- `/my_subscriptions` - Ver tus suscripciones
- `/ticket` - Crear ticket de soporte
- `/close` - Cerrar ticket actual

### Comandos de Administración
- `/config_giveaway_channel` - Configurar canal de sorteos
- `/config_announce_channel` - Configurar canal de anuncios
- `/create_giveaway` - Crear sorteo
- `/end_giveaway` - Finalizar sorteo
- `/config_verification` - Configurar verificación
- `/create_verification_message` - Crear mensaje de verificación
- `/add_auto_role` - Agregar auto-rol
- `/remove_auto_role` - Eliminar auto-rol
- `/warn` - Advertir usuario
- `/kick` - Expulsar usuario
- `/ban` - Banear usuario

## 🔧 Configuración

### Archivos
- `bot.py` - Código principal del bot
- `bot_data.json` - Datos persistentes del bot
- `.env` - Variables de entorno (token)
- `requirements.txt` - Dependencias de Python

### Estructura de Datos
El bot guarda la configuración en `bot_data.json` incluyendo:
- Canales configurados
- Roles automáticos
- Datos de usuarios (niveles, XP)
- Sorteos activos
- Logs de advertencias
- Configuración de verificación

## 🛡️ Seguridad

- El token del bot nunca debe ser compartido públicamente
- Se recomienda regenerar el token si fue expuesto
- Los comandos sensibles requieren permisos de administrador
- Sistema anti-spam activo por defecto

## 📚 Tecnologías

- Python 3.14
- discord.py
- python-dotenv
- requests

## 📄 Licencia

MIT License

## 👤 Autor

FH4XDZzz

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor abre un issue o pull request para sugerencias o mejoras.

## 📞 Soporte

Para soporte, abre un issue en el repositorio de GitHub.