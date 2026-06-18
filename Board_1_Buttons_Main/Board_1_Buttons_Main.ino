// ==========================================
// Single ESP32: Silk Smooth Fade & Reboot White Pulse (v16.0.0)
// ==========================================
#include <FastLED.h>

#define NUM_LEDS     18   // 總共 18 顆串接燈珠
#define DATA_PIN     13   // 數據訊號線穩穩固定在 D13

CRGB leds[NUM_LEDS];

// 硬體拉線索引校正：C2(0), B2(3), A2(6), A1(9), B1(12), C1(15)
const int nodeStartIdx[6] = {9, 6, 12, 3, 15, 0};

// 【呼吸引擎核心變數】
CRGB targetColors[6] = {CRGB::Black};
CRGB currentColors[6] = {CRGB::Black};

// 狀態旗標
bool passWaveMode = false;
bool rebootMode = false;   // 🌟 全新狀態：重啟低亮度白光呼吸

// 非阻塞按鈕冷卻計時器
unsigned long lastButtonTime = 0;
const unsigned long debounceDelay = 250; 

const int buttonPins[6] = {25, 33, 27, 26, 12, 14}; // A1, A2, B1, B2, C1, C2
const char* nodeNames[6] = {"A1", "A2", "B1", "B2", "C1", "C2"};

void setNodeColor(int nodeIdx, int r, int g, int b) {
  if (nodeIdx < 0 || nodeIdx > 5) return;
  int start = nodeStartIdx[nodeIdx];
  for (int i = 0; i < 3; i++) { 
    leds[start + i] = CRGB(r, g, b);
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setBrightness(50); 

  for (int i = 0; i < 6; i++) {
    pinMode(buttonPins[i], INPUT_PULLUP);
  }

  FastLED.clear();
  FastLED.show();
  Serial.println("[SYS] Calibrated Emerald & Reboot White Engine Online.");
}

void loop() {
  // 📥 1. 監聽來自 Mac Python 的高級控制指令
  if (Serial.available() >= 2) {
    char node = Serial.read();
    char color = Serial.read();
    
    // 當 Python 傳送 "SS" 時，開啟完美過關環狀慢綠波浪
    if (node == 'S' && color == 'S') {
      passWaveMode = true;
      rebootMode = false;
    } 
    // 🌟【全新特殊指令】當 Python 噴射 "WW" 時，代表進入重啟倒數，全場白光低亮度呼吸！
    else if (node == 'W' && color == 'W') {
      rebootMode = true;
      passWaveMode = false;
    }
    // 全局重設熄滅指令
    else if (node == 'X' && color == 'X') {
      passWaveMode = false;
      rebootMode = false;
      for (int i = 0; i < 6; i++) targetColors[i] = CRGB::Black;
    } 
    else {
      passWaveMode = false;
      rebootMode = false;
      int idx = node - '0'; 
      if (idx >= 0 && idx <= 5) {
        if (color == 'X')      targetColors[idx] = CRGB::Black;           
        else if (color == 'P') targetColors[idx] = CRGB(170, 0,   255);     // 紫
        else if (color == 'Y') targetColors[idx] = CRGB(255, 230, 0);       // 黃
        else if (color == 'G') targetColors[idx] = CRGB(0,   255, 60);      // 綠
        else if (color == 'B') targetColors[idx] = CRGB(0,   100, 255);     // 藍
        else if (color == 'R') targetColors[idx] = CRGB(255, 0,   0);       // 純紅
        else if (color == 'W') targetColors[idx] = CRGB(240, 245, 255);     // 白
      }
    }
  }

  // 🔘 2. 實體按鈕硬體掃描
  if (millis() - lastButtonTime > debounceDelay) {
    if (digitalRead(buttonPins[0]) == LOW && digitalRead(buttonPins[1]) == LOW) { 
      Serial.println("DOUBLE");
      lastButtonTime = millis();
    } 
    else {
      for (int i = 0; i < 6; i++) {
        if (digitalRead(buttonPins[i]) == LOW) {
          Serial.println(nodeNames[i]);
          lastButtonTime = millis();
          break;
        }
      }
    }
  }

  // 🌊 3. 實體動態燈光演算法引擎
  if (rebootMode) {
    // 🌟【全新重啟特效：18燈全螢光純白・低亮度優雅深呼吸】
    // 使用 FastLED 的 beatsin8 函數：22 BPM 頻率，亮度在 6 到 32 之間極其柔和沉穩地起伏
    uint8_t pulse = beatsin8(22, 6, 32); 
    fill_solid(leds, NUM_LEDS, CRGB(pulse, pulse, pulse));
    FastLED.show();
  }
  else if (passWaveMode) {
    // 通關特效：純淨翠綠慢速大波浪
    uint32_t ms = millis() / 8; 
    for (int i = 0; i < NUM_LEDS; i++) {
      uint8_t wave = sin8(ms - (i * 14));
      leds[i] = CRGB(0, wave, 0); 
    }
    FastLED.show();
  } 
  else {
    // 常規遊戲模式：優雅的絲綢非阻塞淡入淡出
    EVERY_N_MILLISECONDS(6) {
      bool needUpdate = false;
      for (int i = 0; i < 6; i++) {
        if (currentColors[i] != targetColors[i]) {
          currentColors[i] = blend(currentColors[i], targetColors[i], 24);
          
          int start = nodeStartIdx[i];
          for (int j = 0; j < 3; j++) {
            leds[start + j] = currentColors[i];
          }
          needUpdate = true;
        }
      }
      if (needUpdate) {
        FastLED.show();
      }
    }
  }
}