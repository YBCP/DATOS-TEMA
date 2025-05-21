# 2. config.py - Configuración de la página y estilos

import streamlit as st

def setup_page():
    """Configura la página de Streamlit."""
    st.set_page_config(
        page_title="Tablero de Control de Cronogramas",
        page_icon="📊",
        layout="wide"
    )


def load_css():
    """Carga estilos CSS personalizados."""
    st.markdown("""
    <style>
    /* Estilos existentes... */

    .title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E40AF;
        margin-bottom: 1rem;
    }

    .subtitle {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1E40AF;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 0.5rem;
    }

    /* Más estilos existentes... */

    /* Estilos para las alertas */
    .alert-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    }

    .alert-vencido {
        background-color: #fee2e2;
        border-left: 4px solid #b91c1c;
    }

    .alert-proximo {
        background-color: #fef3c7;
        border-left: 4px solid #b45309;
    }

    .alert-retraso {
        background-color: #dbeafe;
        border-left: 4px solid #1e40af;
    }

    /* Estilos para indicadores de estado */
    .estado-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: bold;
    }

    .estado-vencido {
        background-color: #fee2e2;
        color: #b91c1c;
    }

    .estado-proximo {
        background-color: #fef3c7;
        color: #b45309;
    }

    .estado-retraso {
        background-color: #dbeafe;
        color: #1e40af;
    }

    /* Estilos para las tablas de alertas */
    .stDataFrame {
        margin-bottom: 2rem;
    }

    /* Mejorar la visibilidad de los días de rezago */
    .dias-rezago-positivo {
        color: #b91c1c;
        font-weight: bold;
    }

    .dias-rezago-negativo {
        color: #047857;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
