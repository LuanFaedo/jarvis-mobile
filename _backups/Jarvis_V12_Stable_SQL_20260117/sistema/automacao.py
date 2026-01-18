import pyautogui
import psutil
import time
import os
import subprocess
import platform

# Configurações de Segurança do PyAutoGUI
pyautogui.FAILSAFE = False # Permite mover o mouse para os cantos sem travar (Cuidado!)
pyautogui.PAUSE = 0.5 # Pequena pausa entre ações para estabilidade

class AutomacaoPC:
    def __init__(self):
        self.os_name = platform.system()

    def abrir_programa(self, nome_executavel):
        """Abre um programa pelo nome ou caminho"""
        print(f"[AUTO] Tentando abrir: {nome_executavel}")
        try:
            # Tenta via comando 'start' do Windows (mais robusto que subprocess direto)
            os.system(f"start {nome_executavel}")
            return f"Comando de abertura enviado para: {nome_executavel}"
        except Exception as e:
            return f"Erro ao abrir programa: {e}"

    def fechar_programa(self, nome_processo):
        """Mata um processo pelo nome (ex: chrome.exe)"""
        killed = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if nome_processo.lower() in proc.info['name'].lower():
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        if killed > 0:
            return f"{killed} processos '{nome_processo}' encerrados."
        return f"Nenhum processo '{nome_processo}' encontrado."

    def minimizar_tudo(self):
        pyautogui.hotkey('win', 'd')
        return "Todas as janelas minimizadas."

    def digitar(self, texto):
        """Digita um texto simulando o teclado"""
        pyautogui.write(texto, interval=0.05)
        return "Texto digitado."

    def pressionar(self, tecla):
        """Pressiona uma tecla específica (enter, esc, win, etc)"""
        pyautogui.press(tecla)
        return f"Tecla '{tecla}' pressionada."
    
    def screenshot_region(self, x, y, w, h, save_path):
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
        screenshot.save(save_path)
        return f"Screenshot salva em {save_path}"

    def mover_mouse(self, x, y):
        pyautogui.moveTo(x, y, duration=0.5)
        return f"Mouse movido para ({x}, {y})"

    def clicar(self):
        pyautogui.click()
        return "Clique realizado."

# Instância global para uso
pc = AutomacaoPC()
