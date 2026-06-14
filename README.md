# RPITempMonitor

Sistema de Monitoreo de Raspberry Pi con Logging

Sistema automático de monitoreo remoto de temperatura en Raspberry Pi con alertas visuales, de voz y registros de eventos. 
Utiliza SSH con autenticación por clave privada y almacena toda la actividad en archivos de log.

📋 Tabla de Contenidos

    Características

    Requisitos Previos

    Instalación y Configuración

    Estructura del Proyecto Modular

    Descripción de los Módulos

    Ejecución

📋 Características

    Arquitectura Modular: Separación limpia de la lógica de red/SSH, el planificador y el sistema de notificaciones.

    Monitoreo Continuo: Planificación de tareas automatizada con la librería schedule.

    Conexión SSH Segura: Autenticación remota utilizando claves privadas (.pem) mediante paramiko.

    Gestión de Logs Avanzada: Registro detallado de eventos con rotación automática de archivos (clase RotatingFileHandler) para evitar el consumo excesivo de disco.

    Alertas Multiplataforma:

        Notificaciones nativas del sistema de escritorio (Windows, macOS y Linux).

        Alertas por síntesis de voz en el idioma del sistema operativo.

    Configuración Centralizada: Control total del comportamiento del script mediante un archivo json con soporte robusto para valores por defecto (fallbacks).

🔧 Requisitos Previos
Software requerido

    Python 3.8+

    pip (gestor de paquetes de Python)

    SSH disponible en tu Raspberry Pi

    Conexión LAN entre tu equipo y la Raspberry Pi

    Tu clave privada de SSH (private_key.pem) copiada en el directorio raíz del proyecto.

Herramientas del sistema según SO

Windows:

    PowerShell (incluido por defecto)

macOS:

    Command Line Tools (xcode-select --install)

Linux (Debian/Ubuntu):
Bash

sudo apt-get update
sudo apt-get install openssh-client espeak

## 🚀 Instalación y Configuración
 #Acceder al directorio del proyecto
Bash

cd

# Crear y activar el entorno virtual
Bash

# Crear entorno virtual
python3 -m venv .venv

# Activar en macOS / Linux
source .venv/bin/activate

# Activar en Windows (PowerShell)
.venv\Scripts\Activate.ps1

3. Instalar las dependencias
Bash

pip install -r requirements.txt

4. Configurar el archivo config.json

Crea un archivo llamado config.json en la raíz del proyecto con la siguiente estructura:
JSON

{
  "raspberry_pi": {
    "ip": "10.0.0.195",
    "user": "pinacho",
    "ssh_key_path": "./private_key.pem",
    "port": 22,
    "timeout": 5
  },
  "monitoring": {
    "temp_limit": 60.0,
    "check_interval_seconds": 15
  },
  "logging": {
    "log_dir": "./logs",
    "max_bytes": 10485760,
    "backup_count": 5
  }
}

📁 Estructura del Proyecto Modular
Plaintext

TP-automatizacion/
│
├── .venv/                  # Entorno virtual de Python
├── logs/                   # Carpeta autogenerada con los archivos de log históricos
│   └── monitor_sistema.log
├── config.json             # Archivo de configuración global
├── utils.py                # Módulo de utilidades (Notificaciones y Alertas de voz)
├── monitor_core.py         # Núcleo del sistema (Clases de Config, SSH y Monitoreo)
├── main.py                 # Punto de entrada principal y Daemon del planificador
├── private_key.pem         # Clave privada para la autenticación SSH
├── README.md               # Documentación del proyecto
└─ requirements.txt        # Librerías externas (paramiko, schedule)

⚙️ Descripción de los Módulos
1. utils.py (Módulo de Interfaces del Sistema)

Contiene las funciones nativas que interactúan con el sistema operativo anfitrión (Host). Despliega globos de notificación gráfica y ejecuta la síntesis de texto a voz a través de subprocesos (subprocess) optimizados para Windows (PowerShell), macOS (AppleScript) y Linux.
2. monitor_core.py (Núcleo de Infraestructura)

Contiene toda la lógica pesada y los objetos del negocio:

    ConfigManager: Analiza el archivo JSON y provee un método de lectura anidada seguro (*keys) con control de excepciones.

    LoggerSetup: Configura la salida dual (Consola/Archivo) con políticas de tamaño máximo en bytes para resguardar el almacenamiento local usando archivos rotativos.

    SSHConnection: Encapsula el cliente paramiko para gestionar la apertura, ejecución de comandos Bash remotos y cierre seguro del socket SSH.

    MonitorRaspberryPi: Orquestador principal. Realiza un diagnóstico de Red (Ping ICMP) en Capa 3 antes de iniciar el túnel SSH, analiza la temperatura extraída usando expresiones regulares (re) y evalúa el umbral térmico.

3. main.py (Punto de Entrada)

Es el archivo ejecutable. Inicializa los componentes de forma segura dentro de un bloque de control de fallos, configura el intervalo del planificador (schedule) y mantiene el bucle principal o daemon corriendo en segundo plano hasta recibir una señal de interrupción (Ctrl+C).
💻 Ejecución

Para iniciar el sistema de monitoreo, ejecuta el archivo principal:
Bash

python3 main.py

Para detener el programa de forma segura en cualquier momento, presiona Ctrl + C en la terminal.
