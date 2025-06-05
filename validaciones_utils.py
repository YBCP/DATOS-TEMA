# Validaciones_utils.py actualizado
import pandas as pd
import numpy as np
from data_utils import procesar_fecha
from datetime import datetime

def verificar_condiciones_estandares(row):
    """
    MODIFICADO: Ya no se requiere validación estricta de estándares.
    Esta función ahora es más permisiva y permite cualquier combinación de estados.
    
    Args:
        row: Fila del DataFrame a verificar

    Returns:
        tuple: (True, []) - Siempre válido ya que se permite flexibilidad
    """
    # Nueva lógica: siempre permitir, ya que "No aplica" es válido
    return True, []


def verificar_condicion_publicacion(row):
    """
    MODIFICADO: Simplificado para ser más permisivo.
    Ya no requiere verificación previa de 'Disponer datos temáticos'.
    
    Args:
        row: Fila del DataFrame a verificar

    Returns:
        bool: Siempre True ya que se actualiza automáticamente
    """
    return True


def verificar_condiciones_oficio_cierre(row):
    """
    MODIFICADO: Simplificado drásticamente.
    Solo verifica que la etapa de Publicación esté completada.

    Args:
        row: Fila del DataFrame a verificar

    Returns:
        tuple: (valido, campos_incompletos)
            - valido: True si la Publicación está completada, False en caso contrario
            - campos_incompletos: Lista de campos que faltan (solo Publicación si aplica)
    """
    campos_incompletos = []

    # Solo verificar que la Publicación esté completada
    if 'Publicación' in row:
        if pd.isna(row['Publicación']) or str(row['Publicación']).strip() == "":
            campos_incompletos.append("Debe completar la etapa de Publicación (tener fecha)")
    else:
        campos_incompletos.append("El campo Publicación no existe")

    return len(campos_incompletos) == 0, campos_incompletos


def validar_reglas_negocio(df):
    """
    MODIFICADO: Aplica nuevas reglas de negocio simplificadas:
    1. Si suscripción acuerdo de compromiso o entrega acuerdo de compromiso no está vacío, acuerdo de compromiso = SI
    2. Si análisis y cronograma tiene fecha, análisis de información y cronograma concertado = SI
    3. Al introducir fecha en estándares, campos que no estén "Completo" se actualizan a "No aplica"
    4. Si introduce fecha en publicación, disponer datos temáticos = SI automáticamente
    5. Si oficio de cierre tiene fecha válida, actualizar estado a "Completado"
    6. Si Estado es "Completado" pero no hay fecha de oficio de cierre, cambiar Estado a "En proceso"
    """
    df_actualizado = df.copy()

    # Iterar sobre cada fila
    for idx, row in df.iterrows():
        # Regla 1: Si suscripción o entrega acuerdo de compromiso no está vacío, acuerdo de compromiso = SI
        if 'Suscripción acuerdo de compromiso' in row and pd.notna(row['Suscripción acuerdo de compromiso']) and str(
                row['Suscripción acuerdo de compromiso']).strip() != '':
            df_actualizado.at[idx, 'Acuerdo de compromiso'] = 'Si'

        if 'Entrega acuerdo de compromiso' in row and pd.notna(row['Entrega acuerdo de compromiso']) and str(
                row['Entrega acuerdo de compromiso']).strip() != '':
            df_actualizado.at[idx, 'Acuerdo de compromiso'] = 'Si'

        # Regla 2: Si análisis y cronograma tiene fecha, análisis de información y cronograma concertado = SI
        if 'Análisis y cronograma' in row and pd.notna(row['Análisis y cronograma']) and str(
                row['Análisis y cronograma']).strip() != '':
            fecha = procesar_fecha(row['Análisis y cronograma'])
            if fecha is not None:
                if 'Análisis de información' in df_actualizado.columns:
                    df_actualizado.at[idx, 'Análisis de información'] = 'Si'
                if 'Cronograma Concertado' in df_actualizado.columns:
                    df_actualizado.at[idx, 'Cronograma Concertado'] = 'Si'

        # Regla 3: MODIFICADA - Al introducir fecha en estándares, actualizar campos no completos a "No aplica"
        if 'Estándares' in row and pd.notna(row['Estándares']) and str(row['Estándares']).strip() != '':
            fecha = procesar_fecha(row['Estándares'])
            if fecha is not None:
                # Campos de estándares a verificar
                campos_estandares_completo = [
                    'Registro (completo)', 'ET (completo)', 'CO (completo)',
                    'DD (completo)', 'REC (completo)', 'SERVICIO (completo)'
                ]
                
                for campo in campos_estandares_completo:
                    if campo in df_actualizado.columns:
                        valor_actual = df_actualizado.at[idx, campo] if pd.notna(df_actualizado.at[idx, campo]) else ""
                        # Si no está "Completo", actualizar a "No aplica"
                        if str(valor_actual).strip().upper() != "COMPLETO":
                            df_actualizado.at[idx, campo] = "No aplica"

        # Regla 4: MODIFICADA - Si publicación tiene fecha, disponer datos temáticos = SI automáticamente
        if 'Publicación' in row and pd.notna(row['Publicación']) and str(row['Publicación']).strip() != '':
            fecha = procesar_fecha(row['Publicación'])
            if fecha is not None and 'Disponer datos temáticos' in df_actualizado.columns:
                df_actualizado.at[idx, 'Disponer datos temáticos'] = 'Si'

        # Regla 5: MODIFICADA - Si oficio de cierre tiene fecha, actualizar estado a "Completado" (validación simple)
        if 'Fecha de oficio de cierre' in row and pd.notna(row['Fecha de oficio de cierre']) and str(
                row['Fecha de oficio de cierre']).strip() != '':
            fecha = procesar_fecha(row['Fecha de oficio de cierre'])
            if fecha is not None:
                # Solo verificar que Publicación esté completada
                tiene_publicacion = ('Publicación' in row and pd.notna(row['Publicación']) and 
                                   str(row['Publicación']).strip() != '')
                
                if tiene_publicacion:
                    # Actualizar estado a "Completado"
                    if 'Estado' in df_actualizado.columns:
                        df_actualizado.at[idx, 'Estado'] = 'Completado'
                else:
                    # Si no tiene publicación, eliminar la fecha de oficio de cierre
                    df_actualizado.at[idx, 'Fecha de oficio de cierre'] = ''
                    # Y cambiar estado a "En proceso" si era "Completado"
                    if 'Estado' in df_actualizado.columns and df_actualizado.at[idx, 'Estado'] == 'Completado':
                        df_actualizado.at[idx, 'Estado'] = 'En proceso'
        
        # Regla 6: Si Estado es "Completado" pero no hay fecha de oficio de cierre, cambiar Estado a "En proceso"
        elif 'Estado' in df_actualizado.columns and df_actualizado.at[idx, 'Estado'] == 'Completado':
            # Verificar si hay fecha de oficio de cierre válida
            if 'Fecha de oficio de cierre' not in row or pd.isna(row['Fecha de oficio de cierre']) or row['Fecha de oficio de cierre'] == '':
                df_actualizado.at[idx, 'Estado'] = 'En proceso'

    return df_actualizado


