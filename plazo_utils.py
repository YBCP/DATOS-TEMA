from datetime import datetime, timedelta
import pandas as pd
from fecha_utils import procesar_fecha, es_festivo, formatear_fecha

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

def actualizar_plazo_oficio_cierre(df):
    """
    Actualiza la columna 'Plazo de oficio de cierre' en el DataFrame
    basándose en la columna 'Publicación'.
    """
    if 'Publicación' not in df.columns:
        return df

    # Asegurarse de que la columna 'Plazo de oficio de cierre' exista
    if 'Plazo de oficio de cierre' not in df.columns:
        df['Plazo de oficio de cierre'] = ''

    # Crear una copia del DataFrame
    df_actualizado = df.copy()

    # Iterar sobre cada fila
    for idx, row in df.iterrows():
        fecha_publicacion = row.get('Publicación', None)
        if fecha_publicacion and pd.notna(fecha_publicacion) and fecha_publicacion != '':
            plazo = calcular_plazo_oficio_cierre(fecha_publicacion)
            if plazo is not None:
                df_actualizado.at[idx, 'Plazo de oficio de cierre'] = formatear_fecha(plazo)

    return df_actualizado

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
    test_calcular_plazo_oficio_cierre()
