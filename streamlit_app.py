import streamlit as st
import pandas as pd
from datetime import timedelta, time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión Buenos Aires Bazar",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS (SÓLO PARA OCULTAR MENÚS, SIN CAMBIAR COLORES DE FONDO) ---
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. SEGURIDAD (CANDADO) ---
# Si prefieres quitar la clave, pon un # al inicio de las siguientes 4 líneas
clave = st.sidebar.text_input("🔒 Clave de Acceso", type="password")
if clave != "1519":
    st.warning("👈 Ingresa la clave '1519' en el menú lateral para ver los datos.")
    st.stop() 

# --- 4. ENCABEZADO ---
col_logo, col_texto = st.columns([1, 6])

with col_logo:
    # Reemplaza el enlace entre comillas por la dirección de tu logo
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
        # Lectura inteligente
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

            # Métricas
            k1, k2, k3 = st.columns(3)
            k1.metric("Días Asistidos", len(final))
            
            tarde_total = final['Minutos_Tarde'].sum()
            k2.metric("Minutos Tarde Acumulados", f"{tarde_total} min")

            # Tabla
            st.write("👇 Selecciona una fila para ver el detalle:")
            
            # --- CORRECCIÓN DE COLORES DE LA TABLA ---
            # Usamos una lógica más segura que no rompa el modo oscuro
            def colorear(val):
                # En lugar de colores pastel fijos, usamos lógica condicional simple
                # Si quieres que se vea bien en oscuro y claro, a veces es mejor no forzar background
                if val < 4:
                    return 'color: red; font-weight: bold' # Letra roja negrita (se lee en blanco y negro)
                else:
                    return 'color: green' # Letra verde
            
            display_cols = final[['Date', 'Fichadas', 'Minutos_Tarde']]
            
            # Aplicamos estilo solo al texto, no al fondo, para evitar problemas de contraste
            event = st.dataframe(
                display_cols.style.applymap(colorear, subset=['Fichadas']),
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True
            )

            # Drill-down
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
