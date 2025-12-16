import streamlit as st
import pandas as pd
from datetime import timedelta, time

# --- 1. CONFIGURACIÓN INICIAL (Siempre va primero) ---
st.set_page_config(
    page_title="Gestión Buenos Aires Bazar",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS CSS (Para ocultar elementos de Streamlit) ---
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEMA DE LOGIN (PANTALLA DE BLOQUEO) ---

# Definimos la clave correcta
CLAVE_REAL = "1519"

# Inicializamos el estado de autenticación si no existe
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# Función para verificar la contraseña
def verificar_clave():
    if st.session_state['password_input'] == CLAVE_REAL:
        st.session_state['autenticado'] = True
    else:
        st.error("⛔ Contraseña incorrecta")

# SI NO ESTÁ AUTENTICADO, MOSTRAMOS SOLO EL LOGIN
if not st.session_state['autenticado']:
    # Centramos el login usando columnas
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("## 🔒 Acceso Restringido")
        st.markdown("Sistema de Gestión de Personal | **Buenos Aires BAZAR**")
        
        # Campo de contraseña (input)
        st.text_input(
            "Ingresa la clave de acceso:", 
            type="password", 
            key="password_input", 
            on_change=verificar_clave
        )
        
        st.caption("Por favor, ingresa la clave asignada para desbloquear el sistema.")
    
    # Detenemos el código aquí para que no cargue nada más
    st.stop()


# =========================================================
# A PARTIR DE AQUÍ, SOLO SE EJECUTA SI LA CLAVE ES CORRECTA
# =========================================================

# --- 4. ENCABEZADO CON LOGO ---
col_logo, col_texto = st.columns([1, 6])

with col_logo:
    # 👇 PEGA AQUÍ EL LINK DE TU LOGO
    LOGO_URL = "https://share.google/HfXDL7GQSlrgNYNVP" 
    st.image(LOGO_URL, width=80)

with col_texto:
    st.title("Control de Asistencia")
    st.caption("Panel de Administración | Reporte Mensual")

st.divider()

# --- 5. CONFIGURACIÓN LATERAL (Ahora sí aparece el sidebar) ---
with st.sidebar:
    st.header("⚙️ Parámetros")
    hora_entrada = st.time_input("Horario Ingreso", value=time(10, 00))
    st.info("Se calculan tardanzas basadas en este horario.")
    
    # Botón de Cerrar Sesión (Opcional)
    if st.button("Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.rerun()

# --- 6. LÓGICA PRINCIPAL (TU APP) ---
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

        # Filtro Rebotes
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

            resumen = datos_emp.groupby('Date').size().reset_index(name='Fichadas')
            final = pd.merge(resumen, tardanzas_emp[['Date', 'Minutos_Tarde']], on='Date', how='left')

            k1, k2, k3 = st.columns(3)
            k1.metric("Días Asistidos", len(final))
            
            tarde_total = final['Minutos_Tarde'].sum()
            k2.metric("Minutos Tarde Acumulados", f"{tarde_total} min")

            st.write("👇 Selecciona una fila para ver el detalle:")
            
            def colorear(val):
                if val < 4:
                    return 'color: #ff5252; font-weight: bold' 
                else:
                    return 'color: #69f0ae' 
            
            display_cols = final[['Date', 'Fichadas', 'Minutos_Tarde']]
            
            event = st.dataframe(
                display_cols.style.applymap(colorear, subset=['Fichadas']),
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True
            )

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
