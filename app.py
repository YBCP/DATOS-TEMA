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

    # Diagrama de Gantt
    st.markdown('<div class="subtitle">Diagrama de Gantt - Cronograma de Hitos</div>', unsafe_allow_html=True)

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

        # Agregar botón para descargar la tabla en CSV
        csv = df_mostrar.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar tabla (CSV)",
            data=csv,
            file_name="registros_detalle.csv",
            mime="text/csv",
        )
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


def mostrar_datos_completos_interactivo(registros_df):
    """Muestra la pestaña de datos completos con edición interactiva con calendarios."""
    st.markdown('<div class="subtitle">Datos Completos (Editable)</div>', unsafe_allow_html=True)

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

    # Agregar subtabs para ver todos los datos o editar individualmente
    data_tab1, data_tab2 = st.tabs(["Vista de Tabla Completa", "Edición de Registros"])

    with data_tab1:
        st.markdown("### Tabla Completa de Registros")
        st.info("Esta vista muestra todos los registros. Para editar, use la pestaña 'Edición de Registros'.")

        # Preparar los datos para mostrar en la tabla
        df_mostrar = registros_df.copy()

        # Definir el nuevo orden exacto de las columnas según lo solicitado
        columnas_ordenadas = [
            # Datos básicos
            'Cod', 'Entidad', 'Nivel Información ',
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

        # Filtrar las columnas que existen en el DataFrame
        columnas_mostrar = [col for col in columnas_ordenadas if col in df_mostrar.columns]

        # Reorganizar el DataFrame según el orden especificado
        df_mostrar = df_mostrar[columnas_mostrar]

        # Formatear las columnas de fecha
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
        try:
            st.dataframe(
                df_mostrar
                .style.format({'Porcentaje Avance': '{:.2f}%'})
                .apply(highlight_estado_fechas, axis=1)
                .background_gradient(cmap='RdYlGn', subset=['Porcentaje Avance']),
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error al mostrar la tabla: {e}")
            st.dataframe(df_mostrar)

        # Agregar botón para descargar la tabla completa en CSV
        csv = df_mostrar.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar tabla completa (CSV)",
            data=csv,
            file_name="registros_completos.csv",
            mime="text/csv",
        )
    with data_tab2:
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
                        # Clave actualizada para evitar duplicados
                        on_change=on_change_callback
                    )
                    if gestion_acceso != row['Gestion acceso a los datos y documentos requeridos ']:
                        registros_df.at[registros_df.index[
                            indice_seleccionado], 'Gestion acceso a los datos y documentos requeridos '] = gestion_acceso
                        edited = True

                col1, col2, col3 = st.columns(3)

                with col1:
                    # Análisis de información
                    if 'Análisis de información' in row:
                        analisis_info = st.selectbox(
                            "Análisis de información",
                            options=["", "Si", "No"],
                            index=1 if row['Análisis de información'].upper() in ["SI", "SÍ", "YES", "Y"] else (
                                2 if row['Análisis de información'].upper() == "NO" else 0),
                            key=f"analisis_info_{indice_seleccionado}",
                            on_change=on_change_callback
                        )
                        if analisis_info != row['Análisis de información']:
                            registros_df.at[
                                registros_df.index[indice_seleccionado], 'Análisis de información'] = analisis_info
                            edited = True

                with col2:
                    # Cronograma Concertado
                    if 'Cronograma Concertado' in row:
                        cronograma_concertado = st.selectbox(
                            "Cronograma Concertado",
                            options=["", "Si", "No"],
                            index=1 if row['Cronograma Concertado'].upper() in ["SI", "SÍ", "YES", "Y"] else (
                                2 if row['Cronograma Concertado'].upper() == "NO" else 0),
                            key=f"cronograma_concertado_{indice_seleccionado}",
                            on_change=on_change_callback
                        )
                        if cronograma_concertado != row['Cronograma Concertado']:
                            registros_df.at[registros_df.index[
                                indice_seleccionado], 'Cronograma Concertado'] = cronograma_concertado
                            edited = True

                with col3:
                    # Seguimiento a los acuerdos (si existe)
                    if 'Seguimiento a los acuerdos' in row:
                        seguimiento_acuerdos = st.selectbox(
                            "Seguimiento a los acuerdos",
                            options=["", "Si", "No"],
                            index=1 if row['Seguimiento a los acuerdos'].upper() in ["SI", "SÍ", "YES", "Y"] else (
                                2 if row['Seguimiento a los acuerdos'].upper() == "NO" else 0),
                            key=f"seguimiento_acuerdos_{indice_seleccionado}",
                            on_change=on_change_callback
                        )
                        if seguimiento_acuerdos != row['Seguimiento a los acuerdos']:
                            registros_df.at[registros_df.index[
                                indice_seleccionado], 'Seguimiento a los acuerdos'] = seguimiento_acuerdos
                            edited = True

                # Fecha real de análisis y cronograma
                col1, col2 = st.columns(2)

                with col2:
                    # Usar date_input para la fecha de análisis y cronograma
                    fecha_analisis_dt = fecha_para_selector(row['Análisis y cronograma'])
                    nueva_fecha_analisis = st.date_input(
                        "Análisis y cronograma (fecha real)",
                        value=fecha_analisis_dt,
                        format="DD/MM/YYYY",
                        key=f"fecha_analisis_{indice_seleccionado}",
                        on_change=on_change_callback
                    )

                    # Convertir la fecha a string con formato DD/MM/AAAA
                    nueva_fecha_analisis_str = fecha_desde_selector_a_string(
                        nueva_fecha_analisis) if nueva_fecha_analisis else ""

                    # Actualizar el DataFrame si la fecha cambia
                    fecha_original = "" if pd.isna(row['Análisis y cronograma']) else row['Análisis y cronograma']
                    if nueva_fecha_analisis_str != fecha_original:
                        registros_df.at[
                            registros_df.index[indice_seleccionado], 'Análisis y cronograma'] = nueva_fecha_analisis_str
                        edited = True

                # Fecha de entrega de información y plazo de análisis
                col1, col2 = st.columns(2)

                with col1:
                    # Usar date_input para la fecha de entrega de información
                    fecha_entrega_info_dt = fecha_para_selector(row['Fecha de entrega de información'])
                    nueva_fecha_entrega_info = st.date_input(
                        "Fecha de entrega de información",
                        value=fecha_entrega_info_dt,
                        format="DD/MM/YYYY",
                        key=f"fecha_entrega_info_{indice_seleccionado}"
                    )

                    # Convertir la fecha a string con formato DD/MM/AAAA
                    nueva_fecha_entrega_info_str = fecha_desde_selector_a_string(
                        nueva_fecha_entrega_info) if nueva_fecha_entrega_info else ""

                    # Actualizar el DataFrame si la fecha cambia
                    fecha_original = "" if pd.isna(row['Fecha de entrega de información']) else row[
                        'Fecha de entrega de información']

                    if nueva_fecha_entrega_info_str != fecha_original:
                        registros_df.at[registros_df.index[
                            indice_seleccionado], 'Fecha de entrega de información'] = nueva_fecha_entrega_info_str
                        edited = True

                        # Actualizar automáticamente todos los plazos
                        registros_df = actualizar_plazo_analisis(registros_df)
                        registros_df = actualizar_plazo_cronograma(registros_df)
                        registros_df = actualizar_plazo_oficio_cierre(registros_df)

                        # Guardar los datos actualizados inmediatamente para asegurarnos de que los cambios persistan
                        exito, mensaje = guardar_datos_editados(registros_df)
                        if not exito:
                            st.warning(f"No se pudieron guardar los plazos actualizados: {mensaje}")

                        # Mostrar los nuevos plazos calculados
                        nuevo_plazo_analisis = registros_df.iloc[indice_seleccionado][
                            'Plazo de análisis'] if 'Plazo de análisis' in registros_df.iloc[
                            indice_seleccionado] else ""
                        nuevo_plazo_cronograma = registros_df.iloc[indice_seleccionado][
                            'Plazo de cronograma'] if 'Plazo de cronograma' in registros_df.iloc[
                            indice_seleccionado] else ""
                        st.info(f"El plazo de análisis se ha actualizado automáticamente a: {nuevo_plazo_analisis}")
                        st.info(f"El plazo de cronograma se ha actualizado automáticamente a: {nuevo_plazo_cronograma}")

                        # Guardar cambios inmediatamente
                        exito, mensaje = guardar_datos_editados(registros_df)
                        if exito:
                            st.success("Fecha de entrega actualizada y plazos recalculados correctamente.")
                            st.session_state.cambios_pendientes = False
                            # Actualizar la tabla completa
                            st.rerun()
                        else:
                            st.error(f"Error al guardar cambios: {mensaje}")

                with col2:
                    # Plazo de análisis (solo mostrar, no editar)
                    plazo_analisis = row['Plazo de análisis'] if 'Plazo de análisis' in row and pd.notna(
                        row['Plazo de análisis']) else ""

                    # Mostrar el plazo de análisis como texto (no como selector de fecha porque es automático)
                    st.text_input(
                        "Plazo de análisis (calculado automáticamente)",
                        value=plazo_analisis,
                        disabled=True,
                        key=f"plazo_analisis_{indice_seleccionado}"
                    )

                    # Mostrar el plazo de cronograma
                    plazo_cronograma = row['Plazo de cronograma'] if 'Plazo de cronograma' in row and pd.notna(
                        row['Plazo de cronograma']) else ""

                    # Mostrar el plazo de cronograma como texto (no como selector de fecha porque es automático)
                    st.text_input(
                        "Plazo de cronograma (calculado automáticamente)",
                        value=plazo_cronograma,
                        disabled=True,
                        key=f"plazo_cronograma_{indice_seleccionado}"
                    )

                    # Explicación del cálculo automático
                    st.info(
                        "El plazo de análisis se calcula automáticamente como 5 días hábiles después de la fecha de entrega. "
                        "El plazo de cronograma se calcula como 3 días hábiles después del plazo de análisis."
                    )

                # SECCIÓN 4: ESTÁNDARES
                st.markdown("### 4. Estándares")
                col1, col2 = st.columns(2)

                with col1:
                    # Fecha programada para estándares
                    if 'Estándares (fecha programada)' in row:
                        fecha_estandares_prog_dt = fecha_para_selector(row['Estándares (fecha programada)'])
                        nueva_fecha_estandares_prog = st.date_input(
                            "Estándares (fecha programada)",
                            value=fecha_estandares_prog_dt,
                            format="DD/MM/YYYY",
                            key=f"fecha_estandares_prog_{indice_seleccionado}",
                            on_change=on_change_callback
                        )
                        nueva_fecha_estandares_prog_str = fecha_desde_selector_a_string(
                            nueva_fecha_estandares_prog) if nueva_fecha_estandares_prog else ""

                        fecha_original = "" if pd.isna(row['Estándares (fecha programada)']) else row[
                            'Estándares (fecha programada)']
                        if nueva_fecha_estandares_prog_str != fecha_original:
                            registros_df.at[registros_df.index[
                                indice_seleccionado], 'Estándares (fecha programada)'] = nueva_fecha_estandares_prog_str
                            edited = True

                with col2:
                    # Usar date_input para la fecha de estándares
                    fecha_estandares_dt = fecha_para_selector(row['Estándares'])
                    nueva_fecha_estandares = st.date_input(
                        "Fecha de estándares (real)",
                        value=fecha_estandares_dt,
                        format="DD/MM/YYYY",
                        key=f"fecha_estandares_{indice_seleccionado}",
                        on_change=on_change_callback
                    )

                    # Convertir la fecha a string con formato DD/MM/AAAA
                    nueva_fecha_estandares_str = fecha_desde_selector_a_string(
                        nueva_fecha_estandares) if nueva_fecha_estandares else ""

                    # Actualizar el DataFrame si la fecha cambia
                    fecha_original = "" if pd.isna(row['Estándares']) else row['Estándares']

                    # En la sección de "Fecha de estándares (real)"
                    # Verificar si se ha introducido una fecha nueva en estándares
                    if nueva_fecha_estandares_str and nueva_fecha_estandares_str != fecha_original:
                        # Verificar si todos los campos de estándares están completos
                        campos_estandares = ['Registro (completo)', 'ET (completo)', 'CO (completo)', 'DD (completo)',
                                             'REC (completo)', 'SERVICIO (completo)']
                        todos_completos = True
                        campos_incompletos = []

                        for campo in campos_estandares:
                            if campo in registros_df.columns and campo in registros_df.iloc[indice_seleccionado]:
                                valor = str(registros_df.iloc[indice_seleccionado][campo]).strip()
                                if valor.upper() != "COMPLETO":
                                    todos_completos = False
                                    campos_incompletos.append(campo)

                        # Si no todos están completos, mostrar advertencia y no permitir el cambio
                        if not todos_completos:
                            st.error(
                                f"No es posible diligenciar este campo. Verifique que todos los estándares se encuentren en estado Completo. Campos pendientes: {', '.join(campos_incompletos)}")
                            # Mantener el valor original
                            registros_df.at[registros_df.index[indice_seleccionado], 'Estándares'] = fecha_original
                        else:
                            # Solo actualizar si todos los campos están completos
                            registros_df.at[
                                registros_df.index[indice_seleccionado], 'Estándares'] = nueva_fecha_estandares_str
                            edited = True

                            # Guardar cambios inmediatamente sin más validaciones
                            exito, mensaje = guardar_datos_editados(registros_df)
                            if exito:
                                st.success("Fecha de estándares actualizada y guardada correctamente.")
                                st.session_state.cambios_pendientes = False
                                st.rerun()  # Recargar la página para mostrar los cambios
                            else:
                                st.error(f"Error al guardar cambios: {mensaje}")

                            # Guardar cambios inmediatamente
                            registros_df = validar_reglas_negocio(registros_df)
                            exito, mensaje = guardar_datos_editados(registros_df)
                            if exito:
                                st.success("Fecha de estándares actualizada y guardada correctamente.")
                                st.session_state.cambios_pendientes = False
                            else:
                                st.error(f"Error al guardar cambios: {mensaje}")

                    elif nueva_fecha_estandares_str != fecha_original:
                        # Si se está borrando la fecha, permitir el cambio
                        registros_df.at[
                            registros_df.index[indice_seleccionado], 'Estándares'] = nueva_fecha_estandares_str
                        edited = True
                        # Guardar cambios inmediatamente
                        registros_df = validar_reglas_negocio(registros_df)
                        exito, mensaje = guardar_datos_editados(registros_df)
                        if exito:
                            st.success("Fecha de estándares actualizada y guardada correctamente.")
                            st.session_state.cambios_pendientes = False
                        else:
                            st.error(f"Error al guardar cambios: {mensaje}")

                # Mostrar advertencia si corresponde
                if estandares_warning:
                    st.error(
                        "No se puede diligenciar este campo. Verifique que los estándares se encuentren en estado Completo")

                # Sección: Cumplimiento de estándares
                st.markdown("#### Cumplimiento de estándares")

                # Mostrar campos de estándares con lista desplegable
                campos_estandares_completo = ['Registro (completo)', 'ET (completo)', 'CO (completo)', 'DD (completo)',
                                              'REC (completo)', 'SERVICIO (completo)']
                cols = st.columns(3)

                # Asegurarse de que se muestren todos los campos de estándares (completo)
                for i, campo in enumerate(campos_estandares_completo):
                    # Verificar si el campo existe en el registro
                    # Si no existe, crearlo para asegurar que se muestre
                    if campo not in registros_df.iloc[indice_seleccionado]:
                        registros_df.at[registros_df.index[indice_seleccionado], campo] = "Sin iniciar"

                    # Obtener el valor actual directamente del DataFrame para asegurar que usamos el valor más reciente
                    valor_actual = registros_df.iloc[indice_seleccionado][campo] if pd.notna(
                        registros_df.iloc[indice_seleccionado][campo]) else "Sin iniciar"

                    with cols[i % 3]:
                        # Determinar el índice correcto para el valor actual
                        opciones = ["Sin iniciar", "En proceso", "Completo"]
                        indice_opcion = 0  # Por defecto "Sin iniciar"

                        if valor_actual in opciones:
                            indice_opcion = opciones.index(valor_actual)
                        elif str(valor_actual).lower() == "en proceso":
                            indice_opcion = 1
                        elif str(valor_actual).lower() == "completo":
                            indice_opcion = 2

                        # Extraer nombre sin el sufijo para mostrar en la interfaz
                        nombre_campo = campo.split(' (')[0]

                        # Crear el selectbox con las opciones
                        nuevo_valor = st.selectbox(
                            f"{nombre_campo}",
                            options=opciones,
                            index=indice_opcion,
                            key=f"estandar_{campo}_{indice_seleccionado}",
                            help=f"Estado de cumplimiento para {nombre_campo}"
                        )

                        # Actualizar el valor si ha cambiado
                        if nuevo_valor != valor_actual:
                            registros_df.at[registros_df.index[indice_seleccionado], campo] = nuevo_valor
                            edited = True

                            # Guardar cambios inmediatamente al modificar estándares
                            registros_df = validar_reglas_negocio(registros_df)
                            exito, mensaje = guardar_datos_editados(registros_df)
                            if exito:
                                st.success(
                                    f"Campo '{nombre_campo}' actualizado a '{nuevo_valor}' y guardado correctamente.")
                                st.session_state.cambios_pendientes = False
                                # Actualizar la tabla completa
                                st.rerun()
                            else:
                                st.error(f"Error al guardar cambios: {mensaje}")

                # Explicación sobre los campos de estándares
                st.info("""
                **Nota sobre los estándares**: Para poder ingresar una fecha en el campo 'Estándares', 
                todos los campos anteriores deben estar en estado 'Completo'. Esto es un requisito 
                obligatorio según las reglas de validación del sistema.
                """)

                # Validaciones (campos adicionales relacionados con validación)
                if 'Resultados de orientación técnica' in row or 'Verificación del servicio web geográfico' in row or 'Verificar Aprobar Resultados' in row:
                    st.markdown("#### Validaciones")
                    cols = st.columns(3)

                    # Campos adicionales en orden específico
                    campos_validaciones = [
                        'Resultados de orientación técnica',
                        'Verificación del servicio web geográfico',
                        'Verificar Aprobar Resultados',
                        'Revisar y validar los datos cargados en la base de datos',
                        'Aprobación resultados obtenidos en la rientación'
                    ]

                    for i, campo in enumerate(campos_validaciones):
                        if campo in row:
                            with cols[i % 3]:
                                valor_actual = row[campo]
                                nuevo_valor = st.selectbox(
                                    f"{campo}",
                                    options=["", "Si", "No"],
                                    index=1 if valor_actual == "Si" or valor_actual.upper() in ["SI", "SÍ", "YES",
                                                                                                "Y"] else (
                                        2 if valor_actual == "No" or valor_actual.upper() == "NO" else 0
                                    ),
                                    key=f"{campo}_{indice_seleccionado}",
                                    on_change=on_change_callback
                                )
                                if nuevo_valor != valor_actual:
                                    registros_df.at[registros_df.index[indice_seleccionado], campo] = nuevo_valor
                                    edited = True

                # SECCIÓN 5: PUBLICACIÓN
                st.markdown("### 5. Publicación")
                col1, col2, col3 = st.columns(3)

                with col1:
                    # Disponer datos temáticos
                    if 'Disponer datos temáticos' in row:
                        disponer_datos = st.selectbox(
                            "Disponer datos temáticos",
                            options=["", "Si", "No"],
                            index=1 if row['Disponer datos temáticos'].upper() in ["SI", "SÍ", "YES", "Y"] else (
                                2 if row['Disponer datos temáticos'].upper() == "NO" else 0),
                            key=f"disponer_datos_{indice_seleccionado}",
                            on_change=on_change_callback
                        )
                        if disponer_datos != row['Disponer datos temáticos']:
                            registros_df.at[
                                registros_df.index[indice_seleccionado], 'Disponer datos temáticos'] = disponer_datos

                            # Si se cambia a "No", limpiar la fecha de publicación
                            if disponer_datos.upper() == "NO" and 'Publicación' in registros_df.columns:
                                registros_df.at[registros_df.index[indice_seleccionado], 'Publicación'] = ""
                                st.warning(
                                    "Se ha eliminado la fecha de publicación porque 'Disponer datos temáticos' se marcó como 'No'.")

                            edited = True

                            # Guardar cambios inmediatamente para validar reglas de negocio
                            registros_df = validar_reglas_negocio(registros_df)
                            exito, mensaje = guardar_datos_editados(registros_df)
                            if exito:
                                st.success("Cambios guardados correctamente.")
                                st.session_state.cambios_pendientes = False
                                # Actualizar la tabla completa
                                st.rerun()
                            else:
                                st.error(f"Error al guardar cambios: {mensaje}")

                with col2:
                    # Fecha programada para publicación
                    if 'Fecha de publicación programada' in row:
                        fecha_publicacion_prog_dt = fecha_para_selector(row['Fecha de publicación programada'])
                        nueva_fecha_publicacion_prog = st.date_input(
                            "Fecha de publicación programada",
                            value=fecha_publicacion_prog_dt,
                            format="DD/MM/YYYY",
                            key=f"fecha_publicacion_prog_{indice_seleccionado}",
                            on_change=on_change_callback
                        )
                        nueva_fecha_publicacion_prog_str = fecha_desde_selector_a_string(
                            nueva_fecha_publicacion_prog) if nueva_fecha_publicacion_prog else ""

                        fecha_original = "" if pd.isna(row['Fecha de publicación programada']) else row[
                            'Fecha de publicación programada']
                        if nueva_fecha_publicacion_prog_str != fecha_original:
                            registros_df.at[registros_df.index[
                                indice_seleccionado], 'Fecha de publicación programada'] = nueva_fecha_publicacion_prog_str
                            edited = True

                with col3:
                    # Usar date_input para la fecha de publicación
                    fecha_publicacion_dt = fecha_para_selector(row['Publicación'])
                    nueva_fecha_publicacion = st.date_input(
                        "Fecha de publicación (real)",
                        value=fecha_publicacion_dt,
                        format="DD/MM/YYYY",
                        key=f"fecha_publicacion_{indice_seleccionado}",
                        on_change=on_change_callback
                    )

                    # Convertir la fecha a string con formato DD/MM/AAAA
                    nueva_fecha_publicacion_str = fecha_desde_selector_a_string(
                        nueva_fecha_publicacion) if nueva_fecha_publicacion else ""

                    # Actualizar el DataFrame si la fecha cambia
                    fecha_original = "" if pd.isna(row['Publicación']) else row['Publicación']

                    if nueva_fecha_publicacion_str and nueva_fecha_publicacion_str != fecha_original:
                        # Verificar si Disponer datos temáticos está marcado como Si
                        disponer_datos_tematicos = False
                        if 'Disponer datos temáticos' in registros_df.iloc[indice_seleccionado]:
                            valor = registros_df.iloc[indice_seleccionado]['Disponer datos temáticos']
                            disponer_datos_tematicos = valor.upper() in ["SI", "SÍ", "YES", "Y"] if pd.notna(
                                valor) else False

                        # Si no está marcado como Si, mostrar advertencia y no permitir el cambio
                        if not disponer_datos_tematicos:
                            st.error(
                                "No es posible diligenciar este campo. El campo 'Disponer datos temáticos' debe estar marcado como 'Si'")
                            # No actualizar el valor en el DataFrame
                        else:
                            # Solo actualizar si cumple la condición
                            registros_df.at[
                                registros_df.index[indice_seleccionado], 'Publicación'] = nueva_fecha_publicacion_str
                            edited = True

                            # Recalcular el plazo de oficio de cierre inmediatamente
                            registros_df = actualizar_plazo_oficio_cierre(registros_df)

                            # Obtener el nuevo plazo calculado
                            nuevo_plazo_oficio = registros_df.iloc[indice_seleccionado][
                                'Plazo de oficio de cierre'] if 'Plazo de oficio de cierre' in registros_df.iloc[
                                indice_seleccionado] else ""
                            st.info(
                                f"El plazo de oficio de cierre se ha actualizado automáticamente a: {nuevo_plazo_oficio}")

                            # Guardar cambios inmediatamente
                            registros_df = validar_reglas_negocio(registros_df)
                            exito, mensaje = guardar_datos_editados(registros_df)
                            if exito:
                                st.success(
                                    "Fecha de publicación actualizada y plazo de oficio de cierre recalculado correctamente.")
                                st.session_state.cambios_pendientes = False
                                # Actualizar la tabla completa
                                st.rerun()
                            else:
                                st.error(f"Error al guardar cambios: {mensaje}")

                    elif nueva_fecha_publicacion_str != fecha_original:
                        # Si se está borrando la fecha, permitir el cambio
                        registros_df.at[
                            registros_df.index[indice_seleccionado], 'Publicación'] = nueva_fecha_publicacion_str

                        # Limpiar también el plazo de oficio de cierre
                        if 'Plazo de oficio de cierre' in registros_df.columns:
                            registros_df.at[registros_df.index[indice_seleccionado], 'Plazo de oficio de cierre'] = ""

                        edited = True
                        # Guardar cambios inmediatamente
                        registros_df = validar_reglas_negocio(registros_df)
                        exito, mensaje = guardar_datos_editados(registros_df)
                        if exito:
                            st.success("Fecha de publicación actualizada y guardada correctamente.")
                            st.session_state.cambios_pendientes = False
                            # Actualizar la tabla completa
                            st.rerun()
                        else:
                            st.error(f"Error al guardar cambios: {mensaje}")

                # Mostrar el plazo de oficio de cierre
                col1, col2 = st.columns(2)
                with col1:
                    # Plazo de oficio de cierre (calculado automáticamente)
                    plazo_oficio_cierre = row[
                        'Plazo de oficio de cierre'] if 'Plazo de oficio de cierre' in row and pd.notna(
                        row['Plazo de oficio de cierre']) else ""

                    # Mostrar el plazo de oficio de cierre como texto (no como selector de fecha porque es automático)
                    st.text_input(
                        "Plazo de oficio de cierre (calculado automáticamente)",
                        value=plazo_oficio_cierre,
                        disabled=True,
                        key=f"plazo_oficio_cierre_{indice_seleccionado}"
                    )

                    st.info(
                        "El plazo de oficio de cierre se calcula automáticamente como 7 días hábiles después de la fecha de publicación, "
                        "sin contar sábados, domingos y festivos en Colombia."
                    )
                # Catálogo y oficios de cierre
                if 'Catálogo de recursos geográficos' in row or 'Oficios de cierre' in row:
                    col1, col2, col3 = st.columns(3)

                    # Catálogo de recursos geográficos
                    if 'Catálogo de recursos geográficos' in row:
                        with col1:
                            catalogo_recursos = st.selectbox(
                                "Catálogo de recursos geográficos",
                                options=["", "Si", "No"],
                                index=1 if row['Catálogo de recursos geográficos'].upper() in ["SI", "SÍ", "YES",
                                                                                               "Y"] else (
                                    2 if row['Catálogo de recursos geográficos'].upper() == "NO" else 0),
                                key=f"catalogo_recursos_{indice_seleccionado}",
                                on_change=on_change_callback
                            )
                            if catalogo_recursos != row['Catálogo de recursos geográficos']:
                                registros_df.at[registros_df.index[
                                    indice_seleccionado], 'Catálogo de recursos geográficos'] = catalogo_recursos
                                edited = True

                                # Guardar y validar inmediatamente para detectar posibles cambios en fecha de oficio de cierre
                                registros_df = validar_reglas_negocio(registros_df)
                                exito, mensaje = guardar_datos_editados(registros_df)
                                if exito:
                                    st.success("Campo actualizado correctamente.")
                                    st.session_state.cambios_pendientes = False
                                    st.rerun()
                                else:
                                    st.error(f"Error al guardar cambios: {mensaje}")

                    # Oficios de cierre
                    if 'Oficios de cierre' in row:
                        with col2:
                            oficios_cierre = st.selectbox(
                                "Oficios de cierre",
                                options=["", "Si", "No"],
                                index=1 if row['Oficios de cierre'].upper() in ["SI", "SÍ", "YES", "Y"] else (
                                    2 if row['Oficios de cierre'].upper() == "NO" else 0),
                                key=f"oficios_cierre_{indice_seleccionado}",
                                on_change=on_change_callback
                            )
                            if oficios_cierre != row['Oficios de cierre']:
                                registros_df.at[
                                    registros_df.index[indice_seleccionado], 'Oficios de cierre'] = oficios_cierre
                                edited = True

                                # Guardar y validar inmediatamente para detectar posibles cambios en fecha de oficio de cierre
                                registros_df = validar_reglas_negocio(registros_df)
                                exito, mensaje = guardar_datos_editados(registros_df)
                                if exito:
                                    st.success("Campo actualizado correctamente.")
                                    st.session_state.cambios_pendientes = False
                                    st.rerun()
                                else:
                                    st.error(f"Error al guardar cambios: {mensaje}")

                    # Fecha de oficio de cierre
                    if 'Fecha de oficio de cierre' in row:
                        with col3:
                            fecha_oficio_dt = fecha_para_selector(row['Fecha de oficio de cierre'])
                            nueva_fecha_oficio = st.date_input(
                                "Fecha de oficio de cierre",
                                value=fecha_oficio_dt,
                                format="DD/MM/YYYY",
                                key=f"fecha_oficio_{indice_seleccionado}",
                                on_change=on_change_callback
                            )
                            nueva_fecha_oficio_str = fecha_desde_selector_a_string(
                                nueva_fecha_oficio) if nueva_fecha_oficio else ""

                            fecha_original = "" if pd.isna(row['Fecha de oficio de cierre']) else row[
                                'Fecha de oficio de cierre']

                            # Si se ha introducido una nueva fecha de oficio de cierre
                            if nueva_fecha_oficio_str and nueva_fecha_oficio_str != fecha_original:
                                # Validar los requisitos para oficio de cierre
                                valido, campos_incompletos = verificar_condiciones_oficio_cierre(row)

                                # Si hay campos incompletos, mostrar advertencia y no permitir el cambio
                                if not valido:
                                    st.error(
                                        "No es posible diligenciar la Fecha de oficio de cierre. Debe tener todos los campos Si/No en 'Si', todos los estándares completos, y todas las fechas diligenciadas y anteriores a la fecha de cierre.")
                                    # Mostrar los campos incompletos
                                    st.error(f"Campos incompletos: {', '.join(campos_incompletos)}")
                                    # NO actualizar el valor en el DataFrame para evitar validaciones recursivas
                                else:
                                    # Solo actualizar si se cumplen todas las condiciones
                                    registros_df.at[registros_df.index[
                                        indice_seleccionado], 'Fecha de oficio de cierre'] = nueva_fecha_oficio_str

                                    # Actualizar Estado a "Completado"
                                    registros_df.at[registros_df.index[indice_seleccionado], 'Estado'] = 'Completado'

                                    edited = True
                                    # Guardar cambios sin recargar la página inmediatamente
                                    registros_df = validar_reglas_negocio(registros_df)
                                    exito, mensaje = guardar_datos_editados(registros_df)
                                    if exito:
                                        st.success(
                                            "Fecha de oficio de cierre actualizada y Estado cambiado a 'Completado'.")
                                        st.session_state.cambios_pendientes = False

                                        # NO usar st.rerun() aquí para evitar la recursión infinita
                                        # En su lugar, mostrar un botón para refrescar manualmente
                                        st.button("Actualizar vista", key=f"actualizar_oficio_{indice_seleccionado}",
                                                  on_click=lambda: st.rerun())
                                    else:
                                        st.error(f"Error al guardar cambios: {mensaje}")

                            # Si se está borrando la fecha
                            elif nueva_fecha_oficio_str != fecha_original:
                                # Permitir borrar la fecha y actualizar Estado a "En proceso"
                                registros_df.at[registros_df.index[
                                    indice_seleccionado], 'Fecha de oficio de cierre'] = nueva_fecha_oficio_str

                                # Si se borra la fecha de oficio, cambiar estado a "En proceso"
                                if registros_df.at[registros_df.index[indice_seleccionado], 'Estado'] == 'Completado':
                                    registros_df.at[registros_df.index[indice_seleccionado], 'Estado'] = 'En proceso'
                                    st.info(
                                        "El estado ha sido cambiado a 'En proceso' porque se eliminó la fecha de oficio de cierre.")

                                edited = True
                                # Guardar cambios sin recargar la página inmediatamente
                                registros_df = validar_reglas_negocio(registros_df)
                                exito, mensaje = guardar_datos_editados(registros_df)
                                if exito:
                                    st.success("Fecha de oficio de cierre actualizada correctamente.")
                                    st.session_state.cambios_pendientes = False

                                    # NO usar st.rerun() aquí para evitar la recursión infinita
                                    # En su lugar, mostrar un botón para refrescar manualmente
                                    st.button("Actualizar vista", key=f"actualizar_oficio_borrar_{indice_seleccionado}",
                                              on_click=lambda: st.rerun())
                                else:
                                    st.error(f"Error al guardar cambios: {mensaje}")

                # SECCIÓN 6: ESTADO Y OBSERVACIONES
                st.markdown("### 6. Estado y Observaciones")
                col1, col2 = st.columns(2)

                # Estado general
                if 'Estado' in row:
                    with col1:
                        # Verificar primero si hay fecha de oficio de cierre válida
                        tiene_fecha_oficio = (
                                'Fecha de oficio de cierre' in row and
                                pd.notna(row['Fecha de oficio de cierre']) and
                                row['Fecha de oficio de cierre'] != ""
                        )

                        # Si no hay fecha de oficio, no se debe permitir estado Completado
                        opciones_estado = ["", "En proceso", "En proceso oficio de cierre", "Finalizado"]
                        if tiene_fecha_oficio:
                            opciones_estado = ["", "En proceso", "En proceso oficio de cierre", "Completado",
                                               "Finalizado"]

                        # Determinar el índice actual del estado
                        indice_estado = 0
                        if row['Estado'] in opciones_estado:
                            indice_estado = opciones_estado.index(row['Estado'])

                        # Crear el selector de estado
                        nuevo_estado = st.selectbox(
                            "Estado",
                            options=opciones_estado,
                            index=indice_estado,
                            key=f"estado_{indice_seleccionado}",
                            on_change=on_change_callback
                        )

                        # Si intenta seleccionar Completado sin fecha de oficio, mostrar mensaje
                        if nuevo_estado == "Completado" and not tiene_fecha_oficio:
                            st.error(
                                "No es posible establecer el estado como 'Completado' sin una fecha de oficio de cierre válida.")
                            # No permitir el cambio, mantener el estado original
                            nuevo_estado = row['Estado']

                        # Actualizar el estado si ha cambiado
                        if nuevo_estado != row['Estado']:
                            registros_df.at[registros_df.index[indice_seleccionado], 'Estado'] = nuevo_estado
                            edited = True

                            # Guardar y validar inmediatamente sin recargar la página
                            registros_df = validar_reglas_negocio(registros_df)
                            exito, mensaje = guardar_datos_editados(registros_df)
                            if exito:
                                st.success("Estado actualizado correctamente.")
                                st.session_state.cambios_pendientes = False
                                # Mostrar botón para actualizar manualmente en lugar de recargar automáticamente
                                st.button("Actualizar vista", key=f"actualizar_estado_{indice_seleccionado}",
                                          on_click=lambda: st.rerun())
                            else:
                                st.error(f"Error al guardar cambios: {mensaje}")
                # Observaciones
                if 'Observación' in row:
                    with col2:
                        nueva_observacion = st.text_area(
                            "Observación",
                            value=row['Observación'] if pd.notna(row['Observación']) else "",
                            key=f"observacion_{indice_seleccionado}",
                            on_change=on_change_callback
                        )
                        if nueva_observacion != row['Observación']:
                            registros_df.at[registros_df.index[indice_seleccionado], 'Observación'] = nueva_observacion
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

    # ✅ Crear gráfico de registros completados por fecha (corregido)
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


