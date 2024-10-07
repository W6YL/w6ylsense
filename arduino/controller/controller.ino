#define POWER_RELAY_PIN 12
#define LED_RELAY_PIN 11

#define TOGGLE_LED_PIN 10
#define ENABLE_PIN 9
#define _DISABLE_PIN 8


#ifndef Debounce_h
#define Debounce_h

///////////////// BELOW CLASS LICENSE
/*
  Debounce - v1.2 - May 12, 2021.
  MIT Licensed.
  https://github.com/wkoch/Debounce

  Arduino library for button debouncing.
  Clearly based on the debounce example from the site: http://arduino.cc/en/Tutorial/Debounce
  
  Created by William Koch, improved by the community.
*/

#include "Arduino.h"

class Debounce
{
public:
  // Debounces an input with a 50ms debounce by default.
  // Optional parameters:
  //    - Adjust the delay in milliseconds.
  //    - Pull-Up input.
  // Button pin is required.
  Debounce(byte button, unsigned long delay = 50, boolean pullup = true);

  byte read();          // returns the debounced button state: LOW or HIGH.
  unsigned int count(); // Returns the number of times the button was pressed.
  void resetCount();    // Resets the button count number.

private:
  byte _button, _state, _lastState, _reading;
  unsigned int _count;
  unsigned long _delay, _last;
  boolean _wait;
  boolean _invert;
};

#endif

// Debounces an input with a 50ms debounce by default.
// Optional parameters:
//    - Adjust the delay in milliseconds.
//    - Pull-Up input.
Debounce::Debounce(byte button, unsigned long delay, boolean pullup)
{
  _invert = false;
  if (pullup)
  {
    pinMode(button, INPUT_PULLUP);
    _invert = true;
  }
  
  _button = button;
  _delay = delay;
  _state = _lastState = _reading = (_invert ? !digitalRead(_button) : digitalRead(_button));
  _last = millis();
  _count = 0;
}

// returns the debounced button state: LOW or HIGH.
byte Debounce::read()
{
  _reading = (_invert ? !digitalRead(_button) : digitalRead(_button)); // get current button state.
  if (_reading != _lastState)
  {                   // detect edge: current vs last state:
    _last = millis(); // store millis if change was detected.
    _wait = true;     // Just to avoid calling millis() unnecessarily.
  }

  if (_wait && (millis() - _last) > _delay)
  { // after the delay has passed:
    if (_reading != _state)
    {                    // if the change wasn't stored yet:
      _count++;          // Stores each change.
      _state = _reading; // store the button state change.
      _wait = false;
    }
  }
  _lastState = _reading;
  return _state;
}

// Returns the number of times the button was pressed.
unsigned int Debounce::count()
{
  Debounce::read();
  return _count / 2; // Counts only a full press + release.
}

// Resets the button count number.
void Debounce::resetCount()
{
  _count = 0;
  return;
}

///////////////// END LICENSE /////////////////


void handshake() {
  Serial.read();
  while (Serial.available() == 0) {
    Serial.write(0xFF);
    delay(100);
  }
  delay(500);
  Serial.write(0x02);
}

Debounce LED_Button(TOGGLE_LED_PIN);
Debounce Enable_Button(ENABLE_PIN);
Debounce Disable_Button(_DISABLE_PIN);

bool led_button_pressed = false;
bool enable_button_pressed = false;
bool disable_button_pressed = false;

bool led_state = false;
bool pwr_state = false;

void setup() {
  pinMode(POWER_RELAY_PIN, OUTPUT);
  pinMode(LED_RELAY_PIN, OUTPUT);

  pinMode(TOGGLE_LED_PIN, INPUT_PULLUP);
  pinMode(ENABLE_PIN, INPUT_PULLUP);
  pinMode(_DISABLE_PIN, INPUT_PULLUP);
  Serial.begin(9600);

  handshake();
}

void waitForSerial(int numBytes) {
  while (Serial.available() < numBytes) { }
}

void loop() {
  bool led_button_state = LED_Button.read();
  bool enable_button_state = Enable_Button.read();
  bool disable_button_state = Disable_Button.read();

  if (led_button_state && !led_button_pressed) {
    led_button_pressed = true;
    Serial.write(0x01); // Led button was pressed
  } else if (!led_button_state) {
    led_button_pressed = false;
  }

  if (enable_button_state && !enable_button_pressed) {
    enable_button_pressed = true;
    Serial.write(0x02); // Enable button was pressed
  } else if (!enable_button_state) {
    enable_button_pressed = false;
  }

  if (!disable_button_state && disable_button_pressed) {
    disable_button_pressed = false;
    Serial.write(0x03); // Disable button was pressed
  } else if (disable_button_state) {
    disable_button_pressed = true;
  }
  

  // If there are bytes available to read
  if (Serial.available() > 0) {
    int cmd = Serial.read();
    switch (cmd) {
      case 0x01: // Set light state
        waitForSerial(1); 
        led_state = Serial.read();
        break;
      case 0x02: // Set power state
        waitForSerial(1);
        pwr_state = Serial.read();
        break;
    }
  }


  digitalWrite(LED_RELAY_PIN, led_state);
  digitalWrite(POWER_RELAY_PIN, pwr_state);
}
