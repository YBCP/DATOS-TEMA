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

# ===== FUNCIONES DE AUTENTICACIÓN =====
def verificar_admin():
    """
    Verifica si el usuario está autenticado como administrador.
    Retorna True si está autenticado, False si no.
    """
    # Inicializar estado de autenticación si no existe
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    return st.session_state.admin_authenticated


def mostrar_login_admin():
    """
    Muestra el formulario de login para admin y maneja la autenticación.
    """
    st.sidebar.markdown("**🔐 Acceso Administrador**")
    st.sidebar.markdown("*Requerido para gestión de datos*")
    
    # Formulario de contraseña
    password = st.sidebar.text_input(
        "Contraseña de administrador:",
        type="password",
        key="admin_password",
        help="Ingrese la contraseña de administrador"
    )
    
    if st.sidebar.button("🔓 Acceder", key="login_btn", use_container_width=True):
        if password == "qwerty":
            st.session_state.admin_authenticated = True
            st.sidebar.success("✅ Acceso concedido")
            st.rerun()
        else:
            st.sidebar.error("❌ Contraseña incorrecta")


def mostrar_gestion_datos_admin(registros_df):
    """
    Muestra la sección de gestión de datos Excel solo para administradores autenticados.
    """
    st.sidebar.markdown("**📊 Gestión de Datos - ADMIN**")
    st.sidebar.success("🔓 Acceso autorizado")
    
    # Descargar template Excel
    st.sidebar.markdown("**📥 Descargar Template**")
    
    # Crear archivo Excel con todos los datos actuales como template
    output_template = io.BytesIO()
    with pd.ExcelWriter(output_template, engine='openpyxl') as writer:
        # Hoja principal con todos los registros
        registros_df.to_excel(writer, sheet_name='Registros', index=False)
        
        # Hoja con ejemplo de estructura (solo las primeras 3 filas como ejemplo)
        if len(registros_df) > 0:
            ejemplo_df = registros_df.head(3).copy()
            # Limpiar las fechas del ejemplo para que sea un template limpio
            columnas_fecha = [
                'Suscripción acuerdo de compromiso', 'Entrega acuerdo de compromiso',
                'Fecha de entrega de información', 'Plazo de análisis', 'Plazo de cronograma',
                'Análisis y cronograma', 'Estándares (fecha programada)', 'Estándares',
                'Fecha de publicación programada', 'Publicación',
                'Plazo de oficio de cierre', 'Fecha de oficio de cierre'
            ]
            for col in columnas_fecha:
                if col in ejemplo_df.columns:
                    ejemplo_df[col] = ""
            
            ejemplo_df.to_excel(writer, sheet_name='Template_Ejemplo', index=False)
        
        # Hoja de instrucciones
        instrucciones = pd.DataFrame({
            'INSTRUCCIONES PARA USO DEL TEMPLATE': [
                '1. Use la hoja "Registros" para editar todos los datos',
                '2. NO modifique la estructura de columnas',
                '3. Fechas deben estar en formato DD/MM/AAAA',
                '4. Campos Si/No: use "Si" o "No" exactamente',
                '5. Estándares (completo): use "Sin iniciar", "En proceso" o "Completo"',
                '6. NO modifique la columna "Cod" (código único)',
                '7. Guarde el archivo y súbalo usando el botón "Cargar Datos"',
                '',
                'CAMPOS CALCULADOS AUTOMÁTICAMENTE:',
                '- Plazo de análisis (5 días hábiles después de entrega info)',
                '- Plazo de cronograma (3 días hábiles después de plazo análisis)',
                '- Plazo de oficio de cierre (7 días hábiles después de publicación)',
                '',
                'VALIDACIONES AUTOMÁTICAS:',
                '- Acuerdo compromiso = Si (si hay fecha entrega acuerdo)',
                '- Análisis información = Si (si hay fecha análisis)',
                '- Estado = Completado (si hay fecha oficio cierre)',
                '- Las fechas de estándares requieren todos los campos "completo"',
                '- Las fechas de publicación requieren "Disponer datos" = Si'
            ]
        })
        instrucciones.to_excel(writer, sheet_name='INSTRUCCIONES', index=False)

    excel_template_data = output_template.getvalue()
    
    st.sidebar.download_button(
        label="📊 Descargar Template Excel",
        data=excel_template_data,
        file_name=f"template_cronogramas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Descarga todos los datos actuales en formato Excel para edición",
        use_container_width=True
    )
    
    # Cargar datos desde Excel
    st.sidebar.markdown("**📤 Cargar Datos Editados**")
    
    uploaded_file = st.sidebar.file_uploader(
        "Seleccionar archivo Excel editado",
        type=['xlsx', 'xls'],
        help="Suba el archivo Excel con los datos editados"
    )
    
    if uploaded_file is not None:
        try:
            # Leer el archivo Excel cargado
            df_cargado = pd.read_excel(uploaded_file, sheet_name='Registros')
            
            # Mostrar información del archivo cargado
            st.sidebar.success(f"✅ Archivo cargado: {len(df_cargado)} registros")
            
            # Botón para confirmar la actualización - ARREGLANDO BLOQUEO
            if st.sidebar.button("🔄 Actualizar Datos", type="primary", use_container_width=True):
                try:
                    # Validar que el archivo tenga las columnas necesarias
                    columnas_requeridas = ['Cod', 'Entidad', 'TipoDato', 'Nivel Información ']
                    columnas_faltantes = [col for col in columnas_requeridas if col not in df_cargado.columns]
                    
                    if columnas_faltantes:
                        st.sidebar.error(f"❌ Columnas faltantes: {', '.join(columnas_faltantes)}")
                    else:
                        # Usar la función auxiliar para guardar con todas las validaciones
                        exito, df_cargado = guardar_datos_con_validacion(
                            df_cargado, 
                            "Datos cargados desde Excel y guardados correctamente", 
                            False
                        )
                        
                        if exito:
                            st.sidebar.success("✅ Datos actualizados correctamente desde Excel")
                            st.sidebar.info("🔄 **Por favor, recargue manualmente la página para ver los cambios**")
                            # ELIMINADO: Botón automático que causaba bloqueo
                        else:
                            st.sidebar.error("❌ Error al guardar los datos cargados")
                            
                except Exception as e:
                    st.sidebar.error(f"❌ Error al procesar archivo: {str(e)}")
                    
        except Exception as e:
            st.sidebar.error(f"❌ Error al leer archivo: {str(e)}")
            st.sidebar.info("Verifique que el archivo tenga la hoja 'Registros' y esté bien formateado")
    
    # Botón para cerrar sesión de admin
    if st.sidebar.button("🚪 Cerrar Sesión Admin", use_container_width=True):
        st.session_state.admin_authenticated = False
        st.sidebar.success("✅ Sesión de administrador cerrada")
        st.rerun()