# Función para exportar resultados
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

    # Agregar explicación
    st.markdown("""
    <div class="info-box">
    <p><strong>Información sobre la Exportación</strong></p>
    <p>Los archivos exportados incluyen solo los registros que coinciden con los filtros seleccionados. Puede utilizar estos archivos para análisis adicionales o para compartir información.</p>
    </div>
    """, unsafe_allow_html=True)


# Función para mostrar la sección de diagnóstico
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


# Función para mostrar la sección de ayuda
def mostrar_ayuda():
    """Muestra la sección de ayuda con información sobre el uso del tablero."""
    with st.expander("Ayuda"):
        st.markdown("### Ayuda del Tablero de Control")
        st.markdown("""
        Este tablero de control permite visualizar y gestionar el seguimiento de cronogramas. A continuación se describen las principales funcionalidades:

        #### Navegación
        - **Dashboard**: Muestra métricas generales, comparación con metas y diagrama de Gantt.
        - **Datos Completos**: Permite ver y editar todos los registros.

        #### Filtros
        Puede filtrar los datos por:
        - **Entidad**: Seleccione una entidad específica o "Todas" para ver todas las entidades.
        - **Funcionario**: Seleccione un funcionario específico o "Todos" para ver todos los funcionarios.
        - **Nivel de Información**: Seleccione un nivel específico o "Todos" para ver todos los registros.

        #### Edición de Datos
        En la pestaña "Datos Completos", puede editar los registros de dos formas:
        1. **Vista de Tabla Completa**: Ver todos los registros en formato de tabla.
        2. **Edición de Registros**: Editar campos específicos de cada registro por separado.

        Los cambios se guardan automáticamente al hacer modificaciones y aplicar las validaciones correspondientes.

        #### Exportación
        Puede exportar los datos filtrados en formato CSV o Excel usando los botones en la sección "Exportar Resultados".

        #### Soporte
        Para cualquier consulta o soporte, contacte al administrador del sistema.
        """)


