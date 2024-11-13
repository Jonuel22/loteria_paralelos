const express = require('express');
const mysql = require('mysql2');
const cors = require('cors');

const app = express();
const PORT = 3000;

app.use(cors());

// Configuración de la base de datos
const db = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: '2002',
    database: 'loteria'
});

db.connect(err => {
    if (err) throw err;
    console.log('Conectado a la base de datos.');
});

// Endpoint para obtener el resultado actual de la lotería
app.get('/api/loteria/:nombre', (req, res) => {
    const nombreLoteria = req.params.nombre;
    db.query(
        `SELECT numero1, numero2, numero3, fecha FROM resultados WHERE nombre_loteria = ? ORDER BY fecha DESC LIMIT 1`,
        [nombreLoteria],
        (err, results) => {
            if (err) throw err;
            res.json(results[0] || { numero1: 0, numero2: 0, numero3: 0 });
        }
    );
});

// Endpoint para obtener el resultado anterior de la lotería (penúltimo registro)
app.get('/api/loteria/:nombre/anterior', (req, res) => {
    const nombreLoteria = req.params.nombre;
    db.query(
        `SELECT numero1, numero2, numero3, fecha FROM resultados WHERE nombre_loteria = ? ORDER BY fecha DESC LIMIT 1 OFFSET 1`,
        [nombreLoteria],
        (err, results) => {
            if (err) throw err;
            res.json(results[0] || { numero1: 0, numero2: 0, numero3: 0 });
        }
    );
});


// Endpoint para obtener la última dirección de imagen y su duración
app.get('/api/imagen', (req, res) => {
    db.query(
        `SELECT direccion, duracion FROM imagenes ORDER BY id DESC LIMIT 1`,
        (err, results) => {
            if (err) throw err;
            if (results.length > 0) {
                res.json({ direccion: results[0].direccion, duracion: results[0].duracion });
            } else {
                res.json({ direccion: null, duracion: null });
            }
        }
    );
});


app.listen(PORT, () => {
    console.log(`Servidor API en ejecución en http://localhost:${PORT}`);
});
