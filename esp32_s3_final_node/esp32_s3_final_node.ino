/*
  SIT314 6.3D Final Project - ESP32-S3 Smart Building Sensor Node

  Board: ESP32-S3-WROOM-1 dev board

  Sends real sensor telemetry to the Raspberry Pi edge gateway:
    POST http://<raspberry-pi-ip>:3000/telemetry

  Evidence to capture:
  - Serial Monitor showing Wi-Fi connected
  - Serial Monitor showing HTTP POST 200 response
  - Raspberry Pi edge gateway terminal showing received JSON
  - Dashboard showing latest reading and warning/critical events

  Arduino libraries:
  - DHT sensor library by Adafruit
  - Adafruit Unified Sensor
*/

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"
#include "private_config.h"

// ---------------------------------------------------------------------------
// Wi-Fi and Raspberry Pi settings
// ---------------------------------------------------------------------------
// Wi-Fi, endpoint and device token are deliberately kept in private_config.h.
// Copy private_config.h.example to private_config.h before building locally.

// ---------------------------------------------------------------------------
// Hardware pin mapping from the tested 4.2D bring-up build
// ---------------------------------------------------------------------------
#define DHT_TYPE DHT22

const int PIN_DHT_DATA = 4;
const int PIN_MQ2_AO = 5;
const int PIN_FLAME_AO = 6;   // Optional flame analog output
const int PIN_PIR_OUT = 16;
const int PIN_FLAME_DO = 17;
const int PIN_LED = 18;
const int PIN_BUZZER = 21;

// MQ-2 calibration and event thresholds.
const unsigned long MQ2_WARMUP_MS = 900000;      // 15 minutes
const int MQ2_WARNING_DELTA = 180;
const int MQ2_CRITICAL_DELTA = 320;
const unsigned long MQ2_EVENT_LATCH_MS = 10000;  // Keep alarm visible for evidence

// Sensor behaviour confirmed during 4.2D testing.
const bool PIR_DETECTED_IS_HIGH = true;
const bool FLAME_DETECTED_IS_LOW = false; // KY-026 board used here: raw=1 means flame detected.

DHT dht(PIN_DHT_DATA, DHT_TYPE);

unsigned long lastReadMs = 0;
const unsigned long READ_INTERVAL_MS = 5000;
const unsigned long PIR_WARMUP_MS = 60000;

unsigned long sequenceNumber = 0;
int pirStableHighCount = 0;
int pirStableLowCount = 0;
float mq2Baseline = -1;
int mq2PeakRaw = 0;
int mq2EventPeakAbsDelta = 0;
bool mq2ManualBaselineSet = false;
unsigned long mq2AlarmLatchUntilMs = 0;

String boolJson(bool value) {
  return value ? "true" : "false";
}

bool readFlameDetected(int flameDigitalValue) {
  if (FLAME_DETECTED_IS_LOW) {
    return flameDigitalValue == LOW;
  }
  return flameDigitalValue == HIGH;
}

bool readMotionDetected(int pirValue) {
  if (PIR_DETECTED_IS_HIGH) {
    return pirValue == HIGH;
  }
  return pirValue == LOW;
}

String jsonStringValue(const String& value) {
  String escaped = value;
  escaped.replace("\\", "\\\\");
  escaped.replace("\"", "\\\"");
  return "\"" + escaped + "\"";
}

void connectWiFi() {
  Serial.print("Connecting to Wi-Fi SSID: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startMs = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startMs < 30000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("Wi-Fi connected");
    Serial.print("ESP32 IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi connection timed out. Check SSID/password.");
  }
}

