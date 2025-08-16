import streamlit as st
import requests
import re
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
            login_url = "https://sufarmed.com/sufarmed/iniciar-sesion"
            response = self.session.get(login_url, timeout=15)
            
            if response.status_code != 200:
                return False, f"No se pudo acceder a la página de login (Status: {response.status_code})"
            
            # Extraer datos del formulario
            form_data = {}
            
            # Buscar campos hidden
            hidden_pattern = r'<input[^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']'
            hidden_matches = re.findall(hidden_pattern, response.text, re.IGNORECASE)
            for name, value in hidden_matches:
                form_data[name] = value
            
            # Buscar token CSRF
            token_patterns = [
                r'name=["\']token["\'][^>]*value=["\']([^"\']+)["\']',
                r'name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']'
            ]
            
            for pattern in token_patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    form_data['token'] = match.group(1)
                    break
            
            # Agregar credenciales
            form_data.update({
                'email': email,
                'password': password,
                'submitLogin': '1'
            })
            
            # Headers para POST
            post_headers = {
                'Referer': login_url,
                'Origin': 'https://sufarmed.com',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Enviar datos de login
            login_response = self.session.post(
                login_url, 
                data=form_data, 
                headers=post_headers,
                timeout=15
            )
            
            # Verificar login exitoso
            if login_response.status_code == 200:
                response_text = login_response.text.lower()
                final_url = login_response.url.lower()
                
                success_indicators = [
                    "mi-cuenta" in final_url,
                    "my-account" in final_url,
                    "dashboard" in final_url,
                    "bienvenido" in response_text,
                    "logout" in response_text
                ]
                
                if any(success_indicators):
                    return True, "Login exitoso"
                elif "error" in response_text or "incorrect" in response_text:
                    return False, "Credenciales incorrectas"
                else:
                    return True, "Login posiblemente exitoso"
            
            return False, f"Error en login (Status: {login_response.status_code})"
                
        except Exception as e:
            return False, f"Error durante el login: {str(e)}"
    
    def extract_product_info(self, html_content):
        """Extrae información de productos del HTML"""
        try:
            products = []
            
            # Patrones para encontrar productos
            product_patterns = [
                r'<article[^>]*class=[^>]*product[^>]*>(.*?)</article>',
                r'<div[^>]*class=[^>]*product-miniature[^>]*>(.*?)</div>',
                r'<li[^>]*class=[^>]*product[^>]*>(.*?)</li>'
            ]
            
            for pattern in product_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                
                for match in matches[:3]:  # Solo los primeros 3 productos
                    product_info = self.parse_product_container(match)
                    if product_info:
                        products.append(product_info)
            
            return products
            
        except Exception as e:
            return []
    
    def parse_product_container(self, container_html):
        """Analiza un contenedor de producto para extraer nombre y precio"""
        try:
            # Extraer nombre del producto
            name_patterns = [
                r'<h3[^>]*>.*?<a[^>]*>(.*?)</a>',
                r'<h2[^>]*>.*?<a[^>]*>(.*?)</a>',
                r'<a[^>]*title=["\']([^"\']+)["\']',
                r'<a[^>]*>(.*?)</a>'
            ]
            
            product_name = None
            for pattern in name_patterns:
                match = re.search(pattern, container_html, re.IGNORECASE | re.DOTALL)
                if match:
                    name = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    name = re.sub(r'\s+', ' ', name)
                    if len(name) > 5:
                        product_name = name
                        break
            
            # Extraer precio
            price_patterns = [
                r'content=["\']([0-9]+[.,]?[0-9]*)["\']',
                r'>\$([0-9]+[.,]?[0-9]*)<',
                r'>([0-9]+[.,]?[0-9]*)\s*<',
                r'\$([0-9]+[.,]?[0-9]*)'
            ]
            
            product_price = None
            for pattern in price_patterns:
                match = re.search(pattern, container_html, re.IGNORECASE)
                if match:
                    price = match.group(1).replace(',', '').strip()
                    if price and price.replace('.', '').isdigit():
                        product_price = price
                        break
            
            if product_name and product_price:
                return {
                    'nombre': product_name,
                    'precio': product_price
                }
            
            return None
            
        except Exception as e:
            return None
    
    def buscar_producto(self, producto):
        """Busca un producto y retorna información"""
        try:
            # URLs de búsqueda
            search_urls = [
                f"https://sufarmed.com/sufarmed/buscar?s={producto}",
                f"https://sufarmed.com/buscar?s={producto}"
            ]
            
            for search_url in search_urls:
                try:
                    response = self.session.get(search_url, timeout=15)
                    
                    if response.status_code == 200:
                        products = self.extract_product_info(response.text)
                        
                        if products:
                            return products[0], "Producto encontrado exitosamente"
                        
                        # Fallback: buscar solo precios
                        prices = self.extract_simple_prices(response.text)
                        if prices:
                            return {
                                'nombre': f"Producto relacionado con '{producto}'",
                                'precio': prices[0]
                            }, "Precio encontrado"
                        
                except Exception:
                    continue
            
            return None, "No se encontraron productos"
                
        except Exception as e:
            return None, f"Error durante la búsqueda: {str(e)}"
    
    def extract_simple_prices(self, html_content):
        """Extrae precios simples del HTML"""
        price_patterns = [
            r'content=["\']([0-9]+[.,]?[0-9]*)["\']',
            r'\$([0-9]+[.,]?[0-9]*)',
            r'>([0-9]+[.,]?[0-9]*)<'
        ]
        
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                price = str(match).replace(',', '').strip()
                if price and price.replace('.', '').isdigit() and float(price) > 0:
                    prices.append(price)
        
        return prices[:5]  # Solo los primeros 5 precios
    
    def buscar_sin_login(self, producto):
        """Búsqueda sin login"""
        try:
            search_url = f"https://sufarmed.com/buscar?s={producto}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                products = self.extract_product_info(response.text)
                if products:
                    return products[0], "Producto encontrado sin login"
                
                prices = self.extract_simple_prices(response.text)
                if prices:
                    return {
                        'nombre': f"Producto relacionado con '{producto}'",
                        'precio': prices[0]
                    }, "Precio encontrado sin login"
            
            return None, "No se encontraron resultados sin login"
            
        except Exception as e:
            return None, f"Error en búsqueda sin login: {str(e)}"

# Configuración de credenciales
st.markdown("### 🔐 Configuración de Cuenta")

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

# Interfaz de búsqueda
st.markdown("### 🔍 Buscar Producto")

producto_buscar = st.text_input(
    "Ingresa el nombre del producto:",
    placeholder="Ej: Paracetamol, Ibuprofeno, etc."
)

# Botón para buscar
if st.button("🔍 Buscar Precio", type="primary"):
    if not email_input or not password_input:
        st.error("❌ Debes configurar tu email y contraseña primero")
    elif producto_buscar:
        with st.spinner("Buscando producto..."):
            try:
                scraper = SufarmedScraper()
                
                EMAIL = email_input
                PASSWORD = password_input
                
                # Login
                st.info("🔐 Intentando iniciar sesión en Sufarmed...")
                login_success, login_message = scraper.login(EMAIL, PASSWORD)
                
                producto_info = None
                search_message = ""
                
                if login_success:
                    st.success(f"✅ {login_message}")
                    st.info(f"🔍 Buscando: {producto_buscar}")
                    producto_info, search_message = scraper.buscar_producto(producto_buscar)
                else:
                    st.warning(f"⚠️ Login falló: {login_message}")
                    st.info("🔄 Intentando búsqueda sin login...")
                    producto_info, search_message = scraper.buscar_sin_login(producto_buscar)
                
                # Mostrar resultados
                if producto_info:
                    st.markdown("---")
                    st.markdown("### 💰 Resultado de la Búsqueda")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            label="📦 Producto Encontrado",
                            value="Ver abajo"
                        )
                        st.info(f"**{producto_info['nombre']}**")
                    
                    with col2:
                        precio_display = f"${producto_info['precio']}" if producto_info['precio'] != "No disponible" else "No disponible"
                        st.metric(
                            label="💵 Precio",
                            value=precio_display
                        )
                    
                    st.success(f"🎉 {search_message}")
                    
                    with st.expander("ℹ️ Información Detallada"):
                        st.write(f"**Término búsqueda:** {producto_buscar}")
                        st.write(f"**Nombre completo:** {producto_info['nombre']}")
                        st.write(f"**Precio:** ${producto_info['precio']}")
                        st.write(f"**Estado:** {search_message}")
                else:
                    st.warning(f"⚠️ {search_message}")
                    st.info("💡 Consejos para mejorar la búsqueda:")
                    st.markdown("""
                    - Verifica que tus credenciales sean correctas
                    - Intenta con un nombre de producto más específico
                    - Prueba con sinónimos del producto
                    - Verifica que el producto esté disponible en Sufarmed
                    """)
                    
            except Exception as e:
                st.error(f"❌ Error general: {str(e)}")
    else:
        st.warning("⚠️ Por favor ingresa un nombre de producto")

