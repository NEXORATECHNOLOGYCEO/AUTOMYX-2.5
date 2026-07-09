const express = require('express');
const path = require('path');
const app = express();
const PORT = 5000;

// Middleware
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Rutas
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/api/status', (req, res) => {
  res.json({ status: 'AUTOMYX Server Running on Port 5000', timestamp: new Date() });
});

// Iniciar servidor
app.listen(PORT, () => {
  console.log(`\n🚀 AUTOMYX Server corriendo en http://localhost:${PORT}`);
  console.log(`📡 Puerto: ${PORT}`);
  console.log(`⏰ Hora: ${new Date().toLocaleString()}\n`);
});
