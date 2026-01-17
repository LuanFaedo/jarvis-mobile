import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:audioplayers/audioplayers.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  runApp(const JarvisApp());
}

// ============================================================
// ESTADOS DO JARVIS (Always Listening)
// ============================================================
enum JarvisState {
  idle,              // Esperando wake word
  listeningWakeWord, // Escutando ativamente por "Jarvis"
  listeningCommand,  // Jarvis ativado, esperando comando
  processing,        // Processando no servidor
  speaking,          // Jarvis falando resposta
  followUp,          // Esperando continuação da conversa
}

class JarvisApp extends StatelessWidget {
  const JarvisApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'J.A.R.V.I.S.',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: Colors.black,
        primaryColor: const Color(0xFF00FFFF),
        colorScheme: ColorScheme.dark(
          primary: const Color(0xFF00FFFF),
          secondary: const Color(0xFF008B8B),
          surface: const Color(0xFF050505),
        ),
        useMaterial3: true,
      ),
      home: const HUDInterface(),
    );
  }
}

class HUDInterface extends StatefulWidget {
  const HUDInterface({super.key});

  @override
  State<HUDInterface> createState() => _HUDInterfaceState();
}

class _HUDInterfaceState extends State<HUDInterface> with TickerProviderStateMixin {
  // Controllers
  final TextEditingController _urlController = TextEditingController(text: 'http://192.168.137.1:5000');
  final TextEditingController _messageController = TextEditingController();

  // Socket & Audio
  late IO.Socket socket;
  final AudioPlayer _audioPlayer = AudioPlayer();
  final AudioPlayer _feedbackPlayer = AudioPlayer();

  // Speech Recognition (Wake Word)
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _speechEnabled = false;

  // Animation Controllers
  late AnimationController _pulseController;
  late AnimationController _waveController;
  late AnimationController _glowController;

  // State
  JarvisState _jarvisState = JarvisState.idle;
  String _status = "INICIALIZANDO...";
  String _lastTranscript = "";
  String _jarvisResponse = "";
  bool _isConnected = false;
  bool _alwaysListening = true; // Toggle para modo always listening
  bool _shouldContinueConversation = false; // Controle de fluxo contínuo

  // VAD (Voice Activity Detection)
  Timer? _silenceTimer;
  DateTime? _lastSpeechTime;
  static const Duration _silenceThreshold = Duration(milliseconds: 1500);

  // Push-to-Talk (Long Press) - STT Local
  bool _isPushToTalk = false;
  String _partialTranscript = ""; // Para feedback em tempo real

  // Wake Words (com variações para fuzzy matching)
  final List<String> _wakeWords = [
    'jarvis', 'jarves', 'jarvas', 'jarbis', 'jarvez',
    'service', 'servis', 'chavis', 'chaves', 'javis',
    'jardis', 'jairvis', 'jarvice', 'charvis'
  ];

  @override
  void initState() {
    super.initState();
    _initAnimations();
    _initSpeech();
    _requestPermissions();
    _setupAudioPlayerListeners();
  }

  void _initAnimations() {
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat();

    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
  }

  Future<void> _initSpeech() async {
    _speechEnabled = await _speech.initialize(
      onStatus: _onSpeechStatus,
      onError: (error) {
        print('[STT] Error: ${error.errorMsg}');
        // Tratamento silencioso de erros no modo contínuo
        if (error.errorMsg == 'error_speech_timeout' || error.errorMsg == 'error_no_match') {
          // Se deu timeout esperando comando, volta pro Wake Word sem alarde
          if (_jarvisState == JarvisState.listeningCommand) {
             print('[STT] Timeout silencioso - Voltando a dormir');
             _startWakeWordListener();
          }
        }
      },
    );
    setState(() {});

    if (_speechEnabled && _alwaysListening) {
      _startWakeWordListener();
    }
  }

