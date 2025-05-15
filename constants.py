# 3. constants.py - Datos de ejemplo y constantes

# Datos de ejemplo para registros
REGISTROS_DATA = """Cod;Funcionario;Entidad;Nivel Información ;Frecuencia actualizacion ;TipoDato;Actas de acercamiento y manifestación de interés;Suscripción acuerdo de compromiso;Entrega acuerdo de compromiso;Acuerdo de compromiso;Gestion acceso a los datos y documentos requeridos ; Análisis de información;Cronograma Concertado;Análisis y cronograma (fecha programada);Fecha de entrega de información;Plazo de análisis;Análisis y cronograma;Seguimiento a los acuerdos;Registro;ET;CO;DD;REC;SERVICIO;Estándares (fecha programada);Estándares;Resultados de orientación técnica;Verificación del servicio web geográfico;Verificar Aprobar Resultados;Revisar y validar los datos cargados en la base de datos;Aprobación resultados obtenidos en la rientación;Disponer datos temáticos;Fecha de publicación programada;Publicación;Catálogo de recursos geográficos;Oficios de cierre;Fecha de oficio de cierre;Estado;Observación
2;Daniel Alberto Morales Dueñas;Departamento Administrativo de la Defensoría del Espacio Publico- DADEP;Indicador de Espacio Público por Localidad;Anual;Actualizar;Si;24/01/2024;31/01/2024;Si;Si;Si;Si;31/01/2025;15/01/2025;;15/02/2025;Si;Completo;Completo;Completo;Completo;Completo;Completo;2/03/2025;20/03/2025;Si;Si;Si;Si;Si;Si;1/05/2025;;No;No;;;En proceso oficio de cierre
3;Daniel Alberto Morales Dueñas;Departamento Administrativo de la Defensoría del Espacio Publico- DADEP;Espacio Público Recuperado;Anual;Actualizar;Si;24/01/2024;24/01/2024;Si;Si;Si;Si;25/02/2025;10/02/2025;;28/02/2025;Si;Completo;Completo;Completo;Completo;Completo;Completo;27/03/2025;10/04/2025;Si;Si;Si;Si;Si;Si;26/05/2025;;No;No;;;En proceso oficio de cierre
4;Daniel Alberto Morales Dueñas;Departamento Administrativo de la Defensoría del Espacio Publico- DADEP;Parques;Anual;Nuevo;Si;14/02/2024;14/02/2024;Si;Si;Si;Si;10/04/2025;15/03/2025;;;;Completo;Completo;Completo;Completo;Completo;Completo;15/05/2025;;No;No;No;No;No;No;30/06/2025;;No;No;;;En proceso
5;Claudia Puentes;Secretaría Distrital de Ambiente;Calidad del Aire;Mensual;Actualizar;Si;05/01/2024;12/01/2024;Si;Si;Si;Si;15/02/2025;01/02/2025;;20/02/2025;Si;Completo;Completo;Completo;Completo;Completo;Completo;15/03/2025;25/03/2025;Si;Si;Si;Si;Si;Si;15/04/2025;20/04/2025;Si;Si;20/04/2025;Completado;Finalizado
6;Claudia Puentes;Secretaría Distrital de Ambiente;Ruido Ambiental;Trimestral;Nuevo;Si;15/01/2024;20/01/2024;Si;Si;Si;Si;28/02/2025;15/02/2025;;01/03/2025;Si;Completo;Completo;Completo;Completo;Completo;Completo;30/03/2025;15/04/2025;Si;Si;Si;Si;Si;Si;30/04/2025;05/05/2025;Si;Si;10/05/2025;Completado;Finalizado
7;Juan Pérez;Instituto de Desarrollo Urbano;Malla Vial;Semestral;Actualizar;Si;10/01/2024;15/01/2024;Si;Si;Si;Si;15/03/2025;01/03/2025;;;;Completo;Completo;Completo;Completo;Completo;Completo;15/04/2025;;No;No;No;No;No;No;30/05/2025;;No;No;;;En proceso
8;Juan Pérez;Instituto de Desarrollo Urbano;Ciclorutas;Anual;Nuevo;Si;05/02/2024;10/02/2024;Si;Si;Si;Si;15/03/2025;01/03/2025;;;;Completo;Completo;Completo;Completo;Completo;Completo;20/04/2025;;No;No;No;No;No;No;31/05/2025;;No;No;;;En proceso"""

