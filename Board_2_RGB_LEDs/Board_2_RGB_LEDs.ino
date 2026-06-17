// ==========================================
// Board 2: AnalogWrite Matrix Decoder (v10.0.0)
// ==========================================
#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>

struct RGBLed { int redPin; int greenPin; int bluePin; };

RGBLed leds[6] = {
    {4,  2,  15}, // [0] A1
    {13, 12, 14}, // [1] A2
    {5,  17, 16}, // [2] B1 🌟 獨立正宮
    {27, 26, 25}, // [3] B2
    {21, 19, 18}, // [4] C1
    {0,  0,  0 }  // [5] C2 留空 (在 Board 1)
};

void setNodePWMColor(int index, int r, int g, int b) {
    if (index == 5) return;
    analogWrite(leds[index].redPin,   r);
    analogWrite(leds[index].greenPin, g);
    analogWrite(leds[index].bluePin,  b);
}

void OnDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len) {
    if (len == 2) {
        char node = (char)incomingData[0];
        char color = (char)incomingData[1];
        
        if (node == 'X' && color == 'X') {
            for(int i=0; i<5; i++) setNodePWMColor(i, 0, 0, 0);
            return;
        }
        
        int idx = node - '0'; 
        if (idx >= 0 && idx <= 4) {
            if (color == 'X') setNodePWMColor(idx, 0, 0, 0);
            else if (color == 'P') setNodePWMColor(idx, 255, 0,   255); // 紫
            else if (color == 'Y') setNodePWMColor(idx, 255, 255, 0);   // 黃
            else if (color == 'G') setNodePWMColor(idx, 0,   255, 0);   // 綠
            else if (color == 'B') setNodePWMColor(idx, 0,   0,   255); // 藍
            else if (color == 'R') setNodePWMColor(idx, 255, 0,   0);   // 紅
            else if (color == 'W') setNodePWMColor(idx, 255, 255, 255); // 白
        }
    }
}

void setup() {
    WiFi.mode(WIFI_STA); WiFi.disconnect();
    esp_wifi_set_promiscuous(true);
    esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_promiscuous(false);

    if (esp_now_init() != ESP_OK) return;
    esp_now_register_recv_cb(OnDataRecv);

    for (int i = 0; i < 5; i++) {
        pinMode(leds[i].redPin, OUTPUT); 
        pinMode(leds[i].greenPin, OUTPUT); 
        pinMode(leds[i].bluePin, OUTPUT);
        setNodePWMColor(i, 0, 0, 0); 
    }
}
void loop() { delay(10); }