  void _onSpeechStatus(String status) {
    print('[STT] Status: $status');

    if ((status == 'notListening' || status == 'done') && _isConnected) {
      // LOOP INFINITO: Reinicia sempre que parar, a menos que esteja falando (JarvisState.speaking)
      if (_jarvisState != JarvisState.speaking && _jarvisState != JarvisState.processing) {
          print("[LOOP] Reiniciando escuta contínua...");
          Future.delayed(const Duration(milliseconds: 100), _startContinuousListening);
      }
    }
  }

  void _setupAudioPlayerListeners() {
    _audioPlayer.onPlayerComplete.listen((_) async {
      print('[AUDIO] Jarvis terminou de falar. Continue? $_shouldContinueConversation');

      if (_shouldContinueConversation && _isConnected) {
        // MODO CONVERSA CONTÍNUA
        setState(() {
          _jarvisState = JarvisState.listeningCommand;
          _status = "AGUARDANDO COMANDO...";
        });
        
        // Pequeno delay para evitar captar o próprio eco
        await Future.delayed(const Duration(milliseconds: 500));
        
        // Garante que parou antes de começar (fix error_busy)
        await _speech.stop();
        _startCommandListener();
        
      } else {
        // FIM DA CONVERSA -> VOLTA A DORMIR
        setState(() {
          _jarvisState = JarvisState.idle;
          _status = "AGUARDANDO 'JARVIS'...";
        });
        
        if (_alwaysListening) {
          await _speech.stop();
          _startWakeWordListener();
        }
      }
    });
  }

  Future<void> _requestPermissions() async {
    await Permission.microphone.request();
    await Permission.storage.request();
    await Permission.camera.request();
  }

  // ============================================================
  // QR CODE SCANNER (Quick Connect)
  // ============================================================

