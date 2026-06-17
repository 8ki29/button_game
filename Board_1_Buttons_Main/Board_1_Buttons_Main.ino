// ==========================================
// Board 1: Buttons & C2-LED (AnalogWrite Complete v10.0)
// ==========================================
#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>

const int btnA1 = 22; const int btnA2 = 23; 
const int btnB1 = 19; const int btnB2 = 21; 
const int btnC1 = 5;  const int btnC2 = 18; 

// 精準對齊：本地控制 C2 燈泡 (4, 2, 15)
const int c2Red = 4; const int c2Green = 2; const int c2Blue = 15;

uint8_t broadcastAddress[] = {0x1C, 0xC3, 0xAB, 0xC2, 0xA4, 0xAC};

void setC2Color(int r, int g, int b) {
  analogWrite(c2Red,   r);
  analogWrite(c2Green, g);
  analogWrite(c2Blue,  b);
}

void setup() {
  Serial.begin(115200);
  delay(200);
  
  WiFi.mode(WIFI_STA); WiFi.disconnect();
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);

  if (esp_now_init() != ESP_OK) return;

  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 1; peerInfo.encrypt = false; peerInfo.ifidx = WIFI_IF_STA; 
  esp_now_add_peer(&peerInfo);

  pinMode(btnA1, INPUT_PULLUP); pinMode(btnA2, INPUT_PULLUP);
  pinMode(btnB1, INPUT_PULLUP); pinMode(btnB2, INPUT_PULLUP);
  pinMode(btnC1, INPUT_PULLUP); pinMode(btnC2, INPUT_PULLUP);
  
  pinMode(c2Red, OUTPUT); pinMode(c2Green, OUTPUT); pinMode(c2Blue, OUTPUT);
  setC2Color(0, 0, 0);
}

void loop() {
  // 雙擊最高優先權
  if (digitalRead(btnA1) == LOW && digitalRead(btnA2) == LOW) { Serial.println("DOUBLE"); delay(400); return; }

  // 單鍵點名
  if (digitalRead(btnA1) == LOW) { Serial.println("A1"); delay(250); }
  if (digitalRead(btnA2) == LOW) { Serial.println("A2"); delay(250); }
  if (digitalRead(btnB1) == LOW) { Serial.println("B1"); delay(250); }
  if (digitalRead(btnB2) == LOW) { Serial.println("B2"); delay(250); }
  if (digitalRead(btnC1) == LOW) { Serial.println("C1"); delay(250); }
  if (digitalRead(btnC2) == LOW) { Serial.println("C2"); delay(250); }

  // 接收 2 字元純文字密碼流
  if (Serial.available() >= 2) {
    uint8_t buf[2];
    Serial.readBytes(buf, 2);
    char node = (char)buf[0];
    char color = (char)buf[1];
    
    // 全局重設熄滅
    if (node == 'X' && color == 'X') {
      setC2Color(0, 0, 0);
      esp_now_send(broadcastAddress, buf, 2);
    }
    // 由 Board 1 本地解碼點亮 C2
    else if (node == '5') { 
      if (color == 'X') setC2Color(0, 0, 0);
      else if (color == 'P') setC2Color(255, 0,   255); // 紫
      else if (color == 'Y') setC2Color(255, 255, 0);   // 黃
      else if (color == 'G') setC2Color(0,   255, 0);   // 綠
      else if (color == 'B') setC2Color(0,   0,   255); // 藍
      else if (color == 'R') setC2Color(255, 0,   0);   // 紅
      else if (color == 'W') setC2Color(255, 255, 255); // 白
    }
    // 其餘轉發給 Board 2
    else {
      esp_now_send(broadcastAddress, buf, 2);
    }
  }
  delay(1);
}