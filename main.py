import random
import mysql.connector
import time
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Configuración de la base de datos MySQL
DATABASE_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2002',
    'database': 'loteria',
    'port': 3306
}

# Configuración de CasparCG
CASPARCG_HOST = "localhost"
CASPARCG_PORT = 5250

# Función para establecer la conexión con la base de datos MySQL
def obtener_conexion_db():
    try:
        # Intentar conectarse a la base de datos usando los parámetros de configuración
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        return conn
    except mysql.connector.Error as err:
        # En caso de error de conexión, mostrar el mensaje de error y retornar None
        print(f"Error de conexión a la base de datos: {err}")
        return None

# Función para seleccionar tres números aleatorios de la tabla "numeros" en la base de datos
def seleccionar_numeros_aleatorios():
    conn = obtener_conexion_db()  # Obtener conexión a la base de datos
    if conn is None:
        return [0, 0, 0]  # Si la conexión falla, retornar [0, 0, 0]
    
    cursor = conn.cursor()
    # Seleccionar tres números aleatorios de la tabla "numeros"
    cursor.execute("SELECT numero FROM numeros ORDER BY RAND() LIMIT 3")
    # Convertir los resultados de la consulta en una lista de números
    numeros = [row[0] for row in cursor.fetchall()]
    cursor.close()  # Cerrar el cursor
    conn.close()  # Cerrar la conexión
    return numeros

# Función para enviar cada número a CasparCG en una capa específica
def enviar_a_casparcg_individual(set_data_function, numero, capa, index):
    try:
        # Crear una conexión al servidor CasparCG
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((CASPARCG_HOST, CASPARCG_PORT))

            # Cargar la plantilla solo una vez (al enviar el primer número)
            if index == 1:
                s.sendall(f'CG 1-{capa} ADD {capa} "lottery_template" 1 "<templateData></templateData>"\r\n'.encode('utf-8'))
                time.sleep(0.5)

            # Comando para actualizar la plantilla con el número específico
            comando_actualizar = (
                f'CG 1-{capa} UPDATE {capa} "<templateData>'
                f'<componentData id=\\"{set_data_function}{index}\\"><data value=\\"{numero}\\"/></componentData>'
                f'</templateData>"\r\n'
            )
            # Enviar el comando de actualización a CasparCG
            s.sendall(comando_actualizar.encode('utf-8'))
            print(f"Actualización enviada a CasparCG para capa {capa}: Número {index} -> {numero}")

    except socket.error as err:
        # En caso de error en la conexión a CasparCG, mostrar un mensaje de error
        print(f"Error al enviar datos a CasparCG: {err}")

# Función para enviar tres números en secuencia con hilos
def enviar_numeros_loteria(numeros, capa, set_data_function):
    # Usar ThreadPoolExecutor para manejar los hilos y enviar números en secuencia
    with ThreadPoolExecutor(max_workers=3) as executor:
        for index, numero in enumerate(numeros, start=1):
            # Enviar cada número en su propio hilo y con un retraso entre cada uno
            executor.submit(enviar_a_casparcg_individual, set_data_function, numero, capa, index)
            time.sleep(1)  # Asegurar una secuencia entre números

# Función principal para generar y enviar resultados de la lotería
def generar_resultados_loteria(nombre_loteria, capa, set_data_function, intervalo, retraso_inicial):
    # Esperar el retraso inicial antes de la primera ejecución
    time.sleep(retraso_inicial)
    while True:
        # Seleccionar números aleatorios para la lotería
        numeros = seleccionar_numeros_aleatorios()
        conn = obtener_conexion_db()  # Conectar a la base de datos
        if conn:
            cursor = conn.cursor()
            # Insertar los números generados en la tabla de resultados
            cursor.execute(
                "INSERT INTO resultados (nombre_loteria, numero1, numero2, numero3, fecha) VALUES (%s, %s, %s, %s, %s)",
                (nombre_loteria, numeros[0], numeros[1], numeros[2], datetime.now())
            )
            conn.commit()  # Confirmar la transacción en la base de datos
            cursor.close()
            conn.close()
            print(f"Resultados guardados para {nombre_loteria}: {numeros}")

        # Enviar los números a CasparCG de forma secuencial
        enviar_numeros_loteria(numeros, capa, set_data_function)
        time.sleep(intervalo)  # Esperar el intervalo definido antes de la próxima ejecución

# Configuración principal para ejecutar varias loterías en paralelo
if __name__ == "__main__":
    # Configuración de loterías: cada una tiene su capa y tiempo de inicio
    loterias = [
        ("Loteria_A", 10, "setDataA", 32, 0),   # Lotería A en capa 10
        ("Loteria_B", 11, "setDataB", 32, 0),   # Lotería B en capa 11
        ("Loteria_C", 12, "setDataC", 32, 0)    # Lotería C en capa 12
    ]
    # Ejecutar cada lotería en un hilo separado para manejar los resultados en paralelo
    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(lambda x: generar_resultados_loteria(*x), loterias)
