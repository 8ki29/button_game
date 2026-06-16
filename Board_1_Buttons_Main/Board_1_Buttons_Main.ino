// ==========================================
// Board 1: Buttons MCU (Handshake & Core v3.3.8)
// ==========================================
#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>

const int btnA1 = 22; const int btnA2 = 23; 
const int btnB1 = 19; const int btnB2 = 21; 
const int btnC1 = 5;  const int btnC2 = 18; 

// 目標 Board 2 的 MAC 位址
uint8_t broadcastAddress[] = {0x1C, 0xC3, 0xAB, 0xC2, 0xA4, 0xAC};

void OnDataSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status) {
  // 發射狀態檢查
}

// 【新功能】當收到 B2 傳來的握手訊號時
void OnDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len) {
    if (len > 0 && (char)incomingData[0] == 'H') {
        Serial.println("\n=========================================");
        Serial.println("🤝 [LINK SUCCESS] Board 2 has acknowledged Board 1!");
        Serial.println("=========================================\n");
    }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  // 強制鎖定 Channel 1
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);

  if (esp_now_init() != ESP_OK) {
    Serial.println("[ERROR] ESP-NOW Init Failed");
    return;
  }

  esp_now_register_send_cb(esp_now_send_cb_t(OnDataSent));
  esp_now_register_recv_cb(OnDataRecv); // 註冊接收 B2 訊息

  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 1;
  peerInfo.encrypt = false;
  peerInfo.ifidx = WIFI_IF_STA; // 擊殺 E113

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("[ERROR] Peer Addition Failed");
    return;
  }

  pinMode(btnA1, INPUT_PULLUP); pinMode(btnA2, INPUT_PULLUP);
  pinMode(btnB1, INPUT_PULLUP); pinMode(btnB2, INPUT_PULLUP);
  pinMode(btnC1, INPUT_PULLUP); pinMode(btnC2, INPUT_PULLUP);
  
  Serial.println("[SYS] Board 1 Online. Waiting for Board 2's heartbeat...");
}

void loop() {
  if (digitalRead(btnA1) == LOW) { Serial.println("A1"); delay(200); }
  if (digitalRead(btnA2) == LOW) { Serial.println("A2"); delay(200); }
  if (digitalRead(btnB1) == LOW) { Serial.println("B1"); delay(200); }
  if (digitalRead(btnB2) == LOW) { Serial.println("B2"); delay(200); }
  if (digitalRead(btnC1) == LOW) { Serial.println("C1"); delay(200); }
  if (digitalRead(btnC2) == LOW) { Serial.println("C2"); deslay(200); }

  if (Serial.available() > 0) {
    char cmd = Serial.read();
    esp_now_send(broadcastAddress, (uint8_t *) &cmd, sizeof(cmd));
  }
  delay(1);
}