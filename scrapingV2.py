import streamlit as st
import requests
import re
import json
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
    
    def extract_csrf_token(self, html_content):
        """Extrae token CSRF del HTML usando regex"""
        # Buscar tokens comunes
        patterns = [
            r'name="token"\s+value="([^"]+)"',
            r'name="_token"\s+value="([^"]+)"',
            r'name="csrf_token"\s+value="([^"]+)"',
            r'"token":"([^"]+)"',
            r'csrf_token["\s]*:["\s]*([^"]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def extract_form_data(self, html_content):
        """Extrae datos de formulario usando regex"""
        form_data = {}
        
        # Buscar inputs hidden
        hidden_pattern = r'<input[^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\'][^>]*>'
        matches = re.findall(hidden_pattern, html_content, re.IGNORECASE)
        
        for name, value in matches:
            form_data[name] = value
        
        return form_data
    
    def login(self, email, password):
        """Intenta hacer login en Sufarmed"""
        try:
            # Obtener la página de login
            login_url = "https://sufarmed.com/sufarmed/iniciar-sesion"
            response = self.session.get(login_url, timeout=10)
            
            if response.status_code != 200:
                return False, f"No se pudo acceder a la página de login (Status: {response.status_code})"
            
            # Extraer datos del formulario
            form_data = self.extract_form_data(response.text)
            
            # Buscar token CSRF
            csrf_token = self.extract_csrf_token(response.text)
            if csrf_token:
                form_data['token'] = csrf_token
            
            # Agregar credenciales
            form_data.update({
                'email': email,
                'password': password,
                'submitLogin': '1'
            })
            
            # Enviar datos de login
            login_response = self.session.post(login_url, data=form_data, timeout=10)
            
            # Verificar si el login fue exitoso
            if login_response.status_code == 200:
                if "mi-cuenta" in login_response.url or "my-account" in login_response.url:
                    return True, "Login exitoso"
                elif "dashboard" in login_response.url or "account" in login_response.url:
                    return True, "Login exitoso"
                elif "error" in login_response.text.lower() or "incorrect" in login_response.text.lower():
                    return False, "Credenciales incorrectas"
                else:
                    return True, "Login posiblemente exitoso"
            else:
                return False, f"Error en login (Status: {login_response.status_code})"
                
        except requests.exceptions.Timeout:
            return False, "Timeout: El servidor tardó demasiado en responder"
        except requests.exceptions.ConnectionError:
            return False, "Error de conexión: No se pudo conectar al servidor"
        except Exception as e:
            return False, f"Error durante el login: {str(e)}"
    
    def extract_prices_from_html(self, html_content):
        """Extrae precios del HTML usando regex"""
        price_patterns = [
            r'<[^>]*class=["\'][^"\']*product-price[^"\']*["\'][^>]*content=["\']([^"\']+)["\']',
            r'content=["\']([0-9]+\.?[0-9]*)["\'][^>]*class=["\'][^"\']*product-price',
            r'<[^>]*class=["\'][^"\']*price[^"\']*["\'][^>]*>\s*\$?([0-9]+\.?[0-9]*)',
            r'\$([0-9]+\.?[0-9]*)',
            r'precio["\s]*:["\s]*([0-9]+\.?[0-9]*)',
            r'"price"["\s]*:["\s]*([0-9]+\.?[0-9]*)'
        ]
        
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Limpiar el precio
                price = str(match).replace('$', '').replace(',', '').strip()
                if price and price.replace('.', '').isdigit():
                    prices.append(price)
        
        return prices
    
    def buscar_producto(self, producto):
        """Busca un producto y obtiene su precio"""
        try:
            # URL de búsqueda - probar diferentes formatos
            search_urls = [
                f"https://sufarmed.com/sufarmed/buscar?s={producto}",
                f"https://sufarmed.com/sufarmed/buscar?controller=search&s={producto}",
                f"https://sufarmed.com/buscar?s={producto}"
            ]
            
            for search_url in search_urls:
                try:
                    # Realizar búsqueda
                    response = self.session.get(search_url, timeout=15)
                    
                    if response.status_code == 200:
                        # Extraer precios del HTML
                        prices = self.extract_prices_from_html(response.text)
                        
                        if prices:
                            # Retornar el primer precio encontrado
                            return prices[0], "Precio encontrado"
                        
                        # Si no se encuentran precios, verificar si hay productos
                        if "producto" in response.text.lower() or "product" in response.text.lower():
                            return None, "Productos encontrados pero sin precios visibles"
                    
                except requests.exceptions.Timeout:
                    continue
                except Exception:
                    continue
            
            return None, "No se encontraron productos o no se pudo acceder a la búsqueda"
                
        except Exception as e:
            return None, f"Error durante la búsqueda: {str(e)}"
    
    def buscar_sin_login(self, producto):
        """Busca producto sin login como fallback"""
        try:
            # Intentar búsqueda directa sin login
            search_url = f"https://sufarmed.com/buscar?s={producto}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                prices = self.extract_prices_from_html(response.text)
                if prices:
                    return prices[0], "Precio encontrado (sin login)"
            
            return None, "No se encontraron resultados sin login"
            
        except Exception as e:
            return None, f"Error en búsqueda sin login: {str(e)}"

# Configuración de credenciales
st.markdown("### 🔐 Configuración de Cuenta")

# Credenciales desde el frontend
with st.expander("Configurar Credenciales de Sufarmed", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        email_input = st.text_input(
            "📧 Email de Sufarmed:",
            placeholder="tu-email@ejemplo.com",
            help="Ingresa tu email registrado en Sufarmed"
        )
    
    with col2:
        password_input = st.text_input(
            "🔒 Contraseña de Sufarmed:",
            type="password",
            placeholder="Tu contraseña",
            help="Ingresa tu contraseña de Sufarmed"
        )
    
    if not email_input or not password_input:
        st.warning("⚠️ Debes ingresar tu email y contraseña para continuar")
    else:
        st.success("✅ Credenciales configuradas correctamente")

# Interfaz de usuario
st.markdown("### 🔍 Buscar Producto")

# Input para el producto
producto_buscar = st.text_input(
    "Ingresa el nombre del producto:",
    placeholder="Ej: Paracetamol, Ibuprofeno, etc."
)

# Botón para buscar
if st.button("🔍 Buscar Precio", type="primary"):
    if not email_input or not password_input:
        st.error("❌ Debes configurar tu email y contraseña primero")
    elif producto_buscar:
        # Mostrar spinner mientras se procesa
        with st.spinner("Buscando producto..."):
            try:
                # Crear el scraper
                scraper = SufarmedScraper()
                
                # Usar las credenciales del usuario
                EMAIL = email_input
                PASSWORD = password_input
                
                precio = None
                search_message = ""
                
                # Realizar login
                st.info("🔐 Intentando iniciar sesión en Sufarmed...")
                login_success, login_message = scraper.login(EMAIL, PASSWORD)
                
                if login_success:
                    st.success(f"✅ {login_message}")
                    
                    # Buscar producto con login
                    st.info(f"🔍 Buscando: {producto_buscar}")
                    precio, search_message = scraper.buscar_producto(producto_buscar)
                    
                else:
                    st.warning(f"⚠️ Login falló: {login_message}")
                    st.info("🔄 Intentando búsqueda sin login...")
                    precio, search_message = scraper.buscar_sin_login(producto_buscar)
                
                # Mostrar resultados
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
                    st.info("💡 Intenta con un nombre de producto más específico o verifica que esté disponible en Sufarmed")
                    
            except Exception as e:
                st.error(f"❌ Error general: {str(e)}")
    else:
        st.warning("⚠️ Por favor ingresa un nombre de producto")

# Información adicional
st.markdown("---")
st.markdown("### ℹ️ Información")
st.info("""
- **Paso 1**: Configura tus credenciales de Sufarmed arriba
- **Paso 2**: Ingresa el nombre del producto que deseas buscar
- **Paso 3**: Haz clic en "Buscar Precio"
- Esta aplicación busca precios de productos en Sufarmed.com
- Utiliza requests y regex para extraer información (100% compatible con Streamlit Cloud)
- Intenta hacer login automáticamente, pero también funciona sin login
- Los resultados mostrados corresponden al primer precio encontrado
""")

# Debug/Test section
with st.expander("🔧 Panel de Pruebas"):
    if st.button("Probar Conexión"):
        with st.spinner("Probando conexión..."):
            try:
                response = requests.get("https://sufarmed.com", timeout=5)
                st.success(f"✅ Conexión exitosa - Status: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Error de conexión: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Desarrollado con Streamlit 🚀 | Sin dependencias externas</div>", 
    unsafe_allow_html=True
)
