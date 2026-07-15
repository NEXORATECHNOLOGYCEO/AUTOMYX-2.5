/**
 * utils.js - Funciones auxiliares: geolocalización, geocodificación inversa, cálculo de distancias
 */

(function() {
    'use strict';

    const TAXI_CONFIG = window.TAXI_CONFIG || {};
    const GOOGLE_MAPS_API_KEY = TAXI_CONFIG.googleMapsApiKey || '';

    /**
     * Obtener la ubicación actual del usuario (una sola vez)
     * @returns {Promise<{lat: number, lng: number}>}
     */
    function getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                // Fallback a IP si no hay geolocalización
                resolve(getLocationByIP());
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    TAXI_DEBUG.success('Ubicación obtenida:', { lat, lng });
                    resolve({ lat, lng });
                },
                (error) => {
                    TAXI_DEBUG.warn('Error de geolocalización:', error);
                    // Fallback a IP
                    getLocationByIP().then(resolve).catch(reject);
                },
                { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
            );
        });
    }

    /**
     * Obtener ubicación aproximada por IP
     * @returns {Promise<{lat: number, lng: number}>}
     */
    async function getLocationByIP() {
        try {
            TAXI_DEBUG.info('Obteniendo ubicación por IP...');
            const response = await fetch('https://ipapi.co/json/');
            const data = await response.json();
            if (data && data.latitude && data.longitude) {
                TAXI_DEBUG.success('Ubicación por IP obtenida:', { lat: data.latitude, lng: data.longitude });
                return { lat: data.latitude, lng: data.longitude };
            }
        } catch (error) {
            TAXI_DEBUG.error('Error al obtener ubicación por IP:', error);
        }
        // Fallback final a CDMX
        TAXI_DEBUG.warn('Fallback a CDMX (Centro)');
        return { lat: 19.4326, lng: -99.1332 };
    }

    /**
     * Geocodificación inversa con Google Maps API
     * @param {number} lat
     * @param {number} lng
     * @returns {Promise<string>}
     */
    async function reverseGeocode(lat, lng) {
        if (!GOOGLE_MAPS_API_KEY) {
            TAXI_DEBUG.warn('Google Maps API key no configurada. Usando dirección genérica.');
            return 'Ubicación actual';
        }

        try {
            const url = `https://maps.googleapis.com/maps/api/geocode/json?latlng=${lat},${lng}&key=${GOOGLE_MAPS_API_KEY}&language=es`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.status === 'OK' && data.results.length > 0) {
                // Retornar la dirección más específica disponible
                const address = data.results[0].formatted_address;
                TAXI_DEBUG.success('Dirección obtenida:', address);
                return address;
            }
        } catch (error) {
            TAXI_DEBUG.error('Error en geocodificación inversa:', error);
        }
        return 'Ubicación actual';
    }

    /**
     * Geocodificación directa (dirección → coordenadas)
     * @param {string} address
     * @returns {Promise<{lat: number, lng: number}>}
     */
    async function geocodeAddress(address) {
        if (!GOOGLE_MAPS_API_KEY) {
            TAXI_DEBUG.warn('Google Maps API key no configurada para geocodificación directa.');
            return null;
        }

        try {
            const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(address)}&key=${GOOGLE_MAPS_API_KEY}&language=es`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.status === 'OK' && data.results.length > 0) {
                const location = data.results[0].geometry.location;
                TAXI_DEBUG.success('Dirección geocodificada:', { lat: location.lat, lng: location.lng });
                return { lat: location.lat, lng: location.lng };
            }
        } catch (error) {
            TAXI_DEBUG.error('Error en geocodificación directa:', error);
        }
        return null;
    }

    /**
     * Calcular distancia entre dos coordenadas (fórmula de Haversine)
     * @param {number} lat1
     * @param {number} lng1
     * @param {number} lat2
     * @param {number} lng2
     * @returns {number} Distancia en kilómetros
     */
    function calculateDistance(lat1, lng1, lat2, lng2) {
        const R = 6371; // Radio de la Tierra en km
        const dLat = toRad(lat2 - lat1);
        const dLng = toRad(lng2 - lng1);
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    /**
     * Convertir grados a radianes
     */
    function toRad(degrees) {
        return degrees * (Math.PI / 180);
    }

    /**
     * Calcular tarifa estimada
     * @param {number} distanceKm
     * @param {string} zone
     * @returns {{base: number, total: number}}
     */
    function calculateFare(distanceKm, zone = 'urbano') {
        const fares = TAXI_CONFIG.fares[zone] || TAXI_CONFIG.fares.urban;
        if (!fares) {
            return { base: 15, total: 15 + (distanceKm * 5) };
        }

        const baseFare = fares.base;
        const perKm = fares.perKm;
        const minFare = fares.min;

        let total = baseFare + (distanceKm * perKm);
        total = Math.max(total, minFare);

        return { base: baseFare, perKm: perKm, total: Math.round(total) };
    }

    /**
     * Formatear duración en formato legible
     * @param {number} minutes
     * @returns {string}
     */
    function formatDuration(minutes) {
        if (minutes < 1) return '< 1 min';
        if (minutes === 1) return '1 min';
        if (minutes < 60) return `${Math.round(minutes)} min`;

        const hours = Math.floor(minutes / 60);
        const mins = Math.round(minutes % 60);
        return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    }

    /**
     * Exponer funciones al objeto TAXI_UTILS
     */
    if (typeof window.TAXI_UTILS === 'undefined') {
        window.TAXI_UTILS = {
            getCurrentLocation,
            reverseGeocode,
            geocodeAddress,
            calculateDistance,
            calculateFare,
            formatDuration
        };
    }

})();
