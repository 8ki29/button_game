const int buttonLeft = 23;  // Left Button (Green)
const int buttonRight = 22; // Right Button (Blue)
const int ledGreen = 2;     // Green LED (D2)
const int ledBlue = 15;     // Blue LED (D15)

void setup() {
  Serial.begin(115200);
  pinMode(buttonLeft, INPUT_PULLUP);
  pinMode(buttonRight, INPUT_PULLUP);
  pinMode(ledGreen, OUTPUT);
  pinMode(ledBlue, OUTPUT);
  
  // Start with LEDs off
  digitalWrite(ledGreen, LOW);
  digitalWrite(ledBlue, LOW);
}

void loop() {
  // Read inputs from buttons
  if (digitalRead(buttonLeft) == LOW) {
    Serial.println("B1");
    delay(150); // Small debounce
  }
  if (digitalRead(buttonRight) == LOW) {
    Serial.println("B2");
    delay(150); // Small debounce
  }

  // Intercept output instructions from PC
  if (Serial.available() > 0) {
    char command = Serial.read();
    if (command == 'G') digitalWrite(ledGreen, HIGH);
    else if (command == 'g') digitalWrite(ledGreen, LOW);
    else if (command == 'B') digitalWrite(ledBlue, HIGH);
    else if (command == 'b') digitalWrite(ledBlue, LOW);
    else if (command == 'X') {
      digitalWrite(ledGreen, LOW);
      digitalWrite(ledBlue, LOW);
    }
  }
  delay(5);
}