"""Script ejecutable principal para el monitoreo automatizado de infraestructura."""

import sys
import time
from monitor_core import ConfigManager, LoggerSetup, MonitorRaspberryPi
import schedule

# Inicialización segura de componentes globales
try:
    CONFIG = ConfigManager("config.json")
    LOGGER = LoggerSetup.setup(CONFIG)
    LOGGER.info("Sistema de monitoreo desplegado de forma íntegra.")
except Exception as inicializacion_error:  
    print(f"[CRÍTICO] Fallo catastrófico de entorno: {inicializacion_error}")
    sys.exit(1)


def main():
    """Punto de entrada primario del hilo de ejecución del daemon."""
    monitor = MonitorRaspberryPi(CONFIG, LOGGER)

    intervalo = int(CONFIG.get("monitoring", "check_interval_seconds", default=15))
    schedule.every(intervalo).seconds.do(monitor.ciclo_monitoreo)

    LOGGER.info("Planificador configurado a intervalos de %s segundos.", intervalo)
    LOGGER.info("Servicio activo. Presione Ctrl+C para interrumpir el daemon.")

    # Disparo de calibración inicial inmediato
    monitor.ciclo_monitoreo()

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        LOGGER.info("Daemon de monitoreo terminado por interrupción de usuario.")
        sys.exit(0)
    except Exception as runtime_error:
        LOGGER.critical("Fallo imprevisto en tiempo de ejecución: %s", runtime_error)
        sys.exit(1)


if __name__ == "__main__":
    main()
