import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

# Configurar la página de Streamlit
st.set_page_config(
    page_title="Sufarmed - Buscador de Precios",
    page_icon="💊",
    layout="centered"
)

# Título principal
st.title("🏥 Sufarmed - Buscador de Precios")
st.markdown("---")

def setup_driver():
    """Configurar el WebDriver de Chrome para Streamlit"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ejecutar en modo headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_sufarmed(driver, email, password):
    """Realizar login en Sufarmed"""
    try:
        # Navegar a la página de login
        driver.get("https://sufarmed.com/sufarmed/iniciar-sesion?back=https%3A%2F%2Fsufarmed.com%2Fsufarmed%2Finiciar-sesion%3Fback%3Dmy-account")
        time.sleep(3)
        
        # Encontrar y llenar los campos de login
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")
        
        email_field.send_keys(email)
        password_field.send_keys(password)
        
        # Hacer clic en el botón de login
        login_button = driver.find_element(By.ID, "submit-login")
        login_button.click()
        time.sleep(5)
        
        return True
    except Exception as e:
        st.error(f"Error durante el login: {str(e)}")
        return False

def buscar_producto(driver, producto):
    """Buscar un producto en Sufarmed"""
    try:
        # Buscar la caja de búsqueda y escribir el producto
        search_box = driver.find_element(By.CLASS_NAME, "form-search-control")
        search_box.clear()
        search_box.send_keys(producto)
        search_box.submit()
        time.sleep(3)
        
        # Obtener el precio del primer producto
        precios = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "product-price"))
        )
        
        if precios:
            primer_precio = precios[0].get_attribute("content")
            return primer_precio
        else:
            return None
            
    except Exception as e:
        st.error(f"Error durante la búsqueda: {str(e)}")
        return None

# Interfaz de usuario
st.markdown("### 🔍 Buscar Producto")

# Input para el producto
producto_buscar = st.text_input(
    "Ingresa el nombre del producto:",
    placeholder="Ej: Paracetamol, Ibuprofeno, etc."
)

# Botón para buscar
if st.button("🔍 Buscar Precio", type="primary"):
    if producto_buscar:
        # Mostrar spinner mientras se procesa
        with st.spinner("Iniciando sesión y buscando producto..."):
            driver = None
            try:
                # Configurar el driver
                driver = setup_driver()
                
                # Credenciales (considera usar st.secrets para mayor seguridad)
                EMAIL = "laubec83@gmail.com"
                PASSWORD = "Sr3ChK8pBoSEScZ"
                
                # Realizar login
                st.info("🔐 Iniciando sesión en Sufarmed...")
                if login_sufarmed(driver, EMAIL, PASSWORD):
                    st.success("✅ Sesión iniciada correctamente")
                    
                    # Buscar producto
                    st.info(f"🔍 Buscando: {producto_buscar}")
                    precio = buscar_producto(driver, producto_buscar)
                    
                    if precio:
                        # Mostrar el resultado
                        st.markdown("---")
                        st.markdown("### 💰 Resultado de la Búsqueda")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                label="Producto",
                                value=producto_buscar
                            )
                        with col2:
                            st.metric(
                                label="Precio",
                                value=f"${precio}"
                            )
                        
                        st.success("🎉 ¡Búsqueda completada exitosamente!")
                    else:
                        st.warning("⚠️ No se encontraron precios para este producto")
                else:
                    st.error("❌ Error al iniciar sesión")
                    
            except Exception as e:
                st.error(f"❌ Error general: {str(e)}")
            finally:
                # Cerrar el driver
                if driver:
                    driver.quit()
    else:
        st.warning("⚠️ Por favor ingresa un nombre de producto")

# Información adicional
st.markdown("---")
st.markdown("### ℹ️ Información")
st.info("""
- Esta aplicación busca precios de productos en Sufarmed.com
- Los resultados mostrados corresponden al primer producto encontrado
- El proceso puede tomar unos segundos debido a la navegación web automatizada
""")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Desarrollado con Streamlit 🚀</div>", 
    unsafe_allow_html=True
)