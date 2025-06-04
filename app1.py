import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from validaciones_utils import validar_reglas_negocio, mostrar_estado_validaciones, verificar_condiciones_estandares, verificar_condiciones_oficio_cierre
import io
import base64
import os
import re
from fecha_utils import calcular_plazo_analisis, actualizar_plazo_analisis, calcular_plazo_cronograma, actualizar_plazo_cronograma, calcular_plazo_oficio_cierre, actualizar_plazo_oficio_cierre

# Importar las funciones corregidas
from config import setup_page, load_css
from data_utils import (
    cargar_datos, procesar_metas, calcular_porcentaje_avance,
    verificar_estado_fechas, formatear_fecha, es_fecha_valida,
    validar_campos_fecha, guardar_datos_editados, procesar_fecha,
    contar_registros_completados_por_fecha
)
from visualization import crear_gantt, comparar_avance_metas
from constants import REGISTROS_DATA, META_DATA

# Función para convertir fecha string a datetime
def string_a_fecha(fecha_str):
    """Convierte un string de fecha a objeto datetime para mostrar en el selector de fecha."""
    if not fecha_str or fecha_str == "":
        return None
    fecha = procesar_fecha(fecha_str)
    return fecha


# Función para colorear filas según estado de fechas - definida fuera de los bloques try
def highlight_estado_fechas(s):
    """Función para aplicar estilo según el valor de 'Estado Fechas'"""
    if 'Estado Fechas' in s and s['Estado Fechas'] == 'vencido':
        return ['background-color: #fee2e2'] * len(s)
    elif 'Estado Fechas' in s and s['Estado Fechas'] == 'proximo':
        return ['background-color: #fef3c7'] * len(s)
    else:
        return ['background-color: #ffffff'] * len(s)


