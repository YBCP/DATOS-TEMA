import pandas as pd
import numpy as np
import io
import re
import os
import streamlit as st
from datetime import datetime, timedelta
from constants import REGISTROS_DATA, META_DATA


def normalizar_csv(contenido, separador=';'):
    """Normaliza el contenido de un CSV para asegurar mismo número de columnas."""
    lineas = contenido.split('\n')
    if not lineas:
        return contenido

    # Determinar el número de columnas a partir de la primera línea
    columnas = lineas[0].count(separador) + 1

    lineas_normalizadas = []
    for linea in lineas:
        if not linea.strip():  # Ignorar líneas vacías
            continue

        campos = linea.split(separador)
        if len(campos) < columnas:
            # Añadir campos vacíos faltantes
            linea = linea + separador * (columnas - len(campos))
        elif len(campos) > columnas:
            # Recortar campos excedentes
            linea = separador.join(campos[:columnas])

        lineas_normalizadas.append(linea)

    return '\n'.join(lineas_normalizadas)


def limpiar_valor(valor):
    """Limpia un valor de entrada de posibles errores."""
    if pd.isna(valor) or valor is None:
        return ''

    # Convertir a string
    valor = str(valor)

    # Eliminar caracteres problemáticos
    valor = re.sub(r'[\000-\010]|[\013-\014]|[\016-\037]', '', valor)

    return valor.strip()


