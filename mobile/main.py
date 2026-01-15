from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.utils import platform
import socketio
import base64
import os
import threading

KV = '''
MDScreen:
    md_bg_color: 0.05, 0.05, 0.05, 1

    MDBoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(30)
        pos_hint: {"center_x": .5, "center_y": .5}

        MDLabel:
            text: "JARVIS CLIENT"
            halign: "center"
            font_style: "H4"
            theme_text_color: "Custom"
            text_color: 0, 1, 1, 1
            bold: True
            size_hint_y: None
            height: dp(50)

        MDBoxLayout:
            orientation: 'horizontal'
            spacing: dp(10)
            size_hint_y: None
            height: dp(60)

            MDTextField:
                id: ip_input
                hint_text: "IP do Servidor (192.168.x.x:5000)"
                text: "http://192.168.1.X:5000"
                mode: "rectangle"
                line_color_focus: 0, 1, 1, 1
            
            MDIconButton:
                icon: "connection"
                theme_text_color: "Custom"
                text_color: 0, 1, 0, 1
                on_release: app.conectar()

        Widget:
            size_hint_y: 1

        MDIconButton:
            id: mic_btn
            icon: "microphone"
            user_font_size: "96sp"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            md_bg_color: 0, 0.6, 0.6, 0.3
            pos_hint: {"center_x": .5}
            on_press: app.iniciar_gravacao()
            on_release: app.parar_gravacao()

        MDLabel:
            id: status_lbl
            text: "Toque para configurar IP"
            halign: "center"
            theme_text_color: "Secondary"
            font_style: "Caption"
            size_hint_y: None
            height: dp(40)
'''

class JarvisMobile(MDApp):
    sio = socketio.Client()
    connected = False

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"
        return Builder.load_string(KV)

    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.RECORD_AUDIO, Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE])

    def conectar(self):
        ip = self.root.ids.ip_input.text
        if not ip.startswith('http'): ip = 'http://' + ip
        
        threading.Thread(target=self._connect_thread, args=(ip,)).start()

    def _connect_thread(self, ip):
        try:
            if self.sio.connected: self.sio.disconnect()
            
            self.sio.connect(ip, wait_timeout=5)
            self.connected = True
            
            # Listeners
            self.sio.on('bot_msg', self.on_bot_msg)
            self.sio.on('play_audio_remoto', self.on_audio_receive)
            self.sio.on('stream_audio_chunk', self.on_audio_chunk)
            
            Clock.schedule_once(lambda dt: self.update_status("Conectado!", (0,1,0,1)))
            Clock.schedule_once(lambda dt: toast("Conexão Estabelecida"))
            
        except Exception as e:
            self.connected = False
            Clock.schedule_once(lambda dt: self.update_status(f"Erro: {e}", (1,0,0,1)))
            Clock.schedule_once(lambda dt: toast("Falha na conexão"))

    def update_status(self, text, color):
        self.root.ids.status_lbl.text = text
        self.root.ids.status_lbl.text_color = color

    def on_bot_msg(self, data):
        texto = data.get('data', '')
        Clock.schedule_once(lambda dt: self.update_status(texto[:60]+"...", (1,1,1,1)))

    def on_audio_receive(self, data):
        self.tocar_audio(data.get('url', '').split(',')[1])

    def on_audio_chunk(self, data):
        self.tocar_audio(data.get('audio', ''))

    def tocar_audio(self, b64):
        if not b64: return
        try:
            path = os.path.join(self.user_data_dir, 'resposta_jarvis.mp3')
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
            
            sound = SoundLoader.load(path)
            if sound: sound.play()
        except Exception as e:
            print(e)

    # --- LÓGICA DE MICROFONE (SIMPLIFICADA PARA KIVY) ---
    def iniciar_gravacao(self):
        self.root.ids.mic_btn.md_bg_color = (1, 0, 0, 0.5)
        self.update_status("Ouvindo...", (1,0,0,1))
        
        if platform == 'android':
            # Chama o reconhecimento nativo (Google Intent)
            # Esta é a forma mais robusta sem bibliotecas complexas
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            RecognizerIntent = autoclass('android.speech.RecognizerIntent')
            
            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, 'pt-BR')
            intent.putExtra(RecognizerIntent.EXTRA_PROMPT, 'Fale agora...')
            
            currentActivity = PythonActivity.mActivity
            currentActivity.startActivityForResult(intent, 100)

    def parar_gravacao(self):
        self.root.ids.mic_btn.md_bg_color = (0, 0.6, 0.6, 0.3)
        # No Android, o resultado vem via on_activity_result (que requer Java patch ou Plyer)
        # Para simplificar neste código, vamos assumir que o usuário usa a Intent
        pass

    # MÉTODO DE TESTE PC
    def enviar_comando_teste(self, texto):
        if self.connected:
            self.sio.emit('fala_usuario', {'text': texto, 'user_id': 'AndroidClient'})

if __name__ == '__main__':
    JarvisMobile().run()