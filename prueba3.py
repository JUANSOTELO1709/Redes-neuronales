import speech_recognition as sr
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import socket
import json

class VoiceRecognitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Control por Voz + WiFi ESP32 - Frecuencia LED")
        self.root.geometry("900x750")
        self.root.configure(bg="#2c3e50")
        
        # Variables de estado
        self.listening = False
        self.recognizer = sr.Recognizer()
        self.esp32_ip = "192.168.1.100"  # Cambia por la IP de tu ESP32
        self.esp32_port = 1234
        self.wifi_connected = False
        self.socket = None
        self.led_frequency = 1  # Frecuencia inicial en Hz
        
        self.setup_ui()
        self.update_microphone_list()
        self.connect_to_esp32()
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="🎤 Control por Voz - Frecuencia LED ESP32", 
                               font=("Arial", 16, "bold"), foreground="#3498db")
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        # Configuración WiFi
        wifi_frame = ttk.LabelFrame(main_frame, text="Configuración WiFi ESP32", padding="10")
        wifi_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        wifi_frame.columnconfigure(1, weight=1)
        
        ttk.Label(wifi_frame, text="IP del ESP32:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ip_var = tk.StringVar(value="192.168.1.100")
        ip_entry = ttk.Entry(wifi_frame, textvariable=self.ip_var, width=15)
        ip_entry.grid(row=0, column=1, padx=(10, 5), pady=5, sticky=tk.W)
        
        ttk.Label(wifi_frame, text="Puerto:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        self.port_var = tk.StringVar(value="1234")
        port_entry = ttk.Entry(wifi_frame, textvariable=self.port_var, width=8)
        port_entry.grid(row=0, column=3, padx=(5, 10), pady=5, sticky=tk.W)
        
        self.connect_btn = ttk.Button(wifi_frame, text="Conectar", command=self.connect_to_esp32)
        self.connect_btn.grid(row=0, column=4, padx=(10, 0), pady=5)
        
        self.wifi_status = ttk.Label(wifi_frame, text="Desconectado", foreground="red")
        self.wifi_status.grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=(5, 0))
        
        # Control de Frecuencia LED
        freq_frame = ttk.LabelFrame(main_frame, text="Control de Frecuencia LED", padding="10")
        freq_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        freq_frame.columnconfigure(1, weight=1)
        
        ttk.Label(freq_frame, text="Frecuencia actual:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.freq_var = tk.StringVar(value="1 Hz")
        freq_label = ttk.Label(freq_frame, textvariable=self.freq_var, font=("Arial", 10, "bold"))
        freq_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Label(freq_frame, text="Rango de frecuencia:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.freq_scale = tk.Scale(freq_frame, from_=0.5, to=10, resolution=0.5, orient=tk.HORIZONTAL,
                                  length=300, command=self.update_frequency)
        self.freq_scale.set(1)
        self.freq_scale.grid(row=1, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # Separador
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Configuración de micrófono
        ttk.Label(main_frame, text="Micrófono:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(main_frame, textvariable=self.mic_var, state="readonly", width=40)
        self.mic_combo.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        refresh_btn = ttk.Button(main_frame, text="🔄", width=3, command=self.update_microphone_list)
        refresh_btn.grid(row=4, column=2, padx=(10, 0))
        
        self.mic_status = ttk.Label(main_frame, text="Estado: No configurado", foreground="red")
        self.mic_status.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(0, 15))
        
        # Botón de inicio/parada
        self.toggle_btn = ttk.Button(main_frame, text="🎤 Iniciar Escucha", 
                                    command=self.toggle_listening, width=20, state="disabled")
        self.toggle_btn.grid(row=6, column=0, columnspan=3, pady=10)
        
        # Indicadores de estado
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=7, column=0, columnspan=3, pady=15)
        
        # Indicador de escucha
        listen_frame = ttk.Frame(status_frame)
        listen_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(listen_frame, text="Estado Escucha", font=("Arial", 9)).pack()
        self.status_canvas = tk.Canvas(listen_frame, width=80, height=80, bg="#2c3e50", highlightthickness=0)
        self.status_canvas.pack()
        self.indicator = self.status_canvas.create_oval(15, 15, 65, 65, fill="red")
        self.status_text = self.status_canvas.create_text(40, 40, text="Inactivo", fill="white", font=("Arial", 8))
        
        # Indicador WiFi
        wifi_frame = ttk.Frame(status_frame)
        wifi_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(wifi_frame, text="Conexión WiFi", font=("Arial", 9)).pack()
        self.wifi_canvas = tk.Canvas(wifi_frame, width=80, height=80, bg="#2c3e50", highlightthickness=0)
        self.wifi_canvas.pack()
        self.wifi_indicator = self.wifi_canvas.create_oval(15, 15, 65, 65, fill="red")
        self.wifi_status_text = self.wifi_canvas.create_text(40, 40, text="Desconectado", fill="white", font=("Arial", 8))
        
        # Indicador LED ESP32
        led_frame = ttk.Frame(status_frame)
        led_frame.pack(side=tk.LEFT)
        ttk.Label(led_frame, text="LED ESP32", font=("Arial", 9)).pack()
        self.led_canvas = tk.Canvas(led_frame, width=80, height=80, bg="#2c3e50", highlightthickness=0)
        self.led_canvas.pack()
        self.led_indicator = self.led_canvas.create_oval(15, 15, 65, 65, fill="red")
        self.led_status_text = self.led_canvas.create_text(40, 40, text="Apagado", fill="white", font=("Arial", 8))
        
        # Área de texto para mostrar resultados
        ttk.Label(main_frame, text="Comando reconocido:", font=("Arial", 10)).grid(row=8, column=0, sticky=tk.W, pady=(15, 5))
        
        self.result_text = tk.Text(main_frame, height=4, width=50, font=("Arial", 11), 
                                  bg="#34495e", fg="white", relief=tk.FLAT)
        self.result_text.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # Historial de comandos
        ttk.Label(main_frame, text="Historial de comandos:", font=("Arial", 10)).grid(row=10, column=0, sticky=tk.W, pady=(10, 5))
        
        self.history_listbox = tk.Listbox(main_frame, height=8, font=("Arial", 10), 
                                         bg="#34495e", fg="white", relief=tk.FLAT)
        self.history_listbox.grid(row=11, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Barra de desplazamiento
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.history_listbox.yview)
        scrollbar.grid(row=11, column=3, sticky=(tk.N, tk.S), pady=(0, 10))
        self.history_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Configurar pesos para expandir
        main_frame.rowconfigure(11, weight=1)
        
    def update_frequency(self, value):
        """Actualizar frecuencia del LED"""
        self.led_frequency = float(value)
        self.freq_var.set(f"{self.led_frequency} Hz")
        
        # Enviar comando de frecuencia al ESP32
        if self.wifi_connected:
            self.send_to_esp32(f"FREQ:{self.led_frequency}")
            self.add_to_history(f"Frecuencia cambiada: {self.led_frequency} Hz")
            
            # Actualizar indicador LED
            self.update_led_indicator()
    
    def update_led_indicator(self):
        """Actualizar indicador visual del LED"""
        if self.led_frequency == 0:
            self.led_canvas.itemconfig(self.led_indicator, fill="red")
            self.led_canvas.itemconfig(self.led_status_text, text="Apagado")
        else:
            self.led_canvas.itemconfig(self.led_indicator, fill="green")
            self.led_canvas.itemconfig(self.led_status_text, text=f"{self.led_frequency} Hz")
    
    def connect_to_esp32(self):
        """Conectar al ESP32 por WiFi"""
        try:
            # Cerrar conexión anterior si existe
            if self.socket:
                self.socket.close()
            
            # Crear nuevo socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)
            
            # Conectar
            self.socket.connect((self.ip_var.get(), int(self.port_var.get())))
            
            self.wifi_connected = True
            self.wifi_status.config(text="Conectado", foreground="green")
            self.connect_btn.config(text="Reconectar")
            self.toggle_btn.config(state="normal")
            
            # Actualizar indicadores
            self.wifi_canvas.itemconfig(self.wifi_indicator, fill="green")
            self.wifi_canvas.itemconfig(self.wifi_status_text, text="Conectado")
            
            # Enviar frecuencia inicial
            self.send_to_esp32(f"FREQ:{self.led_frequency}")
            
            self.add_to_history("Conexión WiFi establecida con ESP32")
            
        except Exception as e:
            self.wifi_connected = False
            self.wifi_status.config(text=f"Error: {str(e)}", foreground="red")
            self.toggle_btn.config(state="disabled")
            
            # Actualizar indicadores
            self.wifi_canvas.itemconfig(self.wifi_indicator, fill="red")
            self.wifi_canvas.itemconfig(self.wifi_status_text, text="Error")
            
            messagebox.showerror("Error de conexión", f"No se pudo conectar al ESP32: {str(e)}")
    
    def send_to_esp32(self, command):
        """Enviar comando al ESP32 por WiFi"""
        if not self.wifi_connected or not self.socket:
            self.add_to_history("Error: No hay conexión WiFi")
            return False
            
        try:
            # Crear mensaje JSON
            message = {
                "command": command,
                "timestamp": time.time()
            }
            
            # Enviar comando
            self.socket.sendall(json.dumps(message).encode() + b'\n')
            self.add_to_history(f"Comando enviado: {command}")
            return True
            
        except Exception as e:
            self.add_to_history(f"Error enviando comando: {str(e)}")
            self.wifi_connected = False
            return False
    
    def update_microphone_list(self):
        """Actualizar lista de micrófonos"""
        try:
            mics = sr.Microphone.list_microphone_names()
            self.mic_combo['values'] = mics
            if mics:
                self.mic_combo.current(0)
                self.mic_status.config(text="Estado: Micrófono disponible", foreground="green")
            else:
                self.mic_status.config(text="Estado: No se encontraron micrófonos", foreground="red")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los micrófonos: {e}")
    
    def toggle_listening(self):
        """Alternar entre escuchar y parar"""
        if not self.listening:
            self.start_listening()
        else:
            self.stop_listening()
    
    def start_listening(self):
        """Iniciar escucha"""
        if not self.mic_combo.get():
            messagebox.showwarning("Advertencia", "Selecciona un micrófono primero")
            return
            
        self.listening = True
        self.toggle_btn.config(text="⏹️ Detener Escucha")
        self.status_canvas.itemconfig(self.indicator, fill="green")
        self.status_canvas.itemconfig(self.status_text, text="Escuchando...")
        
        # Iniciar hilo de escucha
        thread = threading.Thread(target=self.listen_loop, daemon=True)
        thread.start()
    
    def stop_listening(self):
        """Detener escucha"""
        self.listening = False
        self.toggle_btn.config(text="🎤 Iniciar Escucha")
        self.status_canvas.itemconfig(self.indicator, fill="red")
        self.status_canvas.itemconfig(self.status_text, text="Inactivo")
    
    def listen_loop(self):
        """Bucle principal de escucha"""
        mic_index = self.mic_combo.current()
        
        with sr.Microphone(device_index=mic_index) as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            while self.listening:
                try:
                    # Escuchar audio
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                    
                    # Reconocer
                    text = self.recognizer.recognize_google(audio, language='es-ES')
                    
                    # Procesar resultado
                    self.root.after(0, lambda t=text: self.process_result(t))
                    
                    # Pequeña pausa
                    time.sleep(1)
                    
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self.root.after(0, self.show_not_understood)
                except sr.RequestError as e:
                    self.root.after(0, lambda: self.show_error(f"Error del servicio: {e}"))
                except Exception as e:
                    self.root.after(0, lambda: self.show_error(f"Error inesperado: {e}"))
    
    def process_result(self, text):
        """Procesar texto reconocido"""
        # Mostrar en área de texto
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        
        # Añadir al historial
        self.add_to_history(f"Voz: {text}")
        
        # Resaltar brevemente
        self.result_text.configure(bg="#27ae60")
        self.root.after(500, lambda: self.result_text.configure(bg="#34495e"))
        
        # Procesar comando y enviar al ESP32
        self.execute_command(text.lower())
    
    def execute_command(self, command):
        """Ejecutar y enviar comandos"""
        action = None
        esp_command = None
        
        if "encender" in command and "led" in command:
            action = "💡 LED ENCENDIDO"
            self.led_frequency = 1  # Frecuencia por defecto
            self.freq_scale.set(self.led_frequency)
            esp_command = f"FREQ:{self.led_frequency}"
        elif "apagar" in command and "led" in command:
            action = "💡 LED APAGADO"
            self.led_frequency = 0
            self.freq_scale.set(0)
            esp_command = "FREQ:0"
        elif "aumentar" in command and "frecuencia" in command:
            new_freq = min(10, self.led_frequency + 0.5)
            action = f"📈 Frecuencia aumentada: {new_freq} Hz"
            self.led_frequency = new_freq
            self.freq_scale.set(new_freq)
            esp_command = f"FREQ:{new_freq}"
        elif "reducir" in command and "frecuencia" in command:
            new_freq = max(0.5, self.led_frequency - 0.5)
            action = f"📉 Frecuencia reducida: {new_freq} Hz"
            self.led_frequency = new_freq
            self.freq_scale.set(new_freq)
            esp_command = f"FREQ:{new_freq}"
        elif "frecuencia" in command and "rápida" in command:
            action = "⚡ Frecuencia rápida: 5 Hz"
            self.led_frequency = 5
            self.freq_scale.set(5)
            esp_command = "FREQ:5"
        elif "frecuencia" in command and "lenta" in command:
            action = "🐢 Frecuencia lenta: 1 Hz"
            self.led_frequency = 1
            self.freq_scale.set(1)
            esp_command = "FREQ:1"
        elif "hola" in command:
            action = "👋 ¡Hola! ¿En qué puedo ayudarte?"
        elif "adiós" in command or "terminar" in command:
            action = "👋 ¡Hasta luego!"
            self.root.after(2000, self.stop_listening)
        
        if action:
            self.add_to_history(action)
            
        if esp_command and self.wifi_connected:
            # Enviar comando al ESP32
            self.send_to_esp32(esp_command)
            self.update_led_indicator()
    
    def add_to_history(self, message):
        """Añadir mensaje al historial"""
        timestamp = time.strftime("%H:%M:%S")
        self.history_listbox.insert(0, f"{timestamp} - {message}")
        if self.history_listbox.size() > 50:
            self.history_listbox.delete(50, tk.END)
    
    def show_not_understood(self):
        """Mostrar mensaje de no entendido"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "No se pudo entender el audio. Intenta de nuevo.")
        self.result_text.configure(bg="#e74c3c")
        self.root.after(1000, lambda: self.result_text.configure(bg="#34495e"))
    
    def show_error(self, message):
        """Mostrar mensaje de error"""
        messagebox.showerror("Error", message)
        self.stop_listening()
    
    def __del__(self):
        """Destructor - cerrar conexión"""
        if self.socket:
            self.socket.close()

def main():
    root = tk.Tk()
    app = VoiceRecognitionApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()