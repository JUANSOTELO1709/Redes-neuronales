import speech_recognition as sr
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import socket
import json
import logging
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageTk

# Configurar logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
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
            
            wrist = landmarks[self.mp_hands.HandLandmark.WRIST]
            
            # Detectar puño cerrado
            fingers_closed = all([
                index_tip.y < landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y,
                middle_tip.y < landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y,
                ring_tip.y < landmarks[self.mp_hands.HandLandmark.RING_FINGER_PIP].y,
                pinky_tip.y < landmarks[self.mp_hands.HandLandmark.PINKY_FINGER_PIP].y
            ])
            
            # Detectar mano abierta
            fingers_open = all([
                index_tip.y > landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y,
                middle_tip.y > landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y,
                ring_tip.y > landmarks[self.mp_hands.HandLandmark.RING_FINGER_PIP].y,
                pinky_tip.y > landmarks[self.mp_hands.HandLandmark.PINKY_FINGER_PIP].y
            ])
            
            # Detectar señal de OK (pulgar e índice juntos)
            thumb_index_distance = np.sqrt(
                (thumb_tip.x - index_tip.x)**2 + 
                (thumb_tip.y - index_tip.y)**2
            )
            
            # Detectar paz y amor (índice y medio arriba, otros abajo)
            peace_sign = (
                index_tip.y < landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_PIP].y and
                middle_tip.y < landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y and
                ring_tip.y > landmarks[self.mp_hands.HandLandmark.RING_FINGER_PIP].y and
                pinky_tip.y > landmarks[self.mp_hands.HandLandmark.PINKY_FINGER_PIP].y
            )
            
            # Determinar gesto
            if thumb_index_distance < 0.05:
                return "OK"
            elif peace_sign:
                return "Paz"
            elif fingers_closed:
                return "Puño"
            elif fingers_open:
                return "Mano Abierta"
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

class DualControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control Dual - Voz y Gestos para ESP32")
        self.root.geometry("1200x800")
        
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
        
        # Configurar interfaz
        self.setup_ui()
        self.update_microphone_list()
        
        # Mapeo de gestos a comandos
        self.gesture_commands = {
            "Mano Abierta": "LED_ON",
            "Puño": "LED_OFF",
            "OK": "FREQ_FAST",
            "Paz": "FREQ_SLOW"
        }
        
    def setup_ui(self):
        # Frame principal con pestañas
        self.tab_control = ttk.Notebook(self.root)
        
        # Pestaña de Control Dual
        self.dual_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.dual_tab, text="🎤 Control Dual")
        
        # Pestaña de Configuración
        self.config_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.config_tab, text="⚙️ Configuración")
        
        self.tab_control.pack(expand=1, fill="both")
        
        self.setup_dual_tab()
        self.setup_config_tab()
        
    def setup_dual_tab(self):
        """Configurar pestaña de control dual"""
        # Frame superior para controles
        control_frame = ttk.Frame(self.dual_tab, padding="10")
        control_frame.pack(fill=tk.X)
        
        # Botones de control
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(pady=10)
        
        self.voice_btn = ttk.Button(btn_frame, text="🎤 Iniciar Voz", 
                                   command=self.toggle_voice, width=15)
        self.voice_btn.pack(side=tk.LEFT, padx=5)
        
        self.gesture_btn = ttk.Button(btn_frame, text="✋ Iniciar Gestos", 
                                     command=self.toggle_gestures, width=15)
        self.gesture_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🔧 Test Conexión", 
                  command=self.test_connection_manual).pack(side=tk.LEFT, padx=5)
        
        # Frame para video y resultados
        content_frame = ttk.Frame(self.dual_tab)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel izquierdo - Video
        left_frame = ttk.LabelFrame(content_frame, text="Cámara en Tiempo Real", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.video_label = ttk.Label(left_frame, text="Cámara no iniciada", 
                                   background="black", foreground="white")
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Panel derecho - Información
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)
        
        # Estado de gestos
        gesture_frame = ttk.LabelFrame(right_frame, text="Estado de Gestos", padding="10")
        gesture_frame.pack(fill=tk.X, pady=5)
        
        self.gesture_status = ttk.Label(gesture_frame, text="Gesto: Ninguno", 
                                       font=("Arial", 14, "bold"))
        self.gesture_status.pack(pady=5)
        
        self.gesture_command = ttk.Label(gesture_frame, text="Comando: -", 
                                        font=("Arial", 12))
        self.gesture_command.pack(pady=5)
        
        # Log de actividad
        log_frame = ttk.LabelFrame(right_frame, text="Log de Actividad", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=15, width=50, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_config_tab(self):
        """Configurar pestaña de configuración"""
        main_frame = ttk.Frame(self.config_tab, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configuración WiFi
        wifi_frame = ttk.LabelFrame(main_frame, text="Configuración WiFi ESP32", padding="10")
        wifi_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(wifi_frame, text="IP del ESP32:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ip_var = tk.StringVar(value=self.esp32_ip)
        ttk.Entry(wifi_frame, textvariable=self.ip_var, width=15).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(wifi_frame, text="Puerto:").grid(row=0, column=2, sticky=tk.W, pady=5)
        self.port_var = tk.StringVar(value="1234")
        ttk.Entry(wifi_frame, textvariable=self.port_var, width=8).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Button(wifi_frame, text="Conectar", command=self.connect_to_esp32).grid(row=0, column=4, padx=5, pady=5)
        
        self.wifi_status = ttk.Label(wifi_frame, text="Desconectado", foreground="red")
        self.wifi_status.grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=5)
        
        # Configuración de micrófono
        mic_frame = ttk.LabelFrame(main_frame, text="Configuración de Micrófono", padding="10")
        mic_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(mic_frame, text="Micrófono:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(mic_frame, textvariable=self.mic_var, state="readonly", width=40)
        self.mic_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(mic_frame, text="🔄", width=3, command=self.update_microphone_list).grid(row=0, column=2, padx=5, pady=5)
        
        # Configuración de gestos
        gesture_config_frame = ttk.LabelFrame(main_frame, text="Configuración de Gestos", padding="10")
        gesture_config_frame.pack(fill=tk.X, pady=10)
        
        # Tabla de gestos
        gestures = [
            ("✋ Mano Abierta", "LED_ON - Encender LED"),
            ("✊ Puño Cerrado", "LED_OFF - Apagar LED"),
            ("👌 Señal OK", "FREQ_FAST - Frecuencia Rápida"),
            ("✌️ Señal de Paz", "FREQ_SLOW - Frecuencia Lenta")
        ]
        
        for i, (gesto, comando) in enumerate(gestures):
            ttk.Label(gesture_config_frame, text=gesto, font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=2)
            ttk.Label(gesture_config_frame, text=comando, font=("Arial", 9)).grid(row=i, column=1, sticky=tk.W, padx=10, pady=2)
        
        # Área de diagnóstico
        diag_frame = ttk.LabelFrame(main_frame, text="Diagnóstico", padding="10")
        diag_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.diag_text = tk.Text(diag_frame, height=8, font=("Consolas", 9))
        scrollbar_diag = ttk.Scrollbar(diag_frame, orient=tk.VERTICAL, command=self.diag_text.yview)
        self.diag_text.configure(yscrollcommand=scrollbar_diag.set)
        
        self.diag_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_diag.pack(side=tk.RIGHT, fill=tk.Y)

    def log_message(self, message):
        """Añadir mensaje al log"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_text.insert(tk.END, formatted_message + "\n")
        self.log_text.see(tk.END)
        self.diag_text.insert(tk.END, formatted_message + "\n")
        self.diag_text.see(tk.END)
        logger.info(message)

    def update_microphone_list(self):
        """Actualizar lista de micrófonos"""
        try:
            mics = sr.Microphone.list_microphone_names()
            self.mic_combo['values'] = mics
            if mics:
                self.mic_combo.current(0)
                self.log_message(f"Micrófonos detectados: {len(mics)}")
        except Exception as e:
            self.log_message(f"Error cargando micrófonos: {e}")

    def connect_to_esp32(self):
        """Conectar al ESP32"""
        try:
            self.log_message(f"Conectando a {self.ip_var.get()}:{self.port_var.get()}")
            
            if self.socket:
                self.socket.close()
                
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip_var.get(), int(self.port_var.get())))
            
            self.wifi_connected = True
            self.wifi_status.config(text="Conectado", foreground="green")
            self.log_message("✅ Conexión WiFi establecida")
            
        except Exception as e:
            self.wifi_connected = False
            self.wifi_status.config(text=f"Error: {str(e)}", foreground="red")
            self.log_message(f"❌ Error de conexión: {e}")

    def send_to_esp32(self, command):
        """Enviar comando al ESP32"""
        if not self.wifi_connected:
            self.log_message("No hay conexión WiFi activa")
            return False
            
        try:
            message = json.dumps({
                "command": command,
                "timestamp": time.time(),
                "type": "control"
            })
            
            self.log_message(f"Enviando: {message}")
            self.socket.sendall(message.encode() + b'\n')
            
            try:
                response = self.socket.recv(1024).decode().strip()
                if response:
                    self.log_message(f"Respuesta ESP32: {response}")
            except socket.timeout:
                self.log_message("El ESP32 no respondió (timeout)")
                
            return True
            
        except Exception as e:
            self.log_message(f"Error enviando comando: {e}")
            self.wifi_connected = False
            return False

    def toggle_voice(self):
        """Alternar control por voz"""
        if not self.listening:
            self.start_voice_listening()
        else:
            self.stop_voice_listening()

    def start_voice_listening(self):
        """Iniciar escucha por voz"""
        self.listening = True
        self.voice_btn.config(text="⏹️ Detener Voz")
        self.log_message("Modo voz activado")
        
        thread = threading.Thread(target=self.voice_listen_loop, daemon=True)
        thread.start()

    def stop_voice_listening(self):
        """Detener escucha por voz"""
        self.listening = False
        self.voice_btn.config(text="🎤 Iniciar Voz")
        self.log_message("Modo voz desactivado")

    def voice_listen_loop(self):
        """Bucle de escucha por voz"""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
            while self.listening:
                try:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                    text = self.recognizer.recognize_google(audio, language='es-ES')
                    self.log_message(f"Voz reconocida: {text}")
                    self.root.after(0, lambda t=text: self.process_voice_command(t))
                    
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self.log_message("No se entendió el audio")
                except Exception as e:
                    self.log_message(f"Error en reconocimiento: {e}")

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
        self.gesture_btn.config(text="⏹️ Detener Gestos")
        self.log_message("Control por gestos activado")
        
        # Iniciar bucle de procesamiento de video
        self.process_video()

    def stop_gesture_control(self):
        """Detener control por gestos"""
        self.gesture_control = False
        self.gesture_btn.config(text="✋ Iniciar Gestos")
        self.gesture_detector.stop_camera()
        self.video_label.config(image='', text="Cámara detenida")
        self.log_message("Control por gestos desactivado")

    def process_video(self):
        """Procesar video en tiempo real"""
        if not self.gesture_control:
            return
            
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
        """Procesar gesto detectado"""
        if gesture != self.last_gesture and gesture != "Ninguno":
            self.current_gesture = gesture
            self.last_gesture = gesture
            
            # Actualizar interfaz
            self.gesture_status.config(text=f"Gesto: {gesture}")
            
            # Verificar si es un comando conocido
            if gesture in self.gesture_commands:
                command = self.gesture_commands[gesture]
                self.gesture_command.config(text=f"Comando: {command}")
                self.log_message(f"Gesto '{gesture}' detectado -> {command}")
                
                # Enviar comando después de un breve cooldown
                current_time = time.time()
                if current_time - self.gesture_cooldown > 2.0:  # 2 segundos de cooldown
                    self.send_to_esp32(command)
                    self.gesture_cooldown = current_time
            else:
                self.gesture_command.config(text="Comando: No asignado")
                self.log_message(f"Gesto '{gesture}' no tiene comando asignado")

    def process_voice_command(self, text):
        """Procesar comando de voz"""
        self.log_message(f"Procesando comando de voz: {text}")
        
        text_lower = text.lower()
        command = None
        
        # Mapeo de comandos de voz
        voice_commands = {
            "encender led": "LED_ON",
            "apagar led": "LED_OFF",
            "frecuencia rápida": "FREQ_FAST",
            "frecuencia lenta": "FREQ_SLOW"
        }
        
        for voice_cmd, esp_cmd in voice_commands.items():
            if voice_cmd in text_lower:
                command = esp_cmd
                break
                
        if command:
            self.send_to_esp32(command)
            self.log_message(f"✅ Comando de voz ejecutado: {command}")
        else:
            self.log_message("❌ Comando de voz no reconocido")

    def test_connection_manual(self):
        """Test manual de conexión"""
        self.log_message("Iniciando test manual de conexión...")
        self.connect_to_esp32()
        
        if self.wifi_connected:
            test_commands = ["LED_ON", "LED_OFF"]
            for cmd in test_commands:
                self.log_message(f"Enviando comando de test: {cmd}")
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
    app = DualControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()