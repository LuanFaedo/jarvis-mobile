import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:flutter_tts/flutter_tts.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:mobile_scanner/mobile_scanner.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.light);
  runApp(const JarvisApp());
}

class ChatLog {
  final String text;
  final bool isUser;
  ChatLog(this.text, this.isUser);
}

class JarvisApp extends StatelessWidget {
  const JarvisApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JARVIS V12',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF000000),
        primaryColor: const Color(0xFF00FFFF),
      ),
      home: const WebLikeInterface(),
    );
  }
}

class WebLikeInterface extends StatefulWidget {
  const WebLikeInterface({super.key});

  @override
  State<WebLikeInterface> createState() => _WebLikeInterfaceState();
}

class _WebLikeInterfaceState extends State<WebLikeInterface> with TickerProviderStateMixin {
  final TextEditingController _urlController = TextEditingController(text: 'http://192.168.3.101:5000');
  final TextEditingController _textInputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  late IO.Socket socket;
  final FlutterTts _flutterTts = FlutterTts();
  final stt.SpeechToText _speech = stt.SpeechToText();
  
  bool _isConnected = false;
  bool _speechEnabled = false;
  bool _isTalking = false;
  String _statusText = "AGUARDANDO COMANDO";
  String _lastSentText = "";
  
  final List<ChatLog> _logs = [];
  String? _holoImageBase64;
  
  // CONFIGURAÇÕES DE ÁUDIO
  double _speechRate = 0.5; 
  String _rateLabel = "1.0x";
  bool _isMuted = false;
  
  // VOZES
  List<dynamic> _voices = [];
  Map<String, String>? _selectedVoice;

  Timer? _manualSilenceTimer;
  late AnimationController _particleController;

  @override
  void initState() {
    super.initState();
    _particleController = AnimationController(vsync: this, duration: const Duration(seconds: 20))..repeat();
    
    WidgetsBinding.instance.addPostFrameCallback((_) {
       _loadConfig().then((_) {
         _initSystem();
         _initTts();
       });
    });
  }

  Future<void> _initTts() async {
    await _flutterTts.setLanguage("pt-BR");
    await _flutterTts.setSpeechRate(_speechRate);
    await _flutterTts.setVolume(_isMuted ? 0.0 : 1.0);
    await _flutterTts.setPitch(1.0);

    _flutterTts.setStartHandler(() => setState(() => _isTalking = true));
    _flutterTts.setCompletionHandler(() {
      setState(() => _isTalking = false);
      if (_isConnected) _startContinuousListening(); 
    });
    _flutterTts.setErrorHandler((msg) => setState(() => _isTalking = false));

    _getVoices();
  }

  Future<void> _getVoices() async {
    try {
      var allVoices = await _flutterTts.getVoices;
      setState(() {
        _voices = allVoices.where((v) {
            String loc = v["locale"].toString().toLowerCase();
            return loc.contains("pt") || loc.contains("bra") || loc.contains("por");
        }).toList();
      });
      if (_selectedVoice != null) {
        await _flutterTts.setVoice(_selectedVoice!);
      }
    } catch (e) { print("Erro vozes: $e"); }
  }

  void _toggleMute() {
      setState(() {
          _isMuted = !_isMuted;
          _flutterTts.setVolume(_isMuted ? 0.0 : 1.0);
          if (_isMuted && _isTalking) _flutterTts.stop();
      });
  }
  
  void _cycleSpeed() {
      setState(() {
          if (_rateLabel == "1.0x") {
              _speechRate = 0.7; // ~1.25x
              _rateLabel = "1.25x";
          } else if (_rateLabel == "1.25x") {
              _speechRate = 0.9; // ~1.5x
              _rateLabel = "1.5x";
          } else {
              _speechRate = 0.5; // Normal
              _rateLabel = "1.0x";
          }
          _flutterTts.setSpeechRate(_speechRate);
      });
  }

  void _changeVoice(Map<dynamic, dynamic> voice) async {
    await _flutterTts.setVoice({"name": voice["name"], "locale": voice["locale"]});
    setState(() {
      _selectedVoice = {"name": voice["name"], "locale": voice["locale"]};
    });
    _saveConfig(); 
    await _flutterTts.stop();
    await _flutterTts.speak("Voz definida.");
  }

