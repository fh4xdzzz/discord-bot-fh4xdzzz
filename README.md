# Discord Bot FH4XDZzz

## 🚀 Despliegue en SparkedHost

### Prerrequisitos
- Cuenta en SparkedHost
- Token de Discord configurado en variables de entorno
- Python 3.14+

### Configuración en SparkedHost

1. **Crear la aplicación**
   - Entra a SparkedHost
   - Crea una nueva aplicación Python
   - Selecciona la región más cercana

2. **Configurar variables de entorno**
   - Ve a Settings → Environment Variables
   - Agrega: `DISCORD_TOKEN` = tu token de Discord
   - NO subas el archivo .env por seguridad

3. **Subir los archivos**
   - Sube todos los archivos del proyecto
   - EXCEPTO: .env, bot_data.json, bot.log
   - Estos se crearán automáticamente en el servidor

4. **Dependencias**
   - Sube el archivo requirements.txt
   - SparkedHost instalará las dependencias automáticamente

5. **Comando de inicio**
   - Usa: `python main.py`
   - O configura el Procfile: `worker: python main.py`

### Archivos Necesarios
- main.py (código principal)
- requirements.txt (dependencias)
- Procfile (comando de inicio)
- .gitignore (archivos a ignorar)

### Archivos que NO subir
- .env (variables de entorno locales)
- bot_data.json (datos locales)
- bot.log (logs locales)
- Scripts temporales

### Funcionalidades del Bot
- Sistema de tickets profesional
- Sistema de sorteos
- Sistema de niveles y ranking
- Sistema de verificación
- Sistema de roles reaccionables
- Sistema de streams
- Sistema de notificaciones
- Sistema de búsqueda y estadísticas

### Comandos Importantes
- /ayuda - Panel de ayuda interactivo
- /ticket_channel - Configura categoría de tickets
- /ticket_create_config - Crea configuración de tickets
- /ticket_send - Envía panel de tickets
- /giveaway_create - Crea sorteo
- /create_verification_message - Crea sistema de verificación

### Soporte
- Para problemas técnicos, revisa los logs en SparkedHost
- Verifica que el token esté configurado correctamente
- Asegúrate de que los intents estén activados en Discord Developer Portal