def mostrar_estado_validaciones(df, st_obj=None):
    """
    MODIFICADO: Muestra el estado actual de las validaciones simplificadas.
    """
    resultados = []

    for idx, row in df.iterrows():
        resultado = {'Cod': row.get('Cod', ''), 'Entidad': row.get('Entidad', ''),
                     'Nivel Información ': row.get('Nivel Información ', '')}

        # Validar Acuerdo de compromiso
        tiene_entrega = ('Entrega acuerdo de compromiso' in row and
                         pd.notna(row['Entrega acuerdo de compromiso']) and
                         str(row['Entrega acuerdo de compromiso']).strip() != '')

        tiene_acuerdo = ('Acuerdo de compromiso' in row and
                         pd.notna(row['Acuerdo de compromiso']) and
                         str(row['Acuerdo de compromiso']).strip().upper() in ['SI', 'SÍ', 'S', 'YES', 'Y', 'COMPLETO'])

        if tiene_entrega and not tiene_acuerdo:
            resultado['Estado Acuerdo'] = 'Inconsistente'
        else:
            resultado['Estado Acuerdo'] = 'Correcto'

        # Validar Análisis de información
        tiene_fecha_analisis = ('Análisis y cronograma' in row and
                                pd.notna(row['Análisis y cronograma']) and
                                str(row['Análisis y cronograma']).strip() != '')

        tiene_analisis_info = ('Análisis de información' in row and
                               pd.notna(row['Análisis de información']) and
                               str(row['Análisis de información']).strip().upper() in ['SI', 'SÍ', 'S', 'YES', 'Y',
                                                                                       'COMPLETO'])

        if tiene_fecha_analisis and not tiene_analisis_info:
            resultado['Estado Análisis'] = 'Inconsistente'
        else:
            resultado['Estado Análisis'] = 'Correcto'

        # MODIFICADO: Validar Estándares (ahora más permisivo)
        tiene_fecha_estandares = ('Estándares' in row and
                                  pd.notna(row['Estándares']) and
                                  str(row['Estándares']).strip() != '')

        if tiene_fecha_estandares:
            resultado['Estado Estándares'] = 'Correcto'
            resultado['Campos Incompletos'] = ''
        else:
            resultado['Estado Estándares'] = 'No aplicable'
            resultado['Campos Incompletos'] = ''

        # MODIFICADO: Validar Publicación (ahora automático)
        tiene_fecha_publicacion = ('Publicación' in row and
                                   pd.notna(row['Publicación']) and
                                   str(row['Publicación']).strip() != '')

        if tiene_fecha_publicacion:
            resultado['Estado Publicación'] = 'Correcto'
        else:
            resultado['Estado Publicación'] = 'No aplicable'

        # MODIFICADO: Validar Oficio de cierre (solo Publicación requerida)
        tiene_fecha_oficio = ('Fecha de oficio de cierre' in row and
                              pd.notna(row['Fecha de oficio de cierre']) and
                              str(row['Fecha de oficio de cierre']).strip() != '')

        if tiene_fecha_oficio:
            valido, campos_incompletos = verificar_condiciones_oficio_cierre(row)
            if not valido:
                resultado['Estado Oficio Cierre'] = 'Inconsistente'
                resultado['Oficio Incompletos'] = ', '.join(campos_incompletos)
            else:
                resultado['Estado Oficio Cierre'] = 'Correcto'
                resultado['Oficio Incompletos'] = ''
        else:
            resultado['Estado Oficio Cierre'] = 'No aplicable'
            resultado['Oficio Incompletos'] = ''
            
        # Validar Estado "Completado" sin fecha de oficio de cierre
        tiene_estado_completado = ('Estado' in row and pd.notna(row['Estado']) and row['Estado'] == 'Completado')
        if tiene_estado_completado and not tiene_fecha_oficio:
            resultado['Estado Inconsistente'] = 'Sí (Completado sin fecha oficio)'
        else:
            resultado['Estado Inconsistente'] = 'No'

        resultados.append(resultado)

    # Crear DataFrame con los resultados
    resultados_df = pd.DataFrame(resultados)

    # Si hay un objeto Streamlit, mostrar advertencias
    if st_obj is not None:
        # MODIFICADO: Filtrar solo los registros con oficio de cierre inconsistentes
        oficio_inconsistentes = resultados_df[resultados_df['Estado Oficio Cierre'] == 'Inconsistente']

        if not oficio_inconsistentes.empty:
            st_obj.error(
                "No es posible diligenciar la Fecha de oficio de cierre. Debe tener la etapa de Publicación completada.")

            # Crear DataFrame para mostrar los registros con problemas
            df_oficio = oficio_inconsistentes[['Cod', 'Entidad', 'Nivel Información ', 'Oficio Incompletos']]
            st_obj.dataframe(df_oficio)

        # Filtrar registros con Estado "Completado" sin fecha de oficio de cierre
        estado_inconsistentes = resultados_df[resultados_df['Estado Inconsistente'] == 'Sí (Completado sin fecha oficio)']
        
        if not estado_inconsistentes.empty:
            st_obj.error(
                "Hay registros con Estado 'Completado' sin fecha de oficio de cierre. El Estado se cambiará a 'En proceso'.")
            
            # Crear DataFrame para mostrar los registros con problemas
            df_estado = estado_inconsistentes[['Cod', 'Entidad', 'Nivel Información ']]
            st_obj.dataframe(df_estado)

        # Filtrar registros con otras inconsistencias menores
        otras_inconsistencias = resultados_df[
            (resultados_df['Estado Acuerdo'] == 'Inconsistente') |
            (resultados_df['Estado Análisis'] == 'Inconsistente')
            ]

        if not otras_inconsistencias.empty:
            if oficio_inconsistentes.empty and estado_inconsistentes.empty:
                st_obj.warning("Se detectaron inconsistencias menores que se corregirán automáticamente:")
            else:
                st_obj.warning("Además, se detectaron inconsistencias menores que se corregirán automáticamente:")

            # Filtrar solo las columnas relevantes
            df_otras = otras_inconsistencias[
                ['Cod', 'Entidad', 'Nivel Información ', 'Estado Acuerdo', 'Estado Análisis']]
            st_obj.dataframe(df_otras)
        elif oficio_inconsistentes.empty and estado_inconsistentes.empty:
            # No hay inconsistencias
            st_obj.success("Todos los registros cumplen con las reglas de validación simplificadas.")

    return resultados_df
