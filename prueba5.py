import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageTk
import speech_recognition as sr
import time
import threading
import socket
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

class HandGestureRecognition:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.cap = None
        self.gesture_recognition_active = False
        self.current_gesture = "Ninguno"
        
    def start_camera(self):
        """Iniciar cámara"""
        try:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            return True
        except Exception as e:
            logger.error(f"Error iniciando cámara: {e}")
            return False
            
    def stop_camera(self):
        """Detener cámara"""
        if self.cap:
            self.cap.release()
        self.gesture_recognition_active = False
        
    def get_gesture(self, landmarks):
        """Detectar gestos basados en landmarks de la mano"""
        try:
            # Coordenadas de puntos clave
            thumb_tip = landmarks[self.mp_hands.HandLandmark.THUMB_TIP]
            index_tip = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
            middle_tip = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            ring_tip = landmarks[self.mp_hands.HandLandmark.RING_FINGER_TIP]
            pinky_tip = landmarks[self.mp_hands.HandLandmark.PINKY_TIP]
            
            # Puntos PIP para verificar si los dedos están extendidos
            index_pip = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_PIP]
            middle_pip = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
            ring_pip = landmarks[self.mp_hands.HandLandmark.RING_FINGER_PIP]
            pinky_pip = landmarks[self.mp_hands.HandLandmark.PINKY_PIP]
            thumb_ip = landmarks[self.mp_hands.HandLandmark.THUMB_IP]
            
            # Detectar puño cerrado (STOP)
            fingers_closed = all([
                index_tip.y > index_pip.y,
                middle_tip.y > middle_pip.y,
                ring_tip.y > ring_pip.y,
                pinky_tip.y > pinky_pip.y,
                thumb_tip.y > thumb_ip.y
            ])
            
            # Detectar mano abierta (ARRANCA)
            fingers_open = all([
                index_tip.y < index_pip.y,
                middle_tip.y < middle_pip.y,
                ring_tip.y < ring_pip.y,
                pinky_tip.y < pinky_pip.y,
                thumb_tip.y < thumb_ip.y
            ])
            
            # Detectar palma extendida perfecta(ARRANCA)
            palm_open_perfectly = (
                fingers_open and
                abs(index_tip.x - pinky_tip.x) > 0.15 and  # Dedos separados horizontalmente
                abs(thumb_tip.y - index_tip.y) < 0.05  # Todos los dedos a la misma altura
            )

                        # Detectar dos dedos (índice y medio arriba, otros abajo)
            un_dedo = (
                index_tip.y < index_pip.y and
                middle_tip.y > middle_pip.y and
                ring_tip.y > ring_pip.y and
                pinky_tip.y > pinky_pip.y
            )
            
            
            # Detectar dos dedos (índice y medio arriba, otros abajo)
            dos_dedos = (
                index_tip.y < index_pip.y and
                middle_tip.y < middle_pip.y and
                ring_tip.y > ring_pip.y and
                pinky_tip.y > pinky_pip.y
            )
            
            # Determinar gesto con prioridad
            if palm_open_perfectly:
                return "arranca"
            if un_dedo:
                return "arranca"
            elif dos_dedos:
                return "izquierda"
            elif fingers_closed:
                return "Detiene"
            elif fingers_open:
                return "arranca"
            else:
                return "Desconocido"
                
        except Exception as e:
            logger.error(f"Error detectando gesto: {e}")
            return "Error"
    
    def process_frame(self):
        """Procesar frame de la cámara"""
        if not self.cap or not self.cap.isOpened():
            return None, "Ninguno"
            
        success, image = self.cap.read()
        if not success:
            return None, "Ninguno"
            
        # Convertir BGR a RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.hands.process(image_rgb)
        
        gesture = "Ninguno"
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Dibujar landmarks
                self.mp_drawing.draw_landmarks(
                    image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                # Detectar gesto
                gesture = self.get_gesture(hand_landmarks.landmark)
                
                # Mostrar gesto en el frame
                cv2.putText(image, f"Gesto: {gesture}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return image, gesture

class ModernVoiceGestureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Control Dual Inteligente - Voz y Gestos")
        self.root.geometry("1400x900")
        self.root.configure(bg='#2c3e50')
        
        # Estilo moderno
        self.setup_styles()
        
        # Variables de estado
        self.listening = False
        self.gesture_control = False
        self.recognizer = sr.Recognizer()
        self.esp32_ip = "10.75.36.124"
        self.esp32_port = 1234
        self.wifi_connected = False
        self.socket = None
        
        # Sistema de gestos
        self.gesture_detector = HandGestureRecognition()
        self.current_gesture = "Ninguno"
        self.last_gesture = "Ninguno"
        self.gesture_cooldown = time.time()
        self.fps_counter = 0
        self.fps_time = time.time()
        
        # Control de modo
        self.current_mode = None  # "voice" o "gesture"
        self.main_container = None
        
        # Configurar pantalla inicial de selección
        self.show_mode_selection()
        
        # Mapeo de gestos a comandos
        self.gesture_commands = {
            "Palma Abierta": "PALM_OPEN",
            "Mano Abierta": "LED_ON",
            "Puño": "LED_OFF", 
            "OK": "FREQ_FAST",
            "Paz": "FREQ_SLOW"
        }

    def setup_styles(self):
        """Configurar estilos modernos"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores modernos
        self.colors = {
            'primary': '#3498db',
            'secondary': '#2ecc71', 
            'accent': '#e74c3c',
            'dark_bg': '#2c3e50',
            'darker_bg': '#34495e',
            'light_bg': '#ecf0f1',
            'text_light': '#ffffff',
            'text_dark': '#2c3e50',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c'
        }
        
        # Configurar estilos de widgets
        style.configure('Modern.TFrame', background=self.colors['dark_bg'])
        style.configure('Title.TLabel', 
                       background=self.colors['dark_bg'],
                       foreground=self.colors['text_light'],
                       font=('Arial', 16, 'bold'))
        
        style.configure('Card.TFrame', 
                       background=self.colors['darker_bg'],
                       relief='raised',
                       borderwidth=2)
        
        style.configure('Primary.TButton',
                       background=self.colors['primary'],
                       foreground=self.colors['text_light'],
                       font=('Arial', 10, 'bold'),
                       focuscolor='none')
        
        style.configure('Success.TButton',
                       background=self.colors['success'],
                       foreground=self.colors['text_light'],
                       font=('Arial', 10, 'bold'))
        
        style.configure('Danger.TButton',
                       background=self.colors['danger'], 
                       foreground=self.colors['text_light'],
                       font=('Arial', 10, 'bold'))

    def show_mode_selection(self):
        """Mostrar pantalla de selección de modo"""
        # Limpiar ventana
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Frame principal centrado
        selection_frame = ttk.Frame(self.root, style='Modern.TFrame')
        selection_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=50)
        
        # Título
        title = ttk.Label(selection_frame, 
                         text="🤖 Control Inteligente", 
                         font=('Arial', 32, 'bold'),
                         background=self.colors['dark_bg'],
                         foreground=self.colors['primary'])
        title.pack(pady=30)
        
        subtitle = ttk.Label(selection_frame,
                            text="Elige el tipo de control que deseas utilizar",
                            font=('Arial', 14),
                            background=self.colors['dark_bg'],
                            foreground=self.colors['text_light'])
        subtitle.pack(pady=(0, 50))
        
        # Contenedor de botones
        buttons_frame = ttk.Frame(selection_frame, style='Modern.TFrame')
        buttons_frame.pack(fill=tk.BOTH, expand=True)
        
        # Botón de control por voz
        voice_card = ttk.Frame(buttons_frame, style='Card.TFrame', padding=30)
        voice_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20)
        
        voice_emoji = ttk.Label(voice_card,
                               text="🎤",
                               font=('Arial', 80),
                               background=self.colors['darker_bg'],
                               foreground=self.colors['success'])
        voice_emoji.pack(pady=10)
        
        voice_title = ttk.Label(voice_card,
                               text="Control por Voz",
                               font=('Arial', 18, 'bold'),
                               background=self.colors['darker_bg'],
                               foreground=self.colors['text_light'])
        voice_title.pack(pady=10)
        
        voice_desc = ttk.Label(voice_card,
                              text="Controla tus dispositivos\nhablando comandos\nen español",
                              font=('Arial', 12),
                              background=self.colors['darker_bg'],
                              foreground='#bdc3c7',
                              justify=tk.CENTER)
        voice_desc.pack(pady=20)
        
        voice_btn = ttk.Button(voice_card,
                              text="Usar Control por Voz",
                              command=lambda: self.select_mode("voice"),
                              style='Success.TButton')
        voice_btn.pack(fill=tk.X, pady=10)
        
        # Botón de control por gestos
        gesture_card = ttk.Frame(buttons_frame, style='Card.TFrame', padding=30)
        gesture_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20)
        
        gesture_emoji = ttk.Label(gesture_card,
                                 text="✋",
                                 font=('Arial', 80),
                                 background=self.colors['darker_bg'],
                                 foreground=self.colors['primary'])
        gesture_emoji.pack(pady=10)
        
        gesture_title = ttk.Label(gesture_card,
                                 text="Control por Gestos",
                                 font=('Arial', 18, 'bold'),
                                 background=self.colors['darker_bg'],
                                 foreground=self.colors['text_light'])
        gesture_title.pack(pady=10)
        
        gesture_desc = ttk.Label(gesture_card,
                                text="Controla tus dispositivos\ncon gestos de mano\ndetectados por cámara",
                                font=('Arial', 12),
                                background=self.colors['darker_bg'],
                                foreground='#bdc3c7',
                                justify=tk.CENTER)
        gesture_desc.pack(pady=20)
        
        gesture_btn = ttk.Button(gesture_card,
                                text="Usar Control por Gestos",
                                command=lambda: self.select_mode("gesture"),
                                style='Primary.TButton')
        gesture_btn.pack(fill=tk.X, pady=10)
        
        # Botón de dual (ambos)
        dual_frame = ttk.Frame(selection_frame, style='Modern.TFrame')
        dual_frame.pack(fill=tk.X, pady=(50, 0))
        
        dual_btn = ttk.Button(dual_frame,
                             text="🎤 ✋ Usar Ambos Controles (Dual)",
                             command=lambda: self.select_mode("dual"),
                             style='Primary.TButton')
        dual_btn.pack(fill=tk.X, padx=20)

    def select_mode(self, mode):
        """Seleccionar modo de control"""
        self.current_mode = mode
        
        # Limpiar ventana
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Configurar interfaz según el modo
        if mode == "voice":
            self.setup_ui_voice_only()
            self.root.after(500, self.update_microphone_list_voice)
        elif mode == "gesture":
            self.setup_ui_gesture_only()
        elif mode == "dual":
            self.setup_ui()
            self.root.after(500, self.update_microphone_list)
    
    def setup_ui_voice_only(self):
        """Interfaz solo para control de voz"""
        header_frame = ttk.Frame(self.root, style='Modern.TFrame', height=80)
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        header_frame.pack_propagate(False)
        
        back_btn = ttk.Button(header_frame, text="⬅️ Volver Atrás", command=self.show_mode_selection, style='Danger.TButton')
        back_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        title_label = ttk.Label(header_frame, text="🎤 Control por Voz", style='Title.TLabel', font=('Arial', 20, 'bold'))
        title_label.pack(side=tk.LEFT, pady=20)
        
        main_container = ttk.Frame(self.root, style='Modern.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        voice_card = ttk.Frame(main_container, style='Card.TFrame', padding=30)
        voice_card.pack(fill=tk.BOTH, expand=True, pady=20)
        
        voice_icon = ttk.Label(voice_card, text="🎤", font=('Arial', 100), background=self.colors['darker_bg'], foreground=self.colors['success'])
        voice_icon.pack(pady=20)
        
        voice_title = ttk.Label(voice_card, text="Control de Voz Inteligente", font=('Arial', 24, 'bold'), background=self.colors['darker_bg'], foreground=self.colors['text_light'])
        voice_title.pack(pady=20)
        
        # Selección de micrófono
        mic_frame = ttk.Frame(voice_card, style='Card.TFrame', padding=15)
        mic_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(mic_frame, text="🎤 Micrófono:", font=('Arial', 12, 'bold'), background=self.colors['darker_bg'], foreground=self.colors['text_light']).pack(side=tk.LEFT, padx=10)
        
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(mic_frame, textvariable=self.mic_var, state="readonly", width=40, font=('Arial', 10))
        self.mic_combo.pack(side=tk.LEFT, padx=5)
        
        refresh_btn = ttk.Button(mic_frame, text="🔄 Actualizar", command=self.update_microphone_list_voice, style='Primary.TButton')
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Botón de inicio/parada prominente
        self.voice_btn = ttk.Button(voice_card, text="🎤 Iniciar Escucha", command=self.toggle_voice, style='Success.TButton')
        self.voice_btn.pack(fill=tk.X, pady=15, padx=50)
        
        self.voice_status = ttk.Label(voice_card, text="Estado: Listo para escuchar", font=('Arial', 14), background=self.colors['darker_bg'], foreground=self.colors['secondary'])
        self.voice_status.pack(pady=10)
        
        commands_frame = ttk.Frame(voice_card, style='Card.TFrame', padding=20)
        commands_frame.pack(fill=tk.X, pady=30)
        
        ttk.Label(commands_frame, text="Último comando:", font=('Arial', 12, 'bold'), background=self.colors['darker_bg'], foreground=self.colors['text_light']).pack()
        
        self.voice_command_text = tk.Text(commands_frame, height=4, width=60, font=('Arial', 12), bg=self.colors['darker_bg'], fg=self.colors['success'], relief=tk.FLAT)
        self.voice_command_text.pack(pady=10)
        self.voice_command_text.insert(tk.END, "Esperando comando...")
        
        wifi_section = ttk.LabelFrame(voice_card, text="📡 Configuración de Conexión", padding=15, style='Card.TFrame')
        wifi_section.pack(fill=tk.X, pady=20)
        
        wifi_config_frame = ttk.Frame(wifi_section, style='Card.TFrame')
        wifi_config_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(wifi_config_frame, text="IP:", background=self.colors['darker_bg'], foreground=self.colors['text_light']).pack(side=tk.LEFT)
        
        self.ip_var = tk.StringVar(value=self.esp32_ip)
        ip_entry = ttk.Entry(wifi_config_frame, textvariable=self.ip_var, width=20, font=('Arial', 10))
        ip_entry.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(wifi_config_frame, text="Puerto:", background=self.colors['darker_bg'], foreground=self.colors['text_light']).pack(side=tk.LEFT, padx=(10, 0))
        
        self.port_var = tk.StringVar(value="1234")
        port_entry = ttk.Entry(wifi_config_frame, textvariable=self.port_var, width=8, font=('Arial', 10))
        port_entry.pack(side=tk.LEFT, padx=5)
        
        connect_btn = ttk.Button(wifi_config_frame, text="🔌 Conectar", command=self.connect_to_esp32, style='Primary.TButton')
        connect_btn.pack(side=tk.LEFT, padx=10)
        
        self.wifi_status = ttk.Label(wifi_section, text="🔴 Desconectado", font=('Arial', 12, 'bold'), background=self.colors['darker_bg'], foreground=self.colors['danger'])
        self.wifi_status.pack(pady=10)
        
        log_label = ttk.Label(voice_card, text="📋 Log de Actividad", font=('Arial', 12, 'bold'), background=self.colors['darker_bg'], foreground=self.colors['text_light'])
        log_label.pack(pady=(20, 5))
        
        log_frame = ttk.Frame(voice_card, style='Card.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, height=6, font=('Consolas', 10), bg='#1a1a1a', fg='#00ff00', insertbackground='white', selectbackground='#3498db')
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_ui_gesture_only(self):
        """Interfaz solo para control de gestos"""
        header_frame = ttk.Frame(self.root, style='Modern.TFrame', height=80)
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        header_frame.pack_propagate(False)
        
        back_btn = ttk.Button(header_frame, text="⬅️ Volver Atrás", command=self.show_mode_selection, style='Danger.TButton')
        back_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        title_label = ttk.Label(header_frame, text="✋ Control por Gestos", style='Title.TLabel', font=('Arial', 20, 'bold'))
        title_label.pack(side=tk.LEFT, pady=20)
        
        self.fps_label = ttk.Label(header_frame, text="FPS: --", font=('Arial', 10), background=self.colors['dark_bg'], foreground=self.colors['text_light'])
        self.fps_label.pack(side=tk.RIGHT)
        
        main_container = ttk.Frame(self.root, style='Modern.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        video_card = ttk.Frame(main_container, style='Card.TFrame', padding=15)
        video_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        video_title = ttk.Label(video_card, text="📷 Vista de Cámara", font=('Arial', 14, 'bold'), background=self.colors['darker_bg'], foreground=self.colors['text_light'])
        video_title.pack(pady=10)
        
        self.video_label = ttk.Label(video_card, text="🎥 Iniciando cámara...", font=('Arial', 12), background='black', foreground='white', anchor='center')
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        control_card = ttk.Frame(main_container, style='Card.TFrame', padding=15, width=350)
        control_card.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        control_card.pack_propagate(False)
        
        gesture_title = ttk.Label(control_card, text="Gesto Detectado", font=('Arial', 14, 'bold'), background=self.colors['darker_bg'], foreground=self.colors['text_light'])
        gesture_title.pack(pady=10)
        
        self.gesture_display = ttk.Label(control_card, text="🤚", font=('Arial', 80), background=self.colors['darker_bg'], foreground=self.colors['primary'])
        self.gesture_display.pack(pady=10)
        
        self.gesture_text = ttk.Label(control_card, text="Gesto: Ninguno", font=('Arial', 16, 'bold'), background=self.colors['darker_bg'], foreground=self.colors['text_light'])
        self.gesture_text.pack(pady=5)
        
        self.command_text = ttk.Label(control_card, text="Comando: -", font=('Arial', 12), background=self.colors['darker_bg'], foreground=self.colors['success'])
        self.command_text.pack(pady=5)
        
        self.gesture_btn = ttk.Button(control_card, text="🚀 Iniciar Detección", command=self.toggle_gestures, style='Primary.TButton')
        self.gesture_btn.pack(fill=tk.X, pady=15)
        
        wifi_section = ttk.LabelFrame(control_card, text="📡 Conexión ESP32", padding=10, style='Card.TFrame')
        wifi_section.pack(fill=tk.X, pady=15)
        
        wifi_config = ttk.Frame(wifi_section, style='Card.TFrame')
        wifi_config.pack(fill=tk.X, pady=5)
        
        ttk.Label(wifi_config, text="IP:", background=self.colors['darker_bg'], foreground=self.colors['text_light']).pack(side=tk.LEFT)
        
        self.ip_var = tk.StringVar(value=self.esp32_ip)
        ip_entry = ttk.Entry(wifi_config, textvariable=self.ip_var, width=12, font=('Arial', 9))
        ip_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(wifi_config, text="Puerto:", background=self.colors['darker_bg'], foreground=self.colors['text_light']).pack(side=tk.LEFT)
        
        self.port_var = tk.StringVar(value="1234")
        port_entry = ttk.Entry(wifi_config, textvariable=self.port_var, width=6, font=('Arial', 9))
        port_entry.pack(side=tk.LEFT, padx=5)
        
        connect_btn = ttk.Button(wifi_config, text="Conectar", command=self.connect_to_esp32, style='Primary.TButton')
        connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.wifi_status = ttk.Label(wifi_section, text="🔴 Desconectado", font=('Arial', 10), background=self.colors['darker_bg'], foreground=self.colors['danger'])
        self.wifi_status.pack(pady=5)
        
        log_label = ttk.Label(control_card, text="📋 Actividad", font=('Arial', 12, 'bold'), background=self.colors['darker_bg'], foreground=self.colors['text_light'])
        log_label.pack(pady=(10, 5))
        
        log_frame = ttk.Frame(control_card, style='Card.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, height=8, font=('Consolas', 8), bg='#1a1a1a', fg='#00ff00', insertbackground='white')
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    def setup_ui(self):
        """Configurar interfaz moderna"""
        # Header principal
        header_frame = ttk.Frame(self.root, style='Modern.TFrame', height=80)
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        header_frame.pack_propagate(False)
        
        # Botón atrás
        back_btn = ttk.Button(header_frame,
                             text="⬅️ Volver Atrás",
                             command=self.show_mode_selection,
                             style='Danger.TButton')
        back_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        title_label = ttk.Label(header_frame, 
                               text="🎮 Control Dual Inteligente - Voz + Gestos", 
                               style='Title.TLabel',
                               font=('Arial', 20, 'bold'))
        title_label.pack(side=tk.LEFT, pady=20)
        
        # Status indicator
        self.status_frame = ttk.Frame(header_frame, style='Modern.TFrame')
        self.status_frame.pack(side=tk.RIGHT, pady=20)
        
        self.wifi_status_indicator = self.create_status_indicator("WiFi", "🔴", "Desconectado")
        self.voice_status_indicator = self.create_status_indicator("Voz", "⚫", "Inactivo") 
        self.gesture_status_indicator = self.create_status_indicator("Gestos", "⚫", "Inactivo")
        
        # Contenido principal
        main_container = ttk.Frame(self.root, style='Modern.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Fila superior - Controles y video
        top_row = ttk.Frame(main_container, style='Modern.TFrame')
        top_row.pack(fill=tk.BOTH, expand=True)
        
        # Panel izquierdo - Video
        self.setup_video_panel(top_row)
        
        # Panel derecho - Controles
        self.setup_control_panel(top_row)
        
        # Fila inferior - Logs y información
        bottom_row = ttk.Frame(main_container, style='Modern.TFrame')
        bottom_row.pack(fill=tk.BOTH, expand=True)
        
        self.setup_log_panel(bottom_row)

    def create_status_indicator(self, label, icon, text):
        """Crear indicador de estado"""
        frame = ttk.Frame(self.status_frame, style='Modern.TFrame')
        frame.pack(side=tk.LEFT, padx=10)
        
        icon_label = ttk.Label(frame, text=icon, font=('Arial', 14), 
                              background=self.colors['dark_bg'],
                              foreground=self.colors['text_light'])
        icon_label.pack(side=tk.LEFT)
        
        text_label = ttk.Label(frame, text=f"{label}: {text}", 
                              font=('Arial', 9),
                              background=self.colors['dark_bg'],
                              foreground=self.colors['text_light'])
        text_label.pack(side=tk.LEFT, padx=(5, 0))
        
        return {'frame': frame, 'icon': icon_label, 'text': text_label}

    def setup_video_panel(self, parent):
        """Panel de video moderno"""
        video_card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        video_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Header del card
        video_header = ttk.Frame(video_card, style='Card.TFrame')
        video_header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(video_header, 
                 text="📷 Cámara en Tiempo Real", 
                 font=('Arial', 14, 'bold'),
                 background=self.colors['darker_bg'],
                 foreground=self.colors['text_light']).pack(side=tk.LEFT)
        
        # Contador de FPS
        self.fps_label = ttk.Label(video_header, 
                                  text="FPS: --",
                                  font=('Arial', 10),
                                  background=self.colors['darker_bg'],
                                  foreground=self.colors['text_light'])
        self.fps_label.pack(side=tk.RIGHT)
        
        # Área de video
        video_container = ttk.Frame(video_card, style='Card.TFrame')
        video_container.pack(fill=tk.BOTH, expand=True)
        
        self.video_label = ttk.Label(video_container, 
                                    text="🎥 Iniciando cámara...",
                                    font=('Arial', 12),
                                    background='black',
                                    foreground='white',
                                    anchor='center')
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_control_panel(self, parent):
        """Panel de controles moderno"""
        control_card = ttk.Frame(parent, style='Card.TFrame', padding=15, width=400)
        control_card.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        control_card.pack_propagate(False)
        
        # Gestos
        gesture_section = ttk.LabelFrame(control_card, 
                                       text="✋ Control por Gestos", 
                                       padding=15,
                                       style='Card.TFrame')
        gesture_section.pack(fill=tk.X, pady=(0, 15))
        
        # Estado del gesto actual
        self.gesture_display = ttk.Label(gesture_section,
                                        text="🤚",
                                        font=('Arial', 48),
                                        background=self.colors['darker_bg'],
                                        foreground=self.colors['primary'])
        self.gesture_display.pack(pady=10)
        
        self.gesture_text = ttk.Label(gesture_section,
                                     text="Gesto: Ninguno",
                                     font=('Arial', 16, 'bold'),
                                     background=self.colors['darker_bg'],
                                     foreground=self.colors['text_light'])
        self.gesture_text.pack(pady=5)
        
        self.command_text = ttk.Label(gesture_section,
                                     text="Comando: -",
                                     font=('Arial', 12),
                                     background=self.colors['darker_bg'],
                                     foreground=self.colors['success'])
        self.command_text.pack(pady=5)
        
        self.gesture_btn = ttk.Button(gesture_section,
                                     text="🚀 Iniciar Detección de Gestos",
                                     command=self.toggle_gestures,
                                     style='Primary.TButton')
        self.gesture_btn.pack(fill=tk.X, pady=10)
        
        # Voz
        voice_section = ttk.LabelFrame(control_card,
                                     text="🎤 Control por Voz", 
                                     padding=15,
                                     style='Card.TFrame')
        voice_section.pack(fill=tk.X, pady=(0, 15))
        
        self.voice_status = ttk.Label(voice_section,
                                     text="🔇 Micrófono listo",
                                     font=('Arial', 12),
                                     background=self.colors['darker_bg'],
                                     foreground=self.colors['text_light'])
        self.voice_status.pack(pady=10)
        
        self.voice_btn = ttk.Button(voice_section,
                                   text="🎤 Iniciar Reconocimiento de Voz", 
                                   command=self.toggle_voice,
                                   style='Success.TButton')
        self.voice_btn.pack(fill=tk.X, pady=5)
        
        # WiFi
        wifi_section = ttk.LabelFrame(control_card,
                                    text="📡 Conexión ESP32",
                                    padding=15,
                                    style='Card.TFrame')
        wifi_section.pack(fill=tk.X)
        
        wifi_config_frame = ttk.Frame(wifi_section, style='Card.TFrame')
        wifi_config_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(wifi_config_frame, 
                 text="IP:", 
                 background=self.colors['darker_bg'],
                 foreground=self.colors['text_light']).pack(side=tk.LEFT)
        
        self.ip_var = tk.StringVar(value=self.esp32_ip)
        ip_entry = ttk.Entry(wifi_config_frame, 
                            textvariable=self.ip_var, 
                            width=15,
                            font=('Arial', 10))
        ip_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(wifi_config_frame, 
                 text="Puerto:",
                 background=self.colors['darker_bg'],
                 foreground=self.colors['text_light']).pack(side=tk.LEFT, padx=(10,0))
        
        self.port_var = tk.StringVar(value="1234")
        port_entry = ttk.Entry(wifi_config_frame, 
                              textvariable=self.port_var, 
                              width=8,
                              font=('Arial', 10))
        port_entry.pack(side=tk.LEFT, padx=5)
        
        connect_btn = ttk.Button(wifi_config_frame,
                               text="🔌 Conectar",
                               command=self.connect_to_esp32,
                               style='Primary.TButton')
        connect_btn.pack(side=tk.LEFT, padx=10)
        
        test_btn = ttk.Button(wifi_section,
                            text="🧪 Test de Comandos",
                            command=self.test_connection_manual,
                            style='Success.TButton')
        test_btn.pack(fill=tk.X, pady=5)

    def setup_log_panel(self, parent):
        """Panel de logs moderno"""
        log_card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        log_card.pack(fill=tk.BOTH, expand=True)
        
        # Header del log
        log_header = ttk.Frame(log_card, style='Card.TFrame')
        log_header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(log_header, 
                 text="📋 Log de Actividad en Tiempo Real",
                 font=('Arial', 14, 'bold'),
                 background=self.colors['darker_bg'],
                 foreground=self.colors['text_light']).pack(side=tk.LEFT)
        
        # Botones de control del log
        log_controls = ttk.Frame(log_header, style='Card.TFrame')
        log_controls.pack(side=tk.RIGHT)
        
        ttk.Button(log_controls, 
                  text="🧹 Limpiar",
                  command=self.clear_logs,
                  style='Primary.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(log_controls,
                  text="💾 Exportar", 
                  command=self.export_logs,
                  style='Success.TButton').pack(side=tk.LEFT, padx=5)
        
        # Área de texto del log
        log_frame = ttk.Frame(log_card, style='Card.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, 
                               height=8, 
                               font=('Consolas', 10),
                               bg='#1a1a1a',
                               fg='#00ff00',
                               insertbackground='white',
                               selectbackground='#3498db')
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def update_status_indicators(self):
        """Actualizar indicadores de estado"""
        if hasattr(self, 'wifi_status_indicator'):
            wifi_icon = "🟢" if self.wifi_connected else "🔴"
            wifi_text = "Conectado" if self.wifi_connected else "Desconectado"
            self.wifi_status_indicator['icon'].config(text=wifi_icon)
            self.wifi_status_indicator['text'].config(text=f"WiFi: {wifi_text}")
        
        if hasattr(self, 'wifi_status'):
            wifi_icon = "🟢" if self.wifi_connected else "🔴"
            wifi_text = "Conectado" if self.wifi_connected else "Desconectado"
            self.wifi_status.config(text=f"{wifi_icon} {wifi_text}")
        
        if hasattr(self, 'voice_status_indicator'):
            voice_icon = "🎤" if self.listening else "🔇"
            voice_text = "Escuchando" if self.listening else "Inactivo"
            self.voice_status_indicator['icon'].config(text=voice_icon)
            self.voice_status_indicator['text'].config(text=f"Voz: {voice_text}")
        
        if hasattr(self, 'gesture_status_indicator'):
            gesture_icon = "👁️" if self.gesture_control else "👁️‍🗨️"
            gesture_text = "Activo" if self.gesture_control else "Inactivo"
            self.gesture_status_indicator['icon'].config(text=gesture_icon)
            self.gesture_status_indicator['text'].config(text=f"Gestos: {gesture_text}")

    def log_message(self, message, message_type="info"):
        """Añadir mensaje al log con colores"""
        timestamp = time.strftime("%H:%M:%S")
        
        # Colores según el tipo de mensaje
        colors = {
            'info': '#3498db',
            'success': '#2ecc71',
            'warning': '#f39c12',
            'error': '#e74c3c',
            'gesture': '#9b59b6',
            'voice': '#1abc9c'
        }
        
        color = colors.get(message_type, '#3498db')
        emoji = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'gesture': '✋',
            'voice': '🎤'
        }.get(message_type, '📝')
        
        formatted_message = f"[{timestamp}] {emoji} {message}"
        
        # Insertar con color
        self.log_text.insert(tk.END, formatted_message + "\n")
        self.log_text.see(tk.END)
        
        # Limitar el número de líneas
        lines = int(self.log_text.index('end-1c').split('.')[0])
        if lines > 1000:
            self.log_text.delete(1.0, 2.0)
        
        logger.info(message)

    def clear_logs(self):
        """Limpiar el log"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("Log limpiado", "info")

    def export_logs(self):
        """Exportar logs a archivo"""
        try:
            filename = f"log_control_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            self.log_message(f"Log exportado como {filename}", "success")
        except Exception as e:
            self.log_message(f"Error exportando log: {e}", "error")

    def update_microphone_list(self):
        """Actualizar lista de micrófonos"""
        try:
            mics = sr.Microphone.list_microphone_names()
            self.log_message(f"Micrófonos detectados: {len(mics)}", "info")
        except Exception as e:
            self.log_message(f"Error cargando micrófonos: {e}", "error")
    
    def update_microphone_list_voice(self):
        """Actualizar lista de micrófonos en modo voz"""
        try:
            mics = sr.Microphone.list_microphone_names()
            self.mic_combo['values'] = mics
            if mics:
                self.mic_combo.current(0)
                self.log_message(f"✅ {len(mics)} micrófono(s) detectado(s)", "voice")
            else:
                self.log_message("❌ No se encontraron micrófonos", "error")
        except Exception as e:
            self.log_message(f"Error cargando micrófonos: {e}", "error")

    def connect_to_esp32(self):
        """Conectar al ESP32"""
        try:
            self.log_message(f"Conectando a {self.ip_var.get()}:{self.port_var.get()}", "info")
            
            if self.socket:
                self.socket.close()
                
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip_var.get(), int(self.port_var.get())))
            
            self.wifi_connected = True
            self.update_status_indicators()
            self.log_message("✅ Conexión WiFi establecida con ESP32", "success")
            
        except Exception as e:
            self.wifi_connected = False
            self.update_status_indicators()
            self.log_message(f"❌ Error de conexión: {e}", "error")

    def send_to_esp32(self, command):
        """Enviar comando al ESP32"""
        if not self.wifi_connected:
            self.log_message("No hay conexión WiFi activa", "warning")
            return False
            
        try:
            message = json.dumps({
                "command": command,
                "timestamp": time.time(),
                "type": "control"
            })
            
            self.log_message(f"Enviando comando: {command}", "info")
            self.socket.sendall(message.encode() + b'\n')
            
            try:
                response = self.socket.recv(1024).decode().strip()
                if response:
                    self.log_message(f"Respuesta del ESP32: {response}", "success")
            except socket.timeout:
                self.log_message("El ESP32 no respondió (timeout)", "warning")
                
            return True
            
        except Exception as e:
            self.log_message(f"Error enviando comando: {e}", "error")
            self.wifi_connected = False
            self.update_status_indicators()
            return False

    def toggle_voice(self):
        """Alternar control por voz"""
        if not self.listening:
            self.start_voice_listening()
        else:
            self.stop_voice_listening()

    def start_voice_listening(self):
        """Iniciar escucha por voz"""
        if not self.mic_combo.get():
            messagebox.showwarning("Advertencia", "Por favor selecciona un micrófono")
            return
        
        self.listening = True
        self.voice_btn.config(text="⏹️ Detener Voz", style='Danger.TButton')
        self.voice_status.config(text="🎤 Escuchando...")
        self.update_status_indicators()
        self.log_message("Modo voz activado - Habla ahora", "voice")
        
        thread = threading.Thread(target=self.voice_listen_loop, daemon=True)
        thread.start()

    def stop_voice_listening(self):
        """Detener escucha por voz"""
        self.listening = False
        self.voice_btn.config(text="🎤 Iniciar Voz", style='Success.TButton')
        self.voice_status.config(text="🔇 Micrófono inactivo")
        self.update_status_indicators()
        self.log_message("Modo voz desactivado", "voice")

    def voice_listen_loop(self):
        """Bucle de escucha por voz"""
        try:
            mic_index = self.mic_combo.current()
            with sr.Microphone(device_index=mic_index) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                while self.listening:
                    try:
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                        text = self.recognizer.recognize_google(audio, language='es-ES')
                        self.log_message(f"Voz reconocida: {text}", "voice")
                        self.root.after(0, lambda t=text: self.process_voice_command(t))
                        
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        self.log_message("No se entendió el audio", "warning")
                    except Exception as e:
                        if self.listening:
                            self.log_message(f"Error en reconocimiento: {e}", "error")
        except Exception as e:
            self.log_message(f"Error al acceder al micrófono: {e}", "error")
            self.listening = False
            self.root.after(0, self.stop_voice_listening)

    def toggle_gestures(self):
        """Alternar control por gestos"""
        if not self.gesture_control:
            self.start_gesture_control()
        else:
            self.stop_gesture_control()

    def start_gesture_control(self):
        """Iniciar control por gestos"""
        if not self.gesture_detector.start_camera():
            messagebox.showerror("Error", "No se pudo iniciar la cámara")
            return
            
        self.gesture_control = True
        self.gesture_btn.config(text="⏹️ Detener Gestos", style='Danger.TButton')
        self.update_status_indicators()
        self.log_message("Control por gestos activado", "gesture")
        
        # Iniciar bucle de procesamiento de video
        self.process_video()

    def stop_gesture_control(self):
        """Detener control por gestos"""
        self.gesture_control = False
        self.gesture_btn.config(text="🚀 Iniciar Gestos", style='Primary.TButton')
        self.gesture_detector.stop_camera()
        self.video_label.config(image='', text="🎥 Cámara detenida")
        self.update_status_indicators()
        self.log_message("Control por gestos desactivado", "gesture")

    def process_video(self):
        """Procesar video en tiempo real"""
        if not self.gesture_control:
            return
            
        # Calcular FPS
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.fps_time >= 1.0:
            fps = self.fps_counter
            self.fps_counter = 0
            self.fps_time = current_time
            self.fps_label.config(text=f"FPS: {fps}")
            
        frame, gesture = self.gesture_detector.process_frame()
        
        if frame is not None:
            # Convertir frame para tkinter
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(image)
            image = ImageTk.PhotoImage(image)
            
            self.video_label.configure(image=image)
            self.video_label.image = image
            
            # Procesar gesto
            self.process_gesture(gesture)
        
        # Continuar el bucle
        self.root.after(10, self.process_video)

    def process_gesture(self, gesture):
        """Procesar gesto detectado con mejoras visuales"""
        if gesture != self.last_gesture and gesture != "Ninguno":
            self.current_gesture = gesture
            self.last_gesture = gesture
            
            # Actualizar interfaz con emojis y colores
            gesture_emojis = {
                "Palma Abierta": "🖐️",
                "Mano Abierta": "✋",
                "Puño": "✊",
                "OK": "👌", 
                "Paz": "✌️",
                "Desconocido": "❓"
            }
            
            emoji = gesture_emojis.get(gesture, "❓")
            self.gesture_display.config(text=emoji)
            self.gesture_text.config(text=f"Gesto: {gesture}")
            
            # Verificar si es un comando conocido
            if gesture in self.gesture_commands:
                command = self.gesture_commands[gesture]
                self.command_text.config(text=f"Comando: {command}")
                self.log_message(f"Gesto '{gesture}' detectado → {command}", "gesture")
                
                # Efecto visual temporal
                self.flash_gesture_display()
                
                # Enviar comando después de un breve cooldown
                current_time = time.time()
                if current_time - self.gesture_cooldown > 2.0:
                    if self.send_to_esp32(command):
                        self.log_message(f"✅ Comando enviado: {command}", "success")
                    self.gesture_cooldown = current_time
            else:
                self.command_text.config(text="Comando: No asignado")
                self.log_message(f"Gesto '{gesture}' no tiene comando asignado", "warning")

    def flash_gesture_display(self):
        """Efecto visual al detectar gesto"""
        original_color = self.colors['primary']
        self.gesture_display.config(foreground=self.colors['success'])
        self.root.after(500, lambda: self.gesture_display.config(foreground=original_color))

    def process_voice_command(self, text):
        """Procesar comando de voz"""
        self.log_message(f"Procesando comando de voz: {text}", "voice")
        
        # Actualizar el campo de texto de comando en voz
        if hasattr(self, 'voice_command_text'):
            self.voice_command_text.config(state=tk.NORMAL)
            self.voice_command_text.delete(1.0, tk.END)
            self.voice_command_text.insert(tk.END, text)
            self.voice_command_text.config(state=tk.DISABLED)
        
        text_lower = text.lower()
        command = None
        
        # Mapeo de comandos de voz
        voice_commands = {
            "encender led": "LED_ON",
            "apagar led": "LED_OFF",
            "frecuencia rápida": "FREQ_FAST",
            "frecuencia lenta": "FREQ_SLOW",
            "prender led": "LED_ON",
            "activar led": "LED_ON"
        }
        
        for voice_cmd, esp_cmd in voice_commands.items():
            if voice_cmd in text_lower:
                command = esp_cmd
                break
                
        if command:
            if self.send_to_esp32(command):
                self.log_message(f"✅ Comando de voz ejecutado: {command}", "success")
        else:
            self.log_message("❌ Comando de voz no reconocido", "warning")

    def test_connection_manual(self):
        """Test manual de conexión"""
        self.log_message("Iniciando test manual de conexión...", "info")
        self.connect_to_esp32()
        
        if self.wifi_connected:
            test_commands = ["LED_ON", "LED_OFF"]
            for cmd in test_commands:
                self.log_message(f"Enviando comando de test: {cmd}", "info")
                self.send_to_esp32(cmd)
                time.sleep(1)

    def on_closing(self):
        """Manejar cierre de la aplicación"""
        self.stop_voice_listening()
        self.stop_gesture_control()
        if self.socket:
            self.socket.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ModernVoiceGestureApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()

