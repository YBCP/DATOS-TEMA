# Validaciones_utils.py actualizado
import pandas as pd
import numpy as np
from data_utils import procesar_fecha
from datetime import datetime

def verificar_condiciones_estandares(row):
    """
    Verifica si las condiciones para ingresar la fecha de Estándares están cumplidas.
    Retorna True si todos los campos requeridos con sufijo (completo) están marcados como 'Completo'.
    Si algún campo no existe, se considerará automáticamente como incompleto.

    Args:
        row: Fila del DataFrame a verificar

    Returns:
        tuple: (valido, campos_incompletos)
            - valido: True si todos los campos existen y están 'Completo', False en caso contrario
            - campos_incompletos: Lista de nombres de campos que no están 'Completo' o no existen
    """
    # Lista de componentes de estándares que deben estar completos (solo con sufijo completo)
    campos_estandares_completo = [
        'Registro (completo)',
        'ET (completo)',
        'CO (completo)',
        'DD (completo)',
        'REC (completo)',
        'SERVICIO (completo)'
    ]

    campos_incompletos = []

    for campo in campos_estandares_completo:
        if campo in row and pd.notna(row[campo]):
            # Verificar si el valor es exactamente "Completo"
            if row[campo] != "Completo":
                # Extraer el nombre sin el sufijo para el mensaje de error
                nombre_campo = campo.split(' (')[0]
                campos_incompletos.append(nombre_campo)
        else:
            # Si el campo no existe o es NaN, considerarlo como incompleto
            nombre_campo = campo.split(' (')[0]
            campos_incompletos.append(f"{nombre_campo} (campo no existe)")

    # Si todos los campos están completos (lista vacía), retornar válido
    return len(campos_incompletos) == 0, campos_incompletos


def verificar_condicion_publicacion(row):
    """
    Verifica si la condición para ingresar la fecha de Publicación está cumplida.
    Retorna True si 'Disponer datos temáticos' está marcado como 'Si'.

    Args:
        row: Fila del DataFrame a verificar

    Returns:
        bool: True si 'Disponer datos temáticos' es 'Si', False en caso contrario
    """
    if 'Disponer datos temáticos' in row and pd.notna(row['Disponer datos temáticos']):
        valor = row['Disponer datos temáticos']
        return valor.upper() in ["SI", "SÍ", "S", "YES", "Y"]
    return False


def verificar_condiciones_oficio_cierre(row):
    """
    Verifica si las condiciones para ingresar la fecha de Oficio de cierre están cumplidas.
    Para poder ingresar fecha en el campo oficio de cierre:
    1. Todos los campos con opciones 'Si' o 'No' deben estar marcados como 'Si'
    2. Todos los estándares (con sufijo completo) deben estar completos
    3. Todos los campos de fecha deben estar diligenciados

    Args:
        row: Fila del DataFrame a verificar

    Returns:
        tuple: (valido, campos_incompletos)
            - valido: True si todas las condiciones se cumplen, False en caso contrario
            - campos_incompletos: Lista de campos que no cumplen las condiciones
    """
    campos_incompletos = []

    # 1. Verificar campos Si/No - todos deben estar como 'Si'
    campos_si_no = [
        'Acuerdo de compromiso',
        'Análisis de información',
        'Cronograma Concertado',
        'Seguimiento a los acuerdos',
        'Disponer datos temáticos',
        'Catálogo de recursos geográficos',
        'Oficios de cierre'
    ]

    for campo in campos_si_no:
        if campo in row:
            valor = str(row[campo]).strip().upper() if pd.notna(row[campo]) else ""
            if valor not in ["SI", "SÍ", "S", "YES", "Y"]:
                campos_incompletos.append(f"{campo} debe ser SI")
        else:
            campos_incompletos.append(f"{campo} no existe y debe ser SI")

    # 2. Verificar que todos los estándares estén completos (usando campos con sufijo completo)
    campos_estandares_completo = [
        'Registro (completo)', 'ET (completo)', 'CO (completo)',
        'DD (completo)', 'REC (completo)', 'SERVICIO (completo)'
    ]

    for campo in campos_estandares_completo:
        if campo in row:
            valor = row[campo] if pd.notna(row[campo]) else ""
            if valor != "Completo":
                nombre_campo = campo.split(' (')[0]
                campos_incompletos.append(f"{nombre_campo} debe estar Completo")
        else:
            nombre_campo = campo.split(' (')[0]
            campos_incompletos.append(f"{nombre_campo} (campo no existe)")

    # 3. Verificar que todos los campos de fecha estén diligenciados
    campos_fecha = [
        'Análisis y cronograma',
        'Estándares',
        'Publicación',
        'Fecha de entrega de información'
    ]

    for campo in campos_fecha:
        if campo in row:
            if pd.isna(row[campo]) or str(row[campo]).strip() == "":
                campos_incompletos.append(f"Falta fecha en {campo}")
        else:
            campos_incompletos.append(f"El campo {campo} no existe")

    # 4. Verificar que todas las fechas sean anteriores a la fecha de oficio de cierre
    fecha_oficio_str = row.get('Fecha de oficio de cierre', None)
    if fecha_oficio_str and pd.notna(fecha_oficio_str) and fecha_oficio_str != '':
        fecha_oficio = procesar_fecha(fecha_oficio_str)
        if fecha_oficio:
            for campo in campos_fecha:
                if campo in row and row[campo] and pd.notna(row[campo]):
                    fecha_campo = procesar_fecha(row[campo])
                    if fecha_campo and fecha_campo > fecha_oficio:
                        campos_incompletos.append(f"La fecha en {campo} debe ser anterior a la fecha de oficio de cierre")

    return len(campos_incompletos) == 0, campos_incompletos