String buildTelemetryJson(
  float temperature,
  float humidity,
  bool dhtOk,
  int mq2Raw,
  int mq2Delta,
  int mq2AbsDelta,
  bool mq2Ready,
  bool motionDetected,
  int flameDigitalValue,
  bool flameDetected,
  int flameAnalogRaw,
  bool alarmOn
) {
  String json = "{";
  json += "\"deviceId\":\"esp32s3-real-01\",";
  json += "\"room\":\"B1-F3-R302\",";
  json += "\"location\":\"building1/floor3/room302\",";
  json += "\"seq\":" + String(sequenceNumber) + ",";
  json += "\"uptimeMs\":" + String(millis()) + ",";
  json += "\"temperature\":";
  json += dhtOk ? String(temperature, 1) : "null";
  json += ",";
  json += "\"humidity\":";
  json += dhtOk ? String(humidity, 1) : "null";
  json += ",";
  json += "\"mq2Raw\":" + String(mq2Raw) + ",";
  json += "\"mq2Baseline\":" + String((int)mq2Baseline) + ",";
  json += "\"mq2Delta\":" + String(mq2Delta) + ",";
  json += "\"mq2AbsDelta\":" + String(mq2AbsDelta) + ",";
  json += "\"mq2PeakRaw\":" + String(mq2PeakRaw) + ",";
  json += "\"mq2EventPeakAbsDelta\":" + String(mq2EventPeakAbsDelta) + ",";
  json += "\"mq2Ready\":" + boolJson(mq2Ready) + ",";
  json += "\"pirMotion\":" + boolJson(motionDetected) + ",";
  json += "\"flameDigitalRaw\":" + String(flameDigitalValue) + ",";
  json += "\"flameDetected\":" + boolJson(flameDetected) + ",";
  json += "\"flameAnalogRaw\":" + String(flameAnalogRaw) + ",";
  json += "\"alarm\":" + boolJson(alarmOn);
  json += "}";
  return json;
}

// Keep the HTTP payload compact, but print an indented copy for readable evidence.
void printTelemetryJsonForSerial(
  float temperature,
  float humidity,
  bool dhtOk,
  int mq2Raw,
  int mq2Delta,
  int mq2AbsDelta,
  bool mq2Ready,
  bool motionDetected,
  int flameDigitalValue,
  bool flameDetected,
  int flameAnalogRaw,
  bool alarmOn
) {
  Serial.println("{");
  Serial.println("  \"deviceId\": \"esp32s3-real-01\",");
  Serial.println("  \"room\": \"B1-F3-R302\",");
  Serial.println("  \"location\": \"building1/floor3/room302\",");
  Serial.println("  \"seq\": " + String(sequenceNumber) + ",");
  Serial.println("  \"uptimeMs\": " + String(millis()) + ",");
  Serial.print("  \"temperature\": ");
  Serial.print(dhtOk ? String(temperature, 1) : "null");
  Serial.println(",");
  Serial.print("  \"humidity\": ");
  Serial.print(dhtOk ? String(humidity, 1) : "null");
  Serial.println(",");
  Serial.println("  \"mq2Raw\": " + String(mq2Raw) + ",");
  Serial.println("  \"mq2Baseline\": " + String((int)mq2Baseline) + ",");
  Serial.println("  \"mq2Delta\": " + String(mq2Delta) + ",");
  Serial.println("  \"mq2AbsDelta\": " + String(mq2AbsDelta) + ",");
  Serial.println("  \"mq2Ready\": " + boolJson(mq2Ready) + ",");
  Serial.println("  \"pirMotion\": " + boolJson(motionDetected) + ",");
  Serial.println("  \"flameDigitalRaw\": " + String(flameDigitalValue) + ",");
  Serial.println("  \"flameDetected\": " + boolJson(flameDetected) + ",");
  Serial.println("  \"flameAnalogRaw\": " + String(flameAnalogRaw) + ",");
  Serial.println("  \"alarm\": " + boolJson(alarmOn));
  Serial.println("}");
}

void postTelemetry(const String& payload) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi disconnected. Reconnecting before POST...");
    connectWiFi();
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("POST skipped because Wi-Fi is not connected.");
    return;
  }

  HTTPClient http;
  http.begin(EDGE_TELEMETRY_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_SHARED_TOKEN);
  int httpCode = http.POST(payload);
  String response = http.getString();
  http.end();

  Serial.print("POST ");
  Serial.print(EDGE_TELEMETRY_URL);
  Serial.print(" -> HTTP ");
  Serial.println(httpCode);
  Serial.print("Edge response: ");
  Serial.println(response);
}

void setup() {
  Serial.begin(115200);
  delay(1200);

  pinMode(PIN_PIR_OUT, INPUT);
  pinMode(PIN_FLAME_DO, INPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_BUZZER, LOW);

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_MQ2_AO, ADC_11db);
  analogSetPinAttenuation(PIN_FLAME_AO, ADC_11db);

  dht.begin();

  Serial.println();
  Serial.println("SIT314 6.3D ESP32-S3 final sensor node started");
  Serial.println("Pins: DHT GPIO4, MQ-2 AO GPIO5, Flame AO GPIO6, PIR GPIO16, Flame DO GPIO17, LED GPIO18, Buzzer GPIO21");
  Serial.println("Type b in Serial Monitor after MQ-2 stabilises to set baseline.");
  Serial.print("Edge endpoint: ");
  Serial.println(EDGE_TELEMETRY_URL);
  connectWiFi();
}

