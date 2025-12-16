import streamlit as st
import pandas as pd
from datetime import timedelta, time

# --- 1. CONFIGURACIÓN DE PÁGINA (Debe ser lo primero) ---
st.set_page_config(
    page_title="Gestión Buenos Aires Bazar",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS CSS (MAQUILLAJE) ---
# Esto oculta el menú de hamburguesa y el pie de página de Streamlit
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp {
            background-color: #FAFAFA; /* Fondo gris muy clarito (opcional) */
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. SEGURIDAD (CANDADO) ---
# Si no quieres clave, borra o comenta estas 4 líneas
clave = st.sidebar.text_input("🔒 Clave de Acceso", type="password")
if clave != "admin123":
    st.warning("👈 Por favor, ingresa la clave en el menú lateral para acceder.")
    st.stop() # Frena la app aquí

# --- 4. ENCABEZADO CON LOGO ---
col_logo, col_texto = st.columns([1, 6])

with col_logo:
    # URL DE TU LOGO: Reemplaza lo que está entre comillas por el link de tu logo real.
    # Si no tienes link, deja este que es un icono genérico de empresa.
    LOGO_URL = "https://share.google/1glH6eX5vazkTjNo2"
    st.image(LOGO_URL, width=80)

with col_texto:
    st.title("Control de Asistencia")
    st.caption("Sistema de gestión de fichadas | **Buenos Aires BAZAR**")

st.divider()

# --- 5. CONFIGURACIÓN LATERAL ---
with st.sidebar:
    st.header("⚙️ Parámetros")
    hora_entrada = st.time_input("Horario Ingreso", value=time(10, 00))
    st.info("Se calculan tardanzas basadas en este horario.")

# --- 6. LÓGICA PRINCIPAL ---
archivo = st.file_uploader("📂 Sube el archivo Transaction aquí", type=['csv', 'xlsx'])

if archivo:
    try:
        # Lectura
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo, header=3)
        else:
            df = pd.read_excel(archivo, header=3)

        if 'First Name' not in df.columns:
            st.error("⚠️ Formato incorrecto. Verifica los encabezados.")
            st.stop()

        # Limpieza
        df['Empleado'] = df['Last Name'] + ', ' + df['First Name']
        df['Marca Temporal'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        df = df.sort_values(by=['Empleado', 'Marca Temporal'])

        # Filtro Rebotes (20 min)
        df['Diferencia'] = df.groupby('Empleado')['Marca Temporal'].diff()
        filtro_rebotes = (df['Diferencia'].isna()) | (df['Diferencia'] > timedelta(minutes=20))
        df_limpio = df[filtro_rebotes].copy()
        
        st.success("✅ Datos procesados exitosamente.")

        # Cálculo Tardanzas
        primeras_fichadas = df_limpio.groupby(['Empleado', 'Date'])['Marca Temporal'].min().reset_index()

        def calcular_demora(fecha_hora_real):
            objetivo = fecha_hora_real.replace(hour=hora_entrada.hour, minute=hora_entrada.minute, second=0)
            if fecha_hora_real > objetivo:
                return int((fecha_hora_real - objetivo).total_seconds() / 60)
            return 0 

        primeras_fichadas['Minutos_Tarde'] = primeras_fichadas['Marca Temporal'].apply(calcular_demora)

        # --- SECCIÓN INTERACTIVA ---
        st.subheader("👤 Detalle por Empleado")
        
        lista = sorted(df_limpio['Empleado'].unique())
        seleccion = st.selectbox("Selecciona un empleado:", lista)

        if seleccion:
            datos_emp = df_limpio[df_limpio['Empleado'] == seleccion].copy()
            tardanzas_emp = primeras_fichadas[primeras_fichadas['Empleado'] == seleccion].copy()

            # Merge
            resumen = datos_emp.groupby('Date').size().reset_index(name='Fichadas')
            final = pd.merge(resumen, tardanzas_emp[['Date', 'Minutos_Tarde']], on='Date', how='left')

            # Métricas visuales
            k1, k2, k3 = st.columns(3)
            k1.metric("Días Asistidos", len(final))
            
            tarde_total = final['Minutos_Tarde'].sum()
            k2.metric("Minutos Tarde Acumulados", f"{tarde_total} min", 
                      delta="- Malo" if tarde_total > 60 else "Normal") # Delta muestra flechita

            # Tabla con colores ESTÉTICOS
            st.write("👇 Selecciona una fila para ver el detalle:")
            
            # Definimos los colores de la tabla
            def colorear(val):
                # Rojo suave si faltan fichadas, Verde suave si está OK
                color = '#ffcdd2' if val < 4 else '#e8f5e9' 
                return f'background-color: {color}'

            display_cols = final[['Date', 'Fichadas', 'Minutos_Tarde']]
            
            event = st.dataframe(
                display_cols.style.applymap(colorear, subset=['Fichadas']),
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True
            )

            # Drill-down (Detalle al hacer clic)
            if len(event.selection.rows) > 0:
                idx = event.selection.rows[0]
                fecha = display_cols.iloc[idx]['Date']
                st.info(f"🕒 Fichadas del día **{fecha}**:")
                st.table(datos_emp[datos_emp['Date'] == fecha][['Time', 'Device Name']])

        # --- REPORTE FINAL ---
        st.divider()
        with st.expander("📊 Ver Ranking General de Tardanzas"):
            rank = primeras_fichadas.groupby('Empleado')['Minutos_Tarde'].sum().reset_index()
            st.dataframe(rank.sort_values('Minutos_Tarde', ascending=False), use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