  void _showVoiceDialog() {
    showDialog(
      context: context,
      builder: (c) => AlertDialog(
        title: Text("Selecionar Voz", style: TextStyle(color: Colors.cyan)),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: _voices.length,
            itemBuilder: (ctx, i) {
              var v = _voices[i];
              return ListTile(
                title: Text(v["name"].toString(), style: TextStyle(fontSize: 14)),
                subtitle: Text(v["locale"].toString(), style: TextStyle(fontSize: 12, color: Colors.grey)),
                trailing: _selectedVoice?["name"] == v["name"] ? Icon(Icons.check, color: Colors.cyan) : null,
                onTap: () {
                  _changeVoice(v);
                  Navigator.pop(c);
                },
              );
            },
          ),
        ),
      ),
    );
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  Future<void> _loadConfig() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/config.json');
      if (await file.exists()) {
        final content = await file.readAsString();
        final data = jsonDecode(content);
        if (data['server_url'] != null) setState(() => _urlController.text = data['server_url']);
        if (data['voice_name'] != null) _selectedVoice = {"name": data['voice_name'], "locale": data['voice_locale']};
      }
    } catch (e) {}
  }

  Future<void> _saveConfig() async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final file = File('${dir.path}/config.json');
      Map<String, dynamic> data = {'server_url': _urlController.text};
      if (_selectedVoice != null) {
        data['voice_name'] = _selectedVoice!["name"];
        data['voice_locale'] = _selectedVoice!["locale"];
      }
      await file.writeAsString(jsonEncode(data));
    } catch (e) {}
  }

  Future<void> _initSystem() async {
    await [Permission.microphone, Permission.storage, Permission.camera].request();
    _speechEnabled = await _speech.initialize(
      onStatus: _onSpeechStatus,
      onError: (e) => print('[STT] ${e.errorMsg}'),
    );
    _connectToServer();
  }

  void _connectToServer() {
    if (_isConnected) { socket.disconnect(); return; }
    setState(() => _statusText = "CONECTANDO...");
    _saveConfig();

    try {
      socket = IO.io(_urlController.text, IO.OptionBuilder().setTransports(['websocket']).disableAutoConnect().build());
      socket.connect();
      
      socket.onConnect((_) {
        setState(() { _isConnected = true; _statusText = "ONLINE"; });
        _startContinuousListening();
      });

      socket.onDisconnect((_) => setState(() { _isConnected = false; _statusText = "OFFLINE"; }));
      
      socket.on('bot_response', (data) => _handleServerResponse(data));
      
      socket.on('bot_image_event', (data) {
        if (data != null && data['image'] != null) {
          setState(() {
            _holoImageBase64 = data['image'];
            _logs.add(ChatLog(">> Visualização gerada.", false));
          });
          _scrollToBottom();
        }
      });

      socket.on('force_stop_playback', (_) async {
        await _flutterTts.stop();
        setState(() { _statusText = "SILÊNCIO..."; _isTalking = false; });
      });

      socket.on('status_update', (data) => setState(() => _statusText = data['status']?.toUpperCase() ?? _statusText));

    } catch (e) { setState(() => _statusText = "ERRO: $e"); }
  }

  void _startContinuousListening() async {
    if (!_speechEnabled || !_isConnected || _speech.isListening) return;
    try {
      await _speech.listen(
        onResult: (result) {
          String text = result.recognizedWords.trim();
          if (text.isEmpty) return;
          
          if (_isTalking) {
             String tLower = text.toLowerCase();
             if (tLower.contains("jarvis") || tLower.contains("pare") || tLower.contains("silêncio")) {
                 _flutterTts.stop();
                 _sendCommand("Jarvis, pare");
             }
             return; 
          }
          
          _manualSilenceTimer?.cancel();
          _manualSilenceTimer = Timer(const Duration(milliseconds: 2000), () {
             if (text.isNotEmpty && text != _lastSentText) _sendCommand(text);
          });
        },
        listenFor: const Duration(seconds: 60),
        pauseFor: const Duration(seconds: 3),
        localeId: 'pt_BR',
        cancelOnError: false,
        partialResults: true,
        onDevice: true,
      );
    } catch (e) { Future.delayed(const Duration(seconds: 1), _startContinuousListening); }
  }

  void _onSpeechStatus(String status) {
    if ((status == 'notListening' || status == 'done') && _isConnected && mounted) {
      if (!_isTalking) Future.delayed(const Duration(milliseconds: 100), _startContinuousListening);
    }
  }

  void _sendCommand(String text) {
    if (!_isConnected) return;
    if (text.trim().isEmpty) return;

    _lastSentText = text;
    HapticFeedback.mediumImpact();
    _textInputController.clear();
    
    if (_isTalking) _flutterTts.stop();
    
    setState(() {
      _statusText = "PROCESSANDO...";
      _logs.add(ChatLog(text, true));
      _holoImageBase64 = null; 
    });
    _scrollToBottom();
    socket.emit('active_command', {'user_id': 'Mestre', 'text': text});
  }

  void _handleServerResponse(dynamic data) async {
    if (data == null) return;
    String text = data['text'] ?? "";
    String displayText = text.replaceAll(RegExp(r'\[\[GEN_IMG:.*?\]\]'), '');
    
    setState(() {
      if (displayText.trim().isNotEmpty) _logs.add(ChatLog(displayText, false));
      _statusText = "FALANDO...";
    });
    _scrollToBottom();

    if (displayText.isNotEmpty) {
        await _speech.stop();
        await _flutterTts.speak(displayText);
    }
  }

  Future<void> _scanQRCode() async {
    final result = await Navigator.push(
      context, MaterialPageRoute(builder: (context) => Scaffold(
          appBar: AppBar(title: const Text("Escanear QR")),
          body: MobileScanner(onDetect: (capture) {
              final List<Barcode> barcodes = capture.barcodes;
              for (final barcode in barcodes) {
                if (barcode.rawValue != null) { Navigator.pop(context, barcode.rawValue); break; }
              }
            }),
        )),
    );
    if (result != null) {
      setState(() => _urlController.text = result);
      _connectToServer();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text("JARVIS ", style: GoogleFonts.orbitron(color: Colors.white, fontWeight: FontWeight.bold)),
            Text("V12", style: GoogleFonts.orbitron(color: Colors.cyan)),
          ],
        ),
        centerTitle: true,
        actions: [
          // MUTE NA TOP BAR
          IconButton(
              icon: Icon(_isMuted ? Icons.volume_off : Icons.volume_up, color: _isMuted ? Colors.red : Colors.cyan),
              onPressed: _toggleMute
          ),
          // SELETOR DE VOZ
          IconButton(icon: Icon(Icons.record_voice_over, color: Colors.cyanAccent), onPressed: _showVoiceDialog),
          
          IconButton(icon: Icon(Icons.qr_code_scanner, color: Colors.white54), onPressed: _scanQRCode),
          IconButton(icon: Icon(Icons.settings, color: Colors.white54), onPressed: () {
             showDialog(context: context, builder: (c) => AlertDialog(
                title: Text("Configurar IP"),
                content: TextField(controller: _urlController),
                actions: [TextButton(onPressed: _connectToServer, child: Text("Conectar"))]
             ));
          })
        ],
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _particleController,
              builder: (context, child) => CustomPaint(
                painter: ParticleBackgroundPainter(time: _particleController.value * 2 * pi, isTalking: _statusText == "FALANDO...")
              ),
            ),
          ),

          Positioned(
            top: 0, left: 0, right: 0, height: 300,
            child: Center(
              child: AnimatedBuilder(
                animation: _particleController,
                builder: (context, child) => CustomPaint(
                  size: const Size(200, 200),
                  painter: GlobePainter(rotation: _particleController.value * 2 * pi, isConnected: _isConnected, isTalking: _statusText == "FALANDO..."),
                ),
              ),
            ),
          ),

          Positioned(
            top: 250, left: 0, right: 0, bottom: 0,
            child: Column(
              children: [
                Expanded(
                  child: ShaderMask(
                    shaderCallback: (Rect bounds) {
                      return LinearGradient(
                        begin: Alignment.topCenter, end: Alignment.bottomCenter,
                        colors: [Colors.transparent, Colors.white, Colors.white, Colors.transparent],
                        stops: [0.0, 0.1, 0.9, 1.0],
                      ).createShader(bounds);
                    },
                    blendMode: BlendMode.dstIn,
                    child: ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                      itemCount: _logs.length,
                      itemBuilder: (context, index) {
                        final log = _logs[index];
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Text(
                            log.isUser ? "> ${log.text}" : log.text,
                            textAlign: log.isUser ? TextAlign.right : TextAlign.left,
                            style: GoogleFonts.robotoMono(
                              color: log.isUser ? Colors.white70 : Colors.cyanAccent,
                              fontSize: 14,
                              shadows: [Shadow(color: log.isUser ? Colors.transparent : Colors.cyan, blurRadius: 2)]
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),
                
                // --- BARRA INFERIOR (INPUT + SPEED) ---
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                  decoration: BoxDecoration(
                    color: Colors.black87,
                    border: Border(top: BorderSide(color: Colors.cyan.withOpacity(0.3))),
                  ),
                  child: SafeArea(
                    child: Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _textInputController,
                            style: GoogleFonts.robotoMono(color: Colors.white),
                            decoration: InputDecoration(
                              hintText: "Comando...",
                              hintStyle: TextStyle(color: Colors.white30),
                              border: InputBorder.none,
                              isDense: true,
                            ),
                            onSubmitted: (val) => _sendCommand(val),
                          ),
                        ),
                        // BOTÃO VELOCIDADE (AQUI EMBAIXO)
                        TextButton(
                            onPressed: _cycleSpeed,
                            style: TextButton.styleFrom(
                                padding: EdgeInsets.symmetric(horizontal: 5),
                                minimumSize: Size(40, 30),
                                tapTargetSize: MaterialTapTargetSize.shrinkWrap
                            ),
                            child: Text(_rateLabel, style: GoogleFonts.orbitron(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 11))
                        ),
                        IconButton(
                          icon: Icon(Icons.send, color: Colors.cyan),
                          onPressed: () => _sendCommand(_textInputController.text),
                        ),
                        IconButton(
                          icon: Icon(Icons.mic, color: _isTalking ? Colors.red : Colors.white54),
                          onPressed: () => _sendCommand("Jarvis"),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          if (_holoImageBase64 != null)
            Positioned(
              top: 150, left: 20, right: 20, bottom: 150,
              child: Center(
                child: Container(
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.cyanAccent, width: 1),
                    color: Colors.black.withOpacity(0.9),
                    boxShadow: [BoxShadow(color: Colors.cyan.withOpacity(0.3), blurRadius: 20)],
                  ),
                  padding: const EdgeInsets.all(2),
                  child: Stack(
                    children: [
                      InteractiveViewer(child: Image.memory(base64Decode(_holoImageBase64!), fit: BoxFit.contain)),
                      Positioned(
                        top: 5, right: 5,
                        child: IconButton(icon: Icon(Icons.close, color: Colors.red), onPressed: () => setState(() => _holoImageBase64 = null)),
                      )
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// Pintores mantidos (GlobePainter, ParticleBackgroundPainter)...
class ParticleBackgroundPainter extends CustomPainter {
  final double time; final bool isTalking;
  ParticleBackgroundPainter({required this.time, required this.isTalking});
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = const Color(0xFF00FFFF).withOpacity(0.15)..style = PaintingStyle.fill;
    final random = Random(42); 
    for (int i = 0; i < 50; i++) {
      double x = (random.nextDouble() * size.width);
      double y = (random.nextDouble() * size.height + time * 20) % size.height;
      double r = random.nextDouble() * 2;
      canvas.drawCircle(Offset(x, y), r, paint);
    }
  }
  @override bool shouldRepaint(covariant ParticleBackgroundPainter old) => true;
}
class GlobePainter extends CustomPainter {
  final double rotation; final bool isConnected; final bool isTalking;
  GlobePainter({required this.rotation, required this.isConnected, required this.isTalking});
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2); final paint = Paint()..strokeCap = StrokeCap.round;
    double radius = size.width / 3; if (isTalking) radius *= 1.05 + (sin(rotation * 20) * 0.05);
    Color baseColor = isConnected ? const Color(0xFF00FFEA) : Colors.redAccent;
    double cosR = cos(rotation); double sinR = sin(rotation);
    for (int i = 0; i < 200; i++) {
      double y = 1 - (i / 199) * 2; double r = sqrt(1 - y * y); double theta = 2.4 * i;
      double x = cos(theta) * r; double z = sin(theta) * r;
      double rx = x * cosR - z * sinR; double rz = z * cosR + x * sinR;
      double pX = rx * radius; double pY = y * radius;
      double opacity = ((rz + 1) / 2).clamp(0.1, 1.0);
      paint.color = baseColor.withOpacity(opacity * (isConnected ? 0.8 : 0.3));
      double dotSize = isTalking ? 2.5 : 1.5;
      canvas.drawCircle(center + Offset(pX, pY), dotSize, paint);
    }
    paint.color = baseColor.withOpacity(0.05);
    paint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 10);
    canvas.drawCircle(center, radius * 0.7, paint);
  }
  @override bool shouldRepaint(covariant GlobePainter old) => true;
}