  void _openQRScanner() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        height: MediaQuery.of(context).size.height * 0.7,
        decoration: BoxDecoration(
          color: Colors.black,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          border: Border.all(color: Colors.cyan.withOpacity(0.5)),
        ),
        child: Column(
          children: [
            // Header
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: Colors.cyan.withOpacity(0.3))),
              ),
              child: Row(
                children: [
                  const Icon(Icons.qr_code_scanner, color: Colors.cyanAccent),
                  const SizedBox(width: 12),
                  Text(
                    "QUICK CONNECT",
                    style: GoogleFonts.orbitron(
                      color: Colors.cyanAccent,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white54),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),

            // Scanner
            Expanded(
              child: ClipRRect(
                borderRadius: const BorderRadius.vertical(bottom: Radius.circular(20)),
                child: MobileScanner(
                  onDetect: (capture) {
                    final List<Barcode> barcodes = capture.barcodes;
                    for (final barcode in barcodes) {
                      if (barcode.rawValue != null) {
                        String scannedUrl = barcode.rawValue!;

                        // Valida se parece uma URL
                        if (scannedUrl.startsWith('http://') || scannedUrl.startsWith('https://')) {
                          // Fecha o scanner
                          Navigator.pop(context);

                          // Atualiza a URL
                          setState(() {
                            _urlController.text = scannedUrl;
                            _status = "URL ESCANEADA!";
                          });

                          // Feedback visual
                          HapticFeedback.mediumImpact();

                          // Conecta automaticamente
                          Future.delayed(const Duration(milliseconds: 500), () {
                            if (!_isConnected) {
                              _connectToServer();
                            }
                          });

                          return;
                        }
                      }
                    }
                  },
                ),
              ),
            ),

            // Instrução
            Container(
              padding: const EdgeInsets.all(16),
              child: Text(
                "Aponte para o QR Code exibido no servidor",
                style: GoogleFonts.sourceCodePro(
                  color: Colors.white54,
                  fontSize: 12,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // MEMÓRIA CONTÍNUA (Always Listening Loop)
  // ============================================================

  void _startContinuousListening() async {
    if (!_speechEnabled || !_isConnected) return;
    
    // Se já estiver ouvindo, não faz nada (evita sobreposição)
    if (_speech.isListening) return;

    setState(() {
      _jarvisState = JarvisState.listeningWakeWord; // Estado visual "Ouvindo"
      _status = "MEMÓRIA ATIVA (OUVINDO...)";
    });

    try {
      await _speech.listen(
        onResult: _onContinuousResult,
        listenFor: const Duration(seconds: 25), // Ciclos de 25s
        pauseFor: const Duration(seconds: 3),   // 3s de silêncio para processar (SENSIVEL)
        partialResults: true,
        localeId: 'pt_BR',
        listenMode: stt.ListenMode.dictation,
        cancelOnError: true,
      );
    } catch (e) {
      print("[STT] Erro Loop: $e");
      // Reinicia em breve se der erro
      Future.delayed(const Duration(seconds: 1), _startContinuousListening);
    }
  }

  void _onContinuousResult(SpeechRecognitionResult result) {
    String transcript = result.recognizedWords.trim();
    
    // Atualiza UI em tempo real
    if (transcript.isNotEmpty) {
       setState(() => _lastTranscript = transcript);
    }

    // Só processa se for resultado FINAL
    if (result.finalResult && transcript.isNotEmpty) {
      print("[STT] Final: '$transcript'");
      
      // Classificação: É comando para o Jarvis ou apenas contexto?
      bool isCommand = _wakeWords.any((w) => transcript.toLowerCase().contains(w));

      if (isCommand) {
        // --- MODO ATIVO (COMANDO) ---
        print(">>> COMANDO DETECTADO <<<");
        _playFeedbackSound(); // Feedback sonoro
        
        // Remove a wake word para limpar o comando
        String cleanText = transcript;
        for (var w in _wakeWords) {
          cleanText = cleanText.replaceAll(RegExp(w, caseSensitive: false), "").trim();
        }
        
        // Se sobrou texto, envia como comando. Se só falou "Jarvis", avisa server
        String finalCmd = cleanText.isEmpty ? "Jarvis" : cleanText;
        
        _sendCommandToServer(finalCmd, triggerType: 'active_command');
        
        // Para momentaneamente para ouvir a resposta
        _speech.stop();
        
      } else {
        // --- MODO PASSIVO (MEMÓRIA) ---
        // Envia silenciosamente para o banco de dados
        if (transcript.length > 4) { // Ignora "oi", "ah"
           print(">>> LOG PASSIVO <<<");
           _sendPassiveLog(transcript);
        }
        
        // Reinicia escuta IMEDIATAMENTE para não perder nada
        // Pequeno delay para evitar crash do plugin
        Future.delayed(const Duration(milliseconds: 50), _startContinuousListening);
      }
    }
  }

  void _sendPassiveLog(String text) {
    if (!_isConnected) return;
    socket.emit('passive_log', {
      'user_id': 'Mestre',
      'text': text,
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  // Substitui o antigo _sendCommandToServer para suportar o novo evento
  void _sendCommandToServer(String command, {String triggerType = 'active_command'}) {
    if (!_isConnected || command.isEmpty) return;

    setState(() {
      _jarvisState = JarvisState.processing;
      _status = "PROCESSANDO...";
    });

    socket.emit('active_command', {
      'user_id': 'Mestre',
      'text': command,
      'trigger_type': triggerType,
    });
  }

  // ============================================================
  // CONEXÃO SOCKET.IO
  // ============================================================

  void _connectToServer() {
    if (_isConnected) {
      _speech.stop();
      socket.disconnect();
      return;
    }

    setState(() => _status = "CONECTANDO...");

    socket = IO.io(_urlController.text, IO.OptionBuilder()
      .setTransports(['websocket'])
      .disableAutoConnect()
      .build());

    socket.connect();

    socket.onConnect((_) {
      print("[SOCKET] Conectado!");
      setState(() {
        _isConnected = true;
        _jarvisState = JarvisState.idle;
        _status = "ONLINE - Diga 'JARVIS'";
      });

      // Inicia always listening
      if (_alwaysListening && _speechEnabled) {
        _startContinuousListening();
      }
    });

    socket.onDisconnect((_) {
      print("[SOCKET] Desconectado.");
      _speech.stop();
      _silenceTimer?.cancel();
      if (mounted) {
        setState(() {
          _isConnected = false;
          _jarvisState = JarvisState.idle;
          _status = "OFFLINE";
        });
      }
    });

    // ---- EVENTOS DO SERVIDOR ----

    // Evento padrao do server.py v2
    socket.on('bot_response', (data) async {
       print("[SOCKET] bot_response recebido");
       await _handleFullResponse(data);
    });

    socket.on('jarvis_ack', (data) {
      String response = data?['response'] ?? "Pois não?";
      setState(() {
        _status = response;
        _jarvisState = JarvisState.listeningCommand;
      });
      _playAudioResponse(data?['audio']);
    });
  }

  // ============================================================
  // REPRODUÇÃO DE ÁUDIO
  // ============================================================

  Future<void> _playFeedbackSound() async {
    try {
      await _feedbackPlayer.play(AssetSource('sounds/activation.mp3'));
    } catch (e) {
      HapticFeedback.mediumImpact();
    }
  }

  Future<void> _playAudioResponse(String? audioB64) async {
    if (audioB64 == null || audioB64.isEmpty) return;

    setState(() => _jarvisState = JarvisState.speaking);

    try {
      final bytes = base64Decode(audioB64);
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/jarvis_response.mp3');
      await file.writeAsBytes(bytes);
      await _audioPlayer.play(DeviceFileSource(file.path));
    } catch (e) {
      print('[AUDIO] Erro: $e');
      // Se der erro no audio, decide se continua mesmo assim
      if (_shouldContinueConversation) _startCommandListener();
    }
  }

  Future<void> _handleFullResponse(dynamic data) async {
    if (data == null) return;

    // Atualiza flag de conversa contínua
    bool continuar = data['continue_conversation'] ?? true;
    
    setState(() {
      _jarvisState = JarvisState.speaking;
      _jarvisResponse = data['text'] ?? "";
      _status = "RESPONDENDO...";
      _shouldContinueConversation = continuar;
    });
    
    print("[LOGICA] Continuar conversa? $continuar");

    if (data['audio'] != null) {
      await _playAudioResponse(data['audio']);
    } else {
        // Se não tem áudio, dispara o fluxo manualmente
        if (continuar) {
            await Future.delayed(const Duration(seconds: 2));
            _startCommandListener();
        }
    }
  }

  // ============================================================
  // PUSH-TO-TALK (Long Press com STT Local - Edge Computing)
  // ============================================================

  Future<void> _startPushToTalk() async {
    if (!_isConnected || !_speechEnabled) return;

    // Para qualquer escuta anterior
    await _speech.stop();
    _silenceTimer?.cancel();

    setState(() {
      _isPushToTalk = true;
      _jarvisState = JarvisState.listeningCommand;
      _status = "OUVINDO (SEGURE)...";
      _partialTranscript = "";
      _lastTranscript = "";
    });

    // Feedback tátil
    HapticFeedback.mediumImpact();

    try {
      await _speech.listen(
        onResult: _onPushToTalkResult,
        listenFor: const Duration(seconds: 60), // Escuta enquanto segurar
        pauseFor: const Duration(seconds: 30),  // Não para por silêncio
        partialResults: true,
        localeId: 'pt_BR',
        listenMode: stt.ListenMode.dictation,
      );
    } catch (e) {
      print("[PTT] Erro: $e");
      setState(() {
        _isPushToTalk = false;
        _status = "ERRO STT: $e";
      });
    }
  }

  void _onPushToTalkResult(SpeechRecognitionResult result) {
    if (!_isPushToTalk) return;

    String transcript = result.recognizedWords.trim();

    setState(() {
      _partialTranscript = transcript;
      _lastTranscript = transcript;
    });

    print("[PTT] Parcial: $transcript");
  }

  Future<void> _stopPushToTalk() async {
    if (!_isPushToTalk) return;

    // Captura o texto final antes de parar
    String finalText = _partialTranscript.isNotEmpty
        ? _partialTranscript
        : _lastTranscript;

    await _speech.stop();

    setState(() {
      _isPushToTalk = false;
    });

    // Feedback tátil
    HapticFeedback.lightImpact();

    if (finalText.isNotEmpty && finalText.length > 1) {
      print("[PTT] Enviando: $finalText");
      _sendCommandToServer(finalText, triggerType: 'push_to_talk');
    } else {
      // Nada reconhecido, volta ao estado anterior
      setState(() {
        _status = "NADA DETECTADO";
        _jarvisState = JarvisState.idle;
      });

      // Retorna ao wake word após 1 segundo
      Future.delayed(const Duration(seconds: 1), () {
        if (_alwaysListening && _isConnected) {
          _startWakeWordListener();
        }
      });
    }
  }

  void _sendTextMessage() {
    String text = _messageController.text.trim();
    if (text.isEmpty || !_isConnected) return;

    _sendCommandToServer(text, triggerType: 'keyboard');
    _messageController.clear();
    FocusScope.of(context).unfocus();
  }

  // ============================================================
  // UI BUILD (MANTIDA IGUAL)
  // ============================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            // Cantos HUD
            _buildCorner(top: 20, left: 20),
            _buildCorner(top: 20, right: 20),
            _buildCorner(bottom: 20, left: 20),
            _buildCorner(bottom: 20, right: 20),

            Column(
              children: [
                // Header
                _buildHeader(),

                const Spacer(),

                // Orbe Central (Estado Visual)
                _buildCentralOrb(),

                const SizedBox(height: 20),

                // Status Text
                _buildStatusText(),

                const SizedBox(height: 10),

                // Transcrição em tempo real (mostra durante escuta também)
                if (_lastTranscript.isNotEmpty ||
                    _jarvisState == JarvisState.listeningCommand ||
                    _jarvisState == JarvisState.listeningWakeWord)
                  _buildTranscriptBubble(),

                const Spacer(),

                // Input de texto
                _buildTextInput(),

                // Barra de status
                _buildStatusBar(),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        children: [
          Text("J.A.R.V.I.S.", style: GoogleFonts.orbitron(
            fontSize: 28, fontWeight: FontWeight.bold, color: Colors.cyanAccent,
          )),
          const SizedBox(height: 20),

          // URL + QR Scanner + Toggle Always Listening
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.cyan.withOpacity(0.3)),
                    borderRadius: BorderRadius.circular(4),
                    color: Colors.cyan.withOpacity(0.05),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _urlController,
                          style: GoogleFonts.orbitron(color: Colors.white, fontSize: 10),
                          decoration: const InputDecoration(border: InputBorder.none, hintText: "SERVER"),
                        ),
                      ),
                      // Botão QR Code Scanner
                      IconButton(
                        icon: const Icon(Icons.qr_code_scanner,
                          color: Colors.cyanAccent, size: 20),
                        onPressed: _openQRScanner,
                        tooltip: "Escanear QR Code",
                      ),
                      // Botão Conectar/Desconectar
                      IconButton(
                        icon: Icon(_isConnected ? Icons.link_off : Icons.link,
                          color: _isConnected ? Colors.greenAccent : Colors.cyanAccent, size: 20),
                        onPressed: _connectToServer,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // Toggle Always Listening
              GestureDetector(
                onTap: () {
                  setState(() => _alwaysListening = !_alwaysListening);
                  if (_alwaysListening && _isConnected) {
                    _startWakeWordListener();
                  } else {
                    _speech.stop();
                  }
                },
                child: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    border: Border.all(color: _alwaysListening ? Colors.greenAccent : Colors.grey),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Icon(
                    _alwaysListening ? Icons.hearing : Icons.hearing_disabled,
                    color: _alwaysListening ? Colors.greenAccent : Colors.grey,
                    size: 20,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildCentralOrb() {
    Color orbColor = _getOrbColor();
    double orbSize = 150;

    return GestureDetector(
      onLongPressStart: (_) => _startPushToTalk(),
      onLongPressEnd: (_) => _stopPushToTalk(),
      onTap: () {
        // Tap para ativar manualmente (modo wake word)
        if (_jarvisState == JarvisState.idle || _jarvisState == JarvisState.listeningWakeWord) {
          _onWakeWordActivated("");
        }
      },
      child: AnimatedBuilder(
        animation: _pulseController,
        builder: (context, child) {
          double scale = 1.0 + (_pulseController.value * 0.1);
          double glowIntensity = _jarvisState == JarvisState.listeningCommand ? 0.8 : 0.3;

          return Container(
            width: orbSize * scale,
            height: orbSize * scale,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  orbColor.withOpacity(0.3),
                  orbColor.withOpacity(0.1),
                  Colors.transparent,
                ],
              ),
              boxShadow: [
                BoxShadow(
                  color: orbColor.withOpacity(glowIntensity * _glowController.value),
                  blurRadius: 30,
                  spreadRadius: 10,
                ),
              ],
            ),
            child: Container(
              margin: const EdgeInsets.all(15),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: orbColor, width: 3),
                color: Colors.black.withOpacity(0.8),
              ),
              child: Center(
                child: _buildOrbContent(orbColor),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildOrbContent(Color color) {
    IconData icon;
    String text = "";

    switch (_jarvisState) {
      case JarvisState.idle:
        icon = Icons.power_settings_new;
        text = "IDLE";
        break;
      case JarvisState.listeningWakeWord:
        icon = Icons.hearing;
        text = "WAKE";
        break;
      case JarvisState.listeningCommand:
        icon = Icons.mic;
        text = "OUVINDO";
        break;
      case JarvisState.processing:
        icon = Icons.sync;
        text = "PROC.";
        break;
      case JarvisState.speaking:
        icon = Icons.volume_up;
        text = "FALANDO";
        break;
      case JarvisState.followUp:
        icon = Icons.chat;
        text = "CONT.";
        break;
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 40, color: color),
        const SizedBox(height: 5),
        Text(text, style: GoogleFonts.orbitron(fontSize: 10, color: color)),
      ],
    );
  }

  Color _getOrbColor() {
    switch (_jarvisState) {
      case JarvisState.idle:
        return Colors.grey;
      case JarvisState.listeningWakeWord:
        return Colors.cyanAccent;
      case JarvisState.listeningCommand:
        return Colors.orangeAccent;
      case JarvisState.processing:
        return Colors.yellowAccent;
      case JarvisState.speaking:
        return Colors.greenAccent;
      case JarvisState.followUp:
        return Colors.purpleAccent;
    }
  }

  Widget _buildStatusText() {
    return Text(
      _getStateLabel(),
      style: GoogleFonts.orbitron(
        color: _getOrbColor(),
        fontSize: 12,
        fontWeight: FontWeight.w500,
      ),
    );
  }

  String _getStateLabel() {
    switch (_jarvisState) {
      case JarvisState.idle:
        return _alwaysListening ? "ALWAYS LISTENING OFF" : "TOQUE PARA ATIVAR";
      case JarvisState.listeningWakeWord:
        return "AGUARDANDO 'JARVIS'...";
      case JarvisState.listeningCommand:
        return "OUVINDO COMANDO...";
      case JarvisState.processing:
        return "PROCESSANDO...";
      case JarvisState.speaking:
        return "JARVIS FALANDO...";
      case JarvisState.followUp:
        return "CONTINUE A CONVERSA...";
    }
  }

  Widget _buildTranscriptBubble() {
    // Determina cor baseado no estado
    Color borderColor = _jarvisState == JarvisState.listeningCommand
        ? Colors.orangeAccent
        : Colors.cyan;

    bool isListening = _jarvisState == JarvisState.listeningCommand ||
        _jarvisState == JarvisState.listeningWakeWord;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      margin: const EdgeInsets.symmetric(horizontal: 40),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: borderColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: borderColor.withOpacity(isListening ? 0.8 : 0.3),
          width: isListening ? 2 : 1,
        ),
        boxShadow: isListening
            ? [
                BoxShadow(
                  color: borderColor.withOpacity(0.3),
                  blurRadius: 10,
                  spreadRadius: 2,
                ),
              ]
            : [],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Indicador de escuta
          if (isListening)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _buildWaveIndicator(borderColor),
                  const SizedBox(width: 8),
                  Text(
                    _isPushToTalk ? "SEGURE PARA FALAR" : "OUVINDO...",
                    style: GoogleFonts.orbitron(
                      color: borderColor,
                      fontSize: 9,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(width: 8),
                  _buildWaveIndicator(borderColor),
                ],
              ),
            ),

          // Texto transcrito
          Text(
            _lastTranscript.isEmpty ? "..." : '"$_lastTranscript"',
            style: GoogleFonts.sourceCodePro(
              color: _lastTranscript.isEmpty ? Colors.white30 : Colors.white70,
              fontSize: 12,
              fontStyle: FontStyle.italic,
            ),
            textAlign: TextAlign.center,
            maxLines: 4,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildWaveIndicator(Color color) {
    return AnimatedBuilder(
      animation: _waveController,
      builder: (context, child) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (index) {
            double delay = index * 0.2;
            double value = ((_waveController.value + delay) % 1.0);
            double height = 4 + (value * 8);

            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 1),
              width: 3,
              height: height,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(2),
              ),
            );
          }),
        );
      },
    );
  }

  Widget _buildTextInput() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.cyan.withOpacity(0.5)),
          borderRadius: BorderRadius.circular(30),
          color: Colors.cyan.withOpacity(0.05),
        ),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _messageController,
                style: GoogleFonts.sourceCodePro(color: Colors.white, fontSize: 13),
                onSubmitted: (_) => _sendTextMessage(),
                decoration: const InputDecoration(
                  border: InputBorder.none,
                  hintText: "DIGITE SEU COMANDO...",
                  hintStyle: TextStyle(color: Colors.white24, fontSize: 11),
                ),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.send, color: Colors.cyanAccent, size: 20),
              onPressed: _sendTextMessage,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBar() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: Colors.cyan.withOpacity(0.2))),
        color: Colors.black,
      ),
      child: Row(
        children: [
          // Indicador de conexão
          Container(
            width: 8, height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _isConnected ? Colors.greenAccent : Colors.redAccent,
            ),
          ),
          const SizedBox(width: 8),

          // Status text
          Expanded(
            child: Text(
              "> $_status",
              style: GoogleFonts.sourceCodePro(
                color: Colors.cyanAccent,
                fontSize: 10,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),

          // Indicador STT
          if (_speechEnabled)
            Icon(
              Icons.mic,
              color: _jarvisState == JarvisState.listeningWakeWord ||
                     _jarvisState == JarvisState.listeningCommand
                  ? Colors.greenAccent
                  : Colors.grey,
              size: 14,
            ),
        ],
      ),
    );
  }

  Widget _buildCorner({double? top, double? bottom, double? left, double? right}) {
    return Positioned(
      top: top, bottom: bottom, left: left, right: right,
      child: Container(
        width: 25, height: 25,
        decoration: BoxDecoration(
          border: Border(
            top: top != null ? const BorderSide(color: Colors.cyan, width: 2) : BorderSide.none,
            bottom: bottom != null ? const BorderSide(color: Colors.cyan, width: 2) : BorderSide.none,
            left: left != null ? const BorderSide(color: Colors.cyan, width: 2) : BorderSide.none,
            right: right != null ? const BorderSide(color: Colors.cyan, width: 2) : BorderSide.none,
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _silenceTimer?.cancel();
    _speech.stop();
    _urlController.dispose();
    _messageController.dispose();
    _pulseController.dispose();
    _waveController.dispose();
    _glowController.dispose();
    _audioPlayer.dispose();
    _feedbackPlayer.dispose();
    super.dispose();
  }
}