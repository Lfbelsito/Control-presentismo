import streamlit as st
import pandas as pd
from datetime import timedelta, time

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Gestión Buenos Aires Bazar",
    page_icon="🏢",
    layout="wide"
)

# Ocultar menú de Streamlit para estilo limpio
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Encabezado
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    st.markdown("# 🏢") 
with col_titulo:
    st.title("Panel de Control de Asistencia")
    st.markdown("**Buenos Aires BAZAR** | Reporte Mensual")

st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    hora_entrada = st.time_input("Horario de Ingreso", value=time(10, 00))
    st.info("Calculando tardanzas después de las 10:00 AM")

# 1. CARGA DE DATOS
archivo = st.file_uploader("📂 Sube el archivo Transaction aquí", type=['csv', 'xlsx'])

if archivo:
    try:
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo, header=3)
        else:
            df = pd.read_excel(archivo, header=3)

        if 'First Name' not in df.columns:
            st.error("⚠️ Error: El archivo no tiene el formato correcto (Fila 4 encabezados).")
            st.stop()

        # 2. LIMPIEZA
        df['Empleado'] = df['Last Name'] + ', ' + df['First Name']
        # Convertir fecha y hora
        df['Marca Temporal'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))
        
        # Ordenar
        df = df.sort_values(by=['Empleado', 'Marca Temporal'])

        # Filtro de Rebotes (20 min)
        df['Diferencia'] = df.groupby('Empleado')['Marca Temporal'].diff()
        filtro_rebotes = (df['Diferencia'].isna()) | (df['Diferencia'] > timedelta(minutes=20))
        df_limpio = df[filtro_rebotes].copy()
        
        st.success(f"✅ Archivo procesado. Se limpiaron duplicados.")

        # 3. CÁLCULO DE TARDANZAS
        primeras_fichadas = df_limpio.groupby(['Empleado', 'Date'])['Marca Temporal'].min().reset_index()

        def calcular_demora(fecha_hora_real):
            objetivo = fecha_hora_real.replace(hour=hora_entrada.hour, minute=hora_entrada.minute, second=0)
            if fecha_hora_real > objetivo:
                diferencia = fecha_hora_real - objetivo
                return int(diferencia.total_seconds() / 60)
            return 0 

        primeras_fichadas['Minutos_Tarde'] = primeras_fichadas['Marca Temporal'].apply(calcular_demora)

        # 4. ANÁLISIS POR EMPLEADO (INTERACTIVO)
        st.divider()
        st.subheader("👤 Analizar Empleado")
        
        lista_empleados = sorted(df_limpio['Empleado'].unique())
        empleado_seleccionado = st.selectbox("Buscar empleado:", lista_empleados)

        if empleado_seleccionado:
            # Datos del empleado
            datos_empleado = df_limpio[df_limpio['Empleado'] == empleado_seleccionado].copy()
            tardanzas_emp = primeras_fichadas[primeras_fichadas['Empleado'] == empleado_seleccionado].copy()

            # Resumen diario
            resumen_diario = datos_empleado.groupby('Date').size().reset_index(name='Fichadas')
            resumen_final = pd.merge(resumen_diario, tardanzas_emp[['Date', 'Minutos_Tarde']], on='Date', how='left')

            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("Días Asistidos", len(resumen_final))
            c2.metric("Minutos Tarde (Mes)", f"{resumen_final['Minutos_Tarde'].sum()} min")
            
            # Tabla Interactiva
            st.write("👇 **Haz clic en cualquier fila** para ver los horarios exactos de ese día:")
            
            tabla_mostrar = resumen_final[['Date', 'Fichadas', 'Minutos_Tarde']].copy()
            
            # Función de colores
            def color_estado(val):
                color = '#ffcdd2' if val < 4 else '#c8e6c9' # Rojo suave vs Verde suave
                return f'background-color: {color}'

            # CREAMOS LA TABLA CON SELECCIÓN ACTIVADA
            event = st.dataframe(
                tabla_mostrar.style.applymap(color_estado, subset=['Fichadas']),
                use_container_width=True,
                on_select="rerun",     # Esto activa la interactividad
                selection_mode="single-row", # Solo deja elegir una fila a la vez
                hide_index=True
            )

            # LÓGICA DE CLIC: Si alguien selecciona una fila...
            if len(event.selection.rows) > 0:
                # 1. Identificar qué fila se tocó
                indice_seleccionado = event.selection.rows[0]
                fecha_seleccionada = tabla_mostrar.iloc[indice_seleccionado]['Date']
                
                # 2. Buscar los fichajes de esa fecha exacta
                detalles_dia = datos_empleado[datos_empleado['Date'] == fecha_seleccionada]
                
                # 3. Mostrar la "Lupa"
                st.info(f"🔎 **Detalle del día {fecha_seleccionada}:**")
                
                # Mostramos una tablita limpia con las horas
                st.table(detalles_dia[['Time', 'Device Name']])
            
            else:
                st.caption("Selecciona una fecha arriba para ver el detalle de horarios.")


        # 5. REPORTE GENERAL
        st.divider()
        with st.expander("📊 Ver Ranking de Tardanzas General"):
            ranking = primeras_fichadas.groupby('Empleado')['Minutos_Tarde'].sum().reset_index()
            ranking = ranking.sort_values('Minutos_Tarde', ascending=False)
            st.dataframe(ranking, use_container_width=True)

    except Exception as e:
        st.error(f"Hubo un error procesando: {e}")

