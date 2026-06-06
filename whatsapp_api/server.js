const express = require('express');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const http = require('http');

const app = express();
app.use(express.json());

let currentQR = null;
let isConnected = false;

// Configurar el cliente de WhatsApp
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Evento: Se genera el código QR
client.on('qr', async (qr) => {
    console.log('Nuevo QR generado');
    // Convertir el texto QR a imagen base64 para el frontend
    currentQR = await qrcode.toDataURL(qr);
    isConnected = false;
});

// Evento: Cliente autenticado y listo
client.on('ready', () => {
    console.log('¡WhatsApp Bot conectado y listo!');
    isConnected = true;
    currentQR = null;
});

// Evento: Cliente desconectado
client.on('disconnected', (reason) => {
    console.log('WhatsApp desconectado:', reason);
    isConnected = false;
    currentQR = null;
    client.initialize(); // Reiniciar para generar un nuevo QR
});

// Evento: Escuchar mensajes entrantes y responder automáticamente
const dmPolicy = "pairing"; // 'pairing' o 'open'
const allowedNumbers = new Set(); // Números permitidos

client.on('message', async (msg) => {
    console.log(`Mensaje recibido de ${msg.from}: ${msg.body}`);
    
    // Evitar responder a mensajes de grupos para no hacer spam o a mensajes propios
    if (!msg.from.includes('@g.us') && !msg.fromMe) {
        
        // --- POLÍTICA DE SEGURIDAD TIPO OPENCLAW (DM PAIRING) ---
        if (dmPolicy === "pairing" && !allowedNumbers.has(msg.from)) {
            // Si el usuario envía el código de aprobación
            if (msg.body.trim() === "APPROVE_ME") {
                allowedNumbers.add(msg.from);
                await msg.reply('✅ *Automyx Gateway:* Dispositivo emparejado con éxito. Ahora puedes hablar con la IA.');
                return;
            } else {
                // Bloquear y pedir código
                await msg.reply('🔒 *Automyx Gateway:* Acceso denegado. Este es un asistente privado. Envía el código "APPROVE_ME" para solicitar acceso.');
                return;
            }
        }
        // --------------------------------------------------------

        try {
            // Preparar datos para enviar a FastAPI
            const postData = JSON.stringify({
                from_number: msg.from,
                message: msg.body
            });

            const options = {
                hostname: '127.0.0.1',
                port: 8000,
                path: '/api/whatsapp/webhook',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(postData)
                }
            };

            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', (chunk) => { data += chunk; });
                res.on('end', async () => {
                    try {
                        const parsedData = JSON.parse(data);
                        await msg.reply(parsedData.reply);
                        console.log(`Auto-respuesta IA enviada a ${msg.from}`);
                    } catch (e) {
                        console.error('Error parseando respuesta:', e);
                        await msg.reply('🤖 *Hola, te comunicas con Automyx*.\n\nEl usuario no está disponible y mi motor de IA tuvo un error al procesar la respuesta.');
                    }
                });
            });

            req.on('error', async (e) => {
                console.error(`Error consultando a FastAPI: ${e.message}`);
                await msg.reply('🤖 *Hola, te comunicas con Automyx*.\n\nEl usuario no está disponible y mi motor de IA está apagado en este momento.');
            });

            req.write(postData);
            req.end();

        } catch (err) {
            console.error('Error general:', err);
        }
    }
});

// Inicializar cliente
console.log('Inicializando cliente de WhatsApp...');
client.initialize();

// Rutas de la API (Consumidas por FastAPI)
app.get('/qr', (req, res) => {
    res.json({ qr: currentQR, connected: isConnected });
});

app.get('/status', (req, res) => {
    res.json({ connected: isConnected });
});

app.post('/send', async (req, res) => {
    if (!isConnected) {
        return res.status(400).json({ error: 'WhatsApp no está conectado' });
    }
    
    const { number, message } = req.body;
    try {
        // whatsapp-web.js requiere el número en formato internacional + "@c.us"
        const formattedNumber = number.replace('+', '') + '@c.us';
        await client.sendMessage(formattedNumber, message);
        console.log(`Mensaje enviado a ${number}`);
        res.json({ success: true });
    } catch (error) {
        console.error('Error enviando mensaje:', error);
        res.status(500).json({ error: error.message });
    }
});

const PORT = 3001;
app.listen(PORT, () => {
    console.log(`Servidor de WhatsApp interno corriendo en el puerto ${PORT}`);
});
