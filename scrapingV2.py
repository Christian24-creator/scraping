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
        """Intenta hacer login en Sufarmed con debug mejorado"""
        try:
            # Obtener la página de login
            login_url = "https://sufarmed.com/sufarmed/iniciar-sesion"
            response = self.session.get(login_url, timeout=15)
            
            if response.status_code != 200:
                return False, f"No se pudo acceder a la página de login (Status: {response.status_code})"
            
            # Debug: verificar que llegamos a la página correcta
            if "login" not in response.text.lower() and "email" not in response.text.lower():
                return False, "La página no parece ser un formulario de login"
            
            # Extraer datos del formulario con patrones más amplios
            form_data = {}
            
            # Patrones más amplios para campos hidden
            hidden_patterns = [
                r'<input[^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']',
                r'<input[^>]*name=["\']([^"\']+)["\'][^>]*type=["\']hidden["\'][^>]*value=["\']([^"\']*)["\']',
                r'<input[^>]*value=["\']([^"\']*)["\'][^>]*name=["\']([^"\']+)["\'][^>]*type=["\']hidden["\']'
            ]
            
            for pattern in hidden_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    if len(match) == 2:
                        name, value = match
                        form_data[name] = value
            
            # Buscar tokens CSRF con más patrones
            csrf_patterns = [
                r'name=["\']token["\'][^>]*value=["\']([^"\']+)["\']',
                r'name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
                r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
                r'name=["\']authenticity_token["\'][^>]*value=["\']([^"\']+)["\']',
                r'"token"[:\s]*"([^"]+)"',
                r'"_token"[:\s]*"([^"]+)"'
            ]
            
            csrf_token = None
            for pattern in csrf_patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    csrf_token = match.group(1)
                    break
            
            if csrf_token:
                form_data['token'] = csrf_token
            
            # Probar diferentes nombres de campos
            possible_field_names = {
                'email': ['email', 'username', 'user', 'login_email', 'customer_email'],
                'password': ['password', 'passwd', 'pwd', 'login_password', 'customer_password'],
                'submit': ['submitLogin', 'submit', 'login', 'submit_login', '1']
            }
            
            # Agregar credenciales con diferentes nombres posibles
            form_data.update({
                'email': email,
                'password': password,
                'submitLogin': '1'
            })
            
            # También probar nombres alternativos
            for field_type, names in possible_field_names.items():
                for name in names:
                    if field_type == 'email':
                        form_data[name] = email
                    elif field_type == 'password':
                        form_data[name] = password
                    elif field_type == 'submit':
                        form_data[name] = '1'
            
            # Headers adicionales para el POST
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
                timeout=15,
                allow_redirects=True
            )
            
            # Debug de la respuesta
            final_url = login_response.url.lower()
            response_text = login_response.text.lower()
            
            # Verificar si el login fue exitoso - criterios más amplios
            success_indicators = [
                "mi-cuenta" in final_url,
                "my-account" in final_url,
                "dashboard" in final_url,
                "account" in final_url,
                "profile" in final_url,
                "bienvenido" in response_text,
                "welcome" in response_text,
                "logout" in response_text,
                "cerrar sesion" in response_text,
                "salir" in response_text
            ]
            
            # Indicadores de error
            error_indicators = [
                "error" in response_text and ("login" in response_text or "email" in response_text),
                "incorrect" in response_text,
                "invalid" in response_text and ("email" in response_text or "password" in response_text),
                "incorrecto" in response_text,
                "invalido" in response_text,
                "credenciales" in response_text and "incorrectas" in response_text
            ]
            
            if any(success_indicators):
                return True, "Login exitoso"
            elif any(error_indicators):
                return False, "Credenciales incorrectas o error en login"
            elif login_response.status_code == 200:
                # Si llegamos aquí, intentar determinar si estamos logueados
                if "login" in response_text and "password" in response_text:
                    return False, "Aún en página de login - posible error de credenciales"
                else:
                    return True, "Login posiblemente exitoso (verificación ambigua)"
            else:
                return False, f"Error HTTP en login (Status: {login_response.status_code})"
                
        except requests.exceptions.Timeout:
            return False, "Timeout: El servidor tardó demasiado en responder durante el login"
        except requests.exceptions.ConnectionError:
            return False, "Error de conexión durante el login"
        except Exception as e:
            return False, f"Error inesperado durante el login: {str(e)}"
    
    def extract_products_from_html(self, html_content):
        """Extrae información de productos (nombre y precio) del HTML usando regex"""
        products = []
        
        # Patrones para encontrar contenedores de productos
        product_container_patterns = [
            r'<article[^>]*class=["\'][^"\']*product[^"\']*["\'][^>]*>(.*?)</article>',
            r'<div[^>]*class=["\'][^"\']*product-miniature[^"\']*["\'][^>]*>(.*?)</div>',
            r'<div[^>]*class=["\'][^"\']*product-item[^"\']*["\'][^>]*>(.*?)</div>',
            r'<li[^>]*class=["\'][^"\']*product[^"\']*["\'][^>]*>(.*?)</li>'
        ]
        
        for pattern in product_container_patterns:
            containers = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            for container in containers[:5]:  # Limitar a los primeros 5 productos
                product_info = self.extract_product_info_from_container(container)
                if product_info and product_info not in products:
                    products.append(product_info)
        
        return products
    
    def extract_product_info_from_container(self, container_html):
        """Extrae nombre y precio de un contenedor de producto"""
        try:
            # Patrones para extraer nombres de productos
            name_patterns = [
                r'<h3[^>]*class=["\'][^"\']*product-title[^"\']*["\'][^>]*>.*?<a[^>]*>(.*?)</a>',
                r'<h2[^>]*class=["\'][^"\']*product-title[^"\']*["\'][^>]*>.*?<a[^>]*>(.*?)</a>',
                r'<a[^>]*class=["\'][^"\']*product-name[^"\']*["\'][^>]*>(.*?)</a>',
                r'<h3[^>]*>.*?<a[^>]*href=["\'][^"\']*["\'][^>]*>(.*?)</a>.*?</h3>',
                r'<h2[^>]*>.*?<a[^>]*href=["\'][^"\']*["\'][^>]*>(.*?)</a>.*?</h2>',
                r'<a[^>]*href=["\'][^"\']*producto[^"\']*["\'][^>]*>(.*?)</a>',
                r'<a[^>]*title=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*product[^"\']*["\']',
                r'title=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*product-title'
            ]
            
            # Patrones para extraer precios
            price_patterns = [
                r'<span[^>]*class=["\'][^"\']*product-price[^"\']*["\'][^>]*content=["\']([^"\']+)["\']',
                r'content=["\']([0-9]+\.?[0-9]*)["\'][^>]*class=["\'][^"\']*product-price',
                r'<span[^>]*class=["\'][^"\']*price[^"\']*["\'][^>]*>\s*\$?([0-9]+\.?[0-9]*)',
                r'<div[^>]*class=["\'][^"\']*price[^"\']*["\'][^>]*>\s*\$?([0-9]+\.?[0-9]*)',
                r'"price"["\s]*:["\s]*([0-9]+\.?[0-9]*)',
                r'precio["\s]*:["\s]*([0-9]+\.?[0-9]*)',
                r'\$([0-9]+\.?[0-9]*)',
                r'<span[^>]*>\s*\$([0-9]+\.?[0-9]*)\s*</span>'
            ]
            
            # Extraer nombre
            product_name = None
            for pattern in name_patterns:
                match = re.search(pattern, container_html, re.IGNORECASE | re.DOTALL)
                if match:
                    name = match.group(1).strip()
                    # Limpiar HTML tags del nombre
                    name = re.sub(r'<[^>]+>', '', name)
                    # Limpiar espacios extra
                    name = re.sub(r'\s+', ' ', name).strip()
                    if name and len(name) > 3:  # Nombre debe tener al menos 3 caracteres
                        product_name = name
                        break
            
            # Extraer precio
            product_price = None
            for pattern in price_patterns:
                match = re.search(pattern, container_html, re.IGNORECASE)
                if match:
                    price = match.group(1).strip().replace('
    
    def buscar_producto(self, producto):
        """Busca un producto y obtiene su información completa (nombre y precio)"""
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
                        # Extraer productos del HTML
                        products = self.extract_products_from_html(response.text)
                        
                        if products:
                            # Retornar el primer producto encontrado
                            first_product = products[0]
                            return first_product, "Producto encontrado exitosamente"
                        
                        # Si no se encuentran productos estructurados, intentar método anterior
                        fallback_prices = self.extract_fallback_prices(response.text)
                        if fallback_prices:
                            return {
                                "nombre": f"Producto relacionado con '{producto}'",
                                "precio": fallback_prices[0]
                            }, "Precio encontrado (información limitada)"
                        
                        # Verificar si hay contenido de productos pero sin precios
                        if "producto" in response.text.lower() or "product" in response.text.lower():
                            return None, "Productos encontrados pero sin información de precio disponible"
                    
                except requests.exceptions.Timeout:
                    continue
                except Exception:
                    continue
            
            return None, "No se encontraron productos o no se pudo acceder a la búsqueda"
                
        except Exception as e:
            return None, f"Error durante la búsqueda: {str(e)}"
    
    def extract_fallback_prices(self, html_content):
        """Método de respaldo para extraer solo precios"""
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
                price = str(match).replace('

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
                with st.spinner("Analizando proceso de login..."):
                    scraper = SufarmedScraper()
                    try:
                        # Obtener página de login para análisis
                        response = scraper.session.get("https://sufarmed.com/sufarmed/iniciar-sesion", timeout=10)
                        
                        st.write("**Análisis de la página de login:**")
                        st.write(f"- Status Code: {response.status_code}")
                        st.write(f"- URL Final: {response.url}")
                        
                        # Buscar campos de formulario
                        email_fields = re.findall(r'name=["\']([^"\']*email[^"\']*)["\']', response.text, re.IGNORECASE)
                        password_fields = re.findall(r'name=["\']([^"\']*password[^"\']*)["\']', response.text, re.IGNORECASE)
                        
                        if email_fields:
                            st.write(f"- Campos de email encontrados: {email_fields}")
                        if password_fields:
                            st.write(f"- Campos de password encontrados: {password_fields}")
                        
                        # Buscar tokens
                        tokens = re.findall(r'name=["\']([^"\']*token[^"\']*)["\'][^>]*value=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
                        if tokens:
                            st.write(f"- Tokens encontrados: {len(tokens)} tokens")
                        
                        st.success("✅ Análisis completado")
                        
                    except Exception as e:
                        st.error(f"❌ Error en debug: {str(e)}")
            else:
                st.warning("Ingresa credenciales primero para hacer debug")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Desarrollado con Streamlit 🚀 | Sin dependencias externas</div>", 
    unsafe_allow_html=True
), '').replace(',', '')
                    if price and price.replace('.', '').isdigit():
                        product_price = price
                        break
            
            # Retornar información si se encontraron ambos
            if product_name and product_price:
                return {
                    "nombre": product_name,
                    "precio": product_price
                }
            elif product_name:  # Si solo encontramos nombre
                return {
                    "nombre": product_name,
                    "precio": "No disponible"
                }
                
            return None
            
        except Exception as e:
            return None
    
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
                with st.spinner("Analizando proceso de login..."):
                    scraper = SufarmedScraper()
                    try:
                        # Obtener página de login para análisis
                        response = scraper.session.get("https://sufarmed.com/sufarmed/iniciar-sesion", timeout=10)
                        
                        st.write("**Análisis de la página de login:**")
                        st.write(f"- Status Code: {response.status_code}")
                        st.write(f"- URL Final: {response.url}")
                        
                        # Buscar campos de formulario
                        email_fields = re.findall(r'name=["\']([^"\']*email[^"\']*)["\']', response.text, re.IGNORECASE)
                        password_fields = re.findall(r'name=["\']([^"\']*password[^"\']*)["\']', response.text, re.IGNORECASE)
                        
                        if email_fields:
                            st.write(f"- Campos de email encontrados: {email_fields}")
                        if password_fields:
                            st.write(f"- Campos de password encontrados: {password_fields}")
                        
                        # Buscar tokens
                        tokens = re.findall(r'name=["\']([^"\']*token[^"\']*)["\'][^>]*value=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
                        if tokens:
                            st.write(f"- Tokens encontrados: {len(tokens)} tokens")
                        
                        st.success("✅ Análisis completado")
                        
                    except Exception as e:
                        st.error(f"❌ Error en debug: {str(e)}")
            else:
                st.warning("Ingresa credenciales primero para hacer debug")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Desarrollado con Streamlit 🚀 | Sin dependencias externas</div>", 
    unsafe_allow_html=True
), '').replace(',', '').strip()
                if price and price.replace('.', '').isdigit():
                    prices.append(price)
        
        return prices
    
    def buscar_sin_login(self, producto):
        """Busca producto sin login como fallback"""
        try:
            # Intentar búsqueda directa sin login
            search_url = f"https://sufarmed.com/buscar?s={producto}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                products = self.extract_products_from_html(response.text)
                if products:
                    first_product = products[0]
                    return first_product, "Producto encontrado (sin login)"
                
                # Fallback a solo precios
                prices = self.extract_fallback_prices(response.text)
                if prices:
                    return {
                        "nombre": f"Producto relacionado con '{producto}'",
                        "precio": prices[0]
                    }, "Precio encontrado sin login (información limitada)"
            
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
                with st.spinner("Analizando proceso de login..."):
                    scraper = SufarmedScraper()
                    try:
                        # Obtener página de login para análisis
                        response = scraper.session.get("https://sufarmed.com/sufarmed/iniciar-sesion", timeout=10)
                        
                        st.write("**Análisis de la página de login:**")
                        st.write(f"- Status Code: {response.status_code}")
                        st.write(f"- URL Final: {response.url}")
                        
                        # Buscar campos de formulario
                        email_fields = re.findall(r'name=["\']([^"\']*email[^"\']*)["\']', response.text, re.IGNORECASE)
                        password_fields = re.findall(r'name=["\']([^"\']*password[^"\']*)["\']', response.text, re.IGNORECASE)
                        
                        if email_fields:
                            st.write(f"- Campos de email encontrados: {email_fields}")
                        if password_fields:
                            st.write(f"- Campos de password encontrados: {password_fields}")
                        
                        # Buscar tokens
                        tokens = re.findall(r'name=["\']([^"\']*token[^"\']*)["\'][^>]*value=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
                        if tokens:
                            st.write(f"- Tokens encontrados: {len(tokens)} tokens")
                        
                        st.success("✅ Análisis completado")
                        
                    except Exception as e:
                        st.error(f"❌ Error en debug: {str(e)}")
            else:
                st.warning("Ingresa credenciales primero para hacer debug")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Desarrollado con Streamlit 🚀 | Sin dependencias externas</div>", 
    unsafe_allow_html=True
), '').replace(',', '')
                    if price and price.replace('.', '').isdigit():
                        product_price = price
                        break
            
            # Retornar información si se encontraron ambos
            if product_name and product_price:
                return {
                    "nombre": product_name,
                    "precio": product_price
                }
            elif product_name:  # Si solo encontramos nombre
                return {
                    "nombre": product_name,
                    "precio": "No disponible"
                }
                
            return None
            
        except Exception as e:
            return None
    
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
                with st.spinner("Analizando proceso de login..."):
                    scraper = SufarmedScraper()
                    try:
                        # Obtener página de login para análisis
                        response = scraper.session.get("https://sufarmed.com/sufarmed/iniciar-sesion", timeout=10)
                        
                        st.write("**Análisis de la página de login:**")
                        st.write(f"- Status Code: {response.status_code}")
                        st.write(f"- URL Final: {response.url}")
                        
                        # Buscar campos de formulario
                        email_fields = re.findall(r'name=["\']([^"\']*email[^"\']*)["\']', response.text, re.IGNORECASE)
                        password_fields = re.findall(r'name=["\']([^"\']*password[^"\']*)["\']', response.text, re.IGNORECASE)
                        
                        if email_fields:
                            st.write(f"- Campos de email encontrados: {email_fields}")
                        if password_fields:
                            st.write(f"- Campos de password encontrados: {password_fields}")
                        
                        # Buscar tokens
                        tokens = re.findall(r'name=["\']([^"\']*token[^"\']*)["\'][^>]*value=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
                        if tokens:
                            st.write(f"- Tokens encontrados: {len(tokens)} tokens")
                        
                        st.success("✅ Análisis completado")
                        
                    except Exception as e:
                        st.error(f"❌ Error en debug: {str(e)}")
            else:
                st.warning("Ingresa credenciales primero para hacer debug")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Desarrollado con Streamlit 🚀 | Sin dependencias externas</div>", 
    unsafe_allow_html=True
)