def mostrar_dashboard(df_filtrado, metas_nuevas_df, metas_actualizar_df, registros_df):
    """Muestra el dashboard principal con métricas y gráficos."""
    # Mostrar métricas generales
    st.markdown('<div class="subtitle">Métricas Generales</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_registros = len(df_filtrado)
        st.markdown(f"""
        <div class="metric-card">
            <p style="font-size: 1rem; color: #64748b;">Total Registros</p>
            <p style="font-size: 2.5rem; font-weight: bold; color: #1E40AF;">{total_registros}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        avance_promedio = df_filtrado['Porcentaje Avance'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <p style="font-size: 1rem; color: #64748b;">Avance Promedio</p>
            <p style="font-size: 2.5rem; font-weight: bold; color: #047857;">{avance_promedio:.2f}%</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        registros_completados = len(df_filtrado[df_filtrado['Porcentaje Avance'] == 100])
        st.markdown(f"""
        <div class="metric-card">
            <p style="font-size: 1rem; color: #64748b;">Registros Completados</p>
            <p style="font-size: 2.5rem; font-weight: bold; color: #B45309;">{registros_completados}</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        porcentaje_completados = (registros_completados / total_registros * 100) if total_registros > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <p style="font-size: 1rem; color: #64748b;">% Completados</p>
            <p style="font-size: 2.5rem; font-weight: bold; color: #BE185D;">{porcentaje_completados:.2f}%</p>
        </div>
        """, unsafe_allow_html=True)

    # Comparación con metas
    st.markdown('<div class="subtitle">Comparación con Metas Quincenales</div>', unsafe_allow_html=True)

    # Calcular comparación con metas
    comparacion_nuevos, comparacion_actualizar, fecha_meta = comparar_avance_metas(df_filtrado, metas_nuevas_df,
                                                                                   metas_actualizar_df)

    # Mostrar fecha de la meta
    st.markdown(f"**Meta más cercana a la fecha actual: {fecha_meta.strftime('%d/%m/%Y')}**")

    # Mostrar comparación en dos columnas
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Registros Nuevos")
        st.dataframe(comparacion_nuevos.style.format({
            'Porcentaje': '{:.2f}%'
        }).background_gradient(cmap='RdYlGn', subset=['Porcentaje']))

        # Gráfico de barras para registros nuevos
        fig_nuevos = px.bar(
            comparacion_nuevos.reset_index(),
            x='index',
            y=['Completados', 'Meta'],
            barmode='group',
            labels={'index': 'Hito', 'value': 'Cantidad', 'variable': 'Tipo'},
            title='Comparación de Avance vs. Meta - Registros Nuevos',
            color_discrete_map={'Completados': '#4B5563', 'Meta': '#1E40AF'}
        )
        st.plotly_chart(fig_nuevos, use_container_width=True)

    with col2:
        st.markdown("### Registros a Actualizar")
        st.dataframe(comparacion_actualizar.style.format({
            'Porcentaje': '{:.2f}%'
        }).background_gradient(cmap='RdYlGn', subset=['Porcentaje']))

        # Gráfico de barras para registros a actualizar
        fig_actualizar = px.bar(
            comparacion_actualizar.reset_index(),
            x='index',
            y=['Completados', 'Meta'],
            barmode='group',
            labels={'index': 'Hito', 'value': 'Cantidad', 'variable': 'Tipo'},
            title='Comparación de Avance vs. Meta - Registros a Actualizar',
            color_discrete_map={'Completados': '#4B5563', 'Meta': '#047857'}
        )
        st.plotly_chart(fig_actualizar, use_container_width=True)

    # Diagrama de Gantt - Cronograma de Hitos por Nivel de Información
    st.markdown('<div class="subtitle">Diagrama de Gantt - Cronograma de Hitos por Nivel de Información</div>',
                unsafe_allow_html=True)

    # Crear el diagrama de Gantt
    fig_gantt = crear_gantt(df_filtrado)
    if fig_gantt is not None:
        st.plotly_chart(fig_gantt, use_container_width=True)
    else:
        st.warning("No hay datos suficientes para crear el diagrama de Gantt.")

    # Tabla de registros con porcentaje de avance
    st.markdown('<div class="subtitle">Detalle de Registros</div>', unsafe_allow_html=True)

    # Definir el nuevo orden exacto de las columnas según lo solicitado
    columnas_mostrar = [
        # Datos básicos
        'Cod', 'Entidad', 'Nivel Información ', 'Funcionario',  # Incluir Funcionario después de datos básicos
        # Columnas adicionales en el orden específico
        'Frecuencia actualizacion ', 'TipoDato',
        'Suscripción acuerdo de compromiso', 'Entrega acuerdo de compromiso',
        'Fecha de entrega de información', 'Plazo de análisis', 'Plazo de cronograma',
        'Análisis y cronograma',
        'Registro (completo)', 'ET (completo)', 'CO (completo)', 'DD (completo)', 'REC (completo)',
        'SERVICIO (completo)',
        'Estándares (fecha programada)', 'Estándares',
        'Fecha de publicación programada', 'Publicación',
        'Plazo de oficio de cierre', 'Fecha de oficio de cierre',
        'Estado', 'Observación', 'Porcentaje Avance'
    ]

    # Mostrar tabla con colores por estado de fechas
    try:
        # Verificar que todas las columnas existan en df_filtrado
        columnas_mostrar_existentes = [col for col in columnas_mostrar if col in df_filtrado.columns]
        df_mostrar = df_filtrado[columnas_mostrar_existentes].copy()

        # Aplicar formato a las fechas
        columnas_fecha = [
            'Suscripción acuerdo de compromiso', 'Entrega acuerdo de compromiso',
            'Fecha de entrega de información', 'Plazo de análisis', 'Plazo de cronograma',
            'Análisis y cronograma', 'Estándares (fecha programada)', 'Estándares',
            'Fecha de publicación programada', 'Publicación',
            'Plazo de oficio de cierre', 'Fecha de oficio de cierre'
        ]

        for col in columnas_fecha:
            if col in df_mostrar.columns:
                df_mostrar[col] = df_mostrar[col].apply(lambda x: formatear_fecha(x) if es_fecha_valida(x) else "")

        # Mostrar el dataframe con formato
        st.dataframe(
            df_mostrar
            .style.format({'Porcentaje Avance': '{:.2f}%'})
            .apply(highlight_estado_fechas, axis=1)
            .background_gradient(cmap='RdYlGn', subset=['Porcentaje Avance']),
            use_container_width=True
        )

        # SECCIÓN DE DESCARGA
        st.markdown("### Descargar Datos")

        col1, col2 = st.columns(2)

        with col1:
            # Botón para descargar los datos filtrados
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_mostrar.to_excel(writer, sheet_name='Registros Filtrados', index=False)

            excel_data = output.getvalue()
            st.download_button(
                label="📊 Descargar datos filtrados (Excel)",
                data=excel_data,
                file_name="registros_filtrados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Descarga los datos filtrados en formato Excel"
            )

        with col2:
            # BOTÓN PARA DESCARGAR TODOS LOS REGISTROS (datos completos)
            output_completo = io.BytesIO()
            with pd.ExcelWriter(output_completo, engine='openpyxl') as writer:
                registros_df.to_excel(writer, sheet_name='Registros Completos', index=False)

                # Añadir hojas adicionales con categorías
                if 'TipoDato' in registros_df.columns:
                    # Hoja para registros nuevos
                    registros_nuevos = registros_df[registros_df['TipoDato'].str.upper() == 'NUEVO']
                    if not registros_nuevos.empty:
                        registros_nuevos.to_excel(writer, sheet_name='Registros Nuevos', index=False)

                    # Hoja para registros a actualizar
                    registros_actualizar = registros_df[registros_df['TipoDato'].str.upper() == 'ACTUALIZAR']
                    if not registros_actualizar.empty:
                        registros_actualizar.to_excel(writer, sheet_name='Registros a Actualizar', index=False)

            excel_data_completo = output_completo.getvalue()

            # Botón para descargar todos los registros
            st.download_button(
                label="📥 Descargar TODOS los registros (Excel)",
                data=excel_data_completo,
                file_name="todos_los_registros.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Descarga todos los registros en formato Excel, sin filtros aplicados",
                use_container_width=True
            )

        # Añadir información sobre el contenido
        num_registros = len(registros_df)
        num_campos = len(registros_df.columns)
        st.info(
            f"El archivo de TODOS los registros incluirá {num_registros} registros con {num_campos} campos originales.")

    except Exception as e:
        st.error(f"Error al mostrar la tabla de registros: {e}")
        st.dataframe(df_filtrado[columnas_mostrar_existentes])


# Función de callback para manejar cambios
def on_change_callback():
    """Callback para marcar que hay cambios pendientes."""
    st.session_state.cambios_pendientes = True


# Función para convertir fecha para mostrar en selectores de fecha
def fecha_para_selector(fecha_str):
    """Convierte una fecha en string a un objeto datetime para el selector."""
    if not fecha_str or pd.isna(fecha_str) or fecha_str == '':
        return None

    try:
        fecha = procesar_fecha(fecha_str)
        if fecha is not None:
            return fecha
    except:
        pass

    return None


# Función para formatear fecha desde el selector para guardar en DataFrame
def fecha_desde_selector_a_string(fecha):
    """Convierte un objeto datetime del selector a string con formato DD/MM/AAAA."""
    if fecha is None:
        return ""
    return fecha.strftime('%d/%m/%Y')


def mostrar_edicion_registros(registros_df):
    """Muestra la pestaña de edición de registros."""
    st.markdown('<div class="subtitle">Edición de Registros</div>', unsafe_allow_html=True)

    st.info(
        "Esta sección permite editar los datos usando selectores de fecha y opciones. Los cambios se guardan automáticamente al hacer modificaciones.")

    # Explicación adicional sobre las fechas y reglas de validación
    st.warning("""
    **Importante**: 
    - Para los campos de fecha, utilice el selector de calendario que aparece.
    - El campo "Plazo de análisis" se calcula automáticamente como 5 días hábiles después de la "Fecha de entrega de información", sin contar fines de semana ni festivos.
    - El campo "Plazo de cronograma" se calcula automáticamente como 3 días hábiles después del "Plazo de análisis", sin contar fines de semana ni festivos.
    - El campo "Plazo de oficio de cierre" se calcula automáticamente como 7 días hábiles después de la fecha real de "Publicación", sin contar fines de semana ni festivos.
    - Se aplicarán automáticamente las siguientes validaciones:
        1. Si 'Entrega acuerdo de compromiso' no está vacío, 'Acuerdo de compromiso' se actualizará a 'SI'
        2. Si 'Análisis y cronograma' tiene fecha, 'Análisis de información' se actualizará a 'SI'
        3. Si introduce fecha en 'Estándares', se verificará que los campos 'Registro (completo)', 'ET (completo)', 'CO (completo)', 'DD (completo)', 'REC (completo)' y 'SERVICIO (completo)' estén 'Completo'
        4. Si introduce fecha en 'Publicación', se verificará que 'Disponer datos temáticos' sea 'SI'
        5. Si 'Disponer datos temáticos' se marca como 'No', se eliminará la fecha de 'Publicación' si existe.
        6. Para introducir una fecha en 'Fecha de oficio de cierre', todos los campos Si/No deben estar marcados como 'Si', todos los estándares deben estar 'Completo' y todas las fechas diligenciadas y anteriores a la fecha de cierre.
        7. Al introducir una fecha en 'Fecha de oficio de cierre', el campo 'Estado' se actualizará automáticamente a 'Completado'.
        8. Si se modifica algún campo de forma que ya no cumpla con las reglas para 'Fecha de oficio de cierre', esta fecha se borrará automáticamente.
        9. Solo los registros con 'Fecha de oficio de cierre' válida pueden tener estado 'Completado'.
    """)
    # Mostrar mensaje de guardado si existe
    if st.session_state.mensaje_guardado:
        if st.session_state.mensaje_guardado[0] == "success":
            st.success(st.session_state.mensaje_guardado[1])
        else:
            st.error(st.session_state.mensaje_guardado[1])
        # Limpiar mensaje después de mostrarlo
        st.session_state.mensaje_guardado = None

    st.markdown("### Edición Individual de Registros")

    # Selector de registro - mostrar lista completa de registros para seleccionar
    codigos_registros = registros_df['Cod'].astype(str).tolist()
    entidades_registros = registros_df['Entidad'].tolist()
    niveles_registros = registros_df['Nivel Información '].tolist()

    # Crear opciones para el selector combinando información
    opciones_registros = [f"{codigos_registros[i]} - {entidades_registros[i]} - {niveles_registros[i]}"
                          for i in range(len(codigos_registros))]

    # Agregar el selector de registro
    seleccion_registro = st.selectbox(
        "Seleccione un registro para editar:",
        options=opciones_registros,
        key="selector_registro"
    )

    # Obtener el índice del registro seleccionado
    indice_seleccionado = opciones_registros.index(seleccion_registro)

    # Mostrar el registro seleccionado para edición
    try:
        # Obtener el registro seleccionado
        row = registros_df.iloc[indice_seleccionado].copy()

        # Flag para detectar cambios
        edited = False

        # Flag para detectar si se ha introducido fecha en estándares sin validadores completos
        estandares_warning = False

        # Contenedor para los datos de edición
        with st.container():
            st.markdown("---")
            # Título del registro
            st.markdown(f"### Editando Registro #{row['Cod']} - {row['Entidad']}")
            st.markdown(f"**Nivel de Información:** {row['Nivel Información ']}")
            st.markdown("---")

            # SECCIÓN 1: INFORMACIÓN BÁSICA
            st.markdown("### 1. Información Básica")
            col1, col2, col3 = st.columns(3)

            with col1:
                # Campos no editables
                st.text_input("Código", value=row['Cod'], disabled=True)

            with col2:
                # Tipo de Dato
                nuevo_tipo = st.selectbox(
                    "Tipo de Dato",
                    options=["Nuevo", "Actualizar"],
                    index=0 if row['TipoDato'].upper() == "NUEVO" else 1,
                    key=f"tipo_{indice_seleccionado}",
                    on_change=on_change_callback
                )
                if nuevo_tipo != row['TipoDato']:
                    registros_df.at[registros_df.index[indice_seleccionado], 'TipoDato'] = nuevo_tipo
                    edited = True

            with col3:
                # Nivel de Información
                nuevo_nivel = st.text_input(
                    "Nivel de Información",
                    value=row['Nivel Información '] if pd.notna(row['Nivel Información ']) else "",
                    key=f"nivel_info_{indice_seleccionado}",
                    on_change=on_change_callback
                )
                if nuevo_nivel != row['Nivel Información ']:
                    registros_df.at[registros_df.index[indice_seleccionado], 'Nivel Información '] = nuevo_nivel
                    edited = True

            # Frecuencia de actualización (si existe)
            if 'Frecuencia actualizacion ' in row:
                col1, col2 = st.columns(2)
                with col1:
                    nueva_frecuencia = st.selectbox(
                        "Frecuencia de actualización",
                        options=["", "Diaria", "Semanal", "Mensual", "Trimestral", "Semestral", "Anual"],
                        index=["", "Diaria", "Semanal", "Mensual", "Trimestral", "Semestral", "Anual"].index(
                            row['Frecuencia actualizacion ']) if row['Frecuencia actualizacion '] in ["", "Diaria",
                                                                                                      "Semanal",
                                                                                                      "Mensual",
                                                                                                      "Trimestral",
                                                                                                      "Semestral",
                                                                                                      "Anual"] else 0,
                        key=f"frecuencia_{indice_seleccionado}",
                        on_change=on_change_callback
                    )
                    if nueva_frecuencia != row['Frecuencia actualizacion ']:
                        registros_df.at[
                            registros_df.index[indice_seleccionado], 'Frecuencia actualizacion '] = nueva_frecuencia
                        edited = True

                # Funcionario (si existe)
                if 'Funcionario' in row:
                    with col2:
                        # Inicializar la lista de funcionarios si es la primera vez
                        if not st.session_state.funcionarios:
                            # Obtener valores únicos de funcionarios que no sean NaN
                            funcionarios_unicos = registros_df['Funcionario'].dropna().unique().tolist()
                            st.session_state.funcionarios = [f for f in funcionarios_unicos if f]

                        # Crear un campo de texto para nuevo funcionario
                        nuevo_funcionario_input = st.text_input(
                            "Nuevo funcionario (dejar vacío si selecciona existente)",
                            key=f"nuevo_funcionario_{indice_seleccionado}"
                        )

                        # Si se introduce un nuevo funcionario, agregarlo a la lista
                        if nuevo_funcionario_input and nuevo_funcionario_input not in st.session_state.funcionarios:
                            st.session_state.funcionarios.append(nuevo_funcionario_input)

                        # Ordenar la lista de funcionarios alfabéticamente
                        funcionarios_ordenados = sorted(st.session_state.funcionarios)

                        # Crear opciones con una opción vacía al principio
                        opciones_funcionarios = [""] + funcionarios_ordenados

                        # Determinar el índice del funcionario actual
                        indice_funcionario = 0
                        if pd.notna(row['Funcionario']) and row['Funcionario'] in opciones_funcionarios:
                            indice_funcionario = opciones_funcionarios.index(row['Funcionario'])

                        # Crear el selectbox para elegir funcionario
                        funcionario_seleccionado = st.selectbox(
                            "Seleccionar funcionario",
                            options=opciones_funcionarios,
                            index=indice_funcionario,
                            key=f"funcionario_select_{indice_seleccionado}",
                            on_change=on_change_callback
                        )

                        # Determinar el valor final del funcionario
                        funcionario_final = nuevo_funcionario_input if nuevo_funcionario_input else funcionario_seleccionado

                        # Actualizar el DataFrame si el funcionario cambia
                        if funcionario_final != row.get('Funcionario', ''):
                            registros_df.at[
                                registros_df.index[indice_seleccionado], 'Funcionario'] = funcionario_final
                            edited = True

            # SECCIÓN 2: ACTA DE COMPROMISO
            st.markdown("### 2. Acta de Compromiso")

            # Actas de acercamiento (si existe)
            if 'Actas de acercamiento y manifestación de interés' in row:
                col1, col2 = st.columns(2)
                with col1:
                    actas_acercamiento = st.selectbox(
                        "Actas de acercamiento",
                        options=["", "Si", "No"],
                        index=1 if row['Actas de acercamiento y manifestación de interés'].upper() in ["SI", "SÍ",
                                                                                                       "YES",
                                                                                                       "Y"] else (
                            2 if row['Actas de acercamiento y manifestación de interés'].upper() == "NO" else 0),
                        key=f"actas_acercamiento_{indice_seleccionado}",
                        on_change=on_change_callback
                    )
                    if actas_acercamiento != row['Actas de acercamiento y manifestación de interés']:
                        registros_df.at[registros_df.index[
                            indice_seleccionado], 'Actas de acercamiento y manifestación de interés'] = actas_acercamiento
                        edited = True

            # Suscripción acuerdo de compromiso (si existe)
            col1, col2, col3 = st.columns(3)
            if 'Suscripción acuerdo de compromiso' in row:
                with col1:
                    fecha_suscripcion_dt = fecha_para_selector(row['Suscripción acuerdo de compromiso'])
                    nueva_fecha_suscripcion = st.date_input(
                        "Suscripción acuerdo de compromiso",
                        value=fecha_suscripcion_dt,
                        format="DD/MM/YYYY",
                        key=f"fecha_suscripcion_{indice_seleccionado}",
                        on_change=on_change_callback
                    )
                    nueva_fecha_suscripcion_str = fecha_desde_selector_a_string(
                        nueva_fecha_suscripcion) if nueva_fecha_suscripcion else ""

                    fecha_original = "" if pd.isna(row['Suscripción acuerdo de compromiso']) else row[
                        'Suscripción acuerdo de compromiso']
                    if nueva_fecha_suscripcion_str != fecha_original:
                        registros_df.at[registros_df.index[
                            indice_seleccionado], 'Suscripción acuerdo de compromiso'] = nueva_fecha_suscripcion_str
                        edited = True

            with col2:
                # Usar date_input para la fecha de entrega de acuerdo
                fecha_entrega_dt = fecha_para_selector(row['Entrega acuerdo de compromiso'])
                nueva_fecha_entrega = st.date_input(
                    "Entrega acuerdo de compromiso",
                    value=fecha_entrega_dt,
                    format="DD/MM/YYYY",
                    key=f"fecha_entrega_{indice_seleccionado}",
                    on_change=on_change_callback
                )

                # Convertir la fecha a string con formato DD/MM/AAAA
                nueva_fecha_entrega_str = fecha_desde_selector_a_string(
                    nueva_fecha_entrega) if nueva_fecha_entrega else ""

                # Actualizar el DataFrame si la fecha cambia
                fecha_original = "" if pd.isna(row['Entrega acuerdo de compromiso']) else row[
                    'Entrega acuerdo de compromiso']

                if nueva_fecha_entrega_str != fecha_original:
                    registros_df.at[registros_df.index[
                        indice_seleccionado], 'Entrega acuerdo de compromiso'] = nueva_fecha_entrega_str
                    edited = True

            with col3:
                # Acuerdo de compromiso
                nuevo_acuerdo = st.selectbox(
                    "Acuerdo de compromiso",
                    options=["", "Si", "No"],
                    index=1 if row['Acuerdo de compromiso'].upper() in ["SI", "SÍ", "YES", "Y"] else (
                        2 if row['Acuerdo de compromiso'].upper() == "NO" else 0),
                    key=f"acuerdo_{indice_seleccionado}",
                    on_change=on_change_callback
                )
                if nuevo_acuerdo != row['Acuerdo de compromiso']:
                    registros_df.at[
                        registros_df.index[indice_seleccionado], 'Acuerdo de compromiso'] = nuevo_acuerdo
                    edited = True

            # SECCIÓN 3: ANÁLISIS Y CRONOGRAMA
            st.markdown("### 3. Análisis y Cronograma")

            # Gestión acceso a datos (como primer campo de esta sección)
            if 'Gestion acceso a los datos y documentos requeridos ' in row:
                gestion_acceso = st.selectbox(
                    "Gestión acceso a los datos",
                    options=["", "Si", "No"],
                    index=1 if row['Gestion acceso a los datos y documentos requeridos '].upper() in ["SI", "SÍ",
                                                                                                      "YES",
                                                                                                      "Y"] else (
                        2 if row['Gestion acceso a los datos y documentos requeridos '].upper() == "NO" else 0),
                    key=f"gestion_acceso_analisis_{indice_seleccionado}",
                    on_change=on_change_callback
                )
                if gestion_acceso != row['Gestion acceso a los datos y documentos requeridos ']:
                    registros_df.at[registros_df.index[
                        indice_seleccionado], 'Gestion acceso a los datos y documentos requeridos '] = gestion_acceso
                    edited = True

            # Mostrar botón de guardar si se han hecho cambios
            if edited or st.session_state.cambios_pendientes:
                if st.button("Guardar Todos los Cambios", key=f"guardar_{indice_seleccionado}"):
                    # Aplicar validaciones de reglas de negocio antes de guardar
                    registros_df = validar_reglas_negocio(registros_df)

                    # Actualizar el plazo de análisis después de los cambios
                    registros_df = actualizar_plazo_analisis(registros_df)

                    # Actualizar el plazo de oficio de cierre después de los cambios
                    registros_df = actualizar_plazo_oficio_cierre(registros_df)

                    # Guardar los datos en el archivo
                    exito, mensaje = guardar_datos_editados(registros_df)

                    if exito:
                        st.session_state.mensaje_guardado = ("success", mensaje)
                        st.session_state.cambios_pendientes = False

                        # Recargar la página para mostrar los cambios actualizados
                        st.rerun()
                    else:
                        st.session_state.mensaje_guardado = ("error", mensaje)

            # Agregar botón para actualizar la tabla completa sin guardar cambios
            if st.button("Actualizar Vista", key=f"actualizar_{indice_seleccionado}"):
                st.rerun()

    except Exception as e:
        st.error(f"Error al editar el registro: {e}")

    return registros_df


def mostrar_detalle_cronogramas(df_filtrado):
    """Muestra el detalle de los cronogramas con información detallada por entidad."""
    st.markdown('<div class="subtitle">Detalle de Cronogramas por Entidad</div>', unsafe_allow_html=True)

    # Verificar si hay datos filtrados
    if df_filtrado.empty:
        st.warning("No hay datos para mostrar con los filtros seleccionados.")
        return

    # Crear gráfico de barras apiladas por entidad y nivel de información
    df_conteo = df_filtrado.groupby(['Entidad', 'Nivel Información ']).size().reset_index(name='Cantidad')

    fig_barras = px.bar(
        df_conteo,
        x='Entidad',
        y='Cantidad',
        color='Nivel Información ',
        title='Cantidad de Registros por Entidad y Nivel de Información',
        labels={'Entidad': 'Entidad', 'Cantidad': 'Cantidad de Registros',
                'Nivel Información ': 'Nivel de Información'},
        color_discrete_sequence=px.colors.qualitative.Plotly
    )

    st.plotly_chart(fig_barras, use_container_width=True)

    # Crear gráfico de barras de porcentaje de avance por entidad
    df_avance = df_filtrado.groupby('Entidad')['Porcentaje Avance'].mean().reset_index()
    df_avance = df_avance.sort_values('Porcentaje Avance', ascending=False)

    fig_avance = px.bar(
        df_avance,
        x='Entidad',
        y='Porcentaje Avance',
        title='Porcentaje de Avance Promedio por Entidad',
        labels={'Entidad': 'Entidad', 'Porcentaje Avance': 'Porcentaje de Avance (%)'},
        color='Porcentaje Avance',
        color_continuous_scale='RdYlGn'
    )

    fig_avance.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_avance, use_container_width=True)

    # Crear gráfico de registros completados por fecha
    df_fechas = df_filtrado.copy()
    df_fechas['Fecha'] = df_fechas['Publicación'].apply(procesar_fecha)
    df_fechas = df_fechas[df_fechas['Fecha'].notna()]

    df_completados = df_fechas.groupby('Fecha').size().reset_index(name='Registros Completados')

    if not df_completados.empty:
        fig_completados = px.line(
            df_completados,
            x='Fecha',
            y='Registros Completados',
            title='Evolución de Registros Completados en el Tiempo',
            labels={'Fecha': 'Fecha', 'Registros Completados': 'Cantidad de Registros Completados'},
            markers=True
        )

        fig_completados.add_trace(
            go.Scatter(
                x=df_completados['Fecha'],
                y=df_completados['Registros Completados'],
                fill='tozeroy',
                fillcolor='rgba(26, 150, 65, 0.2)',
                line=dict(color='rgba(26, 150, 65, 0.8)'),
                name='Registros Completados'
            )
        )

        st.plotly_chart(fig_completados, use_container_width=True)
    else:
        st.warning("No hay suficientes datos para mostrar la evolución temporal de registros completados.")

    # Mostrar detalle de porcentaje de avance por hito
    st.markdown('### Avance por Hito')

    # Calcular porcentajes de avance para cada hito
    hitos = ['Acuerdo de compromiso', 'Análisis y cronograma', 'Estándares', 'Publicación']
    avance_hitos = {}

    for hito in hitos:
        if hito == 'Acuerdo de compromiso':
            completados = df_filtrado[df_filtrado[hito].str.upper().isin(['SI', 'SÍ', 'YES', 'Y'])].shape[0]
        else:
            completados = df_filtrado[df_filtrado[hito].notna() & (df_filtrado[hito] != '')].shape[0]

        total = df_filtrado.shape[0]
        porcentaje = (completados / total * 100) if total > 0 else 0
        avance_hitos[hito] = {'Completados': completados, 'Total': total, 'Porcentaje': porcentaje}

    # Crear dataframe para mostrar los resultados
    avance_hitos_df = pd.DataFrame(avance_hitos).T.reset_index()
    avance_hitos_df.columns = ['Hito', 'Completados', 'Total', 'Porcentaje']

    # Mostrar tabla de avance por hito
    st.dataframe(avance_hitos_df.style.format({
        'Porcentaje': '{:.2f}%'
    }).background_gradient(cmap='RdYlGn', subset=['Porcentaje']))

    # Crear gráfico de barras para el avance por hito
    fig_hitos = px.bar(
        avance_hitos_df,
        x='Hito',
        y='Porcentaje',
        title='Porcentaje de Avance por Hito',
        labels={'Hito': 'Hito', 'Porcentaje': 'Porcentaje de Avance (%)'},
        color='Porcentaje',
        color_continuous_scale='RdYlGn',
        text='Porcentaje'
    )

    fig_hitos.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    st.plotly_chart(fig_hitos, use_container_width=True)


def mostrar_exportar_resultados(df_filtrado):
    """Muestra opciones para exportar los resultados filtrados."""
    st.markdown('<div class="subtitle">Exportar Resultados</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # Exportar a CSV
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar como CSV",
            data=csv,
            file_name="registros_filtrados.csv",
            mime="text/csv",
            help="Descarga los datos filtrados en formato CSV"
        )

    with col2:
        # Exportar a Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_filtrado.to_excel(writer, sheet_name='Registros', index=False)

        excel_data = output.getvalue()
        st.download_button(
            label="Descargar como Excel",
            data=excel_data,
            file_name="registros_filtrados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Descarga los datos filtrados en formato Excel"
        )

    st.markdown("""
    <div class="info-box">
    <p><strong>Información sobre la Exportación</strong></p>
    <p>Los archivos exportados incluyen solo los registros que coinciden con los filtros seleccionados. Para descargar todos los registros completos, utilice el botón correspondiente en la sección Dashboard.</p>
    </div>
    """, unsafe_allow_html=True)


def mostrar_diagnostico(registros_df, meta_df, metas_nuevas_df, metas_actualizar_df, df_filtrado):
    """Muestra la sección de diagnóstico con análisis detallado de los datos."""
    with st.expander("Diagnóstico de Datos"):
        st.markdown("### Diagnóstico de Datos")
        st.markdown("Esta sección proporciona un diagnóstico detallado de los datos cargados.")

        # Información general
        st.markdown("#### Información General")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Total de Registros", len(registros_df))
            st.metric("Registros Filtrados", len(df_filtrado))

        with col2:
            st.metric("Registros Nuevos", len(registros_df[registros_df['TipoDato'].str.upper() == 'NUEVO']))
            st.metric("Registros a Actualizar",
                      len(registros_df[registros_df['TipoDato'].str.upper() == 'ACTUALIZAR']))

        # Análisis de valores faltantes
        st.markdown("#### Análisis de Valores Faltantes")

        # Contar valores faltantes por columna
        valores_faltantes = registros_df.isna().sum()

        # Crear dataframe para mostrar
        df_faltantes = pd.DataFrame({
            'Columna': valores_faltantes.index,
            'Valores Faltantes': valores_faltantes.values,
            'Porcentaje': valores_faltantes.values / len(registros_df) * 100
        })

        # Ordenar por cantidad de valores faltantes
        df_faltantes = df_faltantes.sort_values('Valores Faltantes', ascending=False)

        # Mostrar solo columnas con valores faltantes
        df_faltantes = df_faltantes[df_faltantes['Valores Faltantes'] > 0]

        if not df_faltantes.empty:
            st.dataframe(df_faltantes.style.format({
                'Porcentaje': '{:.2f}%'
            }).background_gradient(cmap='Blues', subset=['Porcentaje']))

            # Crear gráfico de barras para valores faltantes
            fig_faltantes = px.bar(
                df_faltantes,
                x='Columna',
                y='Porcentaje',
                title='Porcentaje de Valores Faltantes por Columna',
                labels={'Columna': 'Columna', 'Porcentaje': 'Porcentaje (%)'},
                color='Porcentaje',
                color_continuous_scale='Blues'
            )

            fig_faltantes.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_faltantes, use_container_width=True)
        else:
            st.success("¡No hay valores faltantes en los datos!")

        # Distribución de registros por entidad
        st.markdown("#### Distribución de Registros por Entidad")

        # Contar registros por entidad
        conteo_entidades = registros_df['Entidad'].value_counts().reset_index()
        conteo_entidades.columns = ['Entidad', 'Cantidad']

        # Mostrar tabla y gráfico
        st.dataframe(conteo_entidades)

        fig_entidades = px.pie(
            conteo_entidades,
            values='Cantidad',
            names='Entidad',
            title='Distribución de Registros por Entidad',
            hole=0.4
        )

        st.plotly_chart(fig_entidades, use_container_width=True)

        # Distribución de registros por funcionario si existe la columna
        if 'Funcionario' in registros_df.columns:
            st.markdown("#### Distribución de Registros por Funcionario")

            # Contar registros por funcionario
            conteo_funcionarios = registros_df['Funcionario'].value_counts().reset_index()
            conteo_funcionarios.columns = ['Funcionario', 'Cantidad']

            # Mostrar tabla y gráfico
            st.dataframe(conteo_funcionarios)

            fig_funcionarios = px.pie(
                conteo_funcionarios,
                values='Cantidad',
                names='Funcionario',
                title='Distribución de Registros por Funcionario',
                hole=0.4
            )

            st.plotly_chart(fig_funcionarios, use_container_width=True)

        # Información sobre las metas
        st.markdown("#### Información sobre Metas")

        st.markdown("##### Metas para Registros Nuevos")
        st.dataframe(metas_nuevas_df)

        st.markdown("##### Metas para Registros a Actualizar")
        st.dataframe(metas_actualizar_df)


def mostrar_ayuda():
    """Muestra la sección de ayuda con información sobre el uso del tablero."""
    with st.expander("Ayuda"):
        st.markdown("### Ayuda del Tablero de Control")
        st.markdown("""
        Este tablero de control permite visualizar y gestionar el seguimiento de cronogramas. A continuación se describen las principales funcionalidades:

        #### Navegación
        - **Dashboard**: Muestra métricas generales, comparación con metas y diagrama de Gantt.
        - **Edición de Registros**: Permite editar los registros de forma individual.

        #### Filtros
        Puede filtrar los datos por:
        - **Entidad**: Seleccione una entidad específica o "Todas" para ver todas las entidades.
        - **Tipo de Dato**: Seleccione "Nuevo", "Actualizar" o "Todos" para filtrar por tipo de dato.
        - **Funcionario**: Seleccione un funcionario específico o "Todos" para ver todos los funcionarios.
        - **Nivel de Información**: Seleccione un nivel específico o "Todos" para ver todos los registros.

        #### Edición de Datos
        En la pestaña "Edición de Registros", puede editar campos específicos de cada registro por separado.

        Los cambios se guardan automáticamente al hacer modificaciones y aplicar las validaciones correspondientes.

        #### Exportación
        Puede exportar los datos filtrados en formato CSV o Excel usando los botones en la sección "Exportar Resultados".

        #### Soporte
        Para cualquier consulta o soporte, contacte al administrador del sistema.
        """)


def mostrar_alertas_vencimientos(registros_df):
    """Muestra alertas de vencimientos de fechas en los registros."""
    st.markdown('<div class="subtitle">Alertas de Vencimientos</div>', unsafe_allow_html=True)

    # Fecha actual para comparaciones
    fecha_actual = datetime.now().date()

    # Función para calcular días hábiles entre fechas (excluyendo fines de semana y festivos)
    def calcular_dias_habiles(fecha_inicio, fecha_fin):
        if not fecha_inicio or not fecha_fin:
            return None

        # Convertir a objetos date si son datetime
        if isinstance(fecha_inicio, datetime):
            fecha_inicio = fecha_inicio.date()
        if isinstance(fecha_fin, datetime):
            fecha_fin = fecha_fin.date()

        # Si la fecha de inicio es posterior a la fecha fin, devolver días negativos
        if fecha_inicio > fecha_fin:
            return -calcular_dias_habiles(fecha_fin, fecha_inicio)

        # Calcular días hábiles
        dias = 0
        fecha_actual = fecha_inicio
        while fecha_actual <= fecha_fin:
            # Si no es fin de semana (0=lunes, 6=domingo)
            if fecha_actual.weekday() < 5:
                dias += 1
            fecha_actual += timedelta(days=1)

        return dias

    st.info("Funcionalidad de alertas de vencimientos implementada.")


def mostrar_error(error):
    """Muestra mensajes de error formateados."""
    st.error(f"Error al cargar o procesar los datos: {error}")
    st.info("""
    Por favor, verifique lo siguiente:
    1. Los archivos CSV están correctamente formateados.
    2. Las columnas requeridas están presentes en los archivos.
    3. Los valores de fecha tienen el formato correcto (DD/MM/AAAA).

    Si el problema persiste, contacte al administrador del sistema.
    """)


def main():
    try:
        # Inicializar estado de sesión para registro de cambios
        if 'cambios_pendientes' not in st.session_state:
            st.session_state.cambios_pendientes = False

        if 'mensaje_guardado' not in st.session_state:
            st.session_state.mensaje_guardado = None

        # Inicializar lista de funcionarios en el estado de sesión
        if 'funcionarios' not in st.session_state:
            st.session_state.funcionarios = []

        # Configuración de la página
        setup_page()

        # Cargar estilos
        load_css()

        # Título
        st.markdown('<div class="title">📊 Tablero de Control de Seguimiento de Cronogramas</div>',
                    unsafe_allow_html=True)

        # Información sobre el tablero
        st.sidebar.markdown('<div class="subtitle">Información</div>', unsafe_allow_html=True)
        st.sidebar.markdown("""
        <div class="info-box">
        <p><strong>Tablero de Control de Cronogramas</strong></p>
        <p>Este tablero muestra el seguimiento de cronogramas, calcula porcentajes de avance y muestra la comparación con metas quincenales.</p>
        </div>
        """, unsafe_allow_html=True)

        # Cargar datos
        registros_df, meta_df = cargar_datos()

        # Asegurar que las columnas requeridas existan
        columnas_requeridas = ['Cod', 'Entidad', 'TipoDato', 'Acuerdo de compromiso',
                               'Análisis y cronograma', 'Estándares', 'Publicación',
                               'Nivel Información ', 'Fecha de entrega de información',
                               'Plazo de análisis', 'Plazo de cronograma', 'Plazo de oficio de cierre']

        for columna in columnas_requeridas:
            if columna not in registros_df.columns:
                registros_df[columna] = ''

        # Actualizar automáticamente todos los plazos
        registros_df = actualizar_plazo_analisis(registros_df)
        registros_df = actualizar_plazo_cronograma(registros_df)
        registros_df = actualizar_plazo_oficio_cierre(registros_df)

        # Guardar los datos actualizados inmediatamente
        exito, mensaje = guardar_datos_editados(registros_df)
        if not exito:
            st.warning(f"No se pudieron guardar los plazos actualizados: {mensaje}")

        # Verificar si los DataFrames están vacíos o no tienen registros
        if registros_df.empty:
            st.error(
                "No se pudieron cargar datos de registros. El archivo registros.csv debe existir en el directorio.")
            st.info(
                "Por favor, asegúrate de que el archivo registros.csv existe y está correctamente formateado. " +
                "El archivo debe tener al menos las siguientes columnas: 'Cod', 'Entidad', 'TipoDato', 'Nivel Información ', " +
                "'Acuerdo de compromiso', 'Análisis y cronograma', 'Estándares', 'Publicación', 'Fecha de entrega de información'."
            )
            return

        if meta_df.empty:
            st.warning("No se pudieron cargar datos de metas. El archivo meta.csv debe existir en el directorio.")
            st.info(
                "Algunas funcionalidades relacionadas con las metas podrían no estar disponibles. " +
                "Por favor, asegúrate de que el archivo meta.csv existe y está correctamente formateado."
            )
            # Creamos un DataFrame de metas básico para que la aplicación pueda continuar
            meta_df = pd.DataFrame({
                0: ["Fecha", "15/01/2025", "31/01/2025"],
                1: [0, 0, 0],
                2: [0, 0, 0],
                3: [0, 0, 0],
                4: [0, 0, 0],
                6: [0, 0, 0],
                7: [0, 0, 0],
                8: [0, 0, 0],
                9: [0, 0, 0]
            })

        # Mostrar el número de registros cargados
        st.success(f"Se han cargado {len(registros_df)} registros de la base de datos.")

        # Aplicar validaciones de reglas de negocio
        registros_df = validar_reglas_negocio(registros_df)

        # Mostrar estado de validaciones
        with st.expander("Validación de Reglas de Negocio"):
            st.markdown("### Estado de Validaciones")
            st.info("""
            Se aplican las siguientes reglas de validación:
            1. Si 'Entrega acuerdo de compromiso' no está vacío, 'Acuerdo de compromiso' se actualiza a 'SI'
            2. Si 'Análisis y cronograma' tiene fecha, 'Análisis de información' se actualiza a 'SI'
            3. Si se introduce fecha en 'Estándares', se verifica que los campos con sufijo (completo) estén 'Completo'
            4. Si se introduce fecha en 'Publicación', se verifica que 'Disponer datos temáticos' sea 'SI'
            5. Para introducir una fecha en 'Fecha de oficio de cierre', todos los campos Si/No deben estar marcados como 'Si', todos los estándares deben estar 'Completo' y todas las fechas diligenciadas.
            6. Al introducir una fecha en 'Fecha de oficio de cierre', el campo 'Estado' se actualizará automáticamente a 'Completado'.
            """)
            mostrar_estado_validaciones(registros_df, st)

        # Actualizar automáticamente el plazo de análisis
        registros_df = actualizar_plazo_analisis(registros_df)

        # Actualizar automáticamente el plazo de oficio de cierre
        registros_df = actualizar_plazo_oficio_cierre(registros_df)

        # Procesar las metas
        metas_nuevas_df, metas_actualizar_df = procesar_metas(meta_df)

        # Asegurar que las columnas requeridas existan
        columnas_requeridas = ['Cod', 'Entidad', 'TipoDato', 'Acuerdo de compromiso',
                               'Análisis y cronograma', 'Estándares', 'Publicación',
                               'Nivel Información ', 'Fecha de entrega de información',
                               'Plazo de análisis', 'Plazo de cronograma', 'Plazo de oficio de cierre']

        for columna in columnas_requeridas:
            if columna not in registros_df.columns:
                registros_df[columna] = ''

        # Convertir columnas de texto a mayúsculas para facilitar comparaciones
        columnas_texto = ['TipoDato', 'Acuerdo de compromiso']
        for columna in columnas_texto:
            registros_df[columna] = registros_df[columna].astype(str)

        # Agregar columna de porcentaje de avance
        registros_df['Porcentaje Avance'] = registros_df.apply(calcular_porcentaje_avance, axis=1)

        # Agregar columna de estado de fechas
        registros_df['Estado Fechas'] = registros_df.apply(verificar_estado_fechas, axis=1)

        # Filtros en la barra lateral
        st.sidebar.markdown('<div class="subtitle">Filtros</div>', unsafe_allow_html=True)

        # Filtro por entidad
        entidades = ['Todas'] + sorted(registros_df['Entidad'].unique().tolist())
        entidad_seleccionada = st.sidebar.selectbox('Entidad', entidades)

        # Filtro por registros - Activado solo cuando se selecciona una entidad específica
        if entidad_seleccionada != 'Todas':
            # Filtrar registros_df por la entidad seleccionada
            registros_entidad = registros_df[registros_df['Entidad'] == entidad_seleccionada]

            # Crear opciones para el selector de registros específicos de esta entidad
            codigos_registros = registros_entidad['Cod'].astype(str).tolist()
            niveles_registros = registros_entidad['Nivel Información '].tolist()

            # Combinar información para mostrar en el selector
            opciones_registros = [f"{codigos_registros[i]} - {niveles_registros[i]}"
                                  for i in range(len(codigos_registros))]

            # Añadir opción para "Todos los registros" de esta entidad
            opciones_registros = ['Todos los registros'] + opciones_registros

            # Agregar selector de registro específico
            registro_seleccionado = st.sidebar.selectbox(
                "Registro específico",
                options=opciones_registros,
                key="selector_registro_filtro"
            )
        else:
            # Si no se selecciona una entidad específica, no se muestra el filtro de registros
            registro_seleccionado = 'Todos los registros'

        # Filtro por funcionario
        funcionarios = ['Todos']
        if 'Funcionario' in registros_df.columns:
            funcionarios += sorted(registros_df['Funcionario'].dropna().unique().tolist())
        funcionario_seleccionado = st.sidebar.selectbox('Funcionario', funcionarios)

        # Filtro por tipo de dato - NUEVA FUNCIONALIDAD
        tipos_dato = ['Todos'] + sorted(registros_df['TipoDato'].dropna().unique().tolist())
        tipo_dato_seleccionado = st.sidebar.selectbox('Tipo de Dato', tipos_dato)

        # Aplicar filtros
        df_filtrado = registros_df.copy()

        if entidad_seleccionada != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Entidad'] == entidad_seleccionada]

            # Aplicar filtro por registro específico si se seleccionó uno
            if registro_seleccionado != 'Todos los registros':
                # Extraer el código del registro de la opción seleccionada
                codigo_registro = registro_seleccionado.split(' - ')[0]
                df_filtrado = df_filtrado[df_filtrado['Cod'].astype(str) == codigo_registro]

        if funcionario_seleccionado != 'Todos' and 'Funcionario' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Funcionario'] == funcionario_seleccionado]

        # Aplicar filtro por tipo de dato - NUEVA FUNCIONALIDAD
        if tipo_dato_seleccionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['TipoDato'].str.upper() == tipo_dato_seleccionado.upper()]

        # Crear pestañas
        tab1, tab2, tab3 = st.tabs(["Dashboard", "Edición de Registros", "Alertas de Vencimientos"])

        with tab1:
            mostrar_dashboard(df_filtrado, metas_nuevas_df, metas_actualizar_df, registros_df)

        with tab2:
            registros_df = mostrar_edicion_registros(registros_df)

        with tab3:
            mostrar_alertas_vencimientos(registros_df)

        # Agregar sección de diagnóstico
        mostrar_diagnostico(registros_df, meta_df, metas_nuevas_df, metas_actualizar_df, df_filtrado)

        # Agregar sección de ayuda
        mostrar_ayuda()

    except Exception as e:
        mostrar_error(e)


if __name__ == "__main__":
    main()
