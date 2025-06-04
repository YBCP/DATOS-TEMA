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
    contar_registros_completados_por_fecha, limpiar_valor
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

    except Exception as e:
        st.error(f"Error al editar el registro: {e}")

    return registros_df


def mostrar_alertas_vencimientos(registros_df):
    """Muestra alertas de vencimientos de fechas en los registros."""
    st.markdown('<div class="subtitle">Alertas de Vencimientos</div>', unsafe_allow_html=True)

    # Fecha actual para comparaciones
    fecha_actual = datetime.now().date()

    st.info("Funcionalidad de alertas de vencimientos - Aquí se mostrarían las alertas de fechas próximas a vencer o vencidas.")


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

        # Verificar si los DataFrames están vacíos
        if registros_df.empty:
            st.error("No se pudieron cargar datos de registros.")
            return

        # Mostrar el número de registros cargados
        st.success(f"Se han cargado {len(registros_df)} registros de la base de datos.")

        # Aplicar validaciones y actualizaciones
        registros_df = validar_reglas_negocio(registros_df)
        registros_df = actualizar_plazo_analisis(registros_df)
        registros_df = actualizar_plazo_cronograma(registros_df)
        registros_df = actualizar_plazo_oficio_cierre(registros_df)

        # Procesar las metas
        metas_nuevas_df, metas_actualizar_df = procesar_metas(meta_df)

        # Agregar columnas calculadas
        registros_df['Porcentaje Avance'] = registros_df.apply(calcular_porcentaje_avance, axis=1)
        registros_df['Estado Fechas'] = registros_df.apply(verificar_estado_fechas, axis=1)

        # FILTROS EN LA BARRA LATERAL
        st.sidebar.markdown('<div class="subtitle">Filtros</div>', unsafe_allow_html=True)

        # Filtro por entidad
        entidades = ['Todas'] + sorted(registros_df['Entidad'].unique().tolist())
        entidad_seleccionada = st.sidebar.selectbox('Entidad', entidades)

        # Filtro por tipo de dato - NUEVA FUNCIONALIDAD
        tipos_dato = ['Todos'] + sorted(registros_df['TipoDato'].dropna().unique().tolist())
        tipo_dato_seleccionado = st.sidebar.selectbox('Tipo de Dato', tipos_dato)

        # Filtro por funcionario
        funcionarios = ['Todos']
        if 'Funcionario' in registros_df.columns:
            funcionarios += sorted(registros_df['Funcionario'].dropna().unique().tolist())
        funcionario_seleccionado = st.sidebar.selectbox('Funcionario', funcionarios)

        # GESTIÓN DE ARCHIVOS EXCEL - NUEVA FUNCIONALIDAD
        st.sidebar.markdown('<div class="subtitle">Gestión de Archivos</div>', unsafe_allow_html=True)

        # Botón para descargar formato Excel
        if st.sidebar.button("📥 Descargar Formato Excel"):
            # Crear un DataFrame con las columnas necesarias pero sin datos (solo encabezados)
            columnas_formato = [
                'Cod', 'Funcionario', 'Entidad', 'Nivel Información ', 'Frecuencia actualizacion ', 'TipoDato',
                'Actas de acercamiento y manifestación de interés', 'Suscripción acuerdo de compromiso',
                'Entrega acuerdo de compromiso', 'Acuerdo de compromiso', 
                'Gestion acceso a los datos y documentos requeridos ', 'Análisis de información',
                'Cronograma Concertado', 'Análisis y cronograma (fecha programada)',
                'Fecha de entrega de información', 'Plazo de análisis', 'Análisis y cronograma',
                'Seguimiento a los acuerdos', 'Registro', 'ET', 'CO', 'DD', 'REC', 'SERVICIO',
                'Registro (completo)', 'ET (completo)', 'CO (completo)', 'DD (completo)', 
                'REC (completo)', 'SERVICIO (completo)', 'Estándares (fecha programada)', 'Estándares',
                'Resultados de orientación técnica', 'Verificación del servicio web geográfico',
                'Verificar Aprobar Resultados', 'Revisar y validar los datos cargados en la base de datos',
                'Aprobación resultados obtenidos en la rientación', 'Disponer datos temáticos',
                'Fecha de publicación programada', 'Publicación', 'Catálogo de recursos geográficos',
                'Oficios de cierre', 'Plazo de oficio de cierre', 'Fecha de oficio de cierre',
                'Estado', 'Observación'
            ]
            
            # Crear DataFrame vacío con las columnas
            df_formato = pd.DataFrame(columns=columnas_formato)
            
            # Agregar una fila de ejemplo
            ejemplo = {
                'Cod': '1',
                'Funcionario': 'Nombre del Funcionario',
                'Entidad': 'Nombre de la Entidad',
                'Nivel Información ': 'Descripción del nivel de información',
                'Frecuencia actualizacion ': 'Anual/Mensual/Trimestral/Semestral',
                'TipoDato': 'Nuevo/Actualizar',
                'Acuerdo de compromiso': 'Si/No',
                'Fecha de entrega de información': 'DD/MM/AAAA',
                'Análisis y cronograma': 'DD/MM/AAAA',
                'Estándares': 'DD/MM/AAAA',
                'Publicación': 'DD/MM/AAAA',
                'Estado': 'En proceso/Completado/Finalizado'
            }
            
            # Llenar solo algunas columnas clave con ejemplos
            for col in df_formato.columns:
                if col in ejemplo:
                    df_formato.loc[0, col] = ejemplo[col]
                else:
                    df_formato.loc[0, col] = ''
            
            # Crear archivo Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Hoja con formato
                df_formato.to_excel(writer, sheet_name='Formato_Registros', index=False)
                
                # Hoja con instrucciones
                instrucciones = pd.DataFrame({
                    'INSTRUCCIONES PARA LLENAR EL FORMATO': [
                        '1. Elimine la fila de ejemplo antes de ingresar sus datos',
                        '2. Llene cada columna según el tipo de dato indicado:',
                        '   - DD/MM/AAAA: Formato de fecha día/mes/año',
                        '   - Si/No: Escriba exactamente "Si" o "No"',
                        '   - Sin iniciar/En proceso/Completo: Estados de estándares',
                        '3. Los campos marcados como (automático) se calculan automáticamente',
                        '4. Asegúrese de que el código (Cod) sea único para cada registro',
                        '5. Guarde el archivo como .xlsx antes de cargarlo',
                        '',
                        'VALIDACIONES IMPORTANTES:',
                        '- Para introducir fecha en Estándares, todos los campos (completo) deben estar "Completo"',
                        '- Para introducir fecha en Publicación, "Disponer datos temáticos" debe ser "Si"',
                        '- Para introducir fecha en "Fecha de oficio de cierre", todos los requisitos deben cumplirse'
                    ]
                })
                
                instrucciones.to_excel(writer, sheet_name='Instrucciones', index=False)
            
            excel_data = output.getvalue()
            st.sidebar.download_button(
                label="📥 Descargar Formato",
                data=excel_data,
                file_name="formato_registros.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Descarga un archivo Excel con el formato para cargar nuevos registros"
            )

        # Cargar archivo Excel
        st.sidebar.markdown("### Cargar Archivo Excel")
        uploaded_file = st.sidebar.file_uploader(
            "Seleccione archivo Excel con registros",
            type=['xlsx', 'xls'],
            help="Cargue un archivo Excel con el formato descargado anteriormente"
        )

        if uploaded_file is not None:
            try:
                # Leer el archivo Excel
                df_cargado = pd.read_excel(uploaded_file, sheet_name=0)
                
                # Mostrar información del archivo cargado
                st.sidebar.success(f"Archivo cargado: {len(df_cargado)} registros encontrados")
                
                # Verificar columnas mínimas
                columnas_minimas = ['Cod', 'Entidad', 'TipoDato', 'Nivel Información ']
                columnas_faltantes = [col for col in columnas_minimas if col not in df_cargado.columns]
                
                if columnas_faltantes:
                    st.sidebar.error(f"Faltan columnas requeridas: {', '.join(columnas_faltantes)}")
                else:
                    col1, col2 = st.sidebar.columns(2)
                    
                    with col1:
                        if st.button("📊 Vista Previa", key="preview_excel"):
                            st.session_state.mostrar_preview = True
                    
                    with col2:
                        if st.button("💾 Cargar Datos", key="load_excel"):
                            try:
                                # Procesar y cargar los datos
                                df_procesado = df_cargado.copy()
                                
                                # Limpiar valores
                                for col in df_procesado.columns:
                                    df_procesado[col] = df_procesado[col].apply(limpiar_valor)
                                
                                # Asegurar columnas requeridas
                                for columna in columnas_requeridas:
                                    if columna not in df_procesado.columns:
                                        df_procesado[columna] = ''
                                
                                # Aplicar validaciones
                                df_procesado = validar_reglas_negocio(df_procesado)
                                df_procesado = actualizar_plazo_analisis(df_procesado)
                                df_procesado = actualizar_plazo_cronograma(df_procesado)
                                df_procesado = actualizar_plazo_oficio_cierre(df_procesado)
                                
                                # Guardar datos
                                exito, mensaje = guardar_datos_editados(df_procesado, 'registros.csv')
                                
                                if exito:
                                    st.sidebar.success("✅ Datos cargados exitosamente")
                                    st.sidebar.info("La página se recargará para mostrar los nuevos datos")
                                    st.rerun()
                                else:
                                    st.sidebar.error(f"❌ Error al guardar: {mensaje}")
                                    
                            except Exception as e:
                                st.sidebar.error(f"❌ Error al procesar archivo: {str(e)}")
                
                # Mostrar vista previa si se solicitó
                if hasattr(st.session_state, 'mostrar_preview') and st.session_state.mostrar_preview:
                    st.markdown("### Vista Previa del Archivo Cargado")
                    st.dataframe(df_cargado.head(10))
                    st.info(f"Mostrando las primeras 10 filas de {len(df_cargado)} registros totales")
                    
                    if st.button("Cerrar Vista Previa"):
                        st.session_state.mostrar_preview = False
                        st.rerun()
                        
            except Exception as e:
                st.sidebar.error(f"❌ Error al leer archivo: {str(e)}")

        # Agregar información sobre formatos soportados
        st.sidebar.markdown("""
        <div class="info-box">
        <p><strong>Formatos Soportados</strong></p>
        <p>• Excel (.xlsx, .xls)<br>
        • Formato de fechas: DD/MM/AAAA<br>
        • Campos Si/No: Escribir exactamente "Si" o "No"</p>
        </div>
        """, unsafe_allow_html=True)

        # APLICAR FILTROS
        df_filtrado = registros_df.copy()

        if entidad_seleccionada != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Entidad'] == entidad_seleccionada]

        # Aplicar filtro por tipo de dato - NUEVA FUNCIONALIDAD
        if tipo_dato_seleccionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['TipoDato'].str.upper() == tipo_dato_seleccionado.upper()]

        if funcionario_seleccionado != 'Todos' and 'Funcionario' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Funcionario'] == funcionario_seleccionado]

        # Mostrar validaciones
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

        # CREAR PESTAÑAS
        tab1, tab2, tab3 = st.tabs(["Dashboard", "Edición de Registros", "Alertas de Vencimientos"])

        with tab1:
            mostrar_dashboard(df_filtrado, metas_nuevas_df, metas_actualizar_df, registros_df)

        with tab2:
            registros_df = mostrar_edicion_registros(registros_df)

        with tab3:
            mostrar_alertas_vencimientos(registros_df)

    except Exception as e:
        st.error(f"Error al cargar o procesar los datos: {e}")
        st.info("""
        Por favor, verifique lo siguiente:
        1. Los archivos CSV están correctamente formateados.
        2. Las columnas requeridas están presentes en los archivos.
        3. Los valores de fecha tienen el formato correcto (DD/MM/AAAA).

        Si el problema persiste, contacte al administrador del sistema.
        """)


if __name__ == "__main__":
    main()
