import streamlit as st
import requests
from bs4 import BeautifulSoup
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

class SufarmedScraper:
    def __init__(self):
        self.session = requests.Session()
        # Headers para simular un navegador real
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def login(self, email, password):
        """Intenta hacer login en Sufarmed"""
        try:
            # Obtener la página de login
            login_url = "https://sufarmed.com/sufarmed/iniciar-sesion"
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                return False, "No se pudo acceder a la página de login"
            
            # Parsear la página para obtener tokens CSRF si existen
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar campos ocultos (tokens CSRF, etc.)
            hidden_inputs = soup.find_all('input', {'type': 'hidden'})
            form_data = {}
            for input_field in hidden_inputs:
                name = input_field.get('name')
                value = input_field.get('value')
                if name:
                    form_data[name] = value or ''
            
            # Agregar credenciales
            form_data.update({
                'email': email,
                'password': password,
                'submitLogin': '1'
            })
            
            # Enviar datos de login
            login_response = self.session.post(login_url, data=form_data)
            
            # Verificar si el login fue exitoso
            if "mi-cuenta" in login_response.url or "my-account" in login_response.url:
                return True, "Login exitoso"
            elif "error" in login_response.text.lower() or "incorrect" in login_response.text.lower():
                return False, "Credenciales incorrectas"
            else:
                return True, "Login posiblemente exitoso"
                
        except Exception as e:
            return False, f"Error durante el login: {str(e)}"
    
    def buscar_producto(self, producto):
        """Busca un producto y obtiene su precio"""
        try:
            # URL de búsqueda
            search_url = "https://sufarmed.com/sufarmed/buscar"
            
            # Parámetros de búsqueda
            search_params = {
                's': producto,
                'controller': 'search'
            }
            
            # Realizar búsqueda
            response = self.session.get(search_url, params=search_params)
            
            if response.status_code != 200:
                return None, "No se pudo realizar la búsqueda"
            
            # Parsear resultados
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar precios con diferentes selectores posibles
            price_selectors = [
                '.product-price[content]',
                '.price',
                '.product-price',
                '[data-price]',
                '.price-current',
                '.current-price'
            ]
            
            precio = None
            for selector in price_selectors:
                price_elements = soup.select(selector)
                if price_elements:
                    price_element = price_elements[0]
                    # Intentar obtener precio del atributo content
                    precio = price_element.get('content')
                    if not precio:
                        # Si no existe content, obtener el texto
                        precio = price_element.get_text().strip()
                    if precio:
                        # Limpiar el precio
                        precio = precio.replace('$', '').replace(',', '').strip()
                        if precio.replace('.', '').isdigit():
                            break
            
            if precio:
                return precio, "Precio encontrado"
            else:
                return None, "No se encontraron precios"
                
        except Exception as e:
            return None, f"Error durante la búsqueda: {str(e)}"

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
        with st.spinner("Buscando producto..."):
            try:
                # Crear el scraper
                scraper = SufarmedScraper()
                
                # Credenciales
                EMAIL = "laubec83@gmail.com"
                PASSWORD = "Sr3ChK8pBoSEScZ"
                
                # Realizar login
                st.info("🔐 Iniciando sesión en Sufarmed...")
                login_success, login_message = scraper.login(EMAIL, PASSWORD)
                
                if login_success:
                    st.success(f"✅ {login_message}")
                    
                    # Buscar producto
                    st.info(f"🔍 Buscando: {producto_buscar}")
                    precio, search_message = scraper.buscar_producto(producto_buscar)
                    
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
                        st.warning(f"⚠️ {search_message}")
                else:
                    st.error(f"❌ {login_message}")
                    
            except Exception as e:
                st.error(f"❌ Error general: {str(e)}")
    else:
        st.warning("⚠️ Por favor ingresa un nombre de producto")

# Información adicional
st.markdown("---")
st.markdown("### ℹ️ Información")
st.info("""
- Esta aplicación busca precios de productos en Sufarmed.com
- Utiliza web scraping con requests y BeautifulSoup (compatible con Streamlit Cloud)
- Los resultados mostrados corresponden al primer producto encontrado
- El proceso puede tomar unos segundos
""")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Desarrollado con Streamlit 🚀</div>", 
    unsafe_allow_html=True
)
