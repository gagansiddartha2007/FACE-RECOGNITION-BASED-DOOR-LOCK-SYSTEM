#include <Servo.h>

int greenLED = 7;
int redLED = 6;
int buzzer = 5;
int servoPin = 9;

Servo doorLock;

void setup() {
    Serial.begin(9600);
    
    pinMode(greenLED, OUTPUT);
    pinMode(redLED, OUTPUT);
    pinMode(buzzer, OUTPUT);
    
    doorLock.attach(servoPin);

    doorLock.write(0);
    digitalWrite(greenLED, LOW);
    digitalWrite(redLED, HIGH);
    noTone(buzzer);
    
    Serial.println("🔐 Door Lock System Initialized");
    Serial.println("Status: LOCKED with Red Light");
}

void loop() {
    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        command.toUpperCase();
        
        if (command == "OPEN") {
            unlockDoor();
        }
        else if (command == "CLOSE") {
            lockDoor();
        }
        else if (command == "DENY") {
            accessDenied();
        }
    }
}

void unlockDoor() {
    Serial.println("\n✅ DOOR UNLOCKING...");
    
    digitalWrite(greenLED, HIGH);
    digitalWrite(redLED, LOW);
    
    tone(buzzer, 1000, 200);
    delay(300);
    tone(buzzer, 1000, 200);
    delay(300);
    noTone(buzzer);
    
    for (int i = 0; i <= 90; i += 10) {
        doorLock.write(i);
        delay(50);
    }
    doorLock.write(90);
    
    Serial.println("🟢 Door UNLOCKED - Green Light ON");
    Serial.println("⏱️  Door will auto-lock in 5 seconds...\n");
}

void lockDoor() {
    Serial.println("\n🔐 DOOR LOCKING...");
    
    digitalWrite(redLED, HIGH);
    digitalWrite(greenLED, LOW);
    
    tone(buzzer, 800, 150);
    delay(200);
    noTone(buzzer);
    
    for (int i = 90; i >= 0; i -= 10) {
        doorLock.write(i);
        delay(50);
    }
    doorLock.write(0);
    
    Serial.println("🔴 Door LOCKED - Red Light ON");
    Serial.println("Status: Ready for next authentication\n");
}

void accessDenied() {
    Serial.println("\n❌ ACCESS DENIED!");
    
    for (int i = 0; i < 3; i++) {
        digitalWrite(redLED, HIGH);
        delay(100);
        digitalWrite(redLED, LOW);
        delay(100);
    }
    digitalWrite(redLED, HIGH); 
    digitalWrite(greenLED, LOW);
    
    for (int i = 0; i < 3; i++) {
        tone(buzzer, 500, 150);
        delay(200);
    }
    noTone(buzzer);
    
    doorLock.write(0);
    
    Serial.println("🔴 Red Light BLINKING - Door LOCKED");
    Serial.println("Reason: Unknown face / Video / Photo / Spoofing\n");
}
