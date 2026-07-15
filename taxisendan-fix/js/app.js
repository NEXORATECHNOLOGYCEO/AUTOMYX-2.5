/**
 * Taxisendan Fix - Lógica Principal
 * Inicialización del mapa Leaflet, geolocalización y manejo de eventos.
 */

(function() {
    'use strict';

    // Referencias globales para el mapa
    let map = null;
    let userMarker = null;
    let userCircle = null;
    const MAPBOX_TOKEN = TAXI_CONFIG.mapboxToken || 'pk.eyJ1IjoiZGVmYXVsdCIsImEiOiJjbGt4In0.example'; // Fallback por si config falla
    const DEFAULT_CENTER = [-34.6037, -58.3816]; // Buenos Aires como fallback
    const DEFAULT_ZOOM = 15;

    /**
     * Inicializa el sistema de debug y logs
     */
    function initDebug() {
        if (typeof Debug !== 'undefined' && typeof Debug.log === 'function') {
            Debug.log('Sistema de debug inicializado.');
        }
    }

    /**
     * Inicializa el mapa Leaflet en el contenedor #map
     */
    function initMap() {
        try {
            if (typeof L === 'undefined') {
                throw new Error('Leaflet no está cargado.');
            }

            const mapContainer = document.getElementById('map');
            if (!mapContainer) {
                throw new Error('Contenedor #map no encontrado en el DOM.');
            }

            // Crear mapa centrado en ubicación por defecto hasta obtener la real
            map = L.map('map').setView(DEFAULT_CENTER, DEFAULT_ZOOM);

            // Capa de tiles (OpenStreetMap gratuito, sin API key)
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                maxZoom: 19
            }).addTo(map);

            if (typeof Debug !== 'undefined') Debug.log('Mapa inicializado con OpenStreetMap.');

            // Intentar geolocalizar al usuario
            locateUser();

        } catch (error) {
            console.error('Error crítico al inicializar el mapa:', error);
            if (typeof Debug !== 'undefined') Debug.error('Fallo en initMap: ' + error.message);
            showMapError(error.message);
        }
    }

    /**
     * Obtiene la ubicación del usuario y actualiza el marcador
     */
    function locateUser() {
        if (!navigator.geolocation) {
            const errorMsg = 'La geolocalización no es soportada por este navegador.';
            console.warn(errorMsg);
            if (typeof Debug !== 'undefined') Debug.warn(errorMsg);
            return;
        }

        if (typeof Debug !== 'undefined') Debug.log('Solicitando ubicación del usuario...');

        navigator.geolocation.getCurrentPosition(
            // Éxito
            function(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                const accuracy = position.coords.accuracy;

                console.log(`Ubicación obtenida: ${lat}, ${lng} (precisión: ${accuracy}m)`);
                if (typeof Debug !== 'undefined') Debug.success(`Ubicación detectada: ${lat.toFixed(4)}, ${lng.toFixed(4)}`);

                // Mover el mapa
                map.setView([lat, lng], 16);

                // Eliminar marcador anterior si existe
                if (userMarker) {
                    map.removeLayer(userMarker);
                }
                if (userCircle) {
                    map.removeLayer(userCircle);
                }

                // Icono personalizado para el usuario
                const userIcon = L.divIcon({
                    className: 'user-marker-icon',
                    html: '<div style="width: 20px; height: 20px; background-color: #3b82f6; border: 3px solid white; border-radius: 50%; box-shadow: 0 2px 6px rgba(0,0,0,0.4);"></div>',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });

                // Añadir marcador
                userMarker = L.marker([lat, lng], { icon: userIcon }).addTo(map);
                userMarker.bindPopup('<b>📍 Tu ubicación</b><br>Precisión: ' + Math.round(accuracy) + ' metros').openPopup();

                // Añadir círculo de precisión
                userCircle = L.circle([lat, lng], {
                    radius: accuracy,
                    color: '#3b82f6',
                    fillColor: '#3b82f6',
                    fillOpacity: 0.15,
                    weight: 1
                }).addTo(map);
            },
            // Error
            function(error) {
                let errorMsg = 'Error desconocido al obtener ubicación.';
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = 'Permiso de geolocalización denegado. Por favor, habilita la ubicación en tu navegador.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = 'Información de ubicación no disponible.';
                        break;
                    case error.TIMEOUT:
                        errorMsg = 'Tiempo de espera agotado al obtener la ubicación.';
                        break;
                }
                console.warn('Geolocalización falló:', errorMsg);
                if (typeof Debug !== 'undefined') Debug.error('Geolocalización: ' + errorMsg);
            },
            // Opciones
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    }

    /**
     * Muestra un mensaje de error sobre el mapa si falla la carga
     */
    function showMapError(message) {
        const mapContainer = document.getElementById('map');
        if (mapContainer) {
            mapContainer.innerHTML = `
                <div style="display: flex; justify-content: center; align-items: center; height: 100%; background-color: #f3f4f6; flex-direction: column; padding: 20px; text-align: center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                    <h3 style="margin-top: 15px; color: #1f2937;">Error al cargar el mapa</h3>
                    <p style="color: #6b7280; max-width: 400px;">${message}</p>
                </div>
            `;
        }
    }

    /**
     * Maneja el evento de ventana redimensionada para actualizar el mapa
     */
    function handleResize() {
        if (map) {
            map.invalidateSize();
        }
    }

    // --- INICIALIZACIÓN AL CARGAR EL DOM ---
    document.addEventListener('DOMContentLoaded', function() {
        try {
            initDebug();
            initMap();
            window.addEventListener('resize', handleResize);
            
            if (typeof Debug !== 'undefined') Debug.log('App.js cargado y listo.');
        } catch (e) {
            console.error('Error en la inicialización global de app.js:', e);
        }
    });

})();
