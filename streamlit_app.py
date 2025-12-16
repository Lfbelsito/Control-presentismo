import streamlit as st
import pandas as pd
from datetime import timedelta, time

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Gestión Buenos Aires Bazar",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed" # Inicia cerrado, pero ahora SÍ tendrás botón para abrirlo
)

# --- 2. ESTILOS CSS (CORREGIDO) ---
st.markdown("""
    <style>
        /* Ocultamos el menú de los 3 puntos y el pie de página "Made with Streamlit" */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* BORRÉ LA LÍNEA QUE OCULTABA EL HEADER */
        /* Ahora podrás ver la flecha para abrir la barra lateral */
    </style>
""", unsafe_allow_html=True)

# --- 3. SISTEMA DE LOGIN ---
CLAVE_REAL = "1519"

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

def verificar_clave():
    if st.session_state['password_input'] == CLAVE_REAL:
        st.session_state['autenticado'] = True
    else:
        st.error("⛔ Contraseña incorrecta")

if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔒 Acceso Restringido")
        st.markdown("**Buenos Aires BAZAR** | Sistema de Gestión")
        st.text_input("Clave de acceso:", type="password", key="password_input", on_change=verificar_clave)
    st.stop()

# =========================================================
# APP PRINCIPAL
# =========================================================

# --- ENCABEZADO ---
col_logo, col_texto = st.columns([1, 6])
with col_logo:
    # 👇 LINK DE TU LOGO
    LOGO_URL = "https://cdn-icons-png.flaticon.com/512/4091/4091968.png" 
    st.image(LOGO_URL, width=80)
with col_texto:
    st.title("Control de Asistencia Completo")
    st.caption("Presentismo + Tardanzas + Extras (con Umbral) | **Buenos Aires BAZAR**")

st.divider()