# Función para mostrar mensajes de error
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

        # Si deseas ver las columnas cargadas (útil para depuración)
        #if st.checkbox("Mostrar columnas cargadas", value=False):
        #    st.write("Columnas en registros_df:", list(registros_df.columns))

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

        # Filtro por funcionario
        funcionarios = ['Todos']
        if 'Funcionario' in registros_df.columns:
            funcionarios += sorted(registros_df['Funcionario'].dropna().unique().tolist())
        funcionario_seleccionado = st.sidebar.selectbox('Funcionario', funcionarios)

        # Filtro por nivel de información
        niveles_info = ['Todos']
        if 'Nivel Información ' in registros_df.columns:  # Nota: incluye un espacio al final
            niveles_info += sorted(registros_df['Nivel Información '].dropna().unique().tolist())
        nivel_info_seleccionado = st.sidebar.selectbox('Nivel de Información', niveles_info)

        # Aplicar filtros
        df_filtrado = registros_df.copy()

        if entidad_seleccionada != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Entidad'] == entidad_seleccionada]

        if funcionario_seleccionado != 'Todos' and 'Funcionario' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Funcionario'] == funcionario_seleccionado]

        if nivel_info_seleccionado != 'Todos' and 'Nivel Información ' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Nivel Información '] == nivel_info_seleccionado]

        # Crear pestañas
        tab1, tab2 = st.tabs(["Dashboard", "Datos Completos"])

        with tab1:
            mostrar_dashboard(df_filtrado, metas_nuevas_df, metas_actualizar_df, registros_df)

        with tab2:
            registros_df = mostrar_datos_completos_interactivo(registros_df)

        # Sección para exportar resultados
        mostrar_exportar_resultados(df_filtrado)

        # Agregar sección de diagnóstico
        mostrar_diagnostico(registros_df, meta_df, metas_nuevas_df, metas_actualizar_df, df_filtrado)

        # Agregar sección de ayuda
        mostrar_ayuda()

    except Exception as e:
        mostrar_error(e)


if __name__ == "__main__":
    main()