# Información
st.markdown("---")
st.markdown("### ℹ️ Información")
st.info("""
- **Paso 1**: Configura tus credenciales de Sufarmed arriba
- **Paso 2**: Ingresa el nombre del producto que deseas buscar  
- **Paso 3**: Haz clic en "Buscar Precio"
- Esta aplicación extrae precios y nombres completos de productos en Sufarmed.com
""")

# Panel de debug
with st.expander("🔧 Panel de Pruebas y Debug"):
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Probar Conexión"):
            with st.spinner("Probando conexión..."):
                try:
                    response = requests.get("https://sufarmed.com", timeout=5)
                    st.success(f"✅ Conexión exitosa - Status: {response.status_code}")
                except Exception as e:
                    st.error(f"❌ Error de conexión: {str(e)}")
    
    with col2:
        if st.button("Debug Login"):
            if email_input and password_input:
                with st.spinner("Analizando login..."):
                    try:
                        scraper = SufarmedScraper()
                        response = scraper.session.get("https://sufarmed.com/sufarmed/iniciar-sesion", timeout=10)
                        
                        st.write("**Análisis de login:**")
                        st.write(f"- Status: {response.status_code}")
                        st.write(f"- URL: {response.url}")
                        
                        email_fields = re.findall(r'name=["\']([^"\']*email[^"\']*)["\']', response.text, re.IGNORECASE)
                        if email_fields:
                            st.write(f"- Campos email: {email_fields}")
                        
                        tokens = re.findall(r'name=["\']([^"\']*token[^"\']*)["\']', response.text, re.IGNORECASE)
                        if tokens:
                            st.write(f"- Tokens: {tokens}")
                            
                        st.success("✅ Análisis completado")
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("Configura credenciales primero")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Desarrollado con Streamlit 🚀</div>", 
    unsafe_allow_html=True
)
