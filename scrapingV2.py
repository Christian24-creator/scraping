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
            
            # Explicitly set email and password. This will take precedence.
            form_data['email'] = email
            form_data['password'] = password
            
            # Add common submit button value if not already captured by hidden fields
            if 'submitLogin' not in form_data and 'submit' not in form_data:
                 form_data['submitLogin'] = '1'
            
            # This loop is kept for robustness, it might find other field names
            for field_type, names in possible_field_names.items():
                for name in names:
                    if field_type == 'email':
                        form_data[name] = email
                    elif field_type == 'password':
                        form_data[name] = password
                    elif field_type == 'submit' and name not in form_data: # Only add if not already present
                        if name in response.text: # Check if the name exists on the page
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

        # Patrón para encontrar un bloque completo de producto (ej. <article class="product-miniature">)
        # Esto es crucial para asociar correctamente el nombre y el precio de un mismo producto.
        # Captura el ID del producto (si está en 'data-id-product') y todo el HTML del bloque.
        product_miniature_pattern = r'<article[^>]*class=["\'][^"\']*(?:product-miniature|js-product-miniature)[^"\']*["\'][^>]*data-id-product=["\'](\d+)["\'][^>]*>(.*?)<\/article>'
        product_miniature_matches = re.findall(product_miniature_pattern, html_content, re.IGNORECASE | re.DOTALL)

        if not product_miniature_matches:
            # Fallback si no se encuentran 'product-miniature' (ej. buscar un div genérico de columna)
            # Esto es menos preciso, pero puede ser útil si el sitio no usa 'article product-miniature'
            # Se asume que divs con clases 'col-X' pueden ser contenedores de producto.
            generic_product_block_pattern = r'<div[^>]*class=["\'][^"\']*\b(?:col-\d+|product-item)\b[^"\']*["\'][^>]*>(.*?)<\/div>'
            generic_matches = re.findall(generic_product_block_pattern, html_content, re.IGNORECASE | re.DOTALL)
            # Para simplificar, si no hay ID, usamos un valor por defecto o un índice.
            product_miniature_matches = [(f"generic_{i}", html) for i, html in enumerate(generic_matches)]


        for product_id, miniature_html in product_miniature_matches:
            name = "Nombre no encontrado"
            price = "Precio no disponible"

            # Buscar el nombre del producto dentro del HTML del bloque
            name_pattern = r'<h2[^>]*class=["\'][^"\']*product-title[^"\']*["\'][^>]*>\s*<a[^>]*>(.*?)<\/a>'
            name_match = re.search(name_pattern, miniature_html, re.IGNORECASE | re.DOTALL)
            if name_match:
                name = name_match.group(1).strip()
                # Limpiar el nombre de entidades HTML y saltos de línea
                name = re.sub(r'\s*\n\s*', ' ', name)
                name = re.sub(r'&\w+;', '', name)

            # Buscar el precio dentro del HTML del bloque
            # Prioridad 1: Atributo 'content' del span con clase "product-price"
            price_content_pattern = r'<span[^>]*class=["\'][^"\']*product-price[^"\']*["\'][^>]*content=["\']([^"\']+)["\']'
            price_match = re.search(price_content_pattern, miniature_html, re.IGNORECASE)
            
            if price_match:
                price = price_match.group(1).strip()
            else:
                # Prioridad 2: Contenido de texto del span con clase "product-price"
                # Limpiar '&nbsp;' para facilitar la extracción del número
                cleaned_miniature_html = miniature_html.replace('&nbsp;', ' ')
                
                # Este patrón busca el valor numérico (con punto o coma como decimal)
                # dentro de un span con la clase 'product-price'.
                price_text_pattern = r'<span[^>]*class=["\'][^"\']*product-price[^"\']*["\'][^>]*>\s*\$?\s*([0-9]+\.?[0-9]*(?:,\d{2})?)\s*(?:[^<>]*)?<\/span>'
                price_match = re.search(price_text_pattern, cleaned_miniature_html, re.IGNORECASE | re.DOTALL)
                
                if price_match:
                    price_val = price_match.group(1).strip()
                    price = price_val.replace(',', '.') # Reemplazar coma por punto para consistencia
                    # Verificar si el precio es un número válido después de la limpieza
                    if not price.replace('.', '', 1).isdigit():
                         price = "Precio no disponible"
                else:
                    # Fallback a otros patrones genéricos si los específicos fallan
                    generic_price_patterns = [
                        # Busca en cualquier elemento con clases "product-price" o "price"
                        r'<[^>]*class=["\'][^"\']*(?:product-price|price)[^"\']*["\'][^>]*>\s*\$?([0-9]+\.?[0-9]*)',
                        r'\$([0-9]+\.?[0-9]*)', # Cualquier número precedido por $
                        r'precio["\s]*:["\s]*([0-9]+\.?[0-9]*)', # Patrón JSON-like para "precio"
                        r'"price"["\s]*:["\s]*([0-9]+\.?[0-9]*)' # Patrón JSON-like para "price"
                    ]
                    for gen_pattern in generic_price_patterns:
                        gen_match = re.search(gen_pattern, cleaned_miniature_html, re.IGNORECASE)
                        if gen_match:
                            found_price = str(gen_match.group(1)).replace('$', '').replace(',', '').strip()
                            if found_price and found_price.replace('.', '', 1).isdigit():
                                price = found_price
                                break
            
            # Solo añadir el producto a la lista si se encontró un nombre (el precio puede ser "No disponible")
            if name != "Nombre no encontrado":
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
                except Exception as e: # Captura excepciones generales para probar otras URLs
                    # print(f"Error accediendo o parseando {search_url}: {e}") # Descomentar para depuración
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
