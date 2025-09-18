
# Reconocimiento de Voz Profesional en Python

Este proyecto implementa una aplicación de reconocimiento de voz con una interfaz gráfica moderna usando Tkinter y la librería `speech_recognition`. Permite seleccionar el micrófono, iniciar/detener la escucha, y transcribir comandos hablados en español. El historial de comandos reconocidos se muestra en pantalla.

---

## Estructura del Proyecto

- `prueba1.py`: Código principal de la aplicación con interfaz gráfica y lógica de reconocimiento de voz.
- `README.md`: Documentación detallada del proyecto.

---

## Características

- Interfaz profesional y moderna (colores oscuros, acentos, botones grandes)
- Selección de micrófono disponible en el sistema
- Indicador visual del estado de escucha (círculo de color y texto)
- Transcripción automática de voz a texto (Google Speech API)
- Historial de comandos reconocidos con hora
- Mensajes de depuración en consola para facilitar solución de problemas
- Ejecución de comandos por voz (ejemplo: encender/apagar LED, activar/detener motor)

---

## Requisitos

- Python 3.8 o superior
- Paquetes:
  - `speech_recognition`: Reconocimiento de voz
  - `pyaudio`: Acceso al micrófono
  - `tkinter`: Interfaz gráfica (incluido en la mayoría de instalaciones de Python)
  - `pygame`: Para sonidos opcionales

---

## Instalación

1. Instala las dependencias:
   ```powershell
   pip install speechrecognition pyaudio pygame
   ```
   Si tienes problemas con `pyaudio`, usa:
   ```powershell
   pip install pipwin
   pipwin install pyaudio
   ```
2. Descarga o clona este repositorio.
3. Ejecuta el archivo principal:
   ```powershell
   python prueba1.py
   ```

---

## Uso Paso a Paso

1. **Selecciona el micrófono** en el menú desplegable. Si tienes varios, prueba el que funcione mejor.
2. Haz clic en **"Iniciar Escucha"**. El indicador se pondrá verde y el texto dirá "Escuchando...".
3. **Habla claramente** cerca del micrófono. El sistema escuchará durante unos segundos y procesará lo que digas.
4. El **texto reconocido** aparecerá en la pantalla y se guardará en el historial con la hora.
5. Para **detener la escucha**, haz clic en el botón nuevamente.

---

## Ejemplo de Comandos Reconocidos

Puedes personalizar los comandos en el código. Ejemplos incluidos:

- "encender led" → 💡 LED ENCENDIDO
- "apagar led" → 💡 LED APAGADO
- "activar motor" → ⚙️ MOTOR ACTIVADO
- "detener motor" → ⚙️ MOTOR DETENIDO
- "hola" → 👋 ¡Hola! ¿En qué puedo ayudarte?
- "adiós" o "terminar" → 👋 ¡Hasta luego! (detiene la escucha)

Puedes agregar más comandos en la función `execute_command`.

---

## Explicación del Código

### 1. Interfaz Gráfica (Tkinter)
- Ventana principal con fondo oscuro y acentos de color.
- Menú desplegable para seleccionar micrófono.
- Botón grande para iniciar/detener escucha.
- Indicador visual (círculo de color) y texto de estado.
- Área de texto para mostrar el resultado reconocido.
- Historial de comandos con barra de desplazamiento.

### 2. Lógica de Reconocimiento
- Usa la librería `speech_recognition` para captar audio y transcribirlo usando Google Speech API.
- Ajusta automáticamente el micrófono al ruido ambiental.
- El bucle de escucha corre en un hilo separado para no bloquear la interfaz.
- El texto reconocido se procesa y se muestra en pantalla.
- Si el audio no se entiende, muestra un mensaje de error.

### 3. Ejecución de Comandos
- La función `execute_command` busca palabras clave en el texto reconocido y ejecuta acciones (puedes conectar esto a hardware real si lo deseas).

### 4. Personalización
- Puedes cambiar el idioma de reconocimiento modificando el parámetro `language` en el método `recognize_google` (por defecto: español de España `es-ES`).
- Los colores y estilos de la interfaz se pueden ajustar en la función `setup_ui`.
- Puedes agregar sonidos, animaciones o conectar con hardware (Arduino, etc.) en la función `execute_command`.

---

## Solución de Problemas

- Si no reconoce tu voz:
  - Verifica que el micrófono esté seleccionado y funcione en otras apps.
  - Sube el volumen de entrada del micrófono.
  - Revisa los mensajes de depuración en la consola.
- Si `pyaudio` no se instala, usa `pipwin` como se indica arriba.
- Si el reconocimiento falla, verifica tu conexión a internet (usa Google Speech API).
- Si tienes varios micrófonos, prueba cada uno desde el menú.

---

## Personalización Avanzada

- **Agregar comandos:** Edita la función `execute_command` para añadir nuevas frases y acciones.
- **Cambiar idioma:** Modifica el parámetro `language` en `recognize_google` (ejemplo: `en-US` para inglés).
- **Modificar interfaz:** Cambia colores, fuentes y disposición en la función `setup_ui`.
- **Conectar hardware:** Puedes integrar con Arduino, Raspberry Pi, etc. usando librerías como `pyserial`.

---

## Créditos
- Desarrollado por Juan David Sotelo Rozo
- Basado en la librería [SpeechRecognition](https://pypi.org/project/SpeechRecognition/)

---

## Licencia
Este proyecto es de uso libre para fines educativos y personales.