# ===== FUNCIONES AUXILIARES =====
def guardar_datos_con_validacion(registros_df, mensaje_exito="Datos guardados correctamente", mostrar_mensaje=True):
    """
    Función auxiliar que garantiza el guardado de datos con validaciones completas.
    Aplica todas las reglas de negocio y actualiza plazos antes de guardar.
    """
    try:
        # VERIFICACIÓN ADICIONAL DEL GUARDADO CSV
        if mostrar_mensaje:
            st.info("🔄 Procesando y validando datos...")
        
        # Aplicar validaciones de reglas de negocio
        registros_df = validar_reglas_negocio(registros_df)
        
        # Actualizar todos los plazos automáticamente
        registros_df = actualizar_plazo_analisis(registros_df)
        registros_df = actualizar_plazo_cronograma(registros_df)
        registros_df = actualizar_plazo_oficio_cierre(registros_df)
        
        # Recalcular porcentajes y estados
        registros_df['Porcentaje Avance'] = registros_df.apply(calcular_porcentaje_avance, axis=1)
        registros_df['Estado Fechas'] = registros_df.apply(verificar_estado_fechas, axis=1)
        
        if mostrar_mensaje:
            st.info("💾 Guardando en archivo CSV...")
        
        # Guardar en archivo CSV con verificación adicional
        exito, mensaje = guardar_datos_editados(registros_df)
        
        # VERIFICACIÓN ADICIONAL: Intentar leer el archivo para confirmar que se guardó
        if exito:
            try:
                import os
                if os.path.exists('registros.csv'):
                    # Leer archivo para verificar que se guardó correctamente
                    df_verificacion = pd.read_csv('registros.csv', sep=';', dtype=str)
                    if len(df_verificacion) == len(registros_df):
                        if mostrar_mensaje:
                            st.success(f"✅ {mensaje_exito} | Registros: {len(df_verificacion)}")
                        return True, registros_df
                    else:
                        if mostrar_mensaje:
                            st.warning(f"⚠️ Posible problema en guardado: registros esperados {len(registros_df)}, guardados {len(df_verificacion)}")
                        return True, registros_df  # Aún considerarlo exitoso
                else:
                    if mostrar_mensaje:
                        st.warning("⚠️ Archivo CSV no encontrado después del guardado")
                    return False, registros_df
            except Exception as e:
                if mostrar_mensaje:
                    st.warning(f"⚠️ No se pudo verificar el guardado: {str(e)}")
                return True, registros_df  # Asumir que funcionó si llegó hasta aquí
        else:
            if mostrar_mensaje:
                st.error(f"❌ Error al guardar: {mensaje}")
            return False, registros_df
            
    except Exception as e:
        if mostrar_mensaje:
            st.error(f"❌ Error crítico al guardar datos: {str(e)}")
        return False, registros_df


# Función auxiliar para guardar datos de forma consistente
def guardar_datos_con_validacion(registros_df, mensaje_exito="Datos guardados correctamente", mostrar_mensaje=True):
    """
    Función auxiliar que garantiza el guardado de datos con validaciones completas.
    Aplica todas las reglas de negocio y actualiza plazos antes de guardar.
    """
    try:
        # Aplicar validaciones de reglas de negocio
        registros_df = validar_reglas_negocio(registros_df)

        # Asegurar que siempre se guarden los datos con las validaciones aplicadas
        exito, registros_df = guardar_datos_con_validacion(
            registros_df, 
            "Validaciones de reglas de negocio aplicadas", 
            False
        )
        
        # Actualizar todos los plazos automáticamente
        registros_df = actualizar_plazo_analisis(registros_df)
        registros_df = actualizar_plazo_cronograma(registros_df)
        registros_df = actualizar_plazo_oficio_cierre(registros_df)
        
        # Recalcular porcentajes y estados
        registros_df['Porcentaje Avance'] = registros_df.apply(calcular_porcentaje_avance, axis=1)
        registros_df['Estado Fechas'] = registros_df.apply(verificar_estado_fechas, axis=1)
        
        # Guardar en archivo CSV
        exito, mensaje = guardar_datos_editados(registros_df)
        
        if exito:
            if mostrar_mensaje:
                st.success(f"✅ {mensaje_exito}")
            return True, registros_df
        else:
            if mostrar_mensaje:
                st.error(f"❌ Error al guardar: {mensaje}")
            return False, registros_df
            
    except Exception as e:
        if mostrar_mensaje:
            st.error(f"❌ Error crítico al guardar datos: {str(e)}")
        return False, registros_df


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


