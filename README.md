# 🍾 Sistema de Entradas Nominales y Control de Acceso - Fin de Año

Aplicación completa diseñada a medida para gestionar la venta presencial de entradas nominales con código QR cifrado y el control de acceso en puerta para **499 personas**, evitando plagios, reventas y entradas duplicadas.

---

## 🚀 Cómo arrancar el sistema en 1 segundo

Tienes dos formas de iniciarlo según si lo vas a usar solo en tu casa o necesitas compartir el enlace con los porteros y otros ordenadores:

### Opción 1: Con Enlace Público Seguro (Recomendado para la fiesta) 🌐
Genera un enlace público `https://xxxx.trycloudflare.com` con **HTTPS oficial** que funciona en cualquier teléfono móvil (4G/5G) y abre la cámara del escáner al instante:

```bash
cd /Users/ricardo/.gemini/antigravity/scratch/entradas-nochevieja
./iniciar_publico.sh
```

### Opción 2: Solo en red local / Offline 💻
Para usarlo en tu propio Mac o en la misma red Wi-Fi:

```bash
cd /Users/ricardo/.gemini/antigravity/scratch/entradas-nochevieja
./iniciar.sh
```

---

## 📋 ¿Cómo funciona el flujo paso a paso?

### 1. Venta en persona (Tú con tu portátil / móvil)
1. Cuando una persona viene a pagarte (en mano, Bizum, etc.), abres [http://localhost:8000](http://localhost:8000).
2. Introduces:
   - **Nombre y Apellidos**
   - **DNI / NIE / Pasaporte** (Nominal)
   - **Email**
   - **Teléfono móvil** (opcional, para enviársela por WhatsApp al instante)
   - **Precio cobrado y Método de pago** (Efectivo, Bizum, etc.)
   - **Observaciones** (ej. "Incluye 2 copas", "Mesa VIP")
3. Pulsas **"Emitir y Registrar Entrada"**.
4. El sistema comprueba automáticamente:
   - Que no se supere el aforo máximo de 499 personas.
   - Si ese DNI ya compró una entrada antes (para alertarte de posibles despistes).
5. Se abre una ventana de confirmación donde puedes:
   - **Enviar por WhatsApp**: Con un solo clic le envía a su WhatsApp el mensaje con el enlace a su entrada digital.
   - **Abrir Entrada Digital**: Para verla tú mismo o descargarla en PDF.
   - **Enviar por Email**: Si configuraste el servidor SMTP.

---

### 2. La Entrada Digital del Asistente
El cliente recibe su entrada personalizada:
* Diseño exclusivo y festivo para Nochevieja (dorado y negro).
* **Número de entrada secuencial** (ej: `#001 / 499`).
* **Nombre y DNI del titular**.
* **Código QR único de alta resolución** generado con token criptográfico (imposible de adivinar o falsear).
* **Aviso de seguridad**: Recuerda al asistente que es obligatorio presentar su DNI físico original en la puerta.

---

### 3. Nochevieja: Escaneo en Puerta (`/scanner`)
El personal de control de acceso abre la web `/scanner` desde su propio móvil:
* **Escaneo con la cámara**: Enfoca el QR del móvil del asistente.
* **Respuesta en pantalla y sonido**:
  * **Pantalla Verde con pitido alegre**: Muestra en letras gigantes el **NOMBRE y DNI** del titular. El portero pide el DNI físico, comprueba que coincida con la pantalla y le da paso. La entrada queda marcada como **USADA** con la hora exacta en la base de datos.
  * **Pantalla Roja de ALERTA con zumbido grave**: Si intentan pasar dos personas con la misma entrada (captura de pantalla reenviada), el sistema alerta de inmediato: *"¡ALERTA! Entrada ya utilizada a las 00:45:10 por Juan Pérez"*.
  * **Validación Manual de Respaldo**: Si al asistente se le ha roto la pantalla o se ha quedado sin batería, el portero puede escribir su DNI o número de entrada en la casilla inferior y pulsar *"Comprobar"*.
* **Contador en vivo**: Arriba indica en tiempo real cuántas personas van entrando en la sala (ej. `142 / 499`).

---

### 4. Exportar a Excel / Respaldo en papel
En la parte superior tienes el botón **"📥 Exportar Excel / CSV"**:
* Descarga al instante la lista completa de todos los asistentes con sus DNIs, números de entrada y horas de acceso.
* Ideal para imprimirla en papel como respaldo de seguridad para la puerta.

---

## ⚙️ Configuración opcional de correo (SMTP)
Si quieres que además se envíe automáticamente por email:
1. En la web pulsa en **"⚙️ Configuración"**.
2. Rellena los datos de tu cuenta (por ejemplo, una contraseña de aplicación de Gmail o una cuenta gratuita de Brevo/Resend).
3. Si no configuras SMTP, no pasa nada: puedes enviar todas las entradas por **WhatsApp** o enlace directo con los botones integrados.
