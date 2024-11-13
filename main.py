import random
import mysql.connector
import time
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import threading
from tkinter import Tk, Label, Entry, Button, filedialog
import os

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

def obtener_conexion_db():
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error de conexión a la base de datos: {err}")
        return None

def insertar_direccion_en_bd(direccion, duracion):
    """
    Inserta la dirección completa de la imagen y el tiempo de duración en la base de datos.
    """
    conn = obtener_conexion_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO imagenes (direccion, duracion) VALUES (%s, %s)", (direccion, duracion))
            conn.commit()
            cursor.close()
            print(f"Dirección '{direccion}' y duración '{duracion}' insertadas en la base de datos.")
        except mysql.connector.Error as err:
            print(f"Error al insertar en la base de datos: {err}")
        finally:
            conn.close()

def seleccionar_numeros_aleatorios():
    conn = obtener_conexion_db()
    if conn is None:
        return [0, 0, 0]

    cursor = conn.cursor()
    cursor.execute("SELECT numero FROM numeros ORDER BY RAND() LIMIT 3")
    numeros = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return numeros

def enviar_a_casparcg_individual(set_data_function, numero, capa, index):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((CASPARCG_HOST, CASPARCG_PORT))
            if index == 1:
                s.sendall(f'CG 1-{capa} ADD {capa} "lottery_template" 1 "<templateData></templateData>"\r\n'.encode('utf-8'))
                time.sleep(0.5)

            comando_actualizar = (
                f'CG 1-{capa} UPDATE {capa} "<templateData>'
                f'<componentData id=\\"{set_data_function}{index}\\"><data value=\\"{numero}\\"/></componentData>'
                f'</templateData>"\r\n'
            )
            s.sendall(comando_actualizar.encode('utf-8'))
            print(f"Actualización enviada a CasparCG para capa {capa}: Número {index} -> {numero}")

    except socket.error as err:
        print(f"Error al enviar datos a CasparCG: {err}")

def enviar_numeros_loteria(numeros, capa, set_data_function):
    with ThreadPoolExecutor(max_workers=3) as executor:
        for index, numero in enumerate(numeros, start=1):
            executor.submit(enviar_a_casparcg_individual, set_data_function, numero, capa, index)
            time.sleep(1)

def generar_resultados_loteria(nombre_loteria, capa, set_data_function, intervalo, retraso_inicial):
    time.sleep(retraso_inicial)
    while True:
        numeros = seleccionar_numeros_aleatorios()
        conn = obtener_conexion_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO resultados (nombre_loteria, numero1, numero2, numero3, fecha) VALUES (%s, %s, %s, %s, %s)",
                (nombre_loteria, numeros[0], numeros[1], numeros[2], datetime.now())
            )
            conn.commit()
            cursor.close()
            conn.close()
            print(f"Resultados guardados para {nombre_loteria}: {numeros}")

        enviar_numeros_loteria(numeros, capa, set_data_function)
        time.sleep(intervalo)

def mostrar_media_en_casparcg(capa, ruta, duracion):
    """
    Muestra una imagen en CasparCG utilizando la plantilla 'image_overlay_template' en una capa específica
    por un tiempo determinado y registra la dirección y duración en la base de datos.
    """
    # Inserta la dirección completa y la duración en la base de datos
    insertar_direccion_en_bd(ruta, duracion)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((CASPARCG_HOST, CASPARCG_PORT))

            # Convertir la ruta completa para que sea compatible con 'file:///' en caso de espacios
            ruta_completa = f"file:///{ruta.replace(' ', '%20')}"
            print(f"Enviando archivo '{ruta_completa}' a CasparCG en la capa {capa}.")  # Log para el nombre del archivo

            comando_cargar = (
                f'CG 1-{capa} ADD {capa} "image_overlay_template" 1 '
                f'"<templateData><componentData id=\\"imageUrl\\"><data value=\\"{ruta_completa}\\"/></componentData></templateData>"\r\n'
            )

            # Enviar el comando
            s.sendall(comando_cargar.encode('utf-8'))
            print(f"Imagen '{ruta_completa}' cargada en CasparCG en la capa {capa} usando plantilla 'image_overlay_template'.")

            # Esperar la duración especificada
            time.sleep(duracion)

            # Quitar el contenido de la capa
            comando_stop = f'CG 1-{capa} REMOVE {capa}\r\n'
            s.sendall(comando_stop.encode('utf-8'))
            print(f"Imagen en la capa {capa} eliminada después de {duracion} segundos.")

    except socket.error as err:
        print(f"Error al enviar imagen a CasparCG: {err}")

def seleccionar_media():
    """
    Ventana persistente para seleccionar una imagen y especificar la duración.
    """
    def seleccionar_archivo():
        archivo = filedialog.askopenfilename(filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
        ruta_entry.delete(0, "end")
        ruta_entry.insert(0, archivo)

    def enviar_imagen():
        ruta = ruta_entry.get()
        duracion = int(duracion_entry.get()) if duracion_entry.get().isdigit() else 10
        if ruta:
            capa = 20  # Capa específica para mostrar imágenes
            threading.Thread(target=mostrar_media_en_casparcg, args=(capa, ruta, duracion)).start()

    ventana = Tk()
    ventana.title("Seleccionar Media")
    ventana.geometry("400x200")

    Label(ventana, text="Seleccione una imagen (opcional):").pack(pady=5)
    ruta_entry = Entry(ventana, width=50)
    ruta_entry.pack(pady=5)
    Button(ventana, text="Buscar", command=seleccionar_archivo).pack(pady=5)

    Label(ventana, text="Duración en segundos:").pack(pady=5)
    duracion_entry = Entry(ventana, width=10)
    duracion_entry.insert(0, "10")  # Duración por defecto
    duracion_entry.pack(pady=5)

    Button(ventana, text="Enviar a CasparCG", command=enviar_imagen).pack(pady=10)

    ventana.mainloop()

# Configuración principal para ejecutar varias loterías en paralelo
if __name__ == "__main__":
    # Configuración de loterías
    loterias = [
        ("Loteria_A", 10, "setDataA", 32, 0),   # Lotería A en capa 10
        ("Loteria_B", 11, "setDataB", 32, 0),   # Lotería B en capa 11
        ("Loteria_C", 12, "setDataC", 32, 0)    # Lotería C en capa 12
    ]
    # Ejecutar cada lotería en un hilo separado para manejar los resultados en paralelo
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(lambda x: generar_resultados_loteria(*x), loterias)

        # Hilo para mostrar ventana persistente de selección de media
        threading.Thread(target=seleccionar_media).start()
