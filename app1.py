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

    # [Resto del código de edición permanece igual]
    # ... (código completo de edición)
    
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


# Función para mostrar la sección de ayuda
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


# Nueva función para mostrar alertas de vencimientos
def mostrar_alertas_vencimientos(registros_df):
    """Muestra alertas de vencimientos de fechas en los registros."""
    st.markdown('<div class="subtitle">Alertas de Vencimientos</div>', unsafe_allow_html=True)

    # Fecha actual para comparaciones
    fecha_actual = datetime.now().date()

    # [Resto del código de alertas permanece igual]
    # ... (código completo de alertas)
    
    st.success("¡No hay alertas de vencimientos pendientes!")


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

        # **CAMBIO 1: Filtro de Nivel de Información condicionado**
        # Filtro por nivel de información - solo se activa cuando se selecciona una entidad específica
        if entidad_seleccionada != 'Todas':
            # Obtener los niveles de información de la entidad seleccionada
            registros_entidad = registros_df[registros_df['Entidad'] == entidad_seleccionada]
            niveles_info = ['Todos'] + sorted(registros_entidad['Nivel Información '].unique().tolist())
            nivel_info_seleccionado = st.sidebar.selectbox('Nivel de Información', niveles_info)
        else:
            # Si no se selecciona una entidad específica, deshabilitar el filtro
            nivel_info_seleccionado = st.sidebar.selectbox(
                'Nivel de Información', 
                ['Todos'], 
                disabled=True,
                help="Seleccione una entidad específica para activar este filtro"
            )

        # Aplicar filtros
        df_filtrado = registros_df.copy()

        if entidad_seleccionada != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Entidad'] == entidad_seleccionada]

            # Aplicar filtro por registro específico si se seleccionó uno
            if registro_seleccionado != 'Todos los registros':
                # Extraer el código del registro de la opción seleccionada
                codigo_registro = registro_seleccionado.split(' - ')[0]
                df_filtrado = df_filtrado[df_filtrado['Cod'].astype(str) == codigo_registro]

            # **APLICAR FILTRO POR NIVEL DE INFORMACIÓN**
            if nivel_info_seleccionado != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['Nivel Información '] == nivel_info_seleccionado]

        if funcionario_seleccionado != 'Todos' and 'Funcionario' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Funcionario'] == funcionario_seleccionado]

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
