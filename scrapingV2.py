import streamlit as st
import requests
import re
import time
from urllib.parse import quote

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
        # Headers más completos para simular un navegador real
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
    
    def debug_page_content(self, html_content, search_term):
        """Función para debug del contenido de la página"""
        debug_info = {
            'page_length': len(html_content),
            'has_products': False,
            'product_containers_found': 0,
            'price_patterns_found': 0,
            'search_term_found': search_term.lower() in html_content.lower()
        }
        
        # Buscar diferentes tipos de contenedores de productos
        product_selectors = [
            r'<div[^>]*class=[^>]*product[^>]*>',
            r'<article[^>]*class=[^>]*product[^>]*>',
            r'<li[^>]*class=[^>]*product[^>]*>',
            r'<div[^>]*data-product[^>]*>',
            r'<div[^>]*product-item[^>]*>',
        ]
        
        for selector in product_selectors:
            matches = re.findall(selector, html_content, re.IGNORECASE)
            if matches:
                debug_info['product_containers_found'] += len(matches)
                debug_info['has_products'] = True
        
        # Buscar patrones de precios
        price_patterns = [
            r'\$\d+[,.]?\d*',
            r'precio[^>]*>\$?\d+',
            r'price[^>]*>\$?\d+',
            r'content=["\'](\d+[.,]?\d*)["\']'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            debug_info['price_patterns_found'] += len(matches)
        
        return debug_info
    
    def login(self, email, password):
        """Intenta hacer login en Sufarmed con mejor detección"""
        try:
            # Primero acceder a la página principal
            home_response = self.session.get("https://sufarmed.com", timeout=15)
            time.sleep(1)
            
            login_url = "https://sufarmed.com/sufarmed/iniciar-sesion"
            response = self.session.get(login_url, timeout=15)
            
            if response.status_code != 200:
                return False, f"No se pudo acceder a la página de login (Status: {response.status_code})"
            
            # Extraer datos del formulario con patrones mejorados
            form_data = {}
            
            # Buscar campos hidden con más precisión
            hidden_patterns = [
                r'<input[^>]*type=["\']hidden["\'][^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                r'<input[^>]*name=["\']([^"\']+)["\'][^>]*type=["\']hidden["\'][^>]*value=["\']([^"\']*)["\'][^>]*>'
            ]
            
            for pattern in hidden_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                for name, value in matches:
                    form_data[name] = value
            
            # Buscar token CSRF con más patrones
            token_patterns = [
                r'name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
                r'name=["\']token["\'][^>]*value=["\']([^"\']+)["\']',
                r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
                r'"_token"\s*:\s*"([^"]+)"',
                r'csrf["\']?\s*:\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in token_patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    form_data['_token'] = match.group(1)
                    form_data['token'] = match.group(1)
                    break
            
            # Agregar credenciales con diferentes variaciones
            form_data.update({
                'email': email,
                'password': password,
                'submitLogin': '1',
                'login': '1',
                'submit': '1'
            })
            
            # Headers para POST con referer correcto
            post_headers = self.session.headers.copy()
            post_headers.update({
                'Referer': login_url,
                'Origin': 'https://sufarmed.com',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin'
            })
            
            # Enviar datos de login
            login_response = self.session.post(
                login_url, 
                data=form_data, 
                headers=post_headers,
                timeout=15,
                allow_redirects=True
            )
            
            # Verificar login exitoso con múltiples indicadores
            if login_response.status_code in [200, 302]:
                response_text = login_response.text.lower()
                final_url = login_response.url.lower()
                
                success_indicators = [
                    "mi-cuenta" in final_url,
                    "my-account" in final_url,
                    "dashboard" in final_url,
                    "perfil" in final_url,
                    "bienvenido" in response_text,
                    "welcome" in response_text,
                    "logout" in response_text,
                    "cerrar sesion" in response_text,
                    "salir" in response_text,
                    login_url not in final_url  # Redirección exitosa
                ]
                
                error_indicators = [
                    "error" in response_text,
                    "incorrect" in response_text,
                    "incorrecto" in response_text,
                    "invalid" in response_text,
                    "invalido" in response_text,
                    "failed" in response_text
                ]
                
                if any(success_indicators) and not any(error_indicators):
                    return True, "Login exitoso"
                elif any(error_indicators):
                    return False, "Credenciales incorrectas"
                else:
                    # Si no hay indicadores claros, asumir éxito si hay redirección
                    return True, "Login posiblemente exitoso"
            
            return False, f"Error en login (Status: {login_response.status_code})"
                
        except Exception as e:
            return False, f"Error durante el login: {str(e)}"
    
    def extract_product_info(self, html_content):
        """Extrae información de productos del HTML con patrones mejorados"""
        try:
            products = []
            
            # Patrones más amplios para encontrar productos
            product_patterns = [
                # Productos en artículos
                r'<article[^>]*class=[^>]*product[^>]*>(.*?)</article>',
                # Productos en divs
                r'<div[^>]*class=[^>]*(?:product-miniature|product-item|product-card)[^>]*>(.*?)</div>',
                # Productos en listas
                r'<li[^>]*class=[^>]*product[^>]*>(.*?)</li>',
                # Productos con data attributes
                r'<div[^>]*data-product[^>]*>(.*?)</div>',
                # Patrones genéricos más amplios
                r'<div[^>]*class=[^>]*["\'][^"\']*product[^"\']*["\'][^>]*>(.*?)</div>',
            ]
            
            for pattern in product_patterns:
                matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                
                for match in matches[:10]:  # Aumentar a 10 productos
                    product_info = self.parse_product_container(match)
                    if product_info and product_info not in products:
                        products.append(product_info)
            
            # Si no encuentra productos con patrones específicos, buscar de forma más general
            if not products:
                products = self.extract_products_alternative(html_content)
            
            return products[:5]  # Devolver hasta 5 productos
            
        except Exception as e:
            st.error(f"Error extrayendo productos: {str(e)}")
            return []
    
    def extract_products_alternative(self, html_content):
        """Método alternativo para extraer productos"""
        try:
            products = []
            
            # Buscar nombres de productos con patrones más flexibles
            name_patterns = [
                r'<h[1-6][^>]*>\s*<a[^>]*>([^<]+)</a>\s*</h[1-6]>',
                r'<a[^>]*title=["\']([^"\']+)["\'][^>]*>',
                r'<span[^>]*class=[^>]*name[^>]*>([^<]+)</span>',
                r'<div[^>]*class=[^>]*name[^>]*>([^<]+)</div>',
            ]
            
            # Buscar precios con patrones más amplios
            price_patterns = [
                r'<span[^>]*class=[^>]*price[^>]*>[^0-9]*([0-9]+[.,]?[0-9]*)',
                r'<div[^>]*class=[^>]*price[^>]*>[^0-9]*([0-9]+[.,]?[0-9]*)',
                r'\$\s*([0-9]+[.,]?[0-9]*)',
                r'precio[^>]*>[^0-9]*([0-9]+[.,]?[0-9]*)',
            ]
            
            names = []
            prices = []
            
            # Extraer nombres
            for pattern in name_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    clean_name = re.sub(r'<[^>]+>', '', str(match)).strip()
                    clean_name = re.sub(r'\s+', ' ', clean_name)
                    if len(clean_name) > 5 and clean_name not in names:
                        names.append(clean_name)
            
            # Extraer precios
            for pattern in price_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    price = str(match).replace(',', '').strip()
                    if price and price.replace('.', '').isdigit() and float(price) > 0:
                        prices.append(price)
            
            # Combinar nombres y precios
            for i, name in enumerate(names[:5]):
                price = prices[i] if i < len(prices) else "No disponible"
                products.append({
                    'nombre': name,
                    'precio': price
                })
            
            return products
            
        except Exception as e:
            return []
    
    def parse_product_container(self, container_html):
        """Analiza un contenedor de producto con patrones mejorados"""
        try:
            # Extraer nombre del producto con más patrones
            name_patterns = [
                r'<h[1-6][^>]*>.*?<a[^>]*>([^<]+)</a>',
                r'<h[1-6][^>]*>([^<]+)</h[1-6]>',
                r'<a[^>]*title=["\']([^"\']+)["\']',
                r'<a[^>]*class=[^>]*product-name[^>]*>([^<]+)</a>',
                r'<span[^>]*class=[^>]*product-name[^>]*>([^<]+)</span>',
                r'<div[^>]*class=[^>]*product-name[^>]*>([^<]+)</div>',
                r'<a[^>]*>([^<]{10,})</a>',  # Enlaces con texto largo
            ]
            
            product_name = None
            for pattern in name_patterns:
                match = re.search(pattern, container_html, re.IGNORECASE | re.DOTALL)
                if match:
                    name = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    name = re.sub(r'\s+', ' ', name)
                    if len(name) > 5 and not re.match(r'^[\d\s.,]+$', name):  # Evitar solo números
                        product_name = name
                        break
            
            # Extraer precio con más patrones
            price_patterns = [
                r'<span[^>]*class=[^>]*price[^>]*>[^0-9]*([0-9]+[.,]?[0-9]*)',
                r'<div[^>]*class=[^>]*price[^>]*>[^0-9]*([0-9]+[.,]?[0-9]*)',
                r'content=["\']([0-9]+[.,]?[0-9]*)["\']',
                r'\$\s*([0-9]+[.,]?[0-9]*)',
                r'>([0-9]+[.,]?[0-9]*)\s*<',
                r'precio[^>]*>[^0-9]*([0-9]+[.,]?[0-9]*)',
                r'data-price=["\']([0-9]+[.,]?[0-9]*)["\']',
            ]
            
            product_price = None
            for pattern in price_patterns:
                matches = re.findall(pattern, container_html, re.IGNORECASE)
                if matches:
                    for match in matches:
                        price = str(match).replace(',', '').strip()
                        if price and price.replace('.', '').isdigit() and float(price) > 0:
                            product_price = price
                            break
                    if product_price:
                        break
            
            if product_name:
                return {
                    'nombre': product_name,
                    'precio': product_price or "No disponible"
                }
            
            return None
            
        except Exception as e:
            return None
    
    def buscar_producto(self, producto):
        """Busca un producto con URLs mejoradas"""
        try:
            # Codificar el término de búsqueda
            producto_encoded = quote(producto)
            
            # URLs de búsqueda múltiples
            search_urls = [
                f"https://sufarmed.com/sufarmed/buscar?s={producto_encoded}",
                f"https://sufarmed.com/buscar?s={producto_encoded}",
                f"https://sufarmed.com/search?q={producto_encoded}",
                f"https://sufarmed.com/productos?search={producto_encoded}",
            ]
            
            for search_url in search_urls:
                try:
                    # Agregar headers específicos para búsqueda
                    search_headers = self.session.headers.copy()
                    search_headers.update({
                        'Referer': 'https://sufarmed.com',
                        'X-Requested-With': 'XMLHttpRequest'
                    })
                    
                    response = self.session.get(search_url, headers=search_headers, timeout=15)
                    
                    if response.status_code == 200:
                        # Debug de la respuesta
                        debug_info = self.debug_page_content(response.text, producto)
                        
                        products = self.extract_product_info(response.text)
                        
                        if products:
                            return products[0], f"Producto encontrado exitosamente (Debug: {debug_info})"
                        
                        # Intentar extracción más simple
                        simple_result = self.extract_simple_product_info(response.text, producto)
                        if simple_result:
                            return simple_result, f"Información básica encontrada (Debug: {debug_info})"
                        
                except requests.RequestException as e:
                    continue
                except Exception as e:
                    continue
            
            return None, "No se encontraron productos en ninguna URL"
                
        except Exception as e:
            return None, f"Error durante la búsqueda: {str(e)}"
    
    def extract_simple_product_info(self, html_content, search_term):
        """Extracción simple como fallback"""
        try:
            # Buscar cualquier mención del término de búsqueda cerca de un precio
            search_pattern = rf'(?i).*{re.escape(search_term)}.*'
            lines_with_search = []
            
            for line in html_content.split('\n'):
                if re.search(search_pattern, line):
                    lines_with_search.append(line)
            
            # Buscar precios en esas líneas
            for line in lines_with_search[:10]:
                price_match = re.search(r'([0-9]+[.,]?[0-9]*)', line)
                if price_match:
                    price = price_match.group(1)
                    if float(price.replace(',', '')) > 0:
                        return {
                            'nombre': f"Producto relacionado con '{search_term}'",
                            'precio': price
                        }
            
            return None
            
        except Exception as e:
            return None
    
    def buscar_sin_login(self, producto):
        """Búsqueda sin login con mejor manejo"""
        try:
            # Primero visitar la página principal para establecer cookies
            self.session.get("https://sufarmed.com", timeout=10)
            time.sleep(1)
            
            return self.buscar_producto(producto)
            
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
                    - El sitio podría haber cambiado su estructura
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

# Panel de debug mejorado
with st.expander("🔧 Panel de Pruebas y Debug"):
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Probar Conexión"):
            with st.spinner("Probando conexión..."):
                try:
                    response = requests.get("https://sufarmed.com", timeout=10)
                    st.success(f"✅ Conexión exitosa - Status: {response.status_code}")
                    st.info(f"URL final: {response.url}")
                    st.info(f"Headers: {dict(response.headers)}")
                except Exception as e:
                    st.error(f"❌ Error de conexión: {str(e)}")
    
    with col2:
        if st.button("Test Búsqueda Simple"):
            if producto_buscar:
                with st.spinner("Probando búsqueda..."):
                    try:
                        scraper = SufarmedScraper()
                        search_url = f"https://sufarmed.com/buscar?s={producto_buscar}"
                        response = scraper.session.get(search_url, timeout=10)
                        
                        debug_info = scraper.debug_page_content(response.text, producto_buscar)
                        
                        st.write("**Análisis de búsqueda:**")
                        st.json(debug_info)
                        
                        # Mostrar parte del HTML para debug
                        if len(response.text) > 1000:
                            st.text_area("Muestra del HTML:", response.text[:1000], height=200)
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("Ingresa un producto primero")
    
    # Debug avanzado
    if st.button("Debug Avanzado de Login"):
        if email_input and password_input:
            with st.spinner("Analizando login..."):
                try:
                    scraper = SufarmedScraper()
                    response = scraper.session.get("https://sufarmed.com/sufarmed/iniciar-sesion", timeout=15)
                    
                    st.write("**Análisis detallado de login:**")
                    st.write(f"- Status: {response.status_code}")
                    st.write(f"- URL: {response.url}")
                    st.write(f"- Longitud HTML: {len(response.text)}")
                    
                    # Buscar formularios
                    forms = re.findall(r'<form[^>]*>(.*?)</form>', response.text, re.DOTALL | re.IGNORECASE)
                    st.write(f"- Formularios encontrados: {len(forms)}")
                    
                    # Buscar campos
                    inputs = re.findall(r'<input[^>]*>', response.text, re.IGNORECASE)
                    st.write(f"- Inputs encontrados: {len(inputs)}")
                    
                    # Mostrar algunos inputs relevantes
                    relevant_inputs = [inp for inp in inputs if any(keyword in inp.lower() for keyword in ['email', 'password', 'token', 'hidden'])]
                    if relevant_inputs:
                        st.write("**Inputs relevantes:**")
                        for inp in relevant_inputs[:5]:
                            st.code(inp)
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("Configura credenciales primero")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Desarrollado con Streamlit 🚀 - Versión mejorada con debug avanzado</div>", 
    unsafe_allow_html=True
)
