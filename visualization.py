import pandas as pd
import numpy as np
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from datetime import datetime, timedelta
import streamlit as st
from data_utils import procesar_fecha, verificar_completado_por_fecha


def crear_gantt(df):
    """Crea un diagrama de Gantt con los hitos y fechas."""
    import streamlit as st
    from datetime import datetime, timedelta

    if df.empty:
        return None

    # Verificar si hay al menos una fecha válida
    columnas_fecha = [
        'Entrega acuerdo de compromiso', 'Análisis y cronograma',
        'Estándares', 'Publicación', 'Plazo de oficio de cierre'
    ]

    tiene_fechas = False
    for col in columnas_fecha:
        if col in df.columns and df[col].notna().any():
            tiene_fechas = True
            break

    if not tiene_fechas:
        return None

    # Definir los porcentajes por hito
    porcentajes_hitos = {
        'Acuerdo de compromiso': '20%',
        'Análisis y cronograma': '20%',
        'Estándares': '30%',
        'Publicación': '25%',
        'Cierre': '5%'
    }

    # Crear lista de tareas para el diagrama
    tareas = []

    # Para cada registro, crear las tareas correspondientes a cada hito
    for idx, row in df.iterrows():
        try:
            entidad = row['Entidad']
            nivel_info = row['Nivel Información '] if 'Nivel Información ' in row else 'Sin nivel'
            task_id = f"{row['Cod']} - {nivel_info}"

            # Hito 1: Acuerdo de compromiso
            if 'Entrega acuerdo de compromiso' in row and pd.notna(row['Entrega acuerdo de compromiso']) and row[
                'Entrega acuerdo de compromiso'] != "":
                fecha = procesar_fecha(row['Entrega acuerdo de compromiso'])
                if fecha and isinstance(fecha, datetime):  # Verificación adicional de tipo
                    # Modificar la fecha para que comience 7 días antes
                    fecha_inicio = fecha - timedelta(days=7)
                    tareas.append({
                        'Task': task_id,
                        'Start': fecha_inicio,
                        'Finish': fecha,  # La fecha de finalización es la fecha original
                        'Resource': f"Acuerdo de compromiso ({porcentajes_hitos['Acuerdo de compromiso']})",
                        'Entidad': entidad
                    })

            # Hito 2: Análisis y cronograma
            if 'Análisis y cronograma' in row and pd.notna(row['Análisis y cronograma']) and row[
                'Análisis y cronograma'] != "":
                fecha = procesar_fecha(row['Análisis y cronograma'])
                if fecha and isinstance(fecha, datetime):  # Verificación adicional de tipo
                    # Modificar la fecha para que comience 7 días antes
                    fecha_inicio = fecha - timedelta(days=7)
                    tareas.append({
                        'Task': task_id,
                        'Start': fecha_inicio,
                        'Finish': fecha,
                        'Resource': f"Análisis y cronograma ({porcentajes_hitos['Análisis y cronograma']})",
                        'Entidad': entidad
                    })

            # Hito 3: Estándares
            if 'Estándares' in row and pd.notna(row['Estándares']) and row['Estándares'] != "":
                fecha = procesar_fecha(row['Estándares'])
                if fecha and isinstance(fecha, datetime):  # Verificación adicional de tipo
                    # Modificar la fecha para que comience 7 días antes
                    fecha_inicio = fecha - timedelta(days=7)
                    tareas.append({
                        'Task': task_id,
                        'Start': fecha_inicio,
                        'Finish': fecha,
                        'Resource': f"Estándares ({porcentajes_hitos['Estándares']})",
                        'Entidad': entidad
                    })

            # Hito 4: Publicación
            if 'Publicación' in row and pd.notna(row['Publicación']) and row['Publicación'] != "":
                fecha = procesar_fecha(row['Publicación'])
                if fecha and isinstance(fecha, datetime):  # Verificación adicional de tipo
                    # Modificar la fecha para que comience 7 días antes
                    fecha_inicio = fecha - timedelta(days=7)
                    tareas.append({
                        'Task': task_id,
                        'Start': fecha_inicio,
                        'Finish': fecha,
                        'Resource': f"Publicación ({porcentajes_hitos['Publicación']})",
                        'Entidad': entidad
                    })

            # Hito 5: Cierre (Plazo de oficio de cierre)
            if 'Plazo de oficio de cierre' in row and pd.notna(row['Plazo de oficio de cierre']) and row[
                'Plazo de oficio de cierre'] != "":
                fecha = procesar_fecha(row['Plazo de oficio de cierre'])
                if fecha and isinstance(fecha, datetime):  # Verificación adicional de tipo
                    # Modificar la fecha para que comience 7 días antes
                    fecha_inicio = fecha - timedelta(days=7)
                    tareas.append({
                        'Task': task_id,
                        'Start': fecha_inicio,
                        'Finish': fecha,
                        'Resource': f"Cierre ({porcentajes_hitos['Cierre']})",
                        'Entidad': entidad
                    })
        except Exception as e:
            # Si hay un error procesando un registro, simplemente lo omitimos y continuamos
            print(f"Error procesando registro {idx}: {e}")
            continue

    if not tareas:
        return None

    # Crear DataFrame de tareas
    df_tareas = pd.DataFrame(tareas)

    # Definir colores para cada tipo de hito
    colors = {
        f"Acuerdo de compromiso ({porcentajes_hitos['Acuerdo de compromiso']})": '#1E40AF',  # Azul
        f"Análisis y cronograma ({porcentajes_hitos['Análisis y cronograma']})": '#047857',  # Verde
        f"Estándares ({porcentajes_hitos['Estándares']})": '#B45309',  # Naranja
        f"Publicación ({porcentajes_hitos['Publicación']})": '#BE185D',  # Rosa
        f"Cierre ({porcentajes_hitos['Cierre']})": '#7C3AED'  # Púrpura
    }

    try:
        # Crear el gráfico
        fig = px.timeline(
            df_tareas,
            x_start='Start',
            x_end='Finish',
            y='Task',
            color='Resource',
            color_discrete_map=colors,
            hover_data=['Entidad'],
            title='Cronograma de Hitos por Nivel de Información'
        )

        # Ajustar el diseño
        fig.update_layout(
            xaxis_title='Fecha',
            yaxis_title='Registro - Nivel de Información',
            legend_title='Hito',
            height=max(400, len(df_tareas['Task'].unique()) * 40),  # Altura dinámica basada en cantidad de registros
            xaxis=dict(
                type='date',
                tickformat='%d/%m/%Y'
            )
        )

        # Añadir línea vertical para mostrar la fecha actual (HOY)
        # Usar solo la fecha (sin hora) para evitar problemas de tipo
        fecha_hoy = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

        # Añadir la línea vertical
        fig.add_shape(
            type="line",
            x0=fecha_hoy,
            y0=0,
            x1=fecha_hoy,
            y1=1,
            line=dict(
                color="red",
                width=2,
                dash="dash",
            ),
            xref="x",
            yref="paper"  # Usar "paper" para que vaya de 0 a 1 en el eje y
        )

        # Añadir etiqueta "HOY"
        fig.add_annotation(
            x=fecha_hoy,
            y=1,
            text="HOY",
            showarrow=False,
            font=dict(
                color="red",
                size=14
            ),
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="red",
            borderwidth=1,
            xref="x",
            yref="paper",
            yanchor="bottom"
        )

        return fig
    except Exception as e:
        # Si falla la creación del gráfico, imprimir el error y retornar None
        print(f"Error al crear el gráfico: {e}")
        import traceback
        traceback.print_exc()
        return None

