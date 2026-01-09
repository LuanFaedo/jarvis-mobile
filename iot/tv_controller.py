import os
import json
import logging
from wakeonlan import send_magic_packet
from samsungtvws import SamsungTVWS

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JarvisIoT")

TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'tv_token.json')

class TVController:
    def __init__(self, ip, mac=None, model='samsung'):
        self.ip = ip
        self.mac = mac
        self.model = model.lower()
        self.token = self._load_token()

    def _load_token(self):
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get(self.ip)
            except: pass
        return None

    def _save_token(self, token):
        data = {}
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f: data = json.load(f)
            except: pass
        
        data[self.ip] = token
        with open(TOKEN_FILE, 'w') as f:
            json.dump(data, f)

    def ligar(self):
        """Liga a TV usando Wake-on-LAN (Precisa do MAC Address e TV no cabo ou Wi-Fi com WoL ativo)"""
        if not self.mac:
            return "Erro: Preciso do endereço MAC para ligar a TV."
        
        try:
            # Limpa o MAC para evitar erros de formatação
            mac_clean = self.mac.replace(":", "").replace("-", "")
            # Envia 3 pacotes para garantir
            send_magic_packet(mac_clean)
            send_magic_packet(mac_clean)
            send_magic_packet(mac_clean)
            return "Sinal de LIGAR (WoL) enviado via Rede."
        except Exception as e:
            return f"Erro ao tentar ligar: {e}"

    def desligar(self):
        """Desliga a TV via API (Tenta múltiplos métodos)"""
        if self.model == 'samsung':
            res_log = []
            
            # 1. Tenta KEY_POWER (Padrão)
            res1 = self._cmd_samsung('KEY_POWER')
            res_log.append(f"Std: {res1}")
            
            # 2. Tenta KEY_POWEROFF (Explícito)
            try:
                self._cmd_samsung('KEY_POWEROFF')
            except: pass
            
            # 3. Tenta Método Alternativo (Shortcuts) se o primeiro falhou ou retornou status
            if "Falha" in res1 or "Touch" in res1:
                try:
                    tv = SamsungTVWS(host=self.ip, port=8002, token=self.token, timeout=2, name='Jarvis')
                    tv.shortcuts().power()
                    res_log.append("Alt: Enviado")
                except Exception as e:
                    res_log.append(f"Alt: Erro {e}")

            return f"Tentativas de Desligar: {'; '.join(res_log)}"
        return "Modelo não suportado para desligamento via API."

    # --- CONTROLE DE VOLUME COM QUANTIDADE ---
    def volume_up(self, qtd=1):
        return self._send_repeated('KEY_VOLUP', qtd)

    def volume_down(self, qtd=1):
        return self._send_repeated('KEY_VOLDOWN', qtd)
    
    def mute(self):
        return self._cmd_samsung('KEY_MUTE')

    # --- NAVEGAÇÃO ---
    def up(self, qtd=1): return self._send_repeated('KEY_UP', qtd)
    def down(self, qtd=1): return self._send_repeated('KEY_DOWN', qtd)
    def left(self, qtd=1): return self._send_repeated('KEY_LEFT', qtd)
    def right(self, qtd=1): return self._send_repeated('KEY_RIGHT', qtd)
    
    def enter(self): return self._cmd_samsung('KEY_ENTER') 
    def back(self): return self._cmd_samsung('KEY_RETURN')
    def home(self): return self._cmd_samsung('KEY_HOME')
    
    # --- CANAIS ---
    def channel_up(self): return self._cmd_samsung('KEY_CHUP')
    def channel_down(self): return self._cmd_samsung('KEY_CHDOWN')
    def channel_list(self): return self._cmd_samsung('KEY_CH_LIST')
    
    # --- MÍDIA ---
    def play(self): return self._cmd_samsung('KEY_PLAY')
    def pause(self): return self._cmd_samsung('KEY_PAUSE')
    def stop(self): return self._cmd_samsung('KEY_STOP')
    
    # --- SISTEMA ---
    def menu(self): return self._cmd_samsung('KEY_MENU') 
    def source(self): return self._cmd_samsung('KEY_SOURCE')
    def info(self): return self._cmd_samsung('KEY_INFO')
    def exit(self): return self._cmd_samsung('KEY_EXIT')
    
    # --- NUMÉRICO (Genérico) ---
    def num(self, n):
        return self._cmd_samsung(f'KEY_{n}')
        
    # --- DIGITAÇÃO (Novo) ---
    def type_text(self, text):
        """Digita um texto na TV (letra por letra)"""
        import time
        sucesso = 0
        try:
            # Conexão persistente
            tv = SamsungTVWS(host=self.ip, port=8002, token=self.token, timeout=5, name='Jarvis')
            
            for char in text:
                key = None
                if char.isdigit(): key = f"KEY_{char}"
                elif char == " ": key = "KEY_SPACE"
                elif char.isalpha(): key = f"KEY_{char.upper()}"
                
                if key:
                    tv.send_key(key)
                    sucesso += 1
                    time.sleep(0.2) # Delay para a TV processar
            
            # Opcional: Dar Enter no final? Melhor não, deixar usuário confirmar.
            return f"Digitado '{text}' ({sucesso} caracteres)."
        except Exception as e:
            return f"Erro ao digitar: {e}"

    # --- MACROS PERSONALIZADAS (Sua TV - Modo Turbo) ---
    def open_netflix_macro(self):
        """Macro: Home -> Baixo(2) -> Direita(1) -> Enter"""
        return self._exec_macro(['KEY_HOME', 'KEY_DOWN', 'KEY_DOWN', 'KEY_RIGHT', 'KEY_ENTER'])

    def open_youtube_macro(self):
        """Macro: Home -> Baixo(2) -> Direita(2) -> Enter"""
        # Ajuste: Se Youtube for o vizinho da Netflix
        return self._exec_macro(['KEY_HOME', 'KEY_DOWN', 'KEY_DOWN', 'KEY_RIGHT', 'KEY_RIGHT', 'KEY_ENTER'])

    def _exec_macro(self, keys):
        import time
        try:
            tv = SamsungTVWS(host=self.ip, port=8002, token=self.token, timeout=5, name='Jarvis')
            
            # 1. Abre Home (Precisa de tempo pra carregar a UI)
            tv.send_key(keys[0])
            time.sleep(1.5) # Reduzido de 2.5s para 1.5s (Ajuste se falhar)
            
            # 2. Executa o resto rápido
            for k in keys[1:]:
                tv.send_key(k)
                time.sleep(0.15) # Muito rápido
                
            return "Macro executada com sucesso."
        except Exception as e:
            return f"Erro na macro: {e}"

    def open_app(self, app_name):
        """Gerenciador de Apps"""
        app_name = app_name.lower()
        
        # Prioridade: Macros Manuais
        if app_name == 'netflix': return self.open_netflix_macro()
        if app_name == 'youtube': return self.open_youtube_macro()
        
        return "App não mapeado na macro."

    def _send_repeated(self, key_code, count):
        """Envia o mesmo comando X vezes com rapidez"""
        try:
            import time
            count = int(count)
            # Limite de segurança para não travar
            if count > 50: count = 50 
            if count < 1: count = 1
            
            # Conexão persistente para ser rápido
            tv = SamsungTVWS(host=self.ip, port=8002, token=self.token, timeout=5, name='Jarvis')
            
            # Atualiza token se necessário
            if tv.token and tv.token != self.token:
                self._save_token(tv.token)
            
            sucesso = 0
            for _ in range(count):
                tv.send_key(key_code)
                sucesso += 1
                # Pequeno delay para a TV processar (0.1s é muito rápido, 0.2s é seguro)
                time.sleep(0.15)
                
            return f"Comando executado {sucesso} vezes."
        except Exception as e:
            return f"Erro na execução múltipla: {e}"

    def _cmd_samsung(self, key_code):
        try:
            # Tenta conectar. Se tiver token, usa. Se não, abre popup na TV.
            tv = SamsungTVWS(host=self.ip, port=8002, token=self.token, timeout=5, name='Jarvis')
            
            # Atualiza token se mudou
            if tv.token and tv.token != self.token:
                self._save_token(tv.token)

            # Usa o metodo direto send_key
            tv.send_key(key_code)
            
            return "Comando enviado com sucesso."
        except Exception as e:
            # Tratamento de "falso erro" comum em Tizen
            err_str = str(e)
            if "ms.remote.touchDisable" in err_str or "ms.remote.touchEnable" in err_str:
                return "Comando enviado (Status Touch recebido)."
                
            return f"Falha na comunicação com a TV: {e}. (Verifique se ela está ligada ou se o IP mudou)"

# Exemplo de uso para teste
if __name__ == "__main__":
    # Substitua pelos dados da sua TV para testar
    TV_IP = "192.168.1.50" 
    TV_MAC = "AA:BB:CC:DD:EE:FF"
    
    ctrl = TVController(TV_IP, TV_MAC)
    # print(ctrl.desligar())
