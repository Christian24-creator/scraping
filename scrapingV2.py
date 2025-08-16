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
        
        hidden_pattern = r'<input[^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\'][^>]*>'
        matches = re.findall(hidden_pattern, html_content, re.IGNORECASE)
        
        for name, value in matches:
            form_data[name] = value
        
        return form_data
    
    def login(self, email, password):
        """Intenta hacer login en Sufarmed con debug mejorado"""
        try:
            login_url = "https://sufarmed.com/sufarmed/iniciar-sesion"
            response = self.session.get(login_url, timeout=15)
            
            if response.status_code != 200:
                return False, f"No se pudo acceder a la página de login (Status: {response.status_code})"
            
            if "login" not in response.text.lower() and "email" not in response.text.lower():
                return False, "La página no parece ser un formulario de login"
            
            form_data = {}
            
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
            
            possible_field_names = {
                'email': ['email', 'username', 'user', 'login_email', 'customer_email'],
                'password': ['password', 'passwd', 'pwd', 'login_password', 'customer_password'],
                'submit': ['submitLogin', 'submit', 'login', 'submit_login', '1']
            }
            
            # Asegúrate de que los campos de email y password estén en form_data con los nombres correctos
            form_data.update({
                'email': email,
                'password': password,
                'submitLogin': '1' # Por si acaso, un nombre común para el botón de submit
            })
            
            for field_type, names in possible_field_names.items():
                for name in names:
                    if field_type == 'email':
                        form_data[name] = email
                    elif field_type == 'password':
                        form_data[name] = password
                    elif field_type == 'submit':
                        if name in response.text: # Solo si el nombre del submit button está en la página
                            form_data[name] = '1' 

            post_headers = {
                'Referer': login_url,
                'Origin': 'https://sufarmed.com',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            login_response = self.session.post(
                login_url, 
                data=form_data, 
                headers=post_headers,
                timeout=15,
                allow_redirects=True
            )
            
            final_url = login_response.url.lower()
            response_text = login_response.text.lower()
            
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
    
    def extract_product_details(self, html_content):
        """
        Extrae nombres de productos y sus precios asociados del HTML.
        Busca contenedores de productos y luego extrae el nombre y el precio de cada uno.
        """
        products_data = []

        # Patrón para encontrar el div contenedor de la descripción del producto
        # que típicamente contiene el título del producto y el precio.
        # Captura todo el contenido dentro de este div.
        product_container_pattern = r'<div[^>]*class=["\'][^"\']*col-description[^"\']*["\'][^>]*>(.*?)<\/div>'
        
        container_matches = re.findall(product_container_pattern, html_content, re.IGNORECASE | re.DOTALL)
        
        for container_html in container_matches:
            name = None
            price = "No disponible" # Valor por defecto si el precio no se encuentra

            # Patrón para el nombre del producto dentro del <h2>.product-title que contiene un <a>
            # Group 1: El texto del nombre del producto
            name_pattern = r'<h2[^>]*class=["\'][^"\']*product-title[^"\']*["\'][^>]*>\s*<a[^>]*>(.*?)<\/a>'
            name_match = re.search(name_pattern, container_html, re.IGNORECASE | re.DOTALL)
            if name_match:
                name = name_match.group(1).strip()
            
            # Patrón para el precio que sigue inmediatamente al </a> dentro del <h2> (ej. "== $0")
            # Group 1: El valor numérico del precio
            price_after_name_pattern = r'<a[^>]*>.*?<\/a>\s*(?:==\s*\$?([0-9]+\.?[0-9]*))'
            price_match_after_name = re.search(price_after_name_pattern, container_html, re.IGNORECASE | re.DOTALL)
            
            if price_match_after_name and price_match_after_name.group(1):
                price = price_match_after_name.group(1).strip()
            else:
                # Si el precio no está inmediatamente después del nombre, buscarlo con otros patrones comunes
                # dentro del mismo contenedor de producto.
                common_price_patterns = [
                    # Busca precio en etiquetas con class="product-price" o "price"
                    r'<[^>]*class=["\'][^"\']*(?:product-price|price)[^"\']*["\'][^>]*content=["\']([^"\']+)["\']',
                    r'content=["\']([0-9]+\.?[0-9]*)["\'][^>]*class=["\'][^"\']*(?:product-price|price)',
                    r'<[^>]*class=["\'][^"\']*(?:product-price|price)[^"\']*["\'][^>]*>\s*\$?([0-9]+\.?[0-9]*)',
                    # Busca un valor numérico precedido por "$"
                    r'\$([0-9]+\.?[0-9]*)',
                    # Busca precio en JSON-like estructuras (ej. "price": "12.34")
                    r'["\']price["\"]\s*:\s*["\']?([0-9]+\.?[0-9]*)["\']?',
                    r'["\']precio["\"]\s*:\s*["\']?([0-9]+\.?[0-9]*)["\']?'
                ]
                
                for p_pattern in common_price_patterns:
                    price_match_other = re.search(p_pattern, container_html, re.IGNORECASE)
                    if price_match_other:
                        # Limpiar el precio (quitar $, comas)
                        found_price = str(price_match_other.group(1)).replace('$', '').replace(',', '').strip()
                        # Verificar si el precio es un número válido
                        if found_price and found_price.replace('.', '', 1).isdigit(): 
                            price = found_price
                            break # Ya encontramos un precio, no necesitamos buscar más
            
            if name: # Solo añade el producto a la lista si se encontró un nombre
                products_data.append({'name': name, 'price': price})
        
        return products_data

    def buscar_producto(self, producto):
        """Busca un producto y obtiene todos los nombres y precios."""
        try:
            search_urls = [
                f"https://sufarmed.com/sufarmed/buscar?s={producto}",
                f"https://sufarmed.com/sufarmed/buscar?controller=search&s={producto}",
                f"https://sufarmed.com/buscar?s={producto}"
            ]
            
            for search_url in search_urls:
                try:
                    response = self.session.get(search_url, timeout=15)
                    
                    if response.status_code == 200:
                        products_data = self.extract_product_details(response.text)
                        
                        if products_data:
                            return products_data, "Productos y precios encontrados"
                        
                        if "producto" in response.text.lower() or "product" in response.text.lower():
                            return [], "Productos encontrados pero sin precios visibles o no extraíbles"
                    
                except requests.exceptions.Timeout:
                    continue
                except Exception: # Captura excepciones generales para probar otras URLs
                    continue
            
            return [], "No se encontraron productos o no se pudo acceder a la búsqueda"
                
        except Exception as e:
            return [], f"Error durante la búsqueda: {str(e)}"
    
    def buscar_sin_login(self, producto):
        """Busca producto sin login como fallback y obtiene nombres y precios."""
        try:
            search_url = f"https://sufarmed.com/buscar?s={producto}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                products_data = self.extract_product_details(response.text)
                if products_data:
                    return products_data, "Productos y precios encontrados (sin login)"
            
            return [], "No se encontraron resultados sin login"
            
        except Exception as e:
            return [], f"Error en búsqueda sin login: {str(e)}"

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

# Interfaz de usuario
st.markdown("### 🔍 Buscar Producto")

producto_buscar = st.text_input(
    "Ingresa el nombre del producto:",
    placeholder="Ej: Paracetamol, Ibuprofeno, etc."
)

if st.button("🔍 Buscar Precio", type="primary"):
    if not email_input or not password_input:
        st.error("❌ Debes configurar tu email y contraseña primero")
    elif producto_buscar:
        with st.spinner("Buscando producto..."):
            try:
                scraper = SufarmedScraper()
                
                EMAIL = email_input
                PASSWORD = password_input
                
                products_found = []  # Ahora almacenará una lista de diccionarios {name, price}
                search_message = ""
                
                st.info("🔐 Intentando iniciar sesión en Sufarmed...")
                login_success, login_message = scraper.login(EMAIL, PASSWORD)
                
                if login_success:
                    st.success(f"✅ {login_message}")
                    
                    st.info(f"🔍 Buscando: {producto_buscar}")
                    products_found, search_message = scraper.buscar_producto(producto_buscar)
                    
                else:
                    st.warning(f"⚠️ Login falló: {login_message}")
                    st.info("🔄 Intentando búsqueda sin login...")
                    products_found, search_message = scraper.buscar_sin_login(producto_buscar)
                
                if products_found:
                    st.markdown("---")
                    st.markdown("### 💰 Resultados de la Búsqueda")
                    
                    st.subheader(f"Productos encontrados para: {producto_buscar}")
                    for i, product_item in enumerate(products_found):
                        st.markdown(f"**{product_item['name']}**")
                        st.write(f"**Precio:** ${product_item['price']}")
                        st.markdown("---") # Separador para cada producto
                    
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
- Los resultados mostrados corresponden a todos los precios y nombres encontrados para la búsqueda
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
                        response = scraper.session.get("https://sufarmed.com/sufarmed/iniciar-sesion", timeout=10)
                        
                        st.write("**Análisis de la página de login:**")
                        st.write(f"- Status Code: {response.status_code}")
                        st.write(f"- URL Final: {response.url}")
                        
                        email_fields = re.findall(r'name=["\']([^"\']*email[^"\']*)["\']', response.text, re.IGNORECASE)
                        password_fields = re.findall(r'name=["\']([^"\']*password[^"\']*)["\']', response.text, re.IGNORECASE)
                        
                        if email_fields:
                            st.write(f"- Campos de email encontrados: {email_fields}")
                        if password_fields:
                            st.write(f"- Campos de password encontrados: {password_fields}")
                        
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
