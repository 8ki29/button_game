// ==========================================
// Board 2: LED Driver MCU (Handshake & Core v3.3.8)
// ==========================================
#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>

struct RGBLed { int redPin; int greenPin; int bluePin; };

// Version 2.3 黃金配置
RGBLed leds[6] = {
    {4,  2,  15}, {13, 12, 14}, {5,  17, 16}, 
    {27, 26, 25}, {21, 19, 18}, {33, 32, 23} 
};

// 【回傳指定】Board 1 的 MAC 位址，讓 B2 開機可以主動敲門
uint8_t b1Address[] = {0x70, 0x4B, 0xCA, 0x49, 0x5A, 0x48};

void setNodeColor(int index, bool r, bool g, bool b) {
    digitalWrite(leds[index].redPin,   r ? HIGH : LOW);
    digitalWrite(leds[index].greenPin, g ? HIGH : LOW);
    digitalWrite(leds[index].bluePin,  b ? HIGH : LOW);
}

void OnDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *incomingData, int len) {
    if (len > 0) {
        char cmd = (char)incomingData[0];
        
        // 如果收到 B1 的回應
        if (cmd == 'H') {
            Serial.println("\n=========================================");
            Serial.println("🤝 [LINK SUCCESS] Board 1 has acknowledged Board 2!");
            Serial.println("=========================================\n");
            return;
        }
        
        // 原本的燈光遊戲解碼邏輯
        switch (cmd) {
            case 'X': for(int i=0; i<6; i++) setNodeColor(i, false, false, false); break;
            case 'Y': 
                setNodeColor(0, true,  false, true);  setNodeColor(1, true,  true,  false);
                setNodeColor(2, false, true,  false); setNodeColor(3, false, false, true); 
                setNodeColor(4, true,  false, false); setNodeColor(5, true,  true,  true);  
                break;
            case '0': setNodeColor(0, false, false, false); break;
            case '2': setNodeColor(1, false, false, false); break;
            case '4': setNodeColor(2, false, false, false); break;
            case '6': setNodeColor(3, false, false, false); break;
            case '8': setNodeColor(4, false, false, false); break;
            case 'A': setNodeColor(5, false, false, false); break;
            case '1': setNodeColor(0, true,  false, true);  break;
            case '3': setNodeColor(1, true,  true,  false); break;
            case '5': setNodeColor(2, false, true,  false); break;
            case '7': setNodeColor(3, false, false, true);  break;
            case '9': setNodeColor(4, true,  false, false); break;
            case 'B': setNodeColor(5, true,  true,  true);  break;
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(500);
    
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    esp_wifi_set_promiscuous(true);
    esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_promiscuous(false);

    if (esp_now_init() != ESP_OK) {
        return;
    }
    
    esp_now_register_recv_cb(OnDataRecv);

    // 讓 B2 也能主動發報給 B1
    esp_now_peer_info_t peerInfo;
    memset(&peerInfo, 0, sizeof(peerInfo));
    memcpy(peerInfo.peer_addr, b1Address, 6);
    peerInfo.channel = 1;
    peerInfo.encrypt = false;
    peerInfo.ifidx = WIFI_IF_STA;
    esp_now_add_peer(&peerInfo);

    for (int i = 0; i < 6; i++) {
        pinMode(leds[i].redPin, OUTPUT); pinMode(leds[i].greenPin, OUTPUT); pinMode(leds[i].bluePin, OUTPUT);
        setNodeColor(i, false, false, false);
    }
    
    Serial.println("[SYS] Board 2 Online. Sending handshake token to Board 1...");
    
    // 【核心魔法】開機立刻大喊一聲 'H' 向 B1 報到！
    char handshake = 'H';
    esp_now_send(b1Address, (uint8_t *) &handshake, sizeof(handshake));
}

void loop() {
    delay(50); 
}