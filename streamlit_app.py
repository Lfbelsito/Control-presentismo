import streamlit as st
import pandas as pd
from datetime import timedelta, time

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Gestión Buenos Aires Bazar", # Título en la pestaña del navegador
    page_icon="🏢", # Icono en la pestaña
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS PERSONALIZADO (Estilos) ---
# Esto oculta el menú de hamburguesa y el footer de "Made with Streamlit" para que parezca una app pro
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. ENCABEZADO CON LOGO ---
col_logo, col_titulo = st.columns([1, 5])

with col_logo:
    # Aquí puedes poner la URL de tu logo si la tienes en internet.
    # Si no, usamos un emoji gigante como logo temporal.
    st.markdown("# 🏢") 

with col_titulo:
    st.title("Panel de Control de Asistencia")
    st.markdown("**Buenos Aires BAZAR** | Reporte Mensual")

st.divider() # Una línea separadora elegante

# ... AQUI SIGUE EL RESTO DE TU CÓDIGO (Desde el Sidebar) ...


import streamlit as st
import pandas as pd
from datetime import timedelta, time

# Configuración de la página
st.set_page_config(page_title="Control de Asistencia", layout="wide")

st.title("Sistema de Control de Presentismo")
st.markdown("Sube el archivo Transaction exportado por el sistema.")

# --- BARRA LATERAL PARA CONFIGURACIÓN ---
with st.sidebar:
    st.header("Configuración")
    hora_entrada = st.time_input("Horario de Ingreso estipulado", value=time(10, 00))
    st.info(f"Se calcularán tardanzas después de las {hora_entrada}")

# 1. CARGA DE DATOS
archivo = st.file_uploader("Sube el archivo CSV o Excel aquí", type=['csv', 'xlsx'])

if archivo:
    try:
        # Leemos el archivo saltando encabezados
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo, header=3)
        else:
            df = pd.read_excel(archivo, header=3)

        if 'First Name' not in df.columns:
            st.error("Error de formato. Verifica los encabezados en la fila 4.")
            st.stop()

        # 2. LIMPIEZA Y PREPARACIÓN
        df['Empleado'] = df['Last Name'] + ', ' + df['First Name']
        
        # Unimos Fecha y Hora
        df['Marca Temporal'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        
        # Ordenamos
        df = df.sort_values(by=['Empleado', 'Marca Temporal'])

        # 3. FILTRO DE REBOTES (< 20 min)
        df['Diferencia'] = df.groupby('Empleado')['Marca Temporal'].diff()
        filtro_rebotes = (df['Diferencia'].isna()) | (df['Diferencia'] > timedelta(minutes=20))
        df_limpio = df[filtro_rebotes].copy()
        
        st.success("Archivo procesado y limpio de duplicados.")

        # --- CÁLCULO DE TARDANZAS ---
        primeras_fichadas = df_limpio.groupby(['Empleado', 'Date'])['Marca Temporal'].min().reset_index()

        def calcular_demora(fecha_hora_real):
            objetivo = fecha_hora_real.replace(hour=hora_entrada.hour, minute=hora_entrada.minute, second=0)
            if fecha_hora_real > objetivo:
                diferencia = fecha_hora_real - objetivo
                return int(diferencia.total_seconds() / 60)
            return 0 

        primeras_fichadas['Minutos_Tarde'] = primeras_fichadas['Marca Temporal'].apply(calcular_demora)


        # 4. ANÁLISIS POR EMPLEADO
        st.divider()
        st.header("Analizar por Empleado")
        
        lista_empleados = sorted(df_limpio['Empleado'].unique())
        empleado_seleccionado = st.selectbox("Selecciona un empleado:", lista_empleados)

        if empleado_seleccionado:
            datos_empleado = df_limpio[df_limpio['Empleado'] == empleado_seleccionado].copy()
            tardanzas_empleado = primeras_fichadas[primeras_fichadas['Empleado'] == empleado_seleccionado].copy()

            resumen_diario = datos_empleado.groupby('Date').size().reset_index(name='Fichadas')
            resumen_final = pd.merge(resumen_diario, tardanzas_empleado[['Date', 'Minutos_Tarde']], on='Date', how='left')

            col1, col2, col3, col4 = st.columns(4)
            
            dias_totales = len(resumen_final)
            dias_ok = len(resumen_final[resumen_final['Fichadas'] == 4])
            total_minutos_tarde = resumen_final['Minutos_Tarde'].sum()
            promedio_llegada = resumen_final[resumen_final['Minutos_Tarde'] > 0]['Minutos_Tarde'].mean()

            col1.metric("Días Asistidos", dias_totales)
            col2.metric("Días Completos", dias_ok)
            col3.metric("Minutos Tarde Total", f"{total_minutos_tarde} min")
            col4.metric("Promedio demora", f"{promedio_llegada:.1f} min" if total_minutos_tarde > 0 else "0 min")

            st.subheader("Detalle Diario")
            
            tabla_mostrar = resumen_final[['Date', 'Fichadas', 'Minutos_Tarde']].copy()
            tabla_mostrar['Estado'] = tabla_mostrar['Fichadas'].apply(lambda x: "OK" if x==4 else "Incompleto")
            
            st.dataframe(
                tabla_mostrar.style.bar(subset=['Minutos_Tarde'], color='#ffcdd2'),
                use_container_width=True
            )

        # 5. REPORTE GENERAL
        st.divider()
        st.header("Ranking de Tardanzas")
        
        ranking = primeras_fichadas.groupby('Empleado')['Minutos_Tarde'].sum().reset_index()
        ranking = ranking.sort_values('Minutos_Tarde', ascending=False)
        
        st.dataframe(ranking, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
