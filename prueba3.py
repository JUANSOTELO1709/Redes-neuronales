import speech_recognition as sr
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import socket
import json
import logging

# Configurar logging para depuración
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

class VoiceRecognitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Diagnóstico - Control por Voz ESP32")
        self.root.geometry("900x700")
        
        # Variables de estado
        self.listening = False
        self.recognizer = sr.Recognizer()
        self.esp32_ip = "10.75.36.124"  # Cambia por la IP real de tu ESP32
        self.esp32_port = 1234
        self.wifi_connected = False
        self.socket = None
        
        # Configurar interfaz
        self.setup_ui()
        self.update_microphone_list()
        
        # Botón para test de conexión manual
        ttk.Button(self.root, text="🔧 Test de Conexión Manual", 
                  command=self.test_connection_manual).pack(pady=10)
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Área de diagnóstico
        diag_frame = ttk.LabelFrame(main_frame, text="Diagnóstico", padding="10")
        diag_frame.pack(fill=tk.X, pady=10)
        
        self.diag_text = tk.Text(diag_frame, height=10, width=80, font=("Consolas", 9))
        self.diag_text.pack(fill=tk.X)
        self.diag_text.insert(tk.END, "Sistema de diagnóstico iniciado...\n")
        
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
        
        # Botones de control
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        self.toggle_btn = ttk.Button(btn_frame, text="🎤 Iniciar Escucha", 
                                    command=self.toggle_listening, width=20, state="disabled")
        self.toggle_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="🔊 Test de Voz", command=self.test_voice).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📡 Test de WiFi", command=self.test_wifi).pack(side=tk.LEFT, padx=5)
        
        # Área de resultados
        result_frame = ttk.LabelFrame(main_frame, text="Resultados", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.result_text = tk.Text(result_frame, height=8, font=("Arial", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
    def log_diagnostic(self, message):
        """Añadir mensaje al área de diagnóstico"""
        timestamp = time.strftime("%H:%M:%S")
        self.diag_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.diag_text.see(tk.END)
        logger.info(message)
        
    def update_microphone_list(self):
        """Actualizar lista de micrófonos"""
        try:
            mics = sr.Microphone.list_microphone_names()
            self.mic_combo['values'] = mics
            if mics:
                self.mic_combo.current(0)
                self.log_diagnostic(f"Micrófonos detectados: {len(mics)}")
            else:
                self.log_diagnostic("No se encontraron micrófonos")
        except Exception as e:
            self.log_diagnostic(f"Error cargando micrófonos: {e}")
            
    def connect_to_esp32(self):
        """Conectar al ESP32"""
        try:
            self.log_diagnostic(f"Intentando conectar a {self.ip_var.get()}:{self.port_var.get()}")
            
            # Cerrar conexión anterior si existe
            if self.socket:
                self.socket.close()
                
            # Crear nuevo socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            
            # Intentar conexión
            self.socket.connect((self.ip_var.get(), int(self.port_var.get())))
            
            self.wifi_connected = True
            self.wifi_status.config(text="Conectado", foreground="green")
            self.toggle_btn.config(state="normal")
            self.log_diagnostic("✅ Conexión WiFi establecida con ESP32")
            
        except Exception as e:
            self.wifi_connected = False
            self.wifi_status.config(text=f"Error: {str(e)}", foreground="red")
            self.log_diagnostic(f"❌ Error de conexión: {e}")
            
    def send_to_esp32(self, command):
        """Enviar comando al ESP32"""
        if not self.wifi_connected:
            self.log_diagnostic("No hay conexión WiFi activa")
            return False
            
        try:
            # Crear mensaje
            message = json.dumps({
                "command": command,
                "timestamp": time.time(),
                "type": "control"
            })
            
            self.log_diagnostic(f"Enviando: {message}")
            
            # Enviar comando
            self.socket.sendall(message.encode() + b'\n')
            
            # Intentar recibir respuesta
            try:
                response = self.socket.recv(1024).decode().strip()
                if response:
                    self.log_diagnostic(f"Respuesta del ESP32: {response}")
                    self.result_text.insert(tk.END, f"ESP32: {response}\n")
            except socket.timeout:
                self.log_diagnostic("El ESP32 no respondió (timeout)")
            except Exception as e:
                self.log_diagnostic(f"Error recibiendo respuesta: {e}")
                
            return True
            
        except Exception as e:
            self.log_diagnostic(f"Error enviando comando: {e}")
            self.wifi_connected = False
            return False
            
    def test_connection_manual(self):
        """Test manual de conexión"""
        self.log_diagnostic("Iniciando test manual de conexión...")
        self.connect_to_esp32()
        
        if self.wifi_connected:
            # Test de comandos manuales
            test_commands = ["LED_ON", "LED_OFF", "FREQ:1", "FREQ:2"]
            for cmd in test_commands:
                self.log_diagnostic(f"Enviando comando de test: {cmd}")
                self.send_to_esp32(cmd)
                time.sleep(1)
                
    def test_voice(self):
        """Test de reconocimiento de voz"""
        self.log_diagnostic("Iniciando test de voz...")
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.log_diagnostic("Escuchando... Habla ahora")
                
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio, language='es-ES')
                
                self.log_diagnostic(f"Voz reconocida: {text}")
                self.result_text.insert(tk.END, f"Voz: {text}\n")
                self.process_voice_command(text)
                
        except Exception as e:
            self.log_diagnostic(f"Error en test de voz: {e}")
            
    def test_wifi(self):
        """Test de conexión WiFi"""
        self.log_diagnostic("Testeando conexión WiFi...")
        self.connect_to_esp32()
        
    def toggle_listening(self):
        """Alternar escucha"""
        if not self.listening:
            self.start_listening()
        else:
            self.stop_listening()
            
    def start_listening(self):
        """Iniciar escucha continua"""
        self.listening = True
        self.toggle_btn.config(text="⏹️ Detener Escucha")
        self.log_diagnostic("Modo escucha activado")
        
        # Hilo para escucha continua
        thread = threading.Thread(target=self.listen_loop, daemon=True)
        thread.start()
        
    def stop_listening(self):
        """Detener escucha"""
        self.listening = False
        self.toggle_btn.config(text="🎤 Iniciar Escucha")
        self.log_diagnostic("Modo escucha desactivado")
        
    def listen_loop(self):
        """Bucle de escucha"""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
            while self.listening:
                try:
                    self.log_diagnostic("Escuchando...")
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                    
                    text = self.recognizer.recognize_google(audio, language='es-ES')
                    self.log_diagnostic(f"Comando de voz: {text}")
                    
                    # Procesar en el hilo principal
                    self.root.after(0, lambda t=text: self.process_voice_command(t))
                    
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self.log_diagnostic("No se entendió el audio")
                except Exception as e:
                    self.log_diagnostic(f"Error en reconocimiento: {e}")
                    
    def process_voice_command(self, text):
        """Procesar comando de voz"""
        self.result_text.insert(tk.END, f"Comando: {text}\n")
        self.result_text.see(tk.END)
        
        text_lower = text.lower()
        command = None
        
        # Diccionario de comandos
        commands = {
            "encender led": "LED_ON",
            "prender led": "LED_ON", 
            "activar led": "LED_ON",
            "apagar led": "LED_OFF",
            "apaga led": "LED_OFF",
            "desactivar led": "LED_OFF",
            "aumentar frecuencia": "FREQ_UP",
            "subir frecuencia": "FREQ_UP",
            "reducir frecuencia": "FREQ_DOWN", 
            "bajar frecuencia": "FREQ_DOWN",
            "frecuencia rápida": "FREQ_FAST",
            "frecuencia lenta": "FREQ_SLOW"
        }
        
        # Buscar comando coincidente
        for voice_cmd, esp_cmd in commands.items():
            if voice_cmd in text_lower:
                command = esp_cmd
                self.log_diagnostic(f"Comando reconocido: {voice_cmd} -> {esp_cmd}")
                break
                
        if command:
            self.send_to_esp32(command)
        else:
            self.log_diagnostic("Comando no reconocido")
            self.result_text.insert(tk.END, "❌ Comando no reconocido\n")

def main():
    root = tk.Tk()
    app = VoiceRecognitionApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()