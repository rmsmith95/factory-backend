// L298N pins
const int IN1 = 9;
const int IN2 = 8;

void setup() {
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  stopMotor();

  Serial.begin(115200);
  Serial.println("Ready: FWD ms | BKW ms | STOP");

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  delay(1000);
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readString(); 
    // String cmd = Serial.readStringUntil('\n');
    // cmd.trim();

    if (cmd == "STOP") {
      stopMotor();
      Serial.println("STOPPED");
    } 
    else if (cmd.startsWith("FWD") || cmd.startsWith("BKW")) {
      bool forward = cmd.startsWith("FWD");

      // run motor
      digitalWrite(IN1, forward);
      digitalWrite(IN2, !forward);
      Serial.println(forward ? "FWD" : "BKW");

      delay(1000);  // pause for the specified duration
      stopMotor();
      Serial.println("DONE");
    } 
    else {
      Serial.println("UNKNOWN CMD");
    }
  }
}

void stopMotor() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
}