# --- 4. CONFIGURACIÓN LATERAL (HORARIOS Y UMBRAL) ---
with st.sidebar:
    st.header("⚙️ Configuración de Turno")
    
    st.markdown("### 🕒 Definir Horarios")
    hora_entrada = st.time_input("Horario APERTURA (Ingreso)", value=time(10, 00))
    hora_salida = st.time_input("Horario CIERRE (Salida)", value=time(20, 00))
    
    st.divider()
    
    st.markdown("### ⏳ Regla de Extras")
    umbral_extras = st.number_input("Mínimo minutos para contar Extra", min_value=0, value=30, step=5)
    
    st.info(f"""
    **Reglas Actuales:**
    1. **Tarde:** Si entra después de las {hora_entrada.strftime('%H:%M')}.
    2. **Extras:** Solo cuentan si se queda **más de {umbral_extras} minutos** después de las {hora_salida.strftime('%H:%M')}.
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
        
        st.success("✅ Datos procesados.")

        # --- CÁLCULO MAESTRO ---
        diario = df_limpio.groupby(['Empleado', 'Date'])['Marca Temporal'].agg(['min', 'max', 'count']).reset_index()
        diario.columns = ['Empleado', 'Date', 'Entrada_Real', 'Salida_Real', 'Cant_Fichadas']

        # Función Lógica Tiempos
        def calcular_tiempos(row):
            entrada = row['Entrada_Real']
            salida = row['Salida_Real']
            
            objetivo_entrada = entrada.replace(hour=hora_entrada.hour, minute=hora_entrada.minute, second=0)
            objetivo_salida = salida.replace(hour=hora_salida.hour, minute=hora_salida.minute, second=0)
            
            # 1. TARDANZA
            minutos_tarde = 0
            if entrada > objetivo_entrada:
                diff = entrada - objetivo_entrada
                minutos_tarde = int(diff.total_seconds() / 60)
            
            # 2. EXTRAS (CON UMBRAL)
            minutos_extras = 0
            if salida > objetivo_salida:
                diff_extra = salida - objetivo_salida
                minutos_reales = int(diff_extra.total_seconds() / 60)
                
                if minutos_reales >= umbral_extras:
                    minutos_extras = minutos_reales
                else:
                    minutos_extras = 0 
            
            return pd.Series([minutos_tarde, minutos_extras])

        # Aplicamos cálculos
        diario[['Min_Tarde', 'Min_Extras']] = diario.apply(calcular_tiempos, axis=1)

        # --- SECCIÓN INTERACTIVA ---
        st.subheader("👤 Análisis Individual")
        
        lista = sorted(diario['Empleado'].unique())
        seleccion = st.selectbox("Selecciona un empleado:", lista)

        if seleccion:
            datos_emp = diario[diario['Empleado'] == seleccion].copy()
            datos_crudos_emp = df_limpio[df_limpio['Empleado'] == seleccion].copy()
            
            # --- MÉTRICAS ---
            k1, k2, k3, k4 = st.columns(4)
            
            dias_totales = len(datos_emp)
            dias_completos = len(datos_emp[datos_emp['Cant_Fichadas'] == 4])
            tarde_total = datos_emp['Min_Tarde'].sum()
            extra_total = datos_emp['Min_Extras'].sum()

            k1.metric("Días Asistidos", dias_totales)
            k2.metric("Días Completos", dias_completos, 
                      delta="OK" if dias_completos == dias_totales else "Incompleto")
            k3.metric("Minutos Tarde", f"{tarde_total} min", delta_color="inverse")
            k4.metric("Horas Extras (Aprobadas)", f"{extra_total} min", delta="A favor")

            # --- TABLA VISUAL ---
            st.write("👇 **Haz clic en una fila** para ver detalle:")
            
            tabla_ver = datos_emp[['Date', 'Cant_Fichadas', 'Entrada_Real', 'Salida_Real', 'Min_Tarde', 'Min_Extras']].copy()
            
            tabla_ver['Entrada_Real'] = tabla_ver['Entrada_Real'].dt.strftime('%H:%M')
            tabla_ver['Salida_Real'] = tabla_ver['Salida_Real'].dt.strftime('%H:%M')

            def colorear_celdas(row):
                estilos = [''] * len(row)
                
                # Presentismo
                if row['Cant_Fichadas'] < 4:
                    estilos[1] = 'color: #d32f2f; font-weight: bold;' # Rojo
                else:
                    estilos[1] = 'color: #388e3c; font-weight: bold;' # Verde
                
                # Tarde
                if row['Min_Tarde'] > 5:
                    estilos[4] = 'color: #d32f2f; font-weight: bold;'
                
                # Extras
                if row['Min_Extras'] > 0:
                    estilos[5] = 'color: #1976d2; font-weight: bold;'
                
                return estilos

            event = st.dataframe(
                tabla_ver.style.apply(colorear_celdas, axis=1),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            if len(event.selection.rows) > 0:
                idx = event.selection.rows[0]
                fecha_seleccionada = tabla_ver.iloc[idx]['Date']
                st.info(f"🔎 **Detalle del día {fecha_seleccionada}:**")
                detalle = datos_crudos_emp[datos_crudos_emp['Date'] == fecha_seleccionada][['Time', 'Device Name']]
                st.table(detalle)
            
            else:
                st.caption("Selecciona un día para ver los fichajes exactos.")

        # --- REPORTE GENERAL ---
        st.divider()
        with st.expander("📊 Ver Rankings del Mes"):
            col_rank1, col_rank2 = st.columns(2)
            with col_rank1:
                st.markdown("**🏆 Ranking: Extras Acumuladas**")
                rank_extra = diario.groupby('Empleado')['Min_Extras'].sum().reset_index()
                st.dataframe(rank_extra.sort_values('Min_Extras', ascending=False), use_container_width=True, hide_index=True)
            with col_rank2:
                st.markdown("**🐢 Ranking: Tardanzas Acumuladas**")
                rank_tarde = diario.groupby('Empleado')['Min_Tarde'].sum().reset_index()
                st.dataframe(rank_tarde.sort_values('Min_Tarde', ascending=False), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
