"""Núcleo del sistema de monitoreo, telemetría y conexiones remotas."""

import json
import logging
from logging.handlers import RotatingFileHandler
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import paramiko
from utils import enviar_notificacion_local, reproducir_alerta_voz


class ConfigManager:
    """Gestor centralizado de configuración desde archivos estructurados JSON."""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Archivo de configuración no encontrado: {config_path}"
            )

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def get(self, *keys, default=None):                 #acceso al JSON mediante Tupla keys
        """Obtiene valores anidados admitiendo fallback por defecto seguro."""
        lista_keys = list(keys)
        if len(lista_keys) > 1 and not isinstance(lista_keys[-1], str):
            default = lista_keys.pop()

        value = self.config
        try:
            for key in lista_keys:
                value = value[key]
            return value if value is not None else default
        except (KeyError, TypeError):
            return default


class LoggerSetup:
    """Configuración automatizada de logging con rotación y salida dual."""

    @staticmethod
    def setup(config: ConfigManager) -> logging.Logger:
        log_dir_raw = config.get("logging", "log_dir") or "./logs"
        log_dir = Path(log_dir_raw)
        log_dir.mkdir(exist_ok=True)

        logger = logging.getLogger("RaspberryPiMonitor")
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        log_file = log_dir / f"monitor_{datetime.now().strftime('%Y%m%d')}.log"
        max_bytes = config.get("logging", "max_bytes") or 10485760
        backup_count = config.get("logging", "backup_count") or 5

        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=int(max_bytes),
            backupCount=int(backup_count)
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger


class SSHConnection:
    """Administrador de sesiones SSH usando credenciales de llaves asimétricas."""

    def __init__(self, config: ConfigManager, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.ssh = None

    def conectar(self) -> bool:
        """Inicializa el cliente SSH mediante handshake criptográfico."""
        try:
            ip = self.config.get("raspberry_pi", "ip")
            user = self.config.get("raspberry_pi", "user")
            key_path = self.config.get("raspberry_pi", "ssh_key_path")
            port = int(self.config.get("raspberry_pi", "port", default=22))
            timeout = int(self.config.get("raspberry_pi", "timeout", default=5))

            self.logger.info("Intentando conexión SSH a %s@%s:%s...", user, ip, port)

            if not Path(key_path).exists():
                raise FileNotFoundError(f"Clave privada no encontrada: {key_path}")

            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self.ssh.connect(
                hostname=ip,
                port=port,
                username=user,
                key_filename=key_path,
                timeout=timeout,
                look_for_keys=True,
                allow_agent=True
            )
            self.logger.info("Conexión SSH establecida exitosamente")
            return True

        except (paramiko.ssh_exception.NoValidConnectionsError,
                paramiko.ssh_exception.AuthenticationException) as e:
            self.logger.error("Fallo de infraestructura SSH: %s", e)
            return False
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error no controlado en SSH: %s", e)
            return False

    def ejecutar_comando(self, comando: str) -> str:
        """Despacha una instrucción Bash remota y sanitiza buffers de salida."""
        try:
            if not self.ssh:
                self.logger.error("No hay conexión SSH activa")
                return ""

            _, stdout, stderr = self.ssh.exec_command(comando, timeout=10)
            salida = stdout.read().decode("utf-8").strip()
            error = stderr.read().decode("utf-8").strip()

            if error:
                self.logger.warning("Mensaje stderr remoto: %s", error)

            return salida
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error al ejecutar '%s': %s", comando, e)
            return ""

    def cerrar(self):
        """Libera de forma segura el socket remoto asignado."""
        if self.ssh:
            self.ssh.close()
            self.logger.debug("Conexión SSH destruida")


class MonitorRaspberryPi:
    """Orquestador maestro encargado de las rutinas cíclicas de telemetría."""

    def __init__(self, config: ConfigManager, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.ssh_conn = SSHConnection(config, logger)

    def verificar_conectividad_red(self) -> bool:
        """Evalúa respuesta ICMP de capa 3 del nodo remoto."""
        ip = self.config.get("raspberry_pi", "ip")
        parametro_ping = "-n" if sys.platform.startswith("win32") else "-c"

        try:
            self.logger.debug("Validando enlace ICMP hacia %s...", ip)
            resultado = subprocess.run(
                ["ping", parametro_ping, "1", ip],
                capture_output=True,
                text=True,
                timeout=4,
                check=False
            )
            return resultado.returncode == 0
        except Exception as e:  
            self.logger.error("Error en ping socket local: %s", e)
            return False

    def obtener_telemetria(self) -> dict:
        """Recolecta métricas de hardware mediante parsing regex."""
        resultado = {"temperatura": None, "uptime": None, "exito": False}
        try:
            cmd = "vcgencmd measure_temp || cat /sys/class/thermal/thermal_zone0/temp"
            temp_output = self.ssh_conn.ejecutar_comando(cmd)

            temp_match = re.search(r"temp=(\d+\.\d+)|(\d+)", temp_output)
            if temp_match:
                temperatura = float(temp_match.group(1) or temp_match.group(2))
                if temperatura > 1000:
                    temperatura /= 1000
                resultado["temperatura"] = temperatura

            uptime_output = self.ssh_conn.ejecutar_comando("uptime")
            if uptime_output:
                resultado["uptime"] = uptime_output

            resultado["exito"] = resultado["temperatura"] is not None
        except Exception as e:  
            self.logger.error("Fallo recolectando datos raw: %s", e)
        return resultado

    def ciclo_monitoreo(self):
        """Ejecuta una iteración lógica completa de evaluación de métricas."""
        self.logger.info("Iniciando análisis periódico...")

        if not self.verificar_conectividad_red():
            msg = "Dispositivo inaccesible (Fallo ping ICMP)"
            self.logger.error(msg)
            enviar_notificacion_local("Fallo de Conexión LAN", msg)
            reproducir_alerta_voz("Alerta: Conexión de red perdida")
            return

        if not self.ssh_conn.conectar():
            enviar_notificacion_local("Fallo SSH", "Fallo handshake asimétrico")
            reproducir_alerta_voz("Error de autenticación remota")
            return

        telemetria = self.obtener_telemetria()
        if not telemetria["exito"]:
            self.logger.error("Métricas térmicas corruptas o ilegibles")
            self.ssh_conn.cerrar()
            return

        temp = telemetria["temperatura"]
        limite = float(self.config.get("monitoring", "temp_limit", default=60.0))

        self.logger.info("Métrica térmica actual: %s°C | Umbral: %s°C", temp, limite)

        if temp >= limite:
            msg = f"¡ALERTA TÉRMICA! Procesador crítico a {temp}°C"
            self.logger.critical(msg)
            enviar_notificacion_local("⚠️ UMBRAL TÉRMICO CRÍTICO ⚠️", msg)
            reproducir_alerta_voz(msg)
        else:
            self.logger.info("Estado térmico nominal.")
            reproducir_alerta_voz(f"Temperatura en {int(temp)} grados")

        self.ssh_conn.cerrar()