void loop() {
  if (millis() - lastReadMs < READ_INTERVAL_MS) {
    return;
  }
  lastReadMs = millis();
  sequenceNumber++;

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  bool dhtOk = !(isnan(humidity) || isnan(temperature));

  int mq2Raw = analogRead(PIN_MQ2_AO);
  int flameAnalogRaw = analogRead(PIN_FLAME_AO);
  int pirValue = digitalRead(PIN_PIR_OUT);
  int flameDigitalValue = digitalRead(PIN_FLAME_DO);

  bool pirWarmedUp = millis() >= PIR_WARMUP_MS;
  if (pirValue == HIGH) {
    pirStableHighCount++;
    pirStableLowCount = 0;
  } else {
    pirStableLowCount++;
    pirStableHighCount = 0;
  }

  bool motionDetected = pirWarmedUp && readMotionDetected(pirValue);
  bool flameDetected = readFlameDetected(flameDigitalValue);

  bool mq2WarmedUp = millis() >= MQ2_WARMUP_MS;
  if (mq2Raw > mq2PeakRaw) {
    mq2PeakRaw = mq2Raw;
  }
  if (mq2Baseline < 0) {
    mq2Baseline = mq2Raw;
  }

  while (Serial.available() > 0) {
    char command = Serial.read();
    if (command == 'b' || command == 'B') {
      mq2Baseline = mq2Raw;
      mq2PeakRaw = mq2Raw;
      mq2EventPeakAbsDelta = 0;
      mq2ManualBaselineSet = true;
      mq2AlarmLatchUntilMs = 0;
      Serial.println("MQ-2 baseline manually set to current raw value.");
    }
  }

  int mq2Delta = mq2Raw - (int)mq2Baseline;
  int mq2AbsDelta = abs(mq2Delta);
  bool mq2Ready = mq2WarmedUp || mq2ManualBaselineSet;
  if (!mq2Ready) {
    mq2Baseline = (mq2Baseline * 0.90) + (mq2Raw * 0.10);
    mq2Delta = mq2Raw - (int)mq2Baseline;
    mq2AbsDelta = abs(mq2Delta);
  }

  bool smokeWarning = mq2Ready && mq2AbsDelta >= MQ2_WARNING_DELTA;
  bool smokeCritical = mq2Ready && mq2AbsDelta >= MQ2_CRITICAL_DELTA;
  if (smokeWarning) {
    mq2AlarmLatchUntilMs = millis() + MQ2_EVENT_LATCH_MS;
    if (mq2AbsDelta > mq2EventPeakAbsDelta) {
      mq2EventPeakAbsDelta = mq2AbsDelta;
    }
  }
  bool mq2AlarmLatched = millis() < mq2AlarmLatchUntilMs;

  bool alarmOn = flameDetected || smokeCritical || mq2AlarmLatched || (smokeWarning && motionDetected);
  digitalWrite(PIN_LED, alarmOn ? HIGH : LOW);
  digitalWrite(PIN_BUZZER, alarmOn ? HIGH : LOW);

  String payload = buildTelemetryJson(
    temperature,
    humidity,
    dhtOk,
    mq2Raw,
    mq2Delta,
    mq2AbsDelta,
    mq2Ready,
    motionDetected,
    flameDigitalValue,
    flameDetected,
    flameAnalogRaw,
    alarmOn
  );

  Serial.println("--------------------------------------------------");
  Serial.println("JSON payload:");
  printTelemetryJsonForSerial(
    temperature,
    humidity,
    dhtOk,
    mq2Raw,
    mq2Delta,
    mq2AbsDelta,
    mq2Ready,
    motionDetected,
    flameDigitalValue,
    flameDetected,
    flameAnalogRaw,
    alarmOn
  );
  Serial.print("Local alarm LED/buzzer: ");
  Serial.println(alarmOn ? "ON" : "OFF");
  Serial.print("MQ-2 status: ");
  if (!mq2Ready) {
    Serial.print("calibrating, type b to set baseline. ");
    Serial.print((MQ2_WARMUP_MS - millis()) / 1000);
    Serial.println("s remaining");
  } else if (smokeCritical) {
    Serial.println("CRITICAL");
  } else if (smokeWarning) {
    Serial.println("WARNING");
  } else {
    Serial.println("normal");
  }

  postTelemetry(payload);
}
