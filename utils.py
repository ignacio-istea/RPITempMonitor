"""Módulo de utilidades del sistema para alertas visuales y de voz."""

import subprocess
import sys
import warnings

# Silenciamos las alertas molestas de Paramiko
warnings.filterwarnings("ignore", category=UserWarning, module="paramiko")


def enviar_notificacion_local(titulo: str, mensaje: str):
    """Despliega notificaciones gráficas de escritorio según el SO nativo."""
    sistema = sys.platform
    try:
        if sistema.startswith("win32"):
            # Windows
            comando_ps = (
                "[void][System.Reflection.Assembly]::LoadWithPartialName("
                "'System.Windows.Forms'); "
                "$obj = New-Object System.Windows.Forms.NotifyIcon; "
                "$obj.Icon = [System.Drawing.SystemIcons]::Information; "
                f"$obj.BalloonTipTitle = '{titulo}'; "
                f"$obj.BalloonTipText = '{mensaje}'; "
                "$obj.Visible = $true; "
                "$obj.ShowBalloonTip(5000)"
            )
            subprocess.run(
                ["powershell", "-Command", comando_ps],
                shell=False,
                capture_output=True,
                check=False
            )

        elif sistema.startswith("darwin"):
            # MacOS
            comando_as = (
                f'display notification "{mensaje}" with title "{titulo}"'
            )
            subprocess.run(["osascript", "-e", comando_as], shell=False, check=False)

        else:
            # GNU/Linux
            subprocess.run(["notify-send", titulo, mensaje], shell=False, check=False)

    except Exception:  
        pass  # Falla silenciosa si el entorno no soporta GUI


def reproducir_alerta_voz(texto: str):
    """Sintetiza texto a voz de acuerdo al soporte del sistema operativo."""
    sistema = sys.platform
    try:
        if sistema.startswith("win32"):
            comando_ps = (
                "Add-Type -AssemblyName System.Speech; "
                "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$speak.Speak('{texto}')"
            )
            subprocess.run(
                ["powershell", "-Command", comando_ps],
                shell=False,
                capture_output=True,
                check=False
            )

        elif sistema.startswith("darwin"):
            subprocess.run(["say", "-v", "Paulina", texto], shell=False, check=False)

        else:
            subprocess.run(["espeak", "-v", "es", texto], shell=False, check=False)

    except Exception: 
        pass
