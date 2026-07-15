/**
 * debug.js - Sistema de logging personalizado con timestamps y colores
 * Util para diagnosticar carga de scripts, errores CORS y recursos 404
 */

(function() {
    'use strict';

    // Colores para la consola (%c es el formato de estilo en console.log)
    const COLORS = {
        info: '#3498db',      // Azul
        warn: '#f39c12',      // Naranja
        error: '#e74c3c',     // Rojo
        success: '#2ecc71',   // Verde
        debug: '#9b59b6',     // Morado
        log: '#ecf0f1'        // Blanco/Gris claro
    };

    /**
     * Genera un timestamp formateado [HH:MM:SS:ms]
     */
    function getTimestamp() {
        const now = new Date();
        const h = String(now.getHours()).padStart(2, '0');
        const m = String(now.getMinutes()).padStart(2, '0');
        const s = String(now.getSeconds()).padStart(2, '0');
        const ms = String(now.getMilliseconds()).padStart(3, '0');
        return `[${h}:${m}:${s}.${ms}]`;
    }

    /**
     * Logger principal estilizado
     */
    function log(type, message, data) {
        const timestamp = getTimestamp();
        const color = COLORS[type] || COLORS.log;
        const prefix = type.toUpperCase();
        
        // Construir el estilo CSS para console.log
        const style = `color: ${color}; font-weight: bold; font-family: monospace;`;
        const prefixStyle = `background: #333; color: ${color}; padding: 2px 6px; border-radius: 3px; font-weight: bold;`;

        let consoleMessage = `%c${prefix} %c${timestamp} %c${message}`;
        
        // Argumentos de estilo para cada parte del mensaje
        const args = [
            prefixStyle,      // Estilo para [INFO]
            `color: ${color};`, // Estilo para timestamp
            'color: #fff;'    // Estilo para el mensaje
        ];

        switch(type) {
            case 'info':
                console.log(consoleMessage, ...args);
                break;
            case 'warn':
                console.warn(consoleMessage, ...args);
                break;
            case 'error':
                console.error(consoleMessage, ...args);
                if (data) {
                    console.error('%cDetalle del error:', 'color: #e74c3c; font-weight: bold;', data);
                }
                break;
            case 'success':
                console.log(`%c✅ ${prefix} %c${timestamp} %c${message}`, prefixStyle, `color: ${color};`, 'color: #fff;');
                break;
            case 'debug':
                console.debug(consoleMessage, ...args);
                if (data) {
                    console.debug('%cDatos:', 'color: #9b59b6; font-weight: bold;', data);
                }
                break;
            default:
                console.log(consoleMessage, ...args);
        }
    }

    /**
     * Diagnóstico inicial del entorno
     */
    function diagnoseEnvironment() {
        log('info', 'Iniciando diagnóstico del entorno...');
        
        // Verificar si TAXI_CONFIG existe (cargado por config.js)
        if (typeof window.TAXI_CONFIG !== 'undefined') {
            log('success', 'TAXI_CONFIG encontrado:', window.TAXI_CONFIG);
        } else {
            log('error', 'TAXI_CONFIG NO encontrado. Asegúrate de cargar js/config.js ANTES de este archivo.');
        }

        // Verificar APIs globales
        const checks = [
            { name: 'Leaflet', test: typeof L !== 'undefined' },
            { name: 'Fetch API', test: typeof fetch !== 'undefined' },
            { name: 'Geolocation', test: typeof navigator.geolocation !== 'undefined' }
        ];

        checks.forEach(check => {
            if (check.test) {
                log('success', `${check.name} disponible`);
            } else {
                log('error', `${check.name} NO disponible`);
            }
        });

        // Información del navegador
        log('debug', 'User Agent:', navigator.userAgent);
        log('info', 'URL actual:', window.location.href);
        log('info', 'Origen (Origin):', window.location.origin);
    }

    /**
     * Wrapper para monitorizar peticiones fetch y detectar CORS/404
     */
    function monitorFetch() {
        const originalFetch = window.fetch;
        
        window.fetch = function(...args) {
            const url = args[0];
            log('debug', `Petición fetch iniciada: ${url}`);

            return originalFetch.apply(this, args)
                .then(response => {
                    if (response.ok) {
                        log('success', `Fetch exitoso: ${url} (${response.status})`);
                    } else {
                        log('warn', `Fetch con error HTTP: ${url} (${response.status})`);
                    }
                    return response;
                })
                .catch(error => {
                    if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                        log('error', `CORS o Network Error en: ${url}`, error);
                    } else {
                        log('error', `Error en fetch: ${url}`, error);
                    }
                    throw error;
                });
        };
    }

    /**
     * Monitorizar recursos cargados (img, scripts, css) para detectar 404
     */
    function monitorResources() {
        window.addEventListener('error', function(e) {
            const target = e.target || e.srcElement;
            const src = target.src || target.href || target.currentScript?.src;
            
            if (src && src !== 'about:blank') {
                log('error', `Recurso falló al cargar: ${src}`);
            }
        }, true);

        window.addEventListener('load', function() {
            log('success', 'Ventana cargada completamente. Todos los recursos procesados.');
        });
    }

    // Inicializar el sistema de debug
    if (typeof window.TAXI_DEBUG === 'undefined') {
        window.TAXI_DEBUG = {
            log: log,
            info: function(msg, data) { log('info', msg, data); },
            warn: function(msg, data) { log('warn', msg, data); },
            error: function(msg, data) { log('error', msg, data); },
            success: function(msg, data) { log('success', msg, data); },
            debug: function(msg, data) { log('debug', msg, data); }
        };

        // Ejecutar diagnóstico
        monitorFetch();
        monitorResources();
        diagnoseEnvironment();
    } else {
        console.warn('TAXI_DEBUG ya está definido. No se inicializa nuevamente.');
    }

})();