def validar_reglas_negocio(df):
    """
    Aplica reglas de negocio para mantener consistencia en los datos:
    1. Si suscripción acuerdo de compromiso o entrega acuerdo de compromiso no está vacío, acuerdo de compromiso = SI
    2. Si análisis y cronograma tiene fecha, análisis de información y cronograma concertado = SI
    3. Si estándares tiene fecha, verificar que los campos con sufijo (completo) = Completo
    4. Si publicación tiene fecha, disponer datos temáticos = SI
    5. Si oficio de cierre tiene fecha, verificar todas las condiciones necesarias
    6. Si oficio de cierre tiene fecha válida, actualizar estado a "Completado"
    7. Si se marca "Disponer datos temáticos" como "No", borrar fecha de publicación
    8. Si Estado es "Completado" pero no hay fecha de oficio de cierre, cambiar Estado a "En proceso"
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

        # Regla 3: Si estándares tiene fecha, verificar que todos los campos con sufijo (completo) = Completo
        if 'Estándares' in row and pd.notna(row['Estándares']) and str(row['Estándares']).strip() != '':
            fecha = procesar_fecha(row['Estándares'])
            if fecha is not None:
                # Verificar que todos los campos requeridos estén completos
                valido, campos_incompletos = verificar_condiciones_estandares(row)

                # Si hay campos incompletos, eliminar la fecha de estándares
                if not valido:
                    df_actualizado.at[idx, 'Estándares'] = ''

        # Regla 4: Si publicación tiene fecha, disponer datos temáticos = SI
        if 'Publicación' in row and pd.notna(row['Publicación']) and str(row['Publicación']).strip() != '':
            fecha = procesar_fecha(row['Publicación'])
            if fecha is not None and 'Disponer datos temáticos' in df_actualizado.columns:
                df_actualizado.at[idx, 'Disponer datos temáticos'] = 'Si'

        # Regla 7: Si se marca "Disponer datos temáticos" como "No", borrar fecha de publicación
        if 'Disponer datos temáticos' in row and pd.notna(row['Disponer datos temáticos']):
            valor = str(row['Disponer datos temáticos']).strip().upper()
            if valor in ["NO", "N"] and 'Publicación' in df_actualizado.columns:
                df_actualizado.at[idx, 'Publicación'] = ''

        # Regla 5: Si oficio de cierre tiene fecha, verificar todas las condiciones necesarias
        if 'Fecha de oficio de cierre' in row and pd.notna(row['Fecha de oficio de cierre']) and str(
                row['Fecha de oficio de cierre']).strip() != '':
            fecha = procesar_fecha(row['Fecha de oficio de cierre'])
            if fecha is not None:
                # Verificar todas las condiciones para el oficio de cierre
                valido, campos_incompletos = verificar_condiciones_oficio_cierre(row)

                # Si hay campos incompletos, eliminar la fecha de oficio de cierre
                if not valido:
                    df_actualizado.at[idx, 'Fecha de oficio de cierre'] = ''
                    # Si el estado es "Completado", cambiarlo a "En proceso" si se elimina la fecha
                    if 'Estado' in df_actualizado.columns and df_actualizado.at[idx, 'Estado'] == 'Completado':
                        df_actualizado.at[idx, 'Estado'] = 'En proceso'
                else:
                    # Regla 6: Si oficio de cierre tiene fecha válida, actualizar estado a "Completado"
                    if 'Estado' in df_actualizado.columns:
                        df_actualizado.at[idx, 'Estado'] = 'Completado'
        
        # Regla 8: Si Estado es "Completado" pero no hay fecha de oficio de cierre, cambiar Estado a "En proceso"
        elif 'Estado' in df_actualizado.columns and df_actualizado.at[idx, 'Estado'] == 'Completado':
            # Verificar si hay fecha de oficio de cierre válida
            if 'Fecha de oficio de cierre' not in row or pd.isna(row['Fecha de oficio de cierre']) or row['Fecha de oficio de cierre'] == '':
                df_actualizado.at[idx, 'Estado'] = 'En proceso'

    return df_actualizado


def mostrar_estado_validaciones(df, st_obj=None):
    """
    Muestra el estado actual de las validaciones para cada registro.
    Si se proporciona un objeto Streamlit (st_obj), muestra las advertencias en la interfaz.
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

        # Validar Estándares (usando campos con sufijo completo)
        tiene_fecha_estandares = ('Estándares' in row and
                                  pd.notna(row['Estándares']) and
                                  str(row['Estándares']).strip() != '')

        valido, campos_incompletos = verificar_condiciones_estandares(row)

        if tiene_fecha_estandares and not valido:
            resultado['Estado Estándares'] = 'Inconsistente'
            resultado['Campos Incompletos'] = ', '.join(campos_incompletos)
        else:
            resultado['Estado Estándares'] = 'Correcto'
            resultado['Campos Incompletos'] = ''

        # Validar Publicación
        tiene_fecha_publicacion = ('Publicación' in row and
                                   pd.notna(row['Publicación']) and
                                   str(row['Publicación']).strip() != '')

        tiene_disponer_datos = verificar_condicion_publicacion(row)

        if tiene_fecha_publicacion and not tiene_disponer_datos:
            resultado['Estado Publicación'] = 'Inconsistente'
        else:
            resultado['Estado Publicación'] = 'Correcto'

        # Validar condición de "Disponer datos temáticos" como "No" y tener fecha de publicación
        if 'Disponer datos temáticos' in row and pd.notna(row['Disponer datos temáticos']):
            valor = str(row['Disponer datos temáticos']).strip().upper()
            if valor in ["NO", "N"] and tiene_fecha_publicacion:
                resultado['Estado Publicación Disponer'] = 'Inconsistente'
            else:
                resultado['Estado Publicación Disponer'] = 'Correcto'
        else:
            resultado['Estado Publicación Disponer'] = 'No aplicable'

        # Validar Oficio de cierre
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
        # Filtrar los registros con estándares inconsistentes
        estandares_inconsistentes = resultados_df[resultados_df['Estado Estándares'] == 'Inconsistente']

        if not estandares_inconsistentes.empty:
            st_obj.error(
                "No es posible diligenciar este campo. Verifique que todos los estándares se encuentren en estado Completo")

            # Crear DataFrame para mostrar los registros con problemas
            df_validaciones = estandares_inconsistentes[['Cod', 'Entidad', 'Nivel Información ', 'Campos Incompletos']]
            st_obj.dataframe(df_validaciones)

        # Filtrar registros con inconsistencias de publicación
        publicacion_inconsistentes = resultados_df[resultados_df['Estado Publicación'] == 'Inconsistente']

        if not publicacion_inconsistentes.empty:
            st_obj.error(
                "No es posible diligenciar este campo. El campo 'Disponer datos temáticos' debe estar marcado como 'Si'")

            # Crear DataFrame para mostrar los registros con problemas
            df_publicacion = publicacion_inconsistentes[['Cod', 'Entidad', 'Nivel Información ']]
            st_obj.dataframe(df_publicacion)
            
        # Filtrar registros con inconsistencias de "Disponer datos temáticos" como "No" y tener fecha de publicación
        publicacion_disponer_inconsistentes = resultados_df[resultados_df['Estado Publicación Disponer'] == 'Inconsistente']
        
        if not publicacion_disponer_inconsistentes.empty:
            st_obj.error(
                "Si 'Disponer datos temáticos' está marcado como 'No', no debe tener fecha de publicación. Se borrará la fecha.")
            
            # Crear DataFrame para mostrar los registros con problemas
            df_publicacion_disponer = publicacion_disponer_inconsistentes[['Cod', 'Entidad', 'Nivel Información ']]
            st_obj.dataframe(df_publicacion_disponer)

        # Filtrar registros con inconsistencias de oficio de cierre
        oficio_inconsistentes = resultados_df[resultados_df['Estado Oficio Cierre'] == 'Inconsistente']

        if not oficio_inconsistentes.empty:
            st_obj.error(
                "No es posible diligenciar la Fecha de oficio de cierre. Debe tener todos los campos Si/No en 'Si', todos los estándares completos, y todas las fechas diligenciadas y anteriores a la fecha de cierre.")

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

        # Filtrar registros con otras inconsistencias
        otras_inconsistencias = resultados_df[
            (resultados_df['Estado Acuerdo'] == 'Inconsistente') |
            (resultados_df['Estado Análisis'] == 'Inconsistente')
            ]

        if not otras_inconsistencias.empty:
            if (estandares_inconsistentes.empty and publicacion_inconsistentes.empty and 
                publicacion_disponer_inconsistentes.empty and oficio_inconsistentes.empty and 
                estado_inconsistentes.empty):
                st_obj.warning("Se detectaron otras inconsistencias en los datos que se corregirán automáticamente:")
            else:
                st_obj.warning("Además, se detectaron otras inconsistencias que se corregirán automáticamente:")

            # Filtrar solo las columnas relevantes
            df_otras = otras_inconsistencias[
                ['Cod', 'Entidad', 'Nivel Información ', 'Estado Acuerdo', 'Estado Análisis']]
            st_obj.dataframe(df_otras)
        elif (estandares_inconsistentes.empty and publicacion_inconsistentes.empty and 
              publicacion_disponer_inconsistentes.empty and oficio_inconsistentes.empty and 
              estado_inconsistentes.empty):
            # No hay inconsistencias
            st_obj.success("Todos los registros cumplen con las reglas de validación.")

    return resultados_df