def mostrar_dashboard(df_filtrado, metas_nuevas_df, metas_actualizar_df, registros_df, entidad_seleccionada, funcionario_seleccionado, tipo_dato_seleccionado, nivel_seleccionado):
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
        
        # Crear función de estilo personalizada para el gradiente
        def aplicar_gradiente_personalizado(df_style):
            def color_porcentaje(val):
                if pd.isna(val):
                    return ''
                val = float(val)
                if val >= 100:
                    return 'background-color: #22c55e; color: white; font-weight: bold'  # Verde para >= 100%
                elif val >= 80:
                    return f'background-color: #84cc16; color: white'  # Verde claro 80-99%
                elif val >= 60:
                    return f'background-color: #eab308; color: white'  # Amarillo 60-79%
                elif val >= 40:
                    return f'background-color: #f97316; color: white'  # Naranja 40-59%
                elif val >= 20:
                    return f'background-color: #f87171; color: white'  # Rojo claro 20-39%
                else:
                    return f'background-color: #dc2626; color: white; font-weight: bold'  # Rojo intenso 0-19%
            
            return df_style.applymap(color_porcentaje, subset=['Porcentaje'])
        
        st.dataframe(aplicar_gradiente_personalizado(
            comparacion_nuevos.style.format({'Porcentaje': '{:.2f}%'})
        ))

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
        
        # Aplicar el mismo gradiente personalizado
        st.dataframe(aplicar_gradiente_personalizado(
            comparacion_actualizar.style.format({'Porcentaje': '{:.2f}%'})
        ))

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

    # GANTT CONDICIONAL - Solo mostrar si hay filtros aplicados
    filtros_aplicados = (
        entidad_seleccionada != 'Todas' or 
        funcionario_seleccionado != 'Todos' or 
        tipo_dato_seleccionado != 'Todos' or 
        nivel_seleccionado != 'Todos'
    )
    
    if filtros_aplicados:
        # Crear el diagrama de Gantt solo si hay filtros
        fig_gantt = crear_gantt(df_filtrado)
        if fig_gantt is not None:
            st.plotly_chart(fig_gantt, use_container_width=True)
        else:
            st.warning("No hay datos suficientes para crear el diagrama de Gantt con los filtros seleccionados.")
    else:
        # Mostrar mensaje informativo si no hay filtros
        st.info("""
        📊 **Para mostrar el Diagrama de Gantt, seleccione al menos un filtro específico:**
        - Entidad (diferente a 'Todas')
        - Funcionario (diferente a 'Todos') 
        - Tipo de Dato (diferente a 'Todos')
        - Nivel de Información (diferente a 'Todos')
        
        💡 *Esto mejora el rendimiento y la legibilidad del cronograma.*
        """)

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
        def aplicar_gradiente_avance(df_style):
            def color_porcentaje_avance(val):
                if pd.isna(val):
                    return ''
                val = float(val)
                if val >= 100:
                    return 'background-color: #22c55e; color: white; font-weight: bold'  # Verde para >= 100%
                elif val >= 80:
                    return f'background-color: #84cc16; color: white'  # Verde claro 80-99%
                elif val >= 60:
                    return f'background-color: #eab308; color: white'  # Amarillo 60-79%
                elif val >= 40:
                    return f'background-color: #f97316; color: white'  # Naranja 40-59%
                elif val >= 20:
                    return f'background-color: #f87171; color: white'  # Rojo claro 20-39%
                else:
                    return f'background-color: #dc2626; color: white; font-weight: bold'  # Rojo intenso 0-19%
            
            return df_style.applymap(color_porcentaje_avance, subset=['Porcentaje Avance'])
        
        st.dataframe(
            aplicar_gradiente_avance(df_mostrar.style.format({'Porcentaje Avance': '{:.2f}%'}))
            .apply(highlight_estado_fechas, axis=1),
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
                    # Guardar cambio inmediatamente
                    exito, registros_df = guardar_datos_con_validacion(registros_df, "Tipo de dato actualizado", False)
                    if exito:
                        st.session_state.cambios_pendientes = False

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

                    # Guardar cambios inmediatamente con recálculo de plazos
                    exito, registros_df = guardar_datos_con_validacion(
                        registros_df, 
                        "Fecha de entrega actualizada y plazos recalculados correctamente", 
                        True
                    )
                    
                    if exito:
                        st.session_state.cambios_pendientes = False
                        # Mostrar los nuevos plazos calculados
                        nuevo_plazo_analisis = registros_df.iloc[indice_seleccionado].get('Plazo de análisis', "")
                        nuevo_plazo_cronograma = registros_df.iloc[indice_seleccionado].get('Plazo de cronograma', "")
                        st.info(f"📅 Plazo de análisis: {nuevo_plazo_analisis}")
                        st.info(f"📅 Plazo de cronograma: {nuevo_plazo_cronograma}")
                        # Recargar la vista para mostrar cambios
                        st.rerun()
                    else:
                        st.error("Error al guardar cambios")

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
                        exito, registros_df = guardar_datos_con_validacion(
                            registros_df, 
                            f"Campo '{nombre_campo}' actualizado a '{nuevo_valor}'", 
                            True
                        )
                        
                        if exito:
                            st.session_state.cambios_pendientes = False
                            # Actualizar la tabla completa
                            st.rerun()
                        else:
                            st.error("Error al guardar cambios")

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
                                    # ELIMINADO: Botón que causaba bloqueo
                                    st.info("🔄 Recargue manualmente la página para ver todos los cambios")
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
                                # ELIMINADO: Botón que causaba bloqueo
                                st.info("🔄 Recargue manualmente la página para ver todos los cambios")
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
                            # ELIMINADO: Botón que causaba bloqueo
                            st.info("🔄 Recargue manualmente la página para ver todos los cambios")
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

            # ELIMINADO: Botón "Actualizar Vista" que causaba bloqueos

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
    def aplicar_gradiente_hitos(df_style):
        def color_porcentaje_hito(val):
            if pd.isna(val):
                return ''
            val = float(val)
            if val >= 100:
                return 'background-color: #22c55e; color: white; font-weight: bold'  # Verde para >= 100%
            elif val >= 80:
                return f'background-color: #84cc16; color: white'  # Verde claro 80-99%
            elif val >= 60:
                return f'background-color: #eab308; color: white'  # Amarillo 60-79%
            elif val >= 40:
                return f'background-color: #f97316; color: white'  # Naranja 40-59%
            elif val >= 20:
                return f'background-color: #f87171; color: white'  # Rojo claro 20-39%
            else:
                return f'background-color: #dc2626; color: white; font-weight: bold'  # Rojo intenso 0-19%
        
        return df_style.applymap(color_porcentaje_hito, subset=['Porcentaje'])
    
    st.dataframe(aplicar_gradiente_hitos(
        avance_hitos_df.style.format({'Porcentaje': '{:.2f}%'})
    ))

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

    # Eliminar el código duplicado de descarga de registros completos
    # ya que ahora está implementado en la función mostrar_dashboard

    st.markdown("""
    <div class="info-box">
    <p><strong>Información sobre la Exportación</strong></p>
    <p>Los archivos exportados incluyen solo los registros que coinciden con los filtros seleccionados. Para descargar todos los registros completos, utilice el botón correspondiente en la sección Dashboard.</p>
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
            def aplicar_gradiente_faltantes(df_style):
                def color_porcentaje_faltante(val):
                    if pd.isna(val):
                        return ''
                    val = float(val)
                    if val >= 80:
                        return 'background-color: #dc2626; color: white; font-weight: bold'  # Rojo intenso para muchos faltantes
                    elif val >= 60:
                        return f'background-color: #f87171; color: white'  # Rojo claro
                    elif val >= 40:
                        return f'background-color: #f97316; color: white'  # Naranja
                    elif val >= 20:
                        return f'background-color: #eab308; color: white'  # Amarillo
                    elif val > 0:
                        return f'background-color: #84cc16; color: white'  # Verde claro
                    else:
                        return f'background-color: #22c55e; color: white; font-weight: bold'  # Verde para 0% faltantes
                
                return df_style.applymap(color_porcentaje_faltante, subset=['Porcentaje'])
            
            st.dataframe(aplicar_gradiente_faltantes(
                df_faltantes.style.format({'Porcentaje': '{:.2f}%'})
            ))

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
# Función mostrar_alertas_vencimientos corregida para el error NaTType
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

    # Función para determinar si una fecha está próxima a vencer (dentro de 5 días hábiles)
    def es_proximo_vencimiento(fecha_limite):
        if not fecha_limite:
            return False

        # Convertir a objeto date si es datetime
        if isinstance(fecha_limite, datetime):
            fecha_limite = fecha_limite.date()

        # Si ya está vencido, no es "próximo a vencer"
        if fecha_limite < fecha_actual:
            return False

        # Calcular días hábiles hasta la fecha límite
        dias_habiles = calcular_dias_habiles(fecha_actual, fecha_limite)

        # Si está dentro de los próximos 5 días hábiles
        return dias_habiles is not None and 0 <= dias_habiles <= 5

    # Función para determinar si una fecha está vencida
    def es_vencido(fecha_limite):
        if not fecha_limite:
            return False

        # Convertir a objeto date si es datetime
        if isinstance(fecha_limite, datetime):
            fecha_limite = fecha_limite.date()

        return fecha_limite < fecha_actual

    # Función para calcular días de rezago
    def calcular_dias_rezago(fecha_limite):
        if not fecha_limite or not es_vencido(fecha_limite):
            return None

        # Convertir a objeto date si es datetime
        if isinstance(fecha_limite, datetime):
            fecha_limite = fecha_limite.date()

        return (fecha_actual - fecha_limite).days

    # Función para formatear fechas de manera segura
    def formatear_fecha_segura(fecha):
        if fecha is None or pd.isna(fecha):
            return ""
        try:
            return fecha.strftime('%d/%m/%Y')
        except:
            return ""

    # Preprocesar registros para el análisis
    registros_alertas = []

    for idx, row in registros_df.iterrows():
        try:
            # Procesar fechas (convertir de string a datetime) con manejo seguro de NaT
            fecha_entrega_acuerdo = procesar_fecha(row.get('Entrega acuerdo de compromiso', ''))
            fecha_entrega_info = procesar_fecha(row.get('Fecha de entrega de información', ''))
            fecha_plazo_cronograma = procesar_fecha(row.get('Plazo de cronograma', ''))
            fecha_analisis_cronograma = procesar_fecha(row.get('Análisis y cronograma', ''))
            fecha_estandares_prog = procesar_fecha(row.get('Estándares (fecha programada)', ''))
            fecha_estandares = procesar_fecha(row.get('Estándares', ''))
            fecha_publicacion_prog = procesar_fecha(row.get('Fecha de publicación programada', ''))
            fecha_publicacion = procesar_fecha(row.get('Publicación', ''))
            fecha_plazo_oficio_cierre = procesar_fecha(row.get('Plazo de oficio de cierre', ''))
            fecha_oficio_cierre = procesar_fecha(row.get('Fecha de oficio de cierre', ''))

            # Caso especial: Acuerdo de compromiso pendiente
            if fecha_entrega_acuerdo is not None and pd.notna(fecha_entrega_acuerdo) and (
                    fecha_entrega_info is None or pd.isna(fecha_entrega_info)):
                if es_vencido(fecha_entrega_acuerdo):
                    dias_rezago = calcular_dias_rezago(fecha_entrega_acuerdo)
                    registros_alertas.append({
                        'Cod': row['Cod'],
                        'Entidad': row['Entidad'],
                        'Nivel Información': row.get('Nivel Información ', ''),
                        'Funcionario': row.get('Funcionario', ''),
                        'Tipo Alerta': 'Acuerdo de compromiso',
                        'Fecha Programada': fecha_entrega_acuerdo,
                        'Fecha Real': None,
                        'Días Rezago': dias_rezago,
                        'Estado': 'Vencido',
                        'Descripción': f'Entrega de acuerdo vencida hace {dias_rezago} días sin fecha de entrega de información'
                    })

            # 1. Entrega de información
            if fecha_entrega_acuerdo is not None and pd.notna(fecha_entrega_acuerdo):
                if fecha_entrega_info is not None and pd.notna(fecha_entrega_info):
                    # Si hay fecha real, verificar si está con retraso
                    if fecha_entrega_info > fecha_entrega_acuerdo:
                        dias_rezago = calcular_dias_habiles(fecha_entrega_acuerdo, fecha_entrega_info)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Entrega de información',
                            'Fecha Programada': fecha_entrega_acuerdo,
                            'Fecha Real': fecha_entrega_info,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Completado con retraso',
                            'Descripción': f'Entrega de información con {dias_rezago} días hábiles de retraso'
                        })
                else:
                    # No hay fecha real, verificar si está vencido
                    if es_vencido(fecha_entrega_acuerdo):
                        dias_rezago = calcular_dias_rezago(fecha_entrega_acuerdo)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Entrega de información',
                            'Fecha Programada': fecha_entrega_acuerdo,
                            'Fecha Real': None,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Vencido',
                            'Descripción': f'Entrega de información vencida hace {dias_rezago} días'
                        })

            # 2. Análisis y cronograma
            if fecha_plazo_cronograma is not None and pd.notna(fecha_plazo_cronograma):
                if fecha_analisis_cronograma is not None and pd.notna(fecha_analisis_cronograma):
                    # Hay fecha real, verificar si está con retraso
                    if fecha_analisis_cronograma > fecha_plazo_cronograma:
                        dias_rezago = calcular_dias_habiles(fecha_plazo_cronograma, fecha_analisis_cronograma)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Análisis y cronograma',
                            'Fecha Programada': fecha_plazo_cronograma,
                            'Fecha Real': fecha_analisis_cronograma,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Completado con retraso',
                            'Descripción': f'Análisis realizado con {dias_rezago} días hábiles de retraso'
                        })
                else:
                    # No hay fecha real, verificar si está vencido o próximo
                    if es_vencido(fecha_plazo_cronograma):
                        dias_rezago = calcular_dias_rezago(fecha_plazo_cronograma)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Análisis y cronograma',
                            'Fecha Programada': fecha_plazo_cronograma,
                            'Fecha Real': None,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Vencido',
                            'Descripción': f'Plazo de cronograma vencido hace {dias_rezago} días sin fecha real'
                        })
                    elif es_proximo_vencimiento(fecha_plazo_cronograma):
                        dias_restantes = calcular_dias_habiles(fecha_actual, fecha_plazo_cronograma)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Análisis y cronograma',
                            'Fecha Programada': fecha_plazo_cronograma,
                            'Fecha Real': None,
                            'Días Rezago': -dias_restantes,  # Negativo indica días por vencer
                            'Estado': 'Próximo a vencer',
                            'Descripción': f'Plazo de cronograma vence en {dias_restantes} días hábiles'
                        })

            # 3. Estándares - mismo patrón de verificación mejorado
            if fecha_estandares_prog is not None and pd.notna(fecha_estandares_prog):
                if fecha_estandares is not None and pd.notna(fecha_estandares):
                    # Hay fecha real, verificar si está con retraso
                    if fecha_estandares > fecha_estandares_prog:
                        dias_rezago = calcular_dias_habiles(fecha_estandares_prog, fecha_estandares)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Estándares',
                            'Fecha Programada': fecha_estandares_prog,
                            'Fecha Real': fecha_estandares,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Completado con retraso',
                            'Descripción': f'Estándares completados con {dias_rezago} días hábiles de retraso'
                        })
                else:
                    # No hay fecha real, verificar si está vencido o próximo
                    if es_vencido(fecha_estandares_prog):
                        dias_rezago = calcular_dias_rezago(fecha_estandares_prog)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Estándares',
                            'Fecha Programada': fecha_estandares_prog,
                            'Fecha Real': None,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Vencido',
                            'Descripción': f'Plazo de estándares vencido hace {dias_rezago} días sin fecha real'
                        })
                    elif es_proximo_vencimiento(fecha_estandares_prog):
                        dias_restantes = calcular_dias_habiles(fecha_actual, fecha_estandares_prog)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Estándares',
                            'Fecha Programada': fecha_estandares_prog,
                            'Fecha Real': None,
                            'Días Rezago': -dias_restantes,
                            'Estado': 'Próximo a vencer',
                            'Descripción': f'Plazo de estándares vence en {dias_restantes} días hábiles'
                        })

            # 4. Publicación - mismo patrón de verificación mejorado
            if fecha_publicacion_prog is not None and pd.notna(fecha_publicacion_prog):
                if fecha_publicacion is not None and pd.notna(fecha_publicacion):
                    # Hay fecha real, verificar si está con retraso
                    if fecha_publicacion > fecha_publicacion_prog:
                        dias_rezago = calcular_dias_habiles(fecha_publicacion_prog, fecha_publicacion)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Publicación',
                            'Fecha Programada': fecha_publicacion_prog,
                            'Fecha Real': fecha_publicacion,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Completado con retraso',
                            'Descripción': f'Publicación realizada con {dias_rezago} días hábiles de retraso'
                        })
                else:
                    # No hay fecha real, verificar si está vencido o próximo
                    if es_vencido(fecha_publicacion_prog):
                        dias_rezago = calcular_dias_rezago(fecha_publicacion_prog)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Publicación',
                            'Fecha Programada': fecha_publicacion_prog,
                            'Fecha Real': None,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Vencido',
                            'Descripción': f'Plazo de publicación vencido hace {dias_rezago} días sin fecha real'
                        })
                    elif es_proximo_vencimiento(fecha_publicacion_prog):
                        dias_restantes = calcular_dias_habiles(fecha_actual, fecha_publicacion_prog)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Publicación',
                            'Fecha Programada': fecha_publicacion_prog,
                            'Fecha Real': None,
                            'Días Rezago': -dias_restantes,
                            'Estado': 'Próximo a vencer',
                            'Descripción': f'Plazo de publicación vence en {dias_restantes} días hábiles'
                        })

            # 5. Cierre - mismo patrón de verificación mejorado
            if fecha_plazo_oficio_cierre is not None and pd.notna(fecha_plazo_oficio_cierre):
                if fecha_oficio_cierre is not None and pd.notna(fecha_oficio_cierre):
                    # Hay fecha real, verificar si está con retraso
                    if fecha_oficio_cierre > fecha_plazo_oficio_cierre:
                        dias_rezago = calcular_dias_habiles(fecha_plazo_oficio_cierre, fecha_oficio_cierre)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Cierre',
                            'Fecha Programada': fecha_plazo_oficio_cierre,
                            'Fecha Real': fecha_oficio_cierre,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Completado con retraso',
                            'Descripción': f'Oficio de cierre realizado con {dias_rezago} días hábiles de retraso'
                        })
                else:
                    # No hay fecha real, verificar si está vencido o próximo
                    if es_vencido(fecha_plazo_oficio_cierre):
                        dias_rezago = calcular_dias_rezago(fecha_plazo_oficio_cierre)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Cierre',
                            'Fecha Programada': fecha_plazo_oficio_cierre,
                            'Fecha Real': None,
                            'Días Rezago': dias_rezago,
                            'Estado': 'Vencido',
                            'Descripción': f'Plazo de oficio de cierre vencido hace {dias_rezago} días sin fecha real'
                        })
                    elif es_proximo_vencimiento(fecha_plazo_oficio_cierre):
                        dias_restantes = calcular_dias_habiles(fecha_actual, fecha_plazo_oficio_cierre)
                        registros_alertas.append({
                            'Cod': row['Cod'],
                            'Entidad': row['Entidad'],
                            'Nivel Información': row.get('Nivel Información ', ''),
                            'Funcionario': row.get('Funcionario', ''),
                            'Tipo Alerta': 'Cierre',
                            'Fecha Programada': fecha_plazo_oficio_cierre,
                            'Fecha Real': None,
                            'Días Rezago': -dias_restantes,
                            'Estado': 'Próximo a vencer',
                            'Descripción': f'Plazo de oficio de cierre vence en {dias_restantes} días hábiles'
                        })
        except Exception as e:
            st.warning(f"Error procesando registro {row['Cod']}: {e}")
            continue

    # Crear DataFrame de alertas
    if registros_alertas:
        df_alertas = pd.DataFrame(registros_alertas)

        # Asegurarse de que las fechas se formateen correctamente
        for col in ['Fecha Programada', 'Fecha Real']:
            if col in df_alertas.columns:
                df_alertas[col] = df_alertas[col].apply(formatear_fecha_segura)

        # Aplicar colores según estado
        def highlight_estado(val):
            if val == 'Vencido':
                return 'background-color: #fee2e2; color: #b91c1c; font-weight: bold'  # Rojo claro
            elif val == 'Próximo a vencer':
                return 'background-color: #fef3c7; color: #b45309; font-weight: bold'  # Amarillo claro
            elif val == 'Completado con retraso':
                return 'background-color: #dbeafe; color: #1e40af'  # Azul claro
            return ''

        # Mostrar estadísticas de alertas
        st.markdown("### Resumen de Alertas")

        col1, col2, col3 = st.columns(3)

        with col1:
            num_vencidos = len(df_alertas[df_alertas['Estado'] == 'Vencido'])
            st.markdown(f"""
            <div class="metric-card" style="background-color: #fee2e2;">
                <p style="font-size: 1rem; color: #b91c1c;">Vencidos</p>
                <p style="font-size: 2.5rem; font-weight: bold; color: #b91c1c;">{num_vencidos}</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            num_proximos = len(df_alertas[df_alertas['Estado'] == 'Próximo a vencer'])
            st.markdown(f"""
            <div class="metric-card" style="background-color: #fef3c7;">
                <p style="font-size: 1rem; color: #b45309;">Próximos a vencer</p>
                <p style="font-size: 2.5rem; font-weight: bold; color: #b45309;">{num_proximos}</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            num_retrasados = len(df_alertas[df_alertas['Estado'] == 'Completado con retraso'])
            st.markdown(f"""
            <div class="metric-card" style="background-color: #dbeafe;">
                <p style="font-size: 1rem; color: #1e40af;">Completados con retraso</p>
                <p style="font-size: 2.5rem; font-weight: bold; color: #1e40af;">{num_retrasados}</p>
            </div>
            """, unsafe_allow_html=True)

        try:
            # Gráfico de alertas por tipo
            st.markdown("### Alertas por Tipo")

            alertas_por_tipo = df_alertas.groupby(['Tipo Alerta', 'Estado']).size().unstack(fill_value=0)

            # Asegurarse de que existan todas las columnas
            for estado in ['Vencido', 'Próximo a vencer', 'Completado con retraso']:
                if estado not in alertas_por_tipo.columns:
                    alertas_por_tipo[estado] = 0

            # Reordenar las columnas para mantener consistencia visual
            columnas_orden = ['Vencido', 'Próximo a vencer', 'Completado con retraso']
            columnas_disponibles = [col for col in columnas_orden if col in alertas_por_tipo.columns]

            fig = px.bar(
                alertas_por_tipo.reset_index(),
                x='Tipo Alerta',
                y=columnas_disponibles,
                barmode='group',
                title='Distribución de Alertas por Tipo y Estado',
                color_discrete_map={
                    'Vencido': '#b91c1c',  # Rojo
                    'Próximo a vencer': '#b45309',  # Amarillo
                    'Completado con retraso': '#1e40af'  # Azul
                }
            )

            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Error al generar el gráfico de alertas: {e}")

        # Filtros para la tabla de alertas
        st.markdown("### Filtrar Alertas")

        col1, col2, col3 = st.columns(3)

        with col1:
            tipo_alerta_filtro = st.multiselect(
                "Tipo de Alerta",
                options=df_alertas['Tipo Alerta'].unique().tolist(),
                default=df_alertas['Tipo Alerta'].unique().tolist()
            )

        with col2:
            estado_filtro = st.multiselect(
                "Estado",
                options=df_alertas['Estado'].unique().tolist(),
                default=df_alertas['Estado'].unique().tolist()
            )

        with col3:
            if 'Funcionario' in df_alertas.columns and not df_alertas['Funcionario'].isna().all():
                funcionarios = [f for f in df_alertas['Funcionario'].dropna().unique().tolist() if f]
                if funcionarios:
                    funcionario_filtro = st.multiselect(
                        "Funcionario",
                        options=["Todos"] + sorted(funcionarios),
                        default=["Todos"]
                    )
                else:
                    funcionario_filtro = ["Todos"]
            else:
                funcionario_filtro = ["Todos"]

        # Aplicar filtros
        df_alertas_filtrado = df_alertas.copy()

        if tipo_alerta_filtro:
            df_alertas_filtrado = df_alertas_filtrado[df_alertas_filtrado['Tipo Alerta'].isin(tipo_alerta_filtro)]

        if estado_filtro:
            df_alertas_filtrado = df_alertas_filtrado[df_alertas_filtrado['Estado'].isin(estado_filtro)]

        if 'Funcionario' in df_alertas.columns and funcionario_filtro and "Todos" not in funcionario_filtro:
            df_alertas_filtrado = df_alertas_filtrado[df_alertas_filtrado['Funcionario'].isin(funcionario_filtro)]

        # Mostrar tabla de alertas con formato
        st.markdown("### Listado de Alertas")

        # Definir columnas a mostrar
        columnas_alertas = [
            'Cod', 'Entidad', 'Nivel Información', 'Funcionario', 'Tipo Alerta',
            'Estado', 'Fecha Programada', 'Fecha Real', 'Días Rezago', 'Descripción'
        ]

        # Verificar que todas las columnas existan
        columnas_alertas_existentes = [col for col in columnas_alertas if col in df_alertas_filtrado.columns]

        try:
            # Ordenar por estado (vencidos primero) y días de rezago (mayor a menor para vencidos)
            df_alertas_filtrado['Estado_orden'] = df_alertas_filtrado['Estado'].map({
                'Vencido': 1,
                'Próximo a vencer': 2,
                'Completado con retraso': 3
            })

            df_alertas_filtrado = df_alertas_filtrado.sort_values(
                by=['Estado_orden', 'Días Rezago'],
                ascending=[True, False]
            )

            # Mostrar tabla con formato
            st.dataframe(
                df_alertas_filtrado[columnas_alertas_existentes]
                .style.applymap(lambda _: '',
                                subset=['Cod', 'Entidad', 'Nivel Información', 'Funcionario', 'Tipo Alerta',
                                        'Fecha Programada', 'Fecha Real', 'Descripción'])
                .applymap(highlight_estado, subset=['Estado'])
                .format({'Días Rezago': '{:+d}'})  # Mostrar signo + o - en días rezago
            )

            # Botón para descargar alertas
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_alertas_filtrado[columnas_alertas_existentes].to_excel(writer, sheet_name='Alertas', index=False)

            excel_data = output.getvalue()
            st.download_button(
                label="Descargar alertas como Excel",
                data=excel_data,
                file_name="alertas_vencimientos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Descarga las alertas filtradas en formato Excel"
            )
        except Exception as e:
            st.error(f"Error al mostrar la tabla de alertas: {e}")
            # Mostrar tabla sin formato como último recurso
            st.dataframe(df_alertas_filtrado[columnas_alertas_existentes])
    else:
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
        else:
            st.info("✅ Plazos automáticos actualizados y guardados correctamente.")

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

        # AGREGAR FUNCIONALIDAD EXCEL AL SIDEBAR CON AUTENTICACIÓN ADMIN
        # Sección de gestión de datos Excel - Solo para administradores
        st.sidebar.markdown("---")
        st.sidebar.markdown('<div class="subtitle">📊 Gestión de Datos</div>', unsafe_allow_html=True)
        
        # Verificar si el usuario está autenticado como admin
        if verificar_admin():
            # Usuario autenticado - mostrar funcionalidad completa
            mostrar_gestion_datos_admin(registros_df)
        else:
            # Usuario no autenticado - mostrar formulario de login
            mostrar_login_admin()
        
        # Información adicional
        st.sidebar.markdown("---")
        st.sidebar.markdown("**💡 Información:**")
        if verificar_admin():
            st.sidebar.markdown("""
            - ✅ **Modo Administrador Activo**
            - Use Excel para edición masiva de datos
            - Mantenga siempre una copia de respaldo
            - Los plazos se calculan automáticamente
            - Las validaciones se aplican al cargar
            """)
        else:
            st.sidebar.markdown("""
            - 🔒 **Funciones de administrador bloqueadas**
            - Se requiere autenticación para gestionar datos
            - Contacte al administrador del sistema
            - Solo lectura de datos disponible
            """)
        
        st.sidebar.markdown("---")

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

        # APLICAR FILTROS GLOBALES PARA TODAS LAS PESTAÑAS
        # Estos filtros se aplicarán por defecto (sin filtros aplicados)
        df_filtrado_global = registros_df.copy()

        # Crear pestañas - RESTAURANDO LA PESTAÑA FALTANTE
        tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Edición de Registros", "Detalle de Cronogramas", "Alertas de Vencimientos"])
     
        with tab1:
            # FILTROS PARA DASHBOARD
            st.markdown("### 🔍 Filtros")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Filtro por entidad
                entidades = ['Todas'] + sorted(registros_df['Entidad'].unique().tolist())
                entidad_seleccionada = st.selectbox('Entidad', entidades, key="dash_entidad")
            
            with col2:
                # Filtro por funcionario
                funcionarios = ['Todos']
                if 'Funcionario' in registros_df.columns:
                    funcionarios += sorted(registros_df['Funcionario'].dropna().unique().tolist())
                funcionario_seleccionado = st.selectbox('Funcionario', funcionarios, key="dash_funcionario")
            
            with col3:
                # Filtro por tipo de dato
                tipos_dato = ['Todos'] + sorted(registros_df['TipoDato'].dropna().unique().tolist())
                tipo_dato_seleccionado = st.selectbox('Tipo de Dato', tipos_dato, key="dash_tipo")
            
            with col4:
                # Filtro por nivel de información
                niveles = ['Todos'] + sorted(registros_df['Nivel Información '].dropna().unique().tolist())
                nivel_seleccionado = st.selectbox('Nivel de Información', niveles, key="dash_nivel")
            
            # Aplicar filtros
            df_filtrado = registros_df.copy()
            
            if entidad_seleccionada != 'Todas':
                df_filtrado = df_filtrado[df_filtrado['Entidad'] == entidad_seleccionada]
            
            if funcionario_seleccionado != 'Todos' and 'Funcionario' in df_filtrado.columns:
                df_filtrado = df_filtrado[df_filtrado['Funcionario'] == funcionario_seleccionado]
            
            if tipo_dato_seleccionado != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['TipoDato'].str.upper() == tipo_dato_seleccionado.upper()]
            
            if nivel_seleccionado != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['Nivel Información '] == nivel_seleccionado]
            
            st.markdown("---")  # Separador visual
            
            mostrar_dashboard(df_filtrado, metas_nuevas_df, metas_actualizar_df, registros_df, 
                            entidad_seleccionada, funcionario_seleccionado, tipo_dato_seleccionado, nivel_seleccionado)     
        with tab2:
            registros_df = mostrar_edicion_registros(registros_df)

        with tab3:
            # PESTAÑA RESTAURADA: Detalle de Cronogramas
            # Aplicar los mismos filtros que en Dashboard para consistencia
            st.markdown("### 🔍 Filtros")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Filtro por entidad
                entidades_detalle = ['Todas'] + sorted(registros_df['Entidad'].unique().tolist())
                entidad_detalle = st.selectbox('Entidad', entidades_detalle, key="detalle_entidad")
            
            with col2:
                # Filtro por funcionario
                funcionarios_detalle = ['Todos']
                if 'Funcionario' in registros_df.columns:
                    funcionarios_detalle += sorted(registros_df['Funcionario'].dropna().unique().tolist())
                funcionario_detalle = st.selectbox('Funcionario', funcionarios_detalle, key="detalle_funcionario")
            
            with col3:
                # Filtro por tipo de dato
                tipos_dato_detalle = ['Todos'] + sorted(registros_df['TipoDato'].dropna().unique().tolist())
                tipo_dato_detalle = st.selectbox('Tipo de Dato', tipos_dato_detalle, key="detalle_tipo")
            
            with col4:
                # Filtro por nivel de información
                niveles_detalle = ['Todos'] + sorted(registros_df['Nivel Información '].dropna().unique().tolist())
                nivel_detalle = st.selectbox('Nivel de Información', niveles_detalle, key="detalle_nivel")
            
            # Aplicar filtros para detalle
            df_filtrado_detalle = registros_df.copy()
            
            if entidad_detalle != 'Todas':
                df_filtrado_detalle = df_filtrado_detalle[df_filtrado_detalle['Entidad'] == entidad_detalle]
            
            if funcionario_detalle != 'Todos' and 'Funcionario' in df_filtrado_detalle.columns:
                df_filtrado_detalle = df_filtrado_detalle[df_filtrado_detalle['Funcionario'] == funcionario_detalle]
            
            if tipo_dato_detalle != 'Todos':
                df_filtrado_detalle = df_filtrado_detalle[df_filtrado_detalle['TipoDato'].str.upper() == tipo_dato_detalle.upper()]
            
            if nivel_detalle != 'Todos':
                df_filtrado_detalle = df_filtrado_detalle[df_filtrado_detalle['Nivel Información '] == nivel_detalle]
            
            st.markdown("---")  # Separador visual
            
            mostrar_detalle_cronogramas(df_filtrado_detalle)

        with tab4:
            # FILTRO PARA ALERTAS
            st.markdown("### 🔍 Filtro")
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                # Filtro por tipo de dato
                tipos_dato_alertas = ['Todos'] + sorted(registros_df['TipoDato'].dropna().unique().tolist())
                tipo_dato_alertas = st.selectbox('Tipo de Dato', tipos_dato_alertas, key="alertas_tipo")
            
            # Aplicar filtro
            df_filtrado_alertas = registros_df.copy()
            
            if tipo_dato_alertas != 'Todos':
                df_filtrado_alertas = df_filtrado_alertas[df_filtrado_alertas['TipoDato'].str.upper() == tipo_dato_alertas.upper()]
            
            st.markdown("---")  # Separador visual
    
            mostrar_alertas_vencimientos(df_filtrado_alertas)
        
        # Agregar sección de diagnóstico
        mostrar_diagnostico(registros_df, meta_df, metas_nuevas_df, metas_actualizar_df, df_filtrado_global)

        # Agregar sección de ayuda
        mostrar_ayuda()

        # GUARDADO FINAL AUTOMÁTICO - Asegurar que todos los datos estén guardados
        # Esto garantiza que cualquier cambio no guardado se preserve
        try:
            # Aplicar validaciones finales sin mostrar mensajes
            registros_df_final = validar_reglas_negocio(registros_df)
            registros_df_final = actualizar_plazo_analisis(registros_df_final)
            registros_df_final = actualizar_plazo_cronograma(registros_df_final)
            registros_df_final = actualizar_plazo_oficio_cierre(registros_df_final)
            registros_df_final['Porcentaje Avance'] = registros_df_final.apply(calcular_porcentaje_avance, axis=1)
            registros_df_final['Estado Fechas'] = registros_df_final.apply(verificar_estado_fechas, axis=1)
            
            # Guardar sin mostrar mensaje
            guardar_datos_editados(registros_df_final)
            
        except Exception as e:
            # En caso de error en el guardado final, mostrar advertencia
            st.sidebar.warning(f"⚠️ Advertencia: Error en guardado automático final: {str(e)}")

    except Exception as e:
        mostrar_error(e)
        
        # Intentar guardar datos como medida de seguridad incluso en caso de error
        try:
            if 'registros_df' in locals():
                guardar_datos_editados(registros_df)
        except:
            pass  # Si falla, no podemos hacer más


if __name__ == "__main__":
    main()
