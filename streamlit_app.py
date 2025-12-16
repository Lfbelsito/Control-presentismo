import streamlit as st
import pandas as pd
from datetime import timedelta, time
import io # Nueva librería para manejar la descarga en Excel

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
        .stApp { background-color: #FFFFFF; color: #000000; }
        [data-testid="stSidebar"] { background-color: #F8F8F8; }
        h1, h2, h3, h4, h5 { color: #000000 !important; font-weight: 700 !important; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stMetricValue"] { color: #000000; }
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
        st.markdown(f":no_entry: <span style='color:#D32F2F; font-weight:bold'>Contraseña incorrecta</span>", unsafe_allow_html=True)

if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔒 Acceso Restringido")
        st.markdown("**Buenos Aires BAZAR** | Sistema de Gestión")
        st.text_input("Ingrese clave:", type="password", key="password_input", on_change=verificar_clave)
    st.stop()

# =========================================================
# APP PRINCIPAL
# =========================================================

# --- FUNCIÓN PARA GENERAR EXCEL (NUEVO) ---
def convertir_a_excel(df, nombre_hoja='Datos'):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=nombre_hoja)
    processed_data = output.getvalue()
    return processed_data

# --- ENCABEZADO ---
col_logo, col_texto = st.columns([1, 6])
with col_logo:
    # 👇 LINK DE TU LOGO
    LOGO_URL = "https://www.buenosairesbazar.com.ar/Temp/App_WebSite/App_PictureFiles/logonew.svg" 
    st.image(LOGO_URL, width=80)
with col_texto:
    st.title("Control de Asistencia Completo")
    st.caption("Presentismo + Tardanzas + Extras (con Umbral) | **Buenos Aires BAZAR**")

st.divider()

# --- 4. CONFIGURACIÓN LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración de Turno")
    st.markdown("### 🕒 Definir Horarios")
    hora_entrada = st.time_input("Horario APERTURA (Ingreso)", value=time(10, 00))
    hora_salida = st.time_input("Horario CIERRE (Salida)", value=time(20, 00))
    st.divider()
    st.markdown("### ⏳ Regla de Extras")
    umbral_extras = st.number_input("Mínimo minutos para contar Extra", min_value=0, value=30, step=5)
    st.divider()
    if st.button("Cerrar Sesión", type="primary"): 
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

        # Limpieza
        df['Empleado'] = df['Last Name'] + ', ' + df['First Name']
        df['Marca Temporal'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        df = df.sort_values(by=['Empleado', 'Marca Temporal'])

        # Filtro Rebotes
        df['Diferencia'] = df.groupby('Empleado')['Marca Temporal'].diff()
        filtro_rebotes = (df['Diferencia'].isna()) | (df['Diferencia'] > timedelta(minutes=20))
        df_limpio = df[filtro_rebotes].copy()
        
        st.success("✅ Datos procesados.")

        # Cálculo Maestro
        diario = df_limpio.groupby(['Empleado', 'Date'])['Marca Temporal'].agg(['min', 'max', 'count']).reset_index()
        diario.columns = ['Empleado', 'Date', 'Entrada_Real', 'Salida_Real', 'Cant_Fichadas']

        def calcular_tiempos(row):
            entrada = row['Entrada_Real']
            salida = row['Salida_Real']
            objetivo_entrada = entrada.replace(hour=hora_entrada.hour, minute=hora_entrada.minute, second=0)
            objetivo_salida = salida.replace(hour=hora_salida.hour, minute=hora_salida.minute, second=0)
            
            # Tardanza
            minutos_tarde = 0
            if entrada > objetivo_entrada:
                diff = entrada - objetivo_entrada
                minutos_tarde = int(diff.total_seconds() / 60)
            
            # Extras (con umbral)
            minutos_extras = 0
            if salida > objetivo_salida:
                diff_extra = salida - objetivo_salida
                minutos_reales = int(diff_extra.total_seconds() / 60)
                if minutos_reales >= umbral_extras:
                    minutos_extras = minutos_reales
                else:
                    minutos_extras = 0 
            return pd.Series([minutos_tarde, minutos_extras])

        diario[['Min_Tarde', 'Min_Extras']] = diario.apply(calcular_tiempos, axis=1)

        # --- SECCIÓN INTERACTIVA ---
        st.subheader("👤 Análisis Individual")
        
        lista = sorted(diario['Empleado'].unique())
        seleccion = st.selectbox("Selecciona un empleado:", lista)

        if seleccion:
            datos_emp = diario[diario['Empleado'] == seleccion].copy()
            datos_crudos_emp = df_limpio[df_limpio['Empleado'] == seleccion].copy()
            
            # Métricas
            k1, k2, k3, k4 = st.columns(4)
            dias_totales = len(datos_emp)
            dias_completos = len(datos_emp[datos_emp['Cant_Fichadas'] == 4])
            tarde_total = datos_emp['Min_Tarde'].sum()
            extra_total = datos_emp['Min_Extras'].sum()

            k1.metric("Días Asistidos", dias_totales)
            k2.metric("Días Completos", dias_completos, delta="OK" if dias_completos == dias_totales else "Incompleto")
            k3.metric("Minutos Tarde", f"{tarde_total} min", delta_color="inverse")
            k4.metric("Horas Extras", f"{extra_total} min", delta="A favor")

            st.write("👇 **Haz clic en una fila** para ver detalle:")
            
            # Preparar tabla visual
            columnas_a_mostrar = [
                'Date', 
                'Cant_Fichadas', 
                'Entrada_Real', 
                'Salida_Real', 
                'Min_Tarde', 
                'Min_Extras'
            ]
            tabla_ver = datos_emp[columnas_a_mostrar].copy()
            
            # Guardamos una copia para descargar en Excel antes de formatear las horas como texto
            tabla_excel = tabla_ver.copy() 

            # Formato visual
            tabla_ver['Entrada_Real'] = tabla_ver['Entrada_Real'].dt.strftime('%H:%M')
            tabla_ver['Salida_Real'] = tabla_ver['Salida_Real'].dt.strftime('%H:%M')

            # Colores
            def colorear_celdas(row):
                estilos = [''] * len(row)
                BRAND_RED = '#D32F2F'    
                BRAND_YELLOW_BG = '#FFF9C4'
                
                if row['Cant_Fichadas'] < 4:
                    estilos[1] = f'color: {BRAND_RED}; font-weight: 900;' 
                if row['Min_Tarde'] > 5:
                    estilos[4] = f'color: {BRAND_RED}; font-weight: bold;'
                if row['Min_Extras'] > 0:
                    estilos[5] = f'background-color: {BRAND_YELLOW_BG}; color: black; font-weight: bold;'
                return estilos

            event = st.dataframe(
                tabla_ver.style.apply(colorear_celdas, axis=1),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )

            # --- BOTÓN DE DESCARGA EXCEL (NUEVO) ---
            excel_data = convertir_a_excel(tabla_excel, nombre_hoja=seleccion[:30])
            st.download_button(
                label=f"📥 Descargar Ficha de {seleccion} en Excel",
                data=excel_data,
                file_name=f'Ficha_{seleccion}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            # ---------------------------------------

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
        with st.expander("📊 Ver Rankings y Descargar Reporte General"):
            col_rank1, col_rank2 = st.columns(2)
            with col_rank1:
                st.markdown("**🏆 Ranking: Extras Acumuladas**")
                rank_extra = diario.groupby('Empleado')['Min_Extras'].sum().reset_index()
                st.dataframe(
                    rank_extra.sort_values('Min_Extras', ascending=False)
                    .style.highlight_max(subset=['Min_Extras'], color='#FFF9C4'),
                    use_container_width=True, hide_index=True
                )
            with col_rank2:
                st.markdown("**🐢 Ranking: Tardanzas Acumuladas**")
                rank_tarde = diario.groupby('Empleado')['Min_Tarde'].sum().reset_index()
                st.dataframe(
                    rank_tarde.sort_values('Min_Tarde', ascending=False)
                    .style.highlight_max(subset=['Min_Tarde'], color='#ffcdd2'),
                    use_container_width=True, hide_index=True
                )
            
            # Botón descarga general
            st.divider()
            excel_general = convertir_a_excel(diario, nombre_hoja='Reporte Mensual')
            st.download_button(
                label="📥 Descargar Reporte Completo de Todos (Excel)",
                data=excel_general,
                file_name='Reporte_Mensual_Completo.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
