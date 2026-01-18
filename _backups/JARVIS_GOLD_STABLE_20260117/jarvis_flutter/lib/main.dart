import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:audioplayers/audioplayers.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:mobile_scanner/mobile_scanner.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  runApp(const JarvisApp());
}

class JarvisApp extends StatelessWidget {
  const JarvisApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'J.A.R.V.I.S.',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF000000),
        primaryColor: const Color(0xFF00FFFF),
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
  final TextEditingController _urlController = TextEditingController(text: 'http://192.168.3.101:5000');
  final TextEditingController _messageController = TextEditingController();
  
  late IO.Socket socket;
  final AudioPlayer _audioPlayer = AudioPlayer();
  final stt.SpeechToText _speech = stt.SpeechToText();
  
  bool _isConnected = false;
  bool _speechEnabled = false;
  String _statusText = "INICIALIZANDO...";
  String _lastTranscript = "";
  String _lastSentText = "";
  Timer? _manualSilenceTimer;
  
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    )..repeat(reverse: true);

    WidgetsBinding.instance.addPostFrameCallback((_) {
       _loadConfig().then((_) => _initSystem());
    });
  }

  Future<void> _loadConfig() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/config.json');
      if (await file.exists()) {
        final content = await file.readAsString();
        final data = jsonDecode(content);
        if (data['server_url'] != null) {
          setState(() => _urlController.text = data['server_url']);
        }
      }
    } catch (e) { print(e); }
  }

  Future<void> _saveConfig() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/config.json');
      await file.writeAsString(jsonEncode({'server_url': _urlController.text}));
    } catch (e) { print(e); }
  }

  Future<void> _initSystem() async {
    await [Permission.microphone, Permission.storage].request();
    _speechEnabled = await _speech.initialize(
      onStatus: _onSpeechStatus,
      onError: (e) => print('[STT ERROR] ${e.errorMsg}'),
    );
    _connectToServer();
  }

  void _connectToServer() {
    if (_isConnected) { socket.disconnect(); return; }
    
    setState(() => _statusText = "CONECTANDO...");
    _saveConfig();

    try {
      socket = IO.io(_urlController.text, IO.OptionBuilder()
          .setTransports(['websocket'])
          .disableAutoConnect()
          .build());

      socket.connect();
      socket.onConnect((_) {
        setState(() {
          _isConnected = true;
          _statusText = "ONLINE";
        });
        _startContinuousListening();
      });

      socket.onDisconnect((_) => setState(() { _isConnected = false; _statusText = "OFFLINE"; }));
      
      socket.on('bot_response', (data) => _handleServerResponse(data));
      socket.on('status_update', (data) => setState(() => _statusText = data['status'] ?? _statusText));
      socket.on('intent_detected', (data) => setState(() => _statusText = "MODO: ${data['intent']}"));

    } catch (e) {
      setState(() => _statusText = "ERRO: $e");
    }
  }

  // --- RECONHECIMENTO DE VOZ ---

  void _startContinuousListening() async {
    if (!_speechEnabled || !_isConnected || _speech.isListening) return;

    try {
      await _speech.listen(
        onResult: (result) {
          String text = result.recognizedWords.trim();
          if (text.isEmpty) return; // Aceita qualquer tamanho
          
          setState(() => _lastTranscript = text);
          
          _manualSilenceTimer?.cancel();
          _manualSilenceTimer = Timer(const Duration(milliseconds: 1500), () {
             if (text != _lastSentText) {
               _sendCommand(text);
             }
          });
        },
        listenFor: const Duration(seconds: 60),
        pauseFor: const Duration(seconds: 2), // Pausa curta
        localeId: 'pt_BR',
        cancelOnError: false,
        partialResults: true,
      );
    } catch (e) {
      Future.delayed(const Duration(seconds: 1), _startContinuousListening);
    }
  }

  void _onSpeechStatus(String status) {
    if ((status == 'notListening' || status == 'done') && _isConnected && mounted) {
      Future.delayed(const Duration(milliseconds: 500), _startContinuousListening);
    }
  }

  void _sendCommand(String text) {
    if (!_isConnected) return;
    _lastSentText = text;
    HapticFeedback.mediumImpact(); // Vibra
    setState(() => _statusText = "ENVIANDO...");
    socket.emit('active_command', {'user_id': 'Mestre', 'text': text});
  }

  void _handleServerResponse(dynamic data) async {
    if (data == null) return;
    String text = data['text'] ?? "";
    String? audio = data['audio'];
    
    setState(() {
      _lastTranscript = text;
      _statusText = "FALANDO...";
    });

    if (audio != null) {
      await _speech.stop();
      final bytes = base64Decode(data['audio'].split(',').last);
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/resp.mp3');
      await file.writeAsBytes(bytes);
      await _audioPlayer.play(DeviceFileSource(file.path));
      
      _audioPlayer.onPlayerComplete.first.then((_) {
         if (mounted) _startContinuousListening();
      });
    }
  }

  // --- UI SIMPLIFICADA (SAFE MODE) ---

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text("JARVIS V12", style: GoogleFonts.orbitron(color: Colors.cyan)),
        actions: [
          IconButton(
            icon: Icon(Icons.flash_on, color: Colors.yellow), // Teste
            onPressed: () => _sendCommand("teste de conexão"),
          ),
          IconButton(
            icon: Icon(Icons.settings, color: Colors.cyan),
            onPressed: () => _showConfigDialog(),
          )
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: Center(
              child: AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  return Container(
                    width: 200 + (_pulseController.value * 20),
                    height: 200 + (_pulseController.value * 20),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.cyan, width: 2),
                      boxShadow: [
                        BoxShadow(color: Colors.cyan.withOpacity(0.5), blurRadius: 20 * _pulseController.value)
                      ],
                    ),
                    child: Center(
                      child: Icon(
                        _isConnected ? Icons.mic : Icons.mic_off,
                        size: 80,
                        color: _isConnected ? Colors.cyan : Colors.red,
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Text(
              _lastTranscript,
              textAlign: TextAlign.center,
              style: GoogleFonts.robotoMono(fontSize: 18, color: Colors.white70),
            ),
          ),
          Container(
            padding: const EdgeInsets.all(10),
            color: Colors.black54,
            child: Column(
              children: [
                Text(_statusText, style: GoogleFonts.orbitron(fontSize: 12, color: Colors.cyan)),
                const SizedBox(height: 10),
                TextField(
                  controller: _messageController,
                  style: TextStyle(color: Colors.cyan),
                  decoration: InputDecoration(
                    hintText: "Digite ou fale...",
                    border: OutlineInputBorder(),
                    suffixIcon: IconButton(
                      icon: Icon(Icons.send, color: Colors.cyan),
                      onPressed: () {
                        if (_messageController.text.isNotEmpty) {
                          _sendCommand(_messageController.text);
                          _messageController.clear();
                        }
                      },
                    ),
                  ),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }

  void _showConfigDialog() {
    showDialog(
      context: context,
      builder: (c) => AlertDialog(
        title: Text("Configurar IP"),
        content: TextField(controller: _urlController),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: Text("OK")),
          TextButton(onPressed: _connectToServer, child: Text("Conectar")),
        ],
      ),
    );
  }
}