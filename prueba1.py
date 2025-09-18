import speech_recognition as sr
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import pygame
import os

class VoiceRecognitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reconocimiento de Voz - Control por Voz")
        self.root.geometry("800x600")
        self.root.configure(bg="#2c3e50")
        
        # Inicializar pygame para sonidos
        pygame.mixer.init()
        
        # Variables de estado
        self.listening = False
        self.recognizer = sr.Recognizer()
        
        self.setup_ui()
        self.update_microphone_list()
        
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="🎤 Reconocimiento de Voz", 
                               font=("Arial", 18, "bold"), foreground="#3498db")
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Selección de micrófono
        ttk.Label(main_frame, text="Micrófono:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(main_frame, textvariable=self.mic_var, state="readonly")
        self.mic_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Botón para actualizar micrófonos
        refresh_btn = ttk.Button(main_frame, text="🔄", width=3, command=self.update_microphone_list)
        refresh_btn.grid(row=1, column=2, padx=(10, 0))
        
        # Estado del micrófono
        self.mic_status = ttk.Label(main_frame, text="Estado: No configurado", foreground="red")
        self.mic_status.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 20))
        
        # Botón de inicio/parada
        self.toggle_btn = ttk.Button(main_frame, text="🎤 Iniciar Escucha", 
                                    command=self.toggle_listening, width=20)
        self.toggle_btn.grid(row=3, column=0, columnspan=3, pady=10)
        
        # Indicador de escucha
        self.status_canvas = tk.Canvas(main_frame, width=100, height=100, bg="#2c3e50", highlightthickness=0)
        self.status_canvas.grid(row=4, column=0, columnspan=3, pady=20)
        self.indicator = self.status_canvas.create_oval(20, 20, 80, 80, fill="red")
        self.status_text = self.status_canvas.create_text(50, 50, text="Inactivo", fill="white", font=("Arial", 10))
        
        # Área de texto para mostrar resultados
        ttk.Label(main_frame, text="Comando reconocido:", font=("Arial", 10)).grid(row=5, column=0, sticky=tk.W, pady=(20, 5))
        
        self.result_text = tk.Text(main_frame, height=4, width=50, font=("Arial", 11), 
                                  bg="#34495e", fg="white", relief=tk.FLAT)
        self.result_text.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Historial de comandos
        ttk.Label(main_frame, text="Historial de comandos:", font=("Arial", 10)).grid(row=7, column=0, sticky=tk.W, pady=(10, 5))
        
        self.history_listbox = tk.Listbox(main_frame, height=8, font=("Arial", 10), 
                                         bg="#34495e", fg="white", relief=tk.FLAT)
        self.history_listbox.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # Barra de desplazamiento para el historial
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.history_listbox.yview)
        scrollbar.grid(row=8, column=3, sticky=(tk.N, tk.S), pady=(0, 20))
        self.history_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Configurar pesos para expandir
        main_frame.rowconfigure(8, weight=1)
        
    def update_microphone_list(self):
        """Actualiza la lista de micrófonos disponibles"""
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
        """Alterna entre escuchar y parar"""
        if not self.listening:
            self.start_listening()
        else:
            self.stop_listening()
    
    def start_listening(self):
        """Inicia el proceso de escucha"""
        if not self.mic_combo.get():
            messagebox.showwarning("Advertencia", "Selecciona un micrófono primero")
            return
            
        self.listening = True
        self.toggle_btn.config(text="⏹️ Detener Escucha")
        self.status_canvas.itemconfig(self.indicator, fill="green")
        self.status_canvas.itemconfig(self.status_text, text="Escuchando...")
        
        # Iniciar hilo para no bloquear la interfaz
        thread = threading.Thread(target=self.listen_loop, daemon=True)
        thread.start()
    
    def stop_listening(self):
        """Detiene el proceso de escucha"""
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
                    # Actualizar UI desde el hilo principal
                    self.root.after(0, lambda: self.status_canvas.itemconfig(self.indicator, fill="yellow"))
                    self.root.after(0, lambda: self.status_canvas.itemconfig(self.status_text, text="Escuchando..."))
                    
                    # Escuchar audio
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                    
                    # Reconocer
                    self.root.after(0, lambda: self.status_canvas.itemconfig(self.indicator, fill="blue"))
                    self.root.after(0, lambda: self.status_canvas.itemconfig(self.status_text, text="Procesando..."))
                    
                    text = self.recognizer.recognize_google(audio, language='es-ES')
                    
                    # Procesar resultado
                    self.root.after(0, lambda t=text: self.process_result(t))
                    
                    # Pequeña pausa antes de escuchar de nuevo
                    time.sleep(1)
                    
                except sr.WaitTimeoutError:
                    # Timeout es normal, continuar escuchando
                    continue
                except sr.UnknownValueError:
                    self.root.after(0, self.show_not_understood)
                except sr.RequestError as e:
                    self.root.after(0, lambda: self.show_error(f"Error del servicio: {e}"))
                except Exception as e:
                    self.root.after(0, lambda: self.show_error(f"Error inesperado: {e}"))
                
                # Restaurar estado de escucha
                if self.listening:
                    self.root.after(0, lambda: self.status_canvas.itemconfig(self.indicator, fill="green"))
                    self.root.after(0, lambda: self.status_canvas.itemconfig(self.status_text, text="Escuchando..."))
    
    def process_result(self, text):
        """Procesa el texto reconocido"""
        # Mostrar en el área de texto
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        
        # Añadir al historial
        self.history_listbox.insert(0, f"{time.strftime('%H:%M:%S')} - {text}")
        if self.history_listbox.size() > 50:  # Limitar historial
            self.history_listbox.delete(50, tk.END)
        
        # Resaltar brevemente
        self.result_text.configure(bg="#27ae60")
        self.root.after(500, lambda: self.result_text.configure(bg="#34495e"))
        
        # Procesar comando
        self.execute_command(text.lower())
    
    def execute_command(self, command):
        """Ejecuta acciones basadas en el comando de voz"""
        action = None
        
        if "encender" in command and "led" in command:
            action = "💡 LED ENCENDIDO"
        elif "apagar" in command and "led" in command:
            action = "💡 LED APAGADO"
        elif "activar" in command and "motor" in command:
            action = "⚙️ MOTOR ACTIVADO"
        elif "detener" in command and "motor" in command:
            action = "⚙️ MOTOR DETENIDO"
        elif "hola" in command:
            action = "👋 ¡Hola! ¿En qué puedo ayudarte?"
        elif "adiós" in command or "terminar" in command:
            action = "👋 ¡Hasta luego!"
            self.root.after(2000, self.stop_listening)
        
        if action:
            # Mostrar acción en el historial
            self.history_listbox.insert(0, f"{time.strftime('%H:%M:%S')} - {action}")
            if self.history_listbox.size() > 50:
                self.history_listbox.delete(50, tk.END)
    
    def show_not_understood(self):
        """Muestra mensaje de no entendido"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "No se pudo entender el audio. Intenta de nuevo.")
        self.result_text.configure(bg="#e74c3c")
        self.root.after(1000, lambda: self.result_text.configure(bg="#34495e"))
    
    def show_error(self, message):
        """Muestra mensaje de error"""
        messagebox.showerror("Error", message)
        self.stop_listening()

def main():
    root = tk.Tk()
    app = VoiceRecognitionApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()