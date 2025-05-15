from datetime import datetime, timedelta
import pandas as pd
import re

# Lista de días festivos en Colombia para 2025
FESTIVOS_2025 = [
    datetime(2025, 1, 1),  # Año Nuevo
    datetime(2025, 1, 6),  # Día de los Reyes Magos
    datetime(2025, 3, 24),  # Día de San José
    datetime(2025, 4, 17),  # Jueves Santo
    datetime(2025, 4, 18),  # Viernes Santo
    datetime(2025, 5, 1),  # Día del Trabajo
    datetime(2025, 5, 29),  # Ascensión del Señor
    datetime(2025, 6, 19),  # Corpus Christi
    datetime(2025, 6, 27),  # Sagrado Corazón
    datetime(2025, 6, 30),  # San Pedro y San Pablo
    datetime(2025, 7, 20),  # Día de la Independencia
    datetime(2025, 8, 7),  # Batalla de Boyacá
    datetime(2025, 8, 18),  # Asunción de la Virgen
    datetime(2025, 10, 13),  # Día de la Raza
    datetime(2025, 11, 3),  # Todos los Santos
    datetime(2025, 11, 17),  # Independencia de Cartagena
    datetime(2025, 12, 8),  # Día de la Inmaculada Concepción
    datetime(2025, 12, 25)  # Navidad
]


def es_festivo(fecha):
    """Verifica si una fecha es festivo en Colombia."""
    for festivo in FESTIVOS_2025:
        if (fecha.day == festivo.day and
                fecha.month == festivo.month and
                fecha.year == festivo.year):
            return True
    return False


def procesar_fecha(fecha_str):
    """Procesa una fecha de manera segura manejando NaT."""
    if pd.isna(fecha_str) or fecha_str == '' or fecha_str is None:
        return None

    # Si es un objeto datetime o Timestamp, retornarlo directamente
    if isinstance(fecha_str, (pd.Timestamp, datetime)):
        if pd.isna(fecha_str):  # Comprobar si es NaT
            return None
        return fecha_str

    # Si es un string, procesarlo
    try:
        # Eliminar espacios y caracteres extraños
        fecha_str = re.sub(r'[^\d/\-]', '', str(fecha_str).strip())

        # Formatos a intentar
        formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']

        for formato in formatos:
            try:
                fecha = pd.to_datetime(fecha_str, format=formato)
                if pd.notna(fecha):  # Verificar que no sea NaT
                    return fecha
            except:
                continue

        return None
    except Exception:
        return None


def formatear_fecha(fecha_str):
    """Formatea una fecha en formato DD/MM/YYYY manejando NaT."""
    try:
        fecha = procesar_fecha(fecha_str)
        if fecha is not None and pd.notna(fecha):
            return fecha.strftime('%d/%m/%Y')
        return ""
    except Exception:
        # Si hay cualquier error, devuelve cadena vacía
        return ""


def calcular_plazo_analisis(fecha_entrega):
    """
    Calcula el plazo de análisis como 5 días hábiles después de la fecha de entrega,
    sin contar sábados, domingos y festivos en Colombia.
    """
    # Convertir la fecha de entrega a objeto datetime
    fecha = procesar_fecha(fecha_entrega)
    if fecha is None or pd.isna(fecha):
        return None

    # Contador de días hábiles
    dias_habiles = 0
    fecha_actual = fecha

    # Calcular 5 días hábiles a partir de la fecha de entrega
    while dias_habiles < 5:
        # Avanzar un día
        fecha_actual = fecha_actual + timedelta(days=1)

        # Verificar si es día hábil (no es fin de semana ni festivo)
        dia_semana = fecha_actual.weekday()  # 0 = lunes, 6 = domingo

        # Si no es sábado (5) ni domingo (6) ni festivo, contamos como día hábil
        if dia_semana < 5 and not es_festivo(fecha_actual):
            dias_habiles += 1

    # Retornar la fecha calculada
    return fecha_actual


def calcular_plazo_cronograma(fecha_plazo_analisis):
    """
    Calcula el plazo de cronograma como 3 días hábiles después del plazo de análisis,
    sin contar sábados, domingos y festivos en Colombia.
    """
    # Convertir la fecha de plazo de análisis a objeto datetime
    fecha = procesar_fecha(fecha_plazo_analisis)
    if fecha is None or pd.isna(fecha):
        return None

    # Contador de días hábiles
    dias_habiles = 0
    fecha_actual = fecha

    # Calcular 3 días hábiles a partir del plazo de análisis
    while dias_habiles < 3:
        # Avanzar un día
        fecha_actual = fecha_actual + timedelta(days=1)

        # Verificar si es día hábil (no es fin de semana ni festivo)
        dia_semana = fecha_actual.weekday()  # 0 = lunes, 6 = domingo

        # Si no es sábado (5) ni domingo (6) ni festivo, contamos como día hábil
        if dia_semana < 5 and not es_festivo(fecha_actual):
            dias_habiles += 1

    # Retornar la fecha calculada
    return fecha_actual


def calcular_plazo_oficio_cierre(fecha_publicacion):
    """
    Calcula el plazo de oficio de cierre como 7 días hábiles después de la fecha de publicación,
    sin contar sábados, domingos y festivos en Colombia.
    """
    # Convertir la fecha de publicación a objeto datetime
    fecha = procesar_fecha(fecha_publicacion)
    if fecha is None or pd.isna(fecha):
        return None

    # Contador de días hábiles
    dias_habiles = 0
    fecha_actual = fecha

    # Calcular 7 días hábiles a partir de la fecha de publicación
    while dias_habiles < 7:
        # Avanzar un día
        fecha_actual = fecha_actual + timedelta(days=1)

        # Verificar si es día hábil (no es fin de semana ni festivo)
        dia_semana = fecha_actual.weekday()  # 0 = lunes, 6 = domingo

        # Si no es sábado (5) ni domingo (6) ni festivo, contamos como día hábil
        if dia_semana < 5 and not es_festivo(fecha_actual):
            dias_habiles += 1

    # Retornar la fecha calculada
    return fecha_actual


