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
// ESTADOS DO JARVIS
// ============================================================
enum JarvisState {
  initializing,
  passiveListening, 
  activeListening,  
  processing,       
  speaking,         
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
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF00FFFF),
          secondary: Color(0xFF008B8B),
          surface: Color(0xFF050505),
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
  final TextEditingController _urlController = TextEditingController(text: 'http://192.168.1.100:5000');
  final TextEditingController _messageController = TextEditingController();

  late IO.Socket socket;
  final AudioPlayer _audioPlayer = AudioPlayer();
  final AudioPlayer _feedbackPlayer = AudioPlayer();

  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _speechEnabled = false;
  String _lastTranscript = "";

  JarvisState _currentState = JarvisState.initializing;
  String _statusText = "INICIALIZANDO...";
  bool _isConnected = false;
  
  bool _isCommandMode = false;
  Timer? _activeModeTimer;
  
  // Lista de Wake Words (HIPERSENSÍVEL)
  final List<String> _wakeWords = [
    'jarvis', 'jarves', 'jarvas', 'jarbis', 'javis', 
    'jairvis', 'charvis', 'service', 'servis', 'chaves',
    'javes', 'travis', 'david', 'avis', 'jerry', 'garvis',
    'já vi', 'ja vi', 'já viu', 'ja viu', 'já vês', 'ja ves',
    'jarbas', 'jervis', 'gervis', 'yaris', 'chaviz', 'jair'
  ];

  late AnimationController _pulseController;
  
  // STREAM CONTROL
  Timer? _manualSilenceTimer;

  // --- CONTROLE DE SPAM (DEBOUNCE) ---
  String _lastSentText = "";
  Timer? _debounceClearTimer;

  @override
  void initState() {
    super.initState();
    _initAnimations();
    _initSystem();
  }

  void _initAnimations() {
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
  }

  Future<void> _initSystem() async {
    await _requestPermissions();
    await _initSpeech();
    
    _audioPlayer.onPlayerComplete.listen((_) {
       setState(() {
         _currentState = _isCommandMode ? JarvisState.activeListening : JarvisState.passiveListening;
       });
    });
  }

  Future<void> _requestPermissions() async {
    await [Permission.microphone, Permission.storage, Permission.camera].request();
  }

  Future<void> _initSpeech() async {
    _speechEnabled = await _speech.initialize(
      onStatus: _onSpeechStatus,
      onError: (error) => print('[STT] Erro: ${error.errorMsg}'),
    );
    setState(() {});
  }

  // ============================================================
  // ESCUTA CONTÍNUA (BUFFERIZADA)
  // ============================================================

  void _startContinuousListening() async {
    if (!_speechEnabled || !_isConnected) return;
    if (_speech.isListening) return;

    setState(() {
      _currentState = _isCommandMode ? JarvisState.activeListening : JarvisState.passiveListening;
      _statusText = _isCommandMode ? "MODO ATIVO (FALE...)" : "MEMÓRIA ATIVA";
    });

    try {
      await _speech.listen(
        onResult: _onStreamResult,
        listenFor: const Duration(seconds: 30), 
        pauseFor: const Duration(seconds: 3),   // Aumentado para 3s para captar frases longas
        partialResults: true,
        localeId: 'pt_BR',
        listenMode: stt.ListenMode.dictation,
        cancelOnError: false,
      );
    } catch (e) {
      print("[STT] Erro start: $e");
      if (!_speech.isListening) {
         Future.delayed(const Duration(milliseconds: 200), _startContinuousListening);
      }
    }
  }

  void _onSpeechStatus(String status) {
    print('[STT] Status: $status');
    
    if ((status == 'done' || status == 'notListening') && _isConnected) {
        if (mounted) {
           Future.delayed(const Duration(milliseconds: 50), _startContinuousListening);
        }
    }
  }

  void _onStreamResult(SpeechRecognitionResult result) {
    String currentText = result.recognizedWords.trim();
    if (currentText.isEmpty) return;

    if (_currentState != JarvisState.speaking) {
       setState(() => _lastTranscript = currentText);
    }

    _manualSilenceTimer?.cancel();
    _manualSilenceTimer = Timer(const Duration(seconds: 3), () {
        _processFinalText(currentText); 
    });
  }

  // ============================================================
  // PROCESSAMENTO DE FRASE COMPLETA (COM ANTI-SPAM)
  // ============================================================

  void _processFinalText(String text) {
    if (text.isEmpty) return;

    // --- FILTRO ANTI-FRAGMENTAÇÃO ---
    if (text.trim().length < 5) {
       print("[FILTRO] Texto muito curto ignorado: '$text'");
       return;
    }

    // --- FILTRO ANTI-SPAM / REPETIÇÃO ---
    if (text == _lastSentText) {
       print("[FILTRO] Texto duplicado ignorado: '$text'");
       return;
    }

    print("[PROCESSADOR] Analisando: '$text'");
    
    String lowerText = text.toLowerCase();
    String? detectedTrigger;
    
    for (String t in _wakeWords) {
      if (lowerText.contains(t)) {
        detectedTrigger = t;
        break;
      }
    }

    if (detectedTrigger != null) {
        _enterCommandMode(); 
        _playSystemSound('activation');

        String cleanText = text.replaceAll(RegExp(detectedTrigger, caseSensitive: false), "").trim();
        
        if (cleanText.length > 1) {
           _sendCommand(cleanText, isActive: true);
        } else {
           _sendCommand(detectedTrigger, isActive: true);
        }
        return;
    }

    if (_isCommandMode) {
        _renewCommandTimer();
        _sendCommand(text, isActive: true);
        return;
    }

    if (text.length > 4) {
       _sendCommand(text, isActive: false);
    }
  }

  void _enterCommandMode() {
    setState(() {
      _isCommandMode = true;
      _currentState = JarvisState.activeListening;
    });
    _renewCommandTimer();
  }

  void _renewCommandTimer() {
    _activeModeTimer?.cancel();
    _activeModeTimer = Timer(const Duration(seconds: 10), _exitCommandMode); 
  }

  void _exitCommandMode() {
    if (!mounted) return;
    setState(() {
      _isCommandMode = false;
      _currentState = JarvisState.passiveListening;
      _statusText = "MEMÓRIA ATIVA";
    });
    HapticFeedback.lightImpact();
  }

  // ============================================================
  // COMUNICAÇÃO COM SERVIDOR
  // ============================================================

  void _connectToServer() {
    if (_isConnected) {
      socket.disconnect();
      return;
    }

    setState(() => _statusText = "CONECTANDO...");

    try {
      socket = IO.io(_urlController.text, IO.OptionBuilder()
          .setTransports(['websocket'])
          .disableAutoConnect()
          .build());

      socket.connect();

      socket.onConnect((_) {
        print("[SOCKET] Conectado!");
        setState(() {
          _isConnected = true;
          _statusText = "ONLINE";
        });
        _startContinuousListening();
      });

      socket.onDisconnect((_) {
        print("[SOCKET] Desconectado.");
        setState(() {
          _isConnected = false;
          _statusText = "OFFLINE";
          _currentState = JarvisState.initializing;
        });
      });

      socket.on('bot_response', (data) => _handleServerResponse(data));
      
      socket.on('play_audio_remoto', (data) {
        if (data != null && data['url'] != null) {
           _playAudioFromBase64(data['url']);
        }
      });

    } catch (e) {
      print("[SOCKET] Erro conexão: $e");
      setState(() => _statusText = "ERRO: $e");
    }
  }

  void _sendCommand(String text, {required bool isActive}) {
    if (!_isConnected) return;

    // --- ATUALIZA FILTRO ANTI-SPAM ---
    _lastSentText = text;
    _debounceClearTimer?.cancel();
    _debounceClearTimer = Timer(const Duration(seconds: 5), () {
       _lastSentText = "";
    });

    if (isActive) {
      setState(() {
        _currentState = JarvisState.processing;
        _statusText = "PROCESSANDO...";
      });
    }

    String event = isActive ? 'active_command' : 'passive_log';
    
    socket.emit(event, {
      'user_id': 'Mestre',
      'text': text,
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  void _handleServerResponse(dynamic data) async {
    if (data == null) return;
    
    String responseText = data['text'] ?? "";
    String? audioB64 = data['audio'];
    
    setState(() {
      _lastTranscript = responseText;
      _statusText = "RESPONDENDO...";
    });

    if (audioB64 != null) {
      await _playAudioFromBase64("data:audio/mp3;base64,$audioB64");
    }
  }

  Future<void> _playSystemSound(String type) async {
    HapticFeedback.heavyImpact();
  }

  Future<void> _playAudioFromBase64(String dataUrl) async {
    try {
      setState(() => _currentState = JarvisState.speaking);
      
      final base64String = dataUrl.split(',').last;
      final bytes = base64Decode(base64String);


      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/jarvis_response.mp3');
      await file.writeAsBytes(bytes);
      
      await _audioPlayer.play(DeviceFileSource(file.path));
      
      if (!_speech.isListening) {
         _startContinuousListening();
      }
      
    } catch (e) {
      print("[AUDIO] Erro playback: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            _buildBackground(),
            Column(
              children: [
                _buildConnectionHeader(),
                const Spacer(),
                _buildCentralOrb(),
                const SizedBox(height: 30),
                Text(
                  _statusText,
                  style: GoogleFonts.orbitron(
                    color: _getStateColor(),
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 20),
                _buildTranscriptBubble(),
                const Spacer(),
                _buildManualInput(),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBackground() {
    return Container(
      decoration: BoxDecoration(
        gradient: RadialGradient(
          center: Alignment.center,
          radius: 1.5,
          colors: [
            _getStateColor().withOpacity(0.1),
            Colors.black,
          ],
        ),
      ),
    );
  }

  Widget _buildConnectionHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _urlController,
              style: GoogleFonts.sourceCodePro(color: Colors.cyan, fontSize: 12),
              decoration: InputDecoration(
                filled: true,
                fillColor: Colors.white.withOpacity(0.05),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
              ),
            ),
          ),
          const SizedBox(width: 10),
          IconButton(
            icon: Icon(_isConnected ? Icons.link_off : Icons.link),
            color: _isConnected ? Colors.green : Colors.red,
            onPressed: _connectToServer,
          ),
          IconButton(
            icon: const Icon(Icons.qr_code_scanner, color: Colors.cyan),
            onPressed: _openQRScanner,
          ),
        ],
      ),
    );
  }

  Widget _buildCentralOrb() {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        double scale = 1.0 + (_pulseController.value * 0.1);
        Color color = _getStateColor();
        
        return Container(
          width: 180 * scale,
          height: 180 * scale,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: Colors.black,
            border: Border.all(color: color.withOpacity(0.8), width: 4),
            boxShadow: [
              BoxShadow(
                color: color.withOpacity(0.4),
                blurRadius: 30 * scale,
                spreadRadius: 5,
              ),
            ],
          ),
          child: Icon(
            _getIconForState(),
            size: 80,
            color: color,
          ),
        );
      },
    );
  }

  Widget _buildTranscriptBubble() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 30),
      child: Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: Colors.white10),
        ),
        child: Text(
          _lastTranscript.isEmpty ? "..." : '"$_lastTranscript"',
          textAlign: TextAlign.center,
          style: GoogleFonts.robotoMono(
            color: Colors.white70,
            fontSize: 14,
            fontStyle: FontStyle.italic,
          ),
        ),
      ),
    );
  }

  Widget _buildManualInput() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: TextField(
        controller: _messageController,
        style: const TextStyle(color: Colors.white),
        onSubmitted: (text) {
          if (text.isNotEmpty) _sendCommand(text, isActive: true);
          _messageController.clear();
        },
        decoration: InputDecoration(
          hintText: "Comando de texto...",
          hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
          prefixIcon: const Icon(Icons.keyboard, color: Colors.cyan),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(30),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.1)),
          ),
        ),
      ),
    );
  }

  Color _getStateColor() {
    switch (_currentState) {
      case JarvisState.initializing: return Colors.grey;
      case JarvisState.passiveListening: return Colors.cyanAccent;
      case JarvisState.activeListening: return Colors.orangeAccent; 
      case JarvisState.processing: return Colors.purpleAccent;
      case JarvisState.speaking: return Colors.greenAccent;
    }
  }

  IconData _getIconForState() {
    switch (_currentState) {
      case JarvisState.initializing: return Icons.power_settings_new;
      case JarvisState.passiveListening: return Icons.mic_none;
      case JarvisState.activeListening: return Icons.mic;
      case JarvisState.processing: return Icons.psychology;
      case JarvisState.speaking: return Icons.graphic_eq;
    }
  }

  void _openQRScanner() {
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        height: 400,
        color: Colors.black,
        child: MobileScanner(
          onDetect: (capture) {
            final List<Barcode> barcodes = capture.barcodes;
            for (final barcode in barcodes) {
              if (barcode.rawValue != null && barcode.rawValue!.startsWith('http')) {
                setState(() => _urlController.text = barcode.rawValue!);
                Navigator.pop(context);
                _connectToServer();
              }
            }
          },
        ),
      ),
    );
  }

  @override
  void dispose() {
    _manualSilenceTimer?.cancel();
    _activeModeTimer?.cancel();
    _debounceClearTimer?.cancel();
    _pulseController.dispose();
    _speech.stop();
    _urlController.dispose();
    _messageController.dispose();
    _audioPlayer.dispose();
    _feedbackPlayer.dispose();
    super.dispose();
  }
}
