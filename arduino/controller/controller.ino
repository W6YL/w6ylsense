#define LED_RELAY_PIN 11
#define BUTTON_PIN 12

void handshake() {
  Serial.read();
  while (Serial.available() == 0) {
    Serial.write(0xFF);
    delay(100);
  }
  delay(500);
  Serial.write(0x02);
}

void setup() {
  pinMode(LED_RELAY_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  Serial.begin(9600);

  handshake();
}

bool pressedNow = false;
bool buttonState = false;
bool lastButtonState = false;
bool lightState = false;

unsigned long debounceDelay = 50;
unsigned long lastDebounce = 0;

void waitForSerial(int numBytes) {
  while (Serial.available() < numBytes) { }
}

void loop() {
  // If there are bytes available to read
  if (Serial.available() > 0) {
    int cmd = Serial.read();
    switch (cmd) {
      case 0x01: // Set light state
        waitForSerial(1); 
        lightState = Serial.read();
        break;
    }
  }

  // Read the button state & debounce
  buttonState = !digitalRead(BUTTON_PIN);
  if (buttonState != lastButtonState) {
    lastDebounce = millis();
  }
  if ((millis() - lastDebounce) > debounceDelay) {
    if (buttonState && !pressedNow) {
      Serial.write(0x01); // Button pressed, send to serial
      pressedNow = true;
    }
    if (!buttonState) {
      pressedNow = false;
    }
  }
  digitalWrite(LED_RELAY_PIN, lightState);
  lastButtonState = buttonState;
}