def cargar_datos():
    """Carga los datos desde archivos CSV. No usa datos de ejemplo."""
    try:
        # Declarar variables por defecto para evitar errores
        registros_df = None
        meta_df = None

        # Lista de columnas requeridas para asegurar que existan
        columnas_requeridas = [
            'Cod', 'Entidad', 'TipoDato', 'Nivel Información ',
            'Acuerdo de compromiso', 'Análisis y cronograma',
            'Estándares', 'Publicación', 'Fecha de entrega de información',
            'Plazo de análisis', 'Plazo de cronograma', 'Plazo de oficio de cierre'
        ]

        columnas_meta = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        # Cargar archivo de registros
        if os.path.exists('registros.csv'):
            try:
                # Leer el contenido directamente
                with open('registros.csv', 'r', encoding='utf-8') as f:
                    contenido = f.read()

                # Verificar si el delimitador es realmente ';'
                primer_linea = contenido.split('\n')[0]
                if ';' in primer_linea:
                    # Si hay ';' en la primera línea, normalizar y usar ';' como separador
                    contenido_normalizado = normalizar_csv(contenido, ';')
                    registros_df = pd.read_csv(io.StringIO(contenido_normalizado), sep=';',
                                               engine='python', on_bad_lines='skip',
                                               dtype=str)  # Usar string para todos los tipos
                else:
                    # Intentar con coma como separador alternativo
                    contenido_normalizado = normalizar_csv(contenido, ',')
                    registros_df = pd.read_csv(io.StringIO(contenido_normalizado), sep=',',
                                               engine='python', on_bad_lines='skip',
                                               dtype=str)  # Usar string para todos los tipos

                # Mostrar todas las columnas que se han cargado del CSV
                #st.info(f"Columnas cargadas del archivo registros.csv: {', '.join(registros_df.columns)}")

                # Limpiar valores
                for col in registros_df.columns:
                    registros_df[col] = registros_df[col].apply(limpiar_valor)

                # Verificar y añadir columnas requeridas si faltan
                for columna in columnas_requeridas:
                    if columna not in registros_df.columns:
                        st.warning(f"La columna '{columna}' no existe en el archivo. Se creará como columna vacía.")
                        registros_df[columna] = ''

                #st.success(f"Archivo registros.csv cargado correctamente con {len(registros_df)} registros.")
            except Exception as e:
                st.error(f"Error al procesar el archivo registros.csv: {str(e)}")
                registros_df = pd.DataFrame(columns=columnas_requeridas)
                st.warning("Se ha creado un DataFrame vacío con las columnas requeridas.")
        else:
            st.error("El archivo registros.csv no existe en el directorio actual.")
            registros_df = pd.DataFrame(columns=columnas_requeridas)
            st.warning("Se ha creado un DataFrame vacío con las columnas requeridas.")

        # Cargar archivo de metas
        if os.path.exists('meta.csv'):
            try:
                # Leer el contenido y determinar el separador correcto
                with open('meta.csv', 'r', encoding='utf-8') as f:
                    contenido = f.read()

                # Verificar si el delimitador es realmente ';'
                primer_linea = contenido.split('\n')[0]
                if ';' in primer_linea:
                    # Si hay ';' en la primera línea, normalizar y usar ';' como separador
                    contenido_normalizado = normalizar_csv(contenido, ';')
                    meta_df = pd.read_csv(io.StringIO(contenido_normalizado), sep=';',
                                          header=None, engine='python', on_bad_lines='skip',
                                          dtype=str)  # Usar string para todos los tipos
                else:
                    # Intentar con coma como separador alternativo
                    contenido_normalizado = normalizar_csv(contenido, ',')
                    meta_df = pd.read_csv(io.StringIO(contenido_normalizado), sep=',',
                                          header=None, engine='python', on_bad_lines='skip',
                                          dtype=str)  # Usar string para todos los tipos

                # Limpiar valores
                for col in meta_df.columns:
                    meta_df[col] = meta_df[col].apply(limpiar_valor)

                #st.success("Archivo meta.csv cargado correctamente.")
            except Exception as e:
                st.error(f"Error al procesar el archivo meta.csv: {str(e)}")
                meta_df = pd.DataFrame(columns=columnas_meta)
                st.warning("Se ha creado un DataFrame vacío con las columnas requeridas para metas.")
        else:
            st.error("El archivo meta.csv no existe en el directorio actual.")
            meta_df = pd.DataFrame(columns=columnas_meta)
            st.warning("Se ha creado un DataFrame vacío con las columnas requeridas para metas.")

        return registros_df, meta_df

    except Exception as e:
        st.error(f"Error general al cargar los datos: {e}")
        # Crear DataFrames vacíos como último recurso
        registros_df = pd.DataFrame(columns=['Cod', 'Entidad', 'TipoDato', 'Nivel Información ',
                                             'Acuerdo de compromiso', 'Análisis y cronograma',
                                             'Estándares', 'Publicación', 'Fecha de entrega de información',
                                             'Plazo de análisis', 'Plazo de cronograma', 'Plazo de oficio de cierre'])
        meta_df = pd.DataFrame(columns=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

        return registros_df, meta_df

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


def es_fecha_valida(valor):
    """Verifica si un valor es una fecha válida."""
    try:
        fecha = procesar_fecha(valor)
        return fecha is not None and pd.notna(fecha)
    except Exception:
        return False


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


def verificar_completado_por_fecha(fecha_programada, fecha_completado=None):
    """
    Verifica si una tarea está completada basada en fechas.
    Si fecha_completado está presente, la tarea está completada.
    Si no, se verifica si la fecha programada ya pasó.
    """
    if fecha_completado is not None and pd.notna(fecha_completado):
        return True

    fecha_actual = datetime.now()
    fecha_prog = procesar_fecha(fecha_programada)

    if fecha_prog is not None and pd.notna(fecha_prog) and fecha_prog <= fecha_actual:
        return True

    return False


def calcular_porcentaje_avance(registro):
    """
    Calcula el porcentaje de avance de un registro basado en los campos de completitud.

    Ponderación:
    - Acuerdo de compromiso: 20%
    - Análisis y cronograma (fecha real): 20%
    - Estándares (fecha real): 30%
    - Publicación (fecha real): 25%
    - Fecha de oficio de cierre: 5%
    """
    try:
        # Inicializar el avance
        avance = 0

        # Verificar el acuerdo de compromiso (20%)
        if 'Acuerdo de compromiso' in registro and str(registro['Acuerdo de compromiso']).strip().upper() in ['SI',
                                                                                                              'SÍ', 'S',
                                                                                                              'YES',
                                                                                                              'Y',
                                                                                                              'COMPLETO']:
            avance += 20

        # Verificar análisis y cronograma - basado solo en la fecha (20%)
        if 'Análisis y cronograma' in registro and registro['Análisis y cronograma'] and pd.notna(
                registro['Análisis y cronograma']):
            avance += 20

        # Verificar estándares - basado en la fecha (30%)
        if 'Estándares' in registro and registro['Estándares'] and pd.notna(registro['Estándares']):
            avance += 30

        # Verificar publicación - basado en la fecha (25%)
        if 'Publicación' in registro and registro['Publicación'] and pd.notna(registro['Publicación']):
            avance += 25

        # Verificar fecha de oficio de cierre (5%)
        if 'Fecha de oficio de cierre' in registro and registro['Fecha de oficio de cierre'] and pd.notna(
                registro['Fecha de oficio de cierre']):
            avance += 5

        return avance
    except Exception as e:
        # En caso de error, retornar 0
        st.warning(f"Error al calcular porcentaje de avance: {e}")
        return 0
def procesar_metas(meta_df):
    """Procesa las metas a partir del DataFrame de metas."""
    try:
        # La estructura de las metas es compleja, vamos a procesarla
        # Asumiendo que las filas 3 en adelante contienen las fechas y metas
        fechas = []
        metas_nuevas = {}
        metas_actualizar = {}

        # Inicializar listas para cada hito
        for hito in ['Acuerdo de compromiso', 'Análisis y cronograma', 'Estándares', 'Publicación']:
            metas_nuevas[hito] = []
            metas_actualizar[hito] = []

        # Procesar cada fila (desde la fila 3 que contiene las fechas y valores)
        for i in range(3, len(meta_df)):
            try:
                fila = meta_df.iloc[i]

                # La primera columna contiene la fecha
                fecha = procesar_fecha(fila[0])
                if fecha is not None:
                    fechas.append(fecha)

                    # Columnas 1-4 son para registros nuevos (asegurar que existan)
                    metas_nuevas['Acuerdo de compromiso'].append(
                        pd.to_numeric(fila[1] if len(fila) > 1 else 0, errors='coerce') or 0)
                    metas_nuevas['Análisis y cronograma'].append(
                        pd.to_numeric(fila[2] if len(fila) > 2 else 0, errors='coerce') or 0)
                    metas_nuevas['Estándares'].append(
                        pd.to_numeric(fila[3] if len(fila) > 3 else 0, errors='coerce') or 0)
                    metas_nuevas['Publicación'].append(
                        pd.to_numeric(fila[4] if len(fila) > 4 else 0, errors='coerce') or 0)

                    # Columnas 6-9 son para registros a actualizar (asegurar que existan)
                    metas_actualizar['Acuerdo de compromiso'].append(
                        pd.to_numeric(fila[6] if len(fila) > 6 else 0, errors='coerce') or 0)
                    metas_actualizar['Análisis y cronograma'].append(
                        pd.to_numeric(fila[7] if len(fila) > 7 else 0, errors='coerce') or 0)
                    metas_actualizar['Estándares'].append(
                        pd.to_numeric(fila[8] if len(fila) > 8 else 0, errors='coerce') or 0)
                    metas_actualizar['Publicación'].append(
                        pd.to_numeric(fila[9] if len(fila) > 9 else 0, errors='coerce') or 0)
            except Exception as e:
                st.warning(f"Error al procesar fila {i} de metas: {e}")
                continue

        # Si no hay fechas, mostrar un error
        if not fechas:
            st.error("No se pudieron procesar las fechas de las metas")
            # Crear un DataFrame de ejemplo como respaldo
            fechas = [datetime.now()]
            for hito in metas_nuevas:
                metas_nuevas[hito] = [0]
                metas_actualizar[hito] = [0]

        # Convertir a DataFrames
        metas_nuevas_df = pd.DataFrame(metas_nuevas, index=fechas)
        metas_actualizar_df = pd.DataFrame(metas_actualizar, index=fechas)

        return metas_nuevas_df, metas_actualizar_df
    except Exception as e:
        st.error(f"Error al procesar metas: {e}")
        # Crear DataFrames vacíos como respaldo
        fechas = [datetime.now()]
        metas_nuevas = {'Acuerdo de compromiso': [0], 'Análisis y cronograma': [0], 'Estándares': [0],
                        'Publicación': [0]}
        metas_actualizar = {'Acuerdo de compromiso': [0], 'Análisis y cronograma': [0], 'Estándares': [0],
                            'Publicación': [0]}

        metas_nuevas_df = pd.DataFrame(metas_nuevas, index=fechas)
        metas_actualizar_df = pd.DataFrame(metas_actualizar, index=fechas)

        return metas_nuevas_df, metas_actualizar_df


def verificar_estado_fechas(row):
    """Verifica si las fechas están vencidas o próximas a vencer."""
    fecha_actual = datetime.now()
    estado = "normal"  # Por defecto, estado normal

    # Lista de campos de fechas a verificar
    campos_fecha = [
        'Análisis y cronograma (fecha programada)',
        'Estándares (fecha programada)',
        'Fecha de publicación programada'
    ]

    for campo in campos_fecha:
        if campo in row and row[campo]:
            fecha = procesar_fecha(row[campo])
            if fecha is not None and pd.notna(fecha):
                # Si la fecha ya está vencida
                if fecha < fecha_actual:
                    return "vencido"  # Prioridad alta, retornamos inmediatamente

                # Si la fecha está próxima a vencer en los próximos 30 días
                if fecha <= fecha_actual + timedelta(days=30):
                    estado = "proximo"  # Marcamos como próximo, pero seguimos verificando otras fechas

    return estado


def validar_campos_fecha(df, campos_fecha=['Análisis y cronograma', 'Estándares', 'Publicación']):
    """
    Valida que los campos específicos contengan solo fechas válidas.
    Si no son fechas válidas, los convierte a fechas o los deja vacíos.
    """
    df_validado = df.copy()

    for campo in campos_fecha:
        if campo in df_validado.columns:
            df_validado[campo] = df_validado[campo].apply(
                lambda x: formatear_fecha(x) if es_fecha_valida(x) else ""
            )

    return df_validado

def guardar_datos_editados(df, ruta_archivo='registros.csv'):
    """Guarda los datos editados en un archivo CSV, asegurando que ciertos campos sean fechas."""
    try:
        # Validar que los campos de fechas sean fechas válidas
        df_validado = validar_campos_fecha(df)

        # Convertir DataFrame a CSV
        csv_data = df_validado.to_csv(index=False, sep=';')

        # Guardar archivo
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(csv_data)

        return True, "Datos guardados correctamente."
    except Exception as e:
        st.error(f"Error al guardar datos: {e}")
        return False, f"Error al guardar datos: {e}"

def contar_registros_completados_por_fecha(df, columna_fecha_programada, columna_fecha_completado):
    """
    Cuenta los registros que tienen una fecha de completado o cuya fecha programada ya pasó.
    """
    count = 0
    for _, row in df.iterrows():
        if columna_fecha_programada in row and row[columna_fecha_programada]:
            fecha_programada = row[columna_fecha_programada]

            # Verificar si hay una fecha de completado
            fecha_completado = None
            if columna_fecha_completado in row and row[columna_fecha_completado]:
                # Intentar procesar como fecha primero
                fecha_completado = procesar_fecha(row[columna_fecha_completado])
                # Si no es una fecha, verificar si es un valor booleano positivo
                if fecha_completado is None and str(row[columna_fecha_completado]).strip().upper() in ['SI', 'SÍ',
                                                                                                       'S', 'YES',
                                                                                                       'Y',
                                                                                                       'COMPLETO']:
                    fecha_completado = datetime.now()  # Usar fecha actual como completado

            if verificar_completado_por_fecha(fecha_programada, fecha_completado):
                count += 1

    return count