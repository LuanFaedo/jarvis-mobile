import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';

void main() {
  runApp(const JarvisApp());
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

class _HUDInterfaceState extends State<HUDInterface> with SingleTickerProviderStateMixin {
  final TextEditingController _urlController = TextEditingController(text: 'http://192.168.3.101:5001');
  final TextEditingController _messageController = TextEditingController();
  late IO.Socket socket;
  final AudioRecorder _audioRecorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();
  late AnimationController _pulseController;

  String _status = "SISTEMA INICIALIZANDO...";
  bool _isConnected = false;
  bool _isRecording = false;
  bool _isProcessing = false;
  bool _jarvisAwake = false;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    _requestPermissions();
  }

  Future<void> _requestPermissions() async {
    await Permission.microphone.request();
    await Permission.storage.request();
  }

  void _connectToServer() {
    if (_isConnected) {
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
      setState(() {
        _isConnected = true;
        _status = "ONLINE";
      });
    });

    socket.onDisconnect((_) {
      if (mounted) {
        setState(() {
          _isConnected = false;
          _status = "OFFLINE";
        });
      }
    });

    socket.on('jarvis_ack', (_) {
      setState(() {
        _status = "JARVIS OUVIU...";
        _jarvisAwake = true;
      });
    });

    socket.on('bot_msg_partial', (data) {
       setState(() => _status = "JARVIS: ${data['data']}");
    });

    socket.on('response_audio', (data) async {
      setState(() {
        _status = "RECEBENDO RESPOSTA...";
        _isProcessing = false;
        _jarvisAwake = false;
      });
      if (data != null && data['audio'] != null) {
        try {
           final bytes = base64Decode(data['audio']);
           final dir = await getTemporaryDirectory();
           final file = File('${dir.path}/response.mp3');
           await file.writeAsBytes(bytes);
           await _audioPlayer.play(DeviceFileSource(file.path));
           setState(() => _status = "JARVIS FALANDO.");
        } catch (e) {
          setState(() => _status = "ERRO ÁUDIO: $e");
        }
      }
    });
    
    socket.on('bot_msg', (data) {
       setState(() {
         _status = "JARVIS: ${data['data']}";
         _isProcessing = false;
       });
    });
  }

  void _sendTextMessage() {
    String text = _messageController.text.trim();
    if (text.isEmpty || !_isConnected) return;
    setState(() {
      _isProcessing = true;
      _status = "PROCESSANDO...";
    });
    socket.emit('fala_usuario', {'user_id': 'Mestre', 'text': text});
    _messageController.clear();
    FocusScope.of(context).unfocus();
  }

  Future<void> _startRecording() async {
    if (!_isConnected) return;
    try {
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/temp_input.m4a';
      if (await _audioRecorder.hasPermission()) {
        await _audioRecorder.start(const RecordConfig(), path: path);
        setState(() {
          _isRecording = true;
          _status = "ESCUTANDO...";
        });
      }
    } catch (e) {
      setState(() => _status = "ERRO MIC: $e");
    }
  }

  Future<void> _stopAndSend() async {
    if (!_isRecording) return;
    final path = await _audioRecorder.stop();
    setState(() {
      _isRecording = false;
      _isProcessing = true;
      _status = "ANALISANDO...";
    });
    if (path != null) {
      final file = File(path);
      final bytes = await file.readAsBytes();
      socket.emit('audio_stream', bytes);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            _buildCorner(top: 20, left: 20),
            _buildCorner(top: 20, right: 20),
            _buildCorner(bottom: 20, left: 20),
            _buildCorner(bottom: 20, right: 20),
            Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    children: [
                      Text("J.A.R.V.I.S.", style: GoogleFonts.orbitron(
                        fontSize: 28, fontWeight: FontWeight.bold, color: Colors.cyanAccent,
                      )),
                      const SizedBox(height: 20),
                      Container(
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
                                style: GoogleFonts.orbitron(color: Colors.white, fontSize: 11),
                                decoration: const InputDecoration(border: InputBorder.none, hintText: "SERVER URL"),
                              ),
                            ),
                            IconButton(
                              icon: Icon(_isConnected ? Icons.link_off : Icons.link, color: Colors.cyanAccent, size: 20),
                              onPressed: _connectToServer,
                            )
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const Spacer(),
                GestureDetector(
                  onLongPressStart: (_) => _startRecording(),
                  onLongPressEnd: (_) => _stopAndSend(),
                  child: AnimatedBuilder(
                    animation: _pulseController,
                    builder: (context, child) {
                      return Container(
                        width: 130, height: 130,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: _isRecording ? Colors.redAccent : Colors.cyanAccent, width: 3),
                          color: Colors.black,
                        ),
                        child: Icon(
                          _isProcessing ? Icons.sync : Icons.mic,
                          size: 45,
                          color: _isRecording ? Colors.redAccent : Colors.cyanAccent,
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(height: 15),
                Text(_isRecording ? "ESCUTANDO..." : "SEGURE PARA FALAR", 
                  style: GoogleFonts.orbitron(color: Colors.white70, fontSize: 10)),
                const Spacer(),
                Padding(
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
                ),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    border: Border(top: BorderSide(color: Colors.cyan.withOpacity(0.2))),
                    color: Colors.black,
                  ),
                  child: Text(
                    "> $_status",
                    style: GoogleFonts.sourceCodePro(
                      color: _jarvisAwake ? Colors.greenAccent : Colors.cyanAccent, 
                      fontSize: 11
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCorner({double? top, double? bottom, double? left, double? right}) {
    return Positioned(
      top: top, bottom: bottom, left: left, right: right,
      child: Container(width: 25, height: 25, decoration: BoxDecoration(border: Border(
        top: top != null ? const BorderSide(color: Colors.cyan, width: 2) : BorderSide.none,
        bottom: bottom != null ? const BorderSide(color: Colors.cyan, width: 2) : BorderSide.none,
        left: left != null ? const BorderSide(color: Colors.cyan, width: 2) : BorderSide.none,
        right: right != null ? const BorderSide(color: Colors.cyan, width: 2) : BorderSide.none,
      ))),
    );
  }

  @override
  void dispose() {
    _urlController.dispose();
    _messageController.dispose();
    _pulseController.dispose();
    _audioRecorder.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }
}