def comparar_avance_metas(df, metas_nuevas_df, metas_actualizar_df):
    """Compara el avance actual con las metas establecidas."""
    try:
        # Obtener la fecha actual
        fecha_actual = datetime.now()

        # Encontrar la meta más cercana a la fecha actual
        fechas_metas = metas_nuevas_df.index
        fecha_meta_cercana = min(fechas_metas, key=lambda x: abs(x - fecha_actual))

        # Obtener los valores de las metas para esa fecha
        metas_nuevas_actual = metas_nuevas_df.loc[fecha_meta_cercana]
        metas_actualizar_actual = metas_actualizar_df.loc[fecha_meta_cercana]

        # Contar registros completados por hito y tipo (de manera segura)
        # Verificar si la columna TipoDato existe
        if 'TipoDato' not in df.columns:
            # Crear columnas necesarias si no existen
            df['TipoDato'] = 'No especificado'
            df['Acuerdo de compromiso'] = ''
            df['Análisis y cronograma'] = ''
            df['Estándares'] = ''
            df['Publicación'] = ''

        # Filtrar registros por tipo, asegurando que TipoDato exista y no sea NaN
        df['TipoDato'] = df['TipoDato'].fillna('').astype(str)
        registros_nuevos = df[df['TipoDato'].str.upper() == 'NUEVO']
        registros_actualizar = df[df['TipoDato'].str.upper() == 'ACTUALIZAR']

        # Función auxiliar para contar registros con fecha válida
        def contar_con_fecha_valida(registros_filtrados, columna):
            if columna not in registros_filtrados.columns:
                return 0
            return len(registros_filtrados[
                (registros_filtrados[columna].notna()) & 
                (registros_filtrados[columna].astype(str).str.strip() != '')
            ])

        # Para registros nuevos - contar directamente las fechas reales
        completados_nuevos = {
            'Acuerdo de compromiso': len(registros_nuevos[
                registros_nuevos['Acuerdo de compromiso'].astype(str).str.upper().isin(
                    ['SI', 'SÍ', 'S', 'YES', 'Y', 'COMPLETO'])
            ]) if 'Acuerdo de compromiso' in registros_nuevos.columns else 0,
            'Análisis y cronograma': contar_con_fecha_valida(registros_nuevos, 'Análisis y cronograma'),
            'Estándares': contar_con_fecha_valida(registros_nuevos, 'Estándares'),
            'Publicación': contar_con_fecha_valida(registros_nuevos, 'Publicación')
        }

        # Para registros a actualizar - contar directamente las fechas reales
        completados_actualizar = {
            'Acuerdo de compromiso': len(registros_actualizar[
                registros_actualizar['Acuerdo de compromiso'].astype(str).str.upper().isin(
                    ['SI', 'SÍ', 'S', 'YES', 'Y', 'COMPLETO'])
            ]) if 'Acuerdo de compromiso' in registros_actualizar.columns else 0,
            'Análisis y cronograma': contar_con_fecha_valida(registros_actualizar, 'Análisis y cronograma'),
            'Estándares': contar_con_fecha_valida(registros_actualizar, 'Estándares'),
            'Publicación': contar_con_fecha_valida(registros_actualizar, 'Publicación')
        }

        # Crear dataframes para la comparación
        comparacion_nuevos = pd.DataFrame({
            'Completados': completados_nuevos,
            'Meta': metas_nuevas_actual
        })

        comparacion_actualizar = pd.DataFrame({
            'Completados': completados_actualizar,
            'Meta': metas_actualizar_actual
        })

        # Calcular porcentajes de cumplimiento (manejando divisiones por cero)
        comparacion_nuevos['Porcentaje'] = comparacion_nuevos.apply(
            lambda row: (row['Completados'] / row['Meta'] * 100) if row['Meta'] > 0 else 0, 
            axis=1
        ).fillna(0).round(2)
        
        comparacion_actualizar['Porcentaje'] = comparacion_actualizar.apply(
            lambda row: (row['Completados'] / row['Meta'] * 100) if row['Meta'] > 0 else 0, 
            axis=1
        ).fillna(0).round(2)

        return comparacion_nuevos, comparacion_actualizar, fecha_meta_cercana
    except Exception as e:
        st.error(f"Error al comparar avance con metas: {e}")
        # Crear DataFrames de respaldo
        fecha_meta_cercana = datetime.now()

        completados_nuevos = {'Acuerdo de compromiso': 0, 'Análisis y cronograma': 0, 'Estándares': 0,
                              'Publicación': 0}
        completados_actualizar = {'Acuerdo de compromiso': 0, 'Análisis y cronograma': 0, 'Estándares': 0,
                                  'Publicación': 0}

        metas_nuevas_actual = pd.Series(
            {'Acuerdo de compromiso': 0, 'Análisis y cronograma': 0, 'Estándares': 0, 'Publicación': 0})
        metas_actualizar_actual = pd.Series(
            {'Acuerdo de compromiso': 0, 'Análisis y cronograma': 0, 'Estándares': 0, 'Publicación': 0})

        comparacion_nuevos = pd.DataFrame({
            'Completados': completados_nuevos,
            'Meta': metas_nuevas_actual,
            'Porcentaje': [0, 0, 0, 0]
        })

        comparacion_actualizar = pd.DataFrame({
            'Completados': completados_actualizar,
            'Meta': metas_actualizar_actual,
            'Porcentaje': [0, 0, 0, 0]
        })

        return comparacion_nuevos, comparacion_actualizar, fecha_meta_cercana


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
