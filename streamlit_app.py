import streamlit as st
import pandas as pd
from datetime import timedelta, time

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Gestión Buenos Aires Bazar",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS CSS ---
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEMA DE LOGIN ---
CLAVE_REAL = "1519"

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

def verificar_clave():
    if st.session_state['password_input'] == CLAVE_REAL:1519
        st.session_state['autenticado'] = True
    else:
        st.error("⛔ Contraseña incorrecta")

if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔒 Acceso Restringido")
        st.markdown("**Buenos Aires BAZAR** | Sistema de Gestión")
        st.text_input("Clave de acceso:", type="password", key="password_input", on_change=verificar_clave)
        st.caption("Ingresa la clave para desbloquear.")
    st.stop()

# =========================================================
# APP PRINCIPAL (SOLO SI ESTÁ LOGUEADO)
# =========================================================

# --- ENCABEZADO ---
col_logo, col_texto = st.columns([1, 6])
with col_logo:
    # 👇 LINK DE TU LOGO
    LOGO_URL = "https://cdn-icons-png.flaticon.com/512/4091/4091968.png" 
    st.image(LOGO_URL, width=80)
with col_texto:
    st.title("Control de Asistencia y Extras")
    st.caption("Gestión de Tardanzas y Horas Extras | **Buenos Aires BAZAR**")

st.divider()

# --- 4. CONFIGURACIÓN LATERAL (DOBLE HORARIO) ---
with st.sidebar:
    st.header("⚙️ Configuración de Turno")
    
    st.markdown("### 🕒 Horarios Estipulados")
    # Dos relojes: Entrada y Salida
    hora_entrada = st.time_input("Horario de APERTURA (Ingreso)", value=time(10, 00))
    hora_salida = st.time_input("Horario de CIERRE (Salida)", value=time(20, 00))
    
    st.info(f"""
    **Reglas aplicadas:**
    1. Llegadas antes de las {hora_entrada.strftime('%H:%M')} no suman extras.
    2. Salidas después de las {hora_salida.strftime('%H:%M')} suman extras.
    """)
    
    st.divider()
    if st.button("Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.rerun()

# --- 5. LÓGICA DE PROCESAMIENTO ---
archivo = st.file_uploader("📂 Sube el archivo Transaction aquí", type=['csv', 'xlsx'])

if archivo:
    try:
        # Carga
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo, header=3)
        else:
            df = pd.read_excel(archivo, header=3)

        if 'First Name' not in df.columns:
            st.error("⚠️ Formato incorrecto. Verifica los encabezados.")
            st.stop()

        # Limpieza básica
        df['Empleado'] = df['Last Name'] + ', ' + df['First Name']
        df['Marca Temporal'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        df = df.sort_values(by=['Empleado', 'Marca Temporal'])

        # Filtro de Rebotes (20 min)
        df['Diferencia'] = df.groupby('Empleado')['Marca Temporal'].diff()
        filtro_rebotes = (df['Diferencia'].isna()) | (df['Diferencia'] > timedelta(minutes=20))
        df_limpio = df[filtro_rebotes].copy()
        
        st.success("✅ Datos procesados. Configura los horarios en el menú lateral.")

        # --- CÁLCULO DE MINUTOS (NUEVA LÓGICA) ---
        
        # Agrupamos por día: Buscamos la PRIMERA y la ÚLTIMA fichada del día
        diario = df_limpio.groupby(['Empleado', 'Date'])['Marca Temporal'].agg(['min', 'max', 'count']).reset_index()
        diario.columns = ['Empleado', 'Date', 'Entrada_Real', 'Salida_Real', 'Cant_Fichadas']

        # Función Maestra: Calcula Tardanza y Extra en una sola pasada
        def calcular_tiempos(row):
            entrada = row['Entrada_Real']
            salida = row['Salida_Real']
            
            # Definimos los objetivos de ese día específico
            objetivo_entrada = entrada.replace(hour=hora_entrada.hour, minute=hora_entrada.minute, second=0)
            objetivo_salida = salida.replace(hour=hora_salida.hour, minute=hora_salida.minute, second=0)
            
            # 1. CÁLCULO DE TARDANZA
            minutos_tarde = 0
            if entrada > objetivo_entrada:
                diff = entrada - objetivo_entrada
                minutos_tarde = int(diff.total_seconds() / 60)
            
            # 2. CÁLCULO DE EXTRAS
            # Solo si se fue DESPUÉS del horario de salida
            minutos_extras = 0
            if salida > objetivo_salida:
                diff_extra = salida - objetivo_salida
                minutos_extras = int(diff_extra.total_seconds() / 60)
            
            return pd.Series([minutos_tarde, minutos_extras])

        # Aplicamos la función
        diario[['Min_Tarde', 'Min_Extras']] = diario.apply(calcular_tiempos, axis=1)

        # --- SECCIÓN INTERACTIVA ---
        st.subheader("👤 Análisis Individual")
        
        lista = sorted(diario['Empleado'].unique())
        seleccion = st.selectbox("Selecciona un empleado:", lista)

        if seleccion:
            # Filtramos datos del empleado
            datos_emp = diario[diario['Empleado'] == seleccion].copy()
            
            # Métricas Generales
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Días Trabajados", len(datos_emp))
            k2.metric("Llegadas Tarde (Total)", f"{datos_emp['Min_Tarde'].sum()} min")
            k3.metric("Horas Extras (Total)", f"{datos_emp['Min_Extras'].sum()} min", delta="A favor del empleado")
            
            promedio_extra = datos_emp['Min_Extras'].mean()
            k4.metric("Promedio Extras/Día", f"{int(promedio_extra)} min")

            st.write("👇 **Detalle diario (Entrada y Salida):**")
            
            # Preparamos tabla bonita
            tabla_ver = datos_emp[['Date', 'Entrada_Real', 'Salida_Real', 'Min_Tarde', 'Min_Extras']].copy()
            
            # Formateamos las horas para que no muestre la fecha completa en las celdas de hora
            tabla_ver['Entrada_Real'] = tabla_ver['Entrada_Real'].dt.strftime('%H:%M')
            tabla_ver['Salida_Real'] = tabla_ver['Salida_Real'].dt.strftime('%H:%M')

            # Lógica de colores para la tabla
            def colorear_celdas(row):
                estilos = [''] * len(row) # Por defecto nada
                
                # Si llegó tarde, pintamos la celda de Min_Tarde en rojo
                if row['Min_Tarde'] > 5: # Tolerancia de 5 min (opcional)
                    estilos[3] = 'color: #ff5252; font-weight: bold' # Rojo
                
                # Si hizo extras, pintamos la celda de Min_Extras en azul/verde
                if row['Min_Extras'] > 0:
                    estilos[4] = 'color: #448aff; font-weight: bold' # Azul
                
                return estilos

            # Mostrar tabla interactiva
            st.dataframe(
                tabla_ver.style.apply(colorear_celdas, axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            st.caption("Nota: Si 'Min_Extras' es 0, significa que se retiró a su hora o antes. No contamos ingresos tempranos como extra.")

        # --- REPORTE GENERAL ---
        st.divider()
        with st.expander("📊 Ver Ranking: ¿Quién hizo más Extras?"):
            rank = diario.groupby('Empleado')[['Min_Tarde', 'Min_Extras']].sum().reset_index()
            # Ordenamos por quien hizo mas extras
            st.dataframe(rank.sort_values('Min_Extras', ascending=False), use_container_width=True)

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
