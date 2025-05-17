#include <WiFi.h>
#include <PubSubClient.h>
#include <Keypad.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#define PIR_PIN 18
#define BUZZER_PIN 15
#define BUTTON_PIN 23

const char* ssid = "Please_Hack_It";
const char* password = "killernet";
const char* mqtt_server = "192.168.0.108";

WiFiClient espClient;
PubSubClient client(espClient);

Adafruit_SSD1306 display(128, 64, &Wire, -1);

const byte ROWS = 4;  
const byte COLS = 4;  

char keys[ROWS][COLS] = {
  { '1', '2', '3', 'A' },
  { '4', '5', '6', 'B' },
  { '7', '8', '9', 'C' },
  { '*', '0', '#', 'D' }
};
byte rowPins[ROWS] = { 13, 12, 14, 27 };  
byte colPins[COLS] = { 26, 25, 33, 32 };  
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

bool buttonState = false;

String pass = "";

String door = "locked";

void displayShow()
{
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Door: ");
  display.setTextSize(2);
  display.setCursor(0,10);
  display.print(door.c_str());
  display.display();
}

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message received on topic: ");
  Serial.print(topic);
  Serial.print(" => ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
  if(String(topic)=="doorbell/unlock")
  {
    door = "unlocked";
    displayShow();
  }
  if(String(topic)=="doorbell/lock")
  {
    door = "locked";
    displayShow();
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(PIR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("ESP32_Client")) {
      Serial.println("Connected!");
      client.subscribe("raspberrypi/data");
      client.subscribe("doorbell/recognition");
      client.subscribe("doorbell/unlock");
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" Retrying...");
      delay(2000);
    }
  }

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    for (;;)
      ;
  }
  delay(1000);
  display.clearDisplay();
  display.setTextColor(WHITE);
}

void loop() {
  if (!client.connected()) {
    client.connect("ESP32_Client");
  }
  client.loop();

  displayShow();

  buttonState = digitalRead(BUTTON_PIN) == LOW;  // Button pressed (NO closes)

  if (buttonState) {
    Serial.println("ON");
    client.publish("doorbell/ring", "Ringed");
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    delay(100);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(200);
    digitalWrite(BUZZER_PIN, LOW);
    delay(100);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(300);
    digitalWrite(BUZZER_PIN, LOW);
    delay(200);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    delay(100);
  } else {
    //Serial.println("OFF");
  }

  char key = keypad.getKey();

  if (key) {  // If a key is pressed
    Serial.print("Key Pressed: ");
    Serial.println(key);
    if(key == 'D')
    {
      client.publish("doorbell/motion", "Motion Detected");
    }else if(key== 'C')
    {
      pass = "";
    }
    else if(key>='0' && key<='9')
    {
      pass += key;
    }
    else if(key == 'A')
    {
      client.publish("doorbell/password", pass.c_str());
    }
  }
}