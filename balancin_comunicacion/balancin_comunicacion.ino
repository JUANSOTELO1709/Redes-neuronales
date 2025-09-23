#include <WiFi.h>
#include <ArduinoJson.h>

// Configuración de WiFi - ¡ACTUALIZA ESTOS VALORES!
const char* ssid = "HONOR X6s";
const char* password = "Onix1605";

// Configuración del servidor
const int serverPort = 1234;
WiFiServer server(serverPort);
WiFiClient client;

// Control del LED interno
const int ledPin = 2;
bool ledState = false;
float currentFrequency = 1.0;
unsigned long previousMillis = 0;

void setup() {
  Serial.begin(115200);
  
  // Configurar LED
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);
  
  Serial.println("Iniciando ESP32 en modo diagnóstico...");
  
  // Conectar a WiFi
  Serial.print("Conectando a ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  // Intentar conexión con timeout
  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 10000) {
    delay(500);
    Serial.print(".");
    digitalWrite(ledPin, !digitalRead(ledPin)); // Parpadear durante conexión
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi conectado");
    Serial.print("📡 IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(ledPin, HIGH); // LED encendido indicando conexión
    delay(1000);
    digitalWrite(ledPin, LOW);
  } else {
    Serial.println("\n❌ Error conectando al WiFi");
    while (1) {
      // Parpadear rápido indicando error
      digitalWrite(ledPin, HIGH);
      delay(100);
      digitalWrite(ledPin, LOW);
      delay(100);
    }
  }
  
  // Iniciar servidor
  server.begin();
  Serial.println("✅ Servidor iniciado");
  Serial.println("📋 Esperando comandos...");
  Serial.println("Comandos disponibles: LED_ON, LED_OFF, FREQ:X.X");
}

void loop() {
  // Controlar parpadeo del LED según frecuencia
  unsigned long currentMillis = millis();
  if (currentFrequency > 0) {
    unsigned long interval = (unsigned long)(1000.0 / (2 * currentFrequency));
    if (currentMillis - previousMillis >= interval) {
      previousMillis = currentMillis;
      ledState = !ledState;
      digitalWrite(ledPin, ledState);
    }
  } else {
    digitalWrite(ledPin, LOW);
  }
  
  // Manejar clientes WiFi
  if (!client || !client.connected()) {
    client = server.available();
    if (client) {
      Serial.println("✅ Cliente conectado");
      client.println("ESP32 listo - Envía JSON con comando 'command'");
    }
  }
  
  // Procesar datos recibidos
  if (client && client.available()) {
    String message = client.readStringUntil('\n');
    message.trim();
    
    Serial.print("📨 Mensaje recibido: ");
    Serial.println(message);
    
    processMessage(message);
  }
  
  // Pequeño delay para evitar sobrecarga
  delay(10);
}

void processMessage(String jsonMessage) {
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, jsonMessage);
  
  if (error) {
    Serial.print("❌ Error JSON: ");
    Serial.println(error.c_str());
    client.println("ERROR: JSON inválido");
    return;
  }
  
  const char* command = doc["command"];
  Serial.print("🔧 Comando: ");
  Serial.println(command);
  
  // Procesar comandos
  if (strcmp(command, "LED_ON") == 0) {
    digitalWrite(ledPin, HIGH);
    Serial.println("💡 LED encendido");
    client.println("OK: LED encendido");
  } 
  else if (strcmp(command, "LED_OFF") == 0) {
    digitalWrite(ledPin, LOW);
    Serial.println("💡 LED apagado");
    client.println("OK: LED apagado");
  }
  else if (strncmp(command, "FREQ:", 5) == 0) {
    float freq = atof(command + 5);
    if (freq >= 0 && freq <= 10) {
      currentFrequency = freq;
      Serial.print("📊 Frecuencia cambiada: ");
      Serial.print(freq);
      Serial.println(" Hz");
      client.print("OK: Frecuencia ");
      client.print(freq);
      client.println(" Hz");
    } else {
      Serial.println("❌ Frecuencia fuera de rango (0-10 Hz)");
      client.println("ERROR: Frecuencia debe ser 0-10 Hz");
    }
  }
  else if (strcmp(command, "FREQ_UP") == 0) {
    currentFrequency = min(10.0, currentFrequency + 0.5);
    Serial.print("📈 Frecuencia aumentada: ");
    Serial.print(currentFrequency);
    Serial.println(" Hz");
    client.print("OK: Frecuencia ");
    client.print(currentFrequency);
    client.println(" Hz");
  }
  else if (strcmp(command, "FREQ_DOWN") == 0) {
    currentFrequency = max(0.0, currentFrequency - 0.5);
    Serial.print("📉 Frecuencia reducida: ");
    Serial.print(currentFrequency);
    Serial.println(" Hz");
    client.print("OK: Frecuencia ");
    client.print(currentFrequency);
    client.println(" Hz");
  }
  else if (strcmp(command, "FREQ_FAST") == 0) {
    currentFrequency = 5.0;
    Serial.println("⚡ Frecuencia rápida: 5 Hz");
    client.println("OK: Frecuencia rápida 5 Hz");
  }
  else if (strcmp(command, "FREQ_SLOW") == 0) {
    currentFrequency = 1.0;
    Serial.println("🐢 Frecuencia lenta: 1 Hz");
    client.println("OK: Frecuencia lenta 1 Hz");
  }
  else if (strcmp(command, "STATUS") == 0) {
    Serial.println("📋 Estado solicitado");
    client.print("ESTADO: LED=");
    client.print(ledState ? "ON" : "OFF");
    client.print(", FRECUENCIA=");
    client.print(currentFrequency);
    client.println(" Hz");
  }
  else {
    Serial.println("❌ Comando desconocido");
    client.println("ERROR: Comando desconocido");
  }
}