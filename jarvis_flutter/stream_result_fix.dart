
  void _onStreamResult(SpeechRecognitionResult result) {
    String currentText = result.recognizedWords.trim();
    if (currentText.isEmpty) return;
    
    // Atualiza UI
    if (_currentState != JarvisState.speaking || currentText.length > 5) {
       setState(() => _lastTranscript = currentText);
    }

    // --- BARGE-IN (Interrupção) ---
    for (String t in _wakeWords) {
      if (currentText.toLowerCase().contains(t)) {
         
         // Se estiver falando, CORTA
         if (_currentState == JarvisState.speaking) {
            print(">>> BARGE-IN: INTERROMPENDO ÁUDIO <<<");
            _audioPlayer.stop(); 
         }
         
         // Só processa se não estiver já em modo comando (para não resetar à toa)
         if (!_isCommandMode) {
             print(">>> GATILHO DETECTADO (STREAM) <<<");
             _enterCommandMode();
             _playSystemSound('activation');
             _lastTranscript = ""; 
             return; // Sai e espera o próximo bloco de áudio limpo
         }
      }
    }

    // --- VAD MANUAL ---
    _manualSilenceTimer?.cancel();
    _manualSilenceTimer = Timer(const Duration(seconds: 2), () {
        _processFinalBlock(currentText);
    });
  }
