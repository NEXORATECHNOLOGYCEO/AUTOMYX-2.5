/**
 * TAXI SENDAN - Configuración Centralizada
 * 
 * Este archivo define el objeto global TAXI_CONFIG que contiene:
 * - Claves de API para mapas (Leaflet/Mapbox/OpenStreetMap)
 * - Endpoints del backend (si aplica)
 * - Constantes de la aplicación
 */

// Objeto global de configuración
const TAXI_CONFIG = {
  // =========================================================
  // MAPAS Y GEOLOCALIZACIÓN
  // =========================================================
  maps: {
    // Opción A: OpenStreetMap (GRATUITO, no requiere API Key)
    // Recomendado para empezar sin configuraciones adicionales
    use_openstreetmap: true,
    
    // Opción B: Mapbox (Requiere cuenta y API Key)
    mapbox: {
      access_token: null, // Reemplazar con tu token de Mapbox: pk.eyJ1...
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [-74.0817, 4.6097], // Coordenadas por defecto (Bogotá, ejemplo)
      zoom: 13
    },
    
    // Opción C: Leaflet con tiles personalizados
    leaflet: {
      tile_url_template: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      tile_subdomains: ['a', 'b', 'c'],
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    },
    
    // Geocodificación (convertir dirección <-> coordenadas)
    geocoder: {
      // Usar Nominatim de OpenStreetMap (gratuito, sin API key)
      url_template: 'https://nominatim.openstreetmap.org/search?format=json&q={query}',
      reverse_url_template: 'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}',
      // Límite de peticiones por segundo (Nominatim pide ser amable)
      requests_per_second: 1
    }
  },

  // =========================================================
  // BACKEND / API
  // =========================================================
  backend: {
    // URL base del servidor (si el proyecto tiene backend propio)
    // Si no hay backend, dejar vacío o null
    base_url: '',
    
    // Endpoints
    endpoints: {
      get_fares: '/api/fares',
      create_ride: '/api/rides',
      update_location: '/api/location',
      status: '/api/status'
    },
    
    // Configuración de peticiones HTTP
    fetch_options: {
      headers: {
        'Content-Type': 'application/json'
      },
      mode: 'cors',
      credentials: 'same-origin'
    }
  },

  // =========================================================
  // GEOLOCALIZACIÓN DEL NAVEGADOR
  // =========================================================
  geolocation: {
    // Opciones de la API de geolocalización del navegador
    enable_high_accuracy: true,
    maximum_age: 30000,      // Máximo 30 segundos entre actualizaciones
    timeout: 10000,          // Timeout de 10 segundos
    
    // Coordenadas por defecto si el usuario niega el permiso
    fallback_location: {
      lat: -74.0817,
      lng: 4.6097,
      label: 'Ubicación predeterminada (usuario denegó acceso)'
    }
  },

  // =========================================================
  // UI / INTERFAZ DE USUARIO
  // =========================================================
  ui: {
    // Colores de la marca
    colors: {
      primary: '#FFD700',   // Amarillo taxi
      secondary: '#1a1a1a',  // Negro fondo
      accent: '#32CD32',    // Verde éxito
      error: '#DC143C'      // Rojo error
    },
    
    // Animaciones
    animations: {
      enabled: true,
      duration_ms: 300,
      easing: 'ease-in-out'
    }
  },

  // =========================================================
  // DEBUG / DIAGNÓSTICO
  // =========================================================
  debug: {
    // Activar logs detallados en consola
    enabled: true,
    
    // Nivel de log: 'info', 'warn', 'error', 'verbose'
    level: 'verbose',
    
    // Guardar logs en memoria para inspección posterior
    save_logs: true,
    max_log_entries: 500
  }
};

// Exportar para entornos que lo soporte (Node.js, módulos)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TAXI_CONFIG;
}
