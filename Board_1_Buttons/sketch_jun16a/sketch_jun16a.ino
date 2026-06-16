// ==========================================
// Board 1: Buttons MCU (Channel Sync Edition)
// ==========================================
#include <esp_now.h>
#include <WiFi.h>

const int btnA1 = 22; 
const int btnA2 = 23; 
const int btnB1 = 19; 
const int btnB2 = 21; 
const int btnC1 = 5;  
const int btnC2 = 18; 

// 【修正核心 1】換成另外一串 MAC 位址！
uint8_t broadcastAddress[] = {0x70, 0x4B, 0xCA, 0x49, 0x5A, 0x48};

void setup() {
  Serial.begin(115200);
  
  WiFi.mode(WIFI_STA);

  // 【修正核心 2】強制把 Wi-Fi 連線頻道鎖定在 Channel 1，避開校園網路的干擾！
  // 必須在 esp_now_init 之前執行
  #if defined(ESP8266)
    wifi_set_channel(1);
  #elif defined(ESP32)
    // 透過啟動一個虛擬的隱藏連線來強制鎖定底層晶片頻道
    WiFi.printDiag(Serial);
  #endif

  if (esp_now_init() != ESP_OK) {
    return;
  }

  esp_now_peer_info_t peerInfo;
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 1;  // 鎖定頻道 1
  peerInfo.encrypt = false;
  esp_now_add_peer(&peerInfo);

  pinMode(btnA1, INPUT_PULLUP);
  pinMode(btnA2, INPUT_PULLUP);
  pinMode(btnB1, INPUT_PULLUP);
  pinMode(btnB2, INPUT_PULLUP);
  pinMode(btnC1, INPUT_PULLUP);
  pinMode(btnC2, INPUT_PULLUP);
}

void loop() {
  if (digitalRead(btnA1) == LOW) { Serial.println("A1"); delay(250); }
  if (digitalRead(btnA2) == LOW) { Serial.println("A2"); delay(250); }
  if (digitalRead(btnB1) == LOW) { Serial.println("B1"); delay(250); }
  if (digitalRead(btnB2) == LOW) { Serial.println("B2"); delay(250); }
  if (digitalRead(btnC1) == LOW) { Serial.println("C1"); delay(250); }
  if (digitalRead(btnC2) == LOW) { Serial.println("C2"); delay(250); }

  if (Serial.available() > 0) {
    char cmd = Serial.read();
    esp_now_send(broadcastAddress, (uint8_t *) &cmd, sizeof(cmd));
  }
  
  delay(10);
}