def actualizar_plazo_analisis(df):
    """
    Actualiza la columna 'Plazo de análisis' en el DataFrame
    basándose en la columna 'Fecha de entrega de información'.
    """
    if 'Fecha de entrega de información' not in df.columns:
        return df

    # Crear una copia del DataFrame
    df_actualizado = df.copy()

    # Iterar sobre cada fila
    for idx, row in df.iterrows():
        fecha_entrega = row.get('Fecha de entrega de información', None)
        if fecha_entrega and pd.notna(fecha_entrega) and fecha_entrega != '':
            plazo = calcular_plazo_analisis(fecha_entrega)
            if plazo is not None:
                df_actualizado.at[idx, 'Plazo de análisis'] = formatear_fecha(plazo)
                
                # Al actualizar el plazo de análisis, también actualizar el plazo de cronograma
                plazo_cronograma = calcular_plazo_cronograma(plazo)
                if plazo_cronograma is not None:
                    df_actualizado.at[idx, 'Plazo de cronograma'] = formatear_fecha(plazo_cronograma)

    return df_actualizado


def actualizar_plazo_cronograma(df):
    """
    Actualiza la columna 'Plazo de cronograma' en el DataFrame
    basándose en la columna 'Plazo de análisis'.
    """
    if 'Plazo de análisis' not in df.columns:
        return df

    # Crear una copia del DataFrame
    df_actualizado = df.copy()

    # Asegurarse de que la columna 'Plazo de cronograma' exista
    if 'Plazo de cronograma' not in df_actualizado.columns:
        df_actualizado['Plazo de cronograma'] = ''

    # Iterar sobre cada fila
    for idx, row in df.iterrows():
        plazo_analisis = row.get('Plazo de análisis', None)
        if plazo_analisis and pd.notna(plazo_analisis) and plazo_analisis != '':
            plazo_cronograma = calcular_plazo_cronograma(plazo_analisis)
            if plazo_cronograma is not None:
                df_actualizado.at[idx, 'Plazo de cronograma'] = formatear_fecha(plazo_cronograma)

    return df_actualizado


def actualizar_plazo_oficio_cierre(df):
    """
    Actualiza la columna 'Plazo de oficio de cierre' en el DataFrame
    basándose en la columna 'Publicación'.
    """
    if 'Publicación' not in df.columns:
        return df

    # Crear una copia del DataFrame
    df_actualizado = df.copy()

    # Asegurarse de que la columna 'Plazo de oficio de cierre' exista
    if 'Plazo de oficio de cierre' not in df_actualizado.columns:
        df_actualizado['Plazo de oficio de cierre'] = ''

    # Iterar sobre cada fila
    for idx, row in df.iterrows():
        fecha_publicacion = row.get('Publicación', None)
        if fecha_publicacion and pd.notna(fecha_publicacion) and fecha_publicacion != '':
            plazo_oficio = calcular_plazo_oficio_cierre(fecha_publicacion)
            if plazo_oficio is not None:
                df_actualizado.at[idx, 'Plazo de oficio de cierre'] = formatear_fecha(plazo_oficio)

    return df_actualizado


# Función para probar el cálculo del plazo de análisis
def test_calcular_plazo_analisis():
    fechas_prueba = [
        "15/01/2025",
        "27/03/2025",
        "30/04/2025",
        "20/12/2025"
    ]

    for fecha in fechas_prueba:
        plazo = calcular_plazo_analisis(fecha)
        if plazo:
            print(f"Fecha de entrega: {fecha} -> Plazo de análisis: {formatear_fecha(plazo)}")
        else:
            print(f"Fecha de entrega: {fecha} -> Plazo de análisis: No se pudo calcular")


# Función para probar el cálculo del plazo de cronograma
def test_calcular_plazo_cronograma():
    fechas_prueba = [
        "22/01/2025",
        "03/04/2025",
        "08/05/2025",
        "30/12/2025"
    ]

    for fecha in fechas_prueba:
        plazo = calcular_plazo_cronograma(fecha)
        if plazo:
            print(f"Plazo de análisis: {fecha} -> Plazo de cronograma: {formatear_fecha(plazo)}")
        else:
            print(f"Plazo de análisis: {fecha} -> Plazo de cronograma: No se pudo calcular")


# Función para probar el cálculo del plazo de oficio de cierre
def test_calcular_plazo_oficio_cierre():
    fechas_prueba = [
        "15/01/2025",
        "27/03/2025",
        "30/04/2025",
        "20/12/2025"
    ]

    for fecha in fechas_prueba:
        plazo = calcular_plazo_oficio_cierre(fecha)
        if plazo:
            print(f"Fecha de publicación: {fecha} -> Plazo de oficio de cierre: {formatear_fecha(plazo)}")
        else:
            print(f"Fecha de publicación: {fecha} -> Plazo de oficio de cierre: No se pudo calcular")


if __name__ == "__main__":
    # Ejecutar pruebas
    test_calcular_plazo_analisis()
    test_calcular_plazo_cronograma()
    test_calcular_plazo_oficio_cierre()