# Datos de ejemplo para metas
META_DATA = """;;Enero;;Febrero;Marzo;;Abril;;Mayo;;Junio;;Julio;;Agosto;;Septiembre;;Octubre;;Noviembre;;Diciembre;
Nuevo;;;;;Actualizar;;;;;;;;;;;;;;;;;;;;;
Mes;Acuerdo de compromiso;Análisis y cronograma;Estándares;Publicación;;Acuerdo de compromiso;Análisis y cronograma;Estándares;Publicación;;;;;;;;;;;;;;
15/01/2025;5;2;;;15/01/2025;20;8;;;;;;;;;;;;;;;;
31/01/2025;5;2;2;;31/01/2025;30;8;8;;;;;;;;;;;;;;;
14/02/2025;10;2;;;14/02/2025;30;8;;;;;;;;;;;;;;;;
28/02/2025;;2;;;28/02/2025;;8;;;;;;;;;;;;;;;;
15/03/2025;;2;2;;15/03/2025;;8;8;;;;;;;;;;;;;;;
31/03/2025;;2;2;2;31/03/2025;;8;8;8;;;;;;;;;;;;;;
15/04/2025;;2;2;2;15/04/2025;;8;8;;;;;;;;;;;;;;;
30/04/2025;;2;2;2;30/04/2025;;8;8;;;;;;;;;;;;;;;
15/05/2025;;2;;2;15/05/2025;;8;;8;;;;;;;;;;;;;;
31/05/2025;;2;;;31/05/2025;;8;;;;;;;;;;;;;;;;
15/06/2025;;;2;;15/06/2025;;;;;;;;;;;;;;;;;
30/06/2025;;;2;;30/06/2025;;;8;8;;;;;;;;;;;;;;
15/07/2025;;;2;;15/07/2025;;;8;8;;;;;;;;;;;;;;
31/07/2025;;;2;;31/07/2025;;;8;8;;;;;;;;;;;;;;
15/08/2025;;;;8;15/08/2025;;;;8;;;;;;;;;;;;;;
31/08/2025;;;;;31/08/2025;;;;;;;;;;;;;;;;;
15/09/2025;;;;;15/09/2025;;;;;;;;;;;;;;;;;
30/09/2025;;;;;30/09/2025;;;;;;;;;;;;;;;;;
15/10/2025;;;2;;15/10/2025;;;;;;;;;;;;;;;;;
31/10/2025;;;;2;31/10/2025;;;;8;;;;;;;;;;;;;;
15/11/2025;;;;;15/11/2025;;;;;;;;;;;;;;;;;
30/11/2025;;;;;30/11/2025;;;;;;;;;;;;;;;;;
15/12/2025;;;;;15/12/2025;;;;;;;;;;;;;;;;;
31/12/2025;;;;;31/12/2025;;;;;;;;;;;;;;;;;"""

# Lista de valores que se consideran positivos para verificación de campos
VALORES_POSITIVOS = ['SI', 'SÍ', 'S', 'YES', 'Y', 'COMPLETO', 'COMPLETADO', 'TERMINADO']

# Definición de hitos y sus pesos para el cálculo de porcentaje
HITOS = {
    'Acuerdo de compromiso': 0.25,
    'Análisis y cronograma': 0.25,
    'Estándares': 0.25,
    'Publicación': 0.25
}

# Mapeo de campos de fechas para presentación
CAMPOS_FECHA = {
    'Análisis y cronograma': 'Análisis y cronograma (fecha programada)',
    'Estándares': 'Estándares (fecha programada)',
    'Publicación': 'Fecha de publicación programada'
}

# Duración de los hitos en días (para el Gantt)
DURACION_HITOS = {
    'Acuerdo de compromiso': 7,  # 1 semana
    'Análisis y cronograma': 14,  # 2 semanas
    'Estándares': 14,  # 2 semanas
    'Publicación': 7   # 1 semana
}

# Colores para cada tipo de hito
COLORES_HITOS = {
    'Acuerdo de compromiso': '#1E40AF',
    'Análisis y cronograma': '#047857',
    'Estándares': '#B45309',
    'Publicación': '#BE185D'
}

# Días de alerta para fechas próximas a vencer
DIAS_ALERTA = 30
