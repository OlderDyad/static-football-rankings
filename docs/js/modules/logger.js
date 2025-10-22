// docs/js/modules/logger.js
export const DEBUG_LEVELS = {
    DEBUG: 'DEBUG',
    INFO: 'INFO',
    WARNING: 'WARNING',
    ERROR: 'ERROR'
};

export function log(level, ...message) {
    console.log(`[${level}]`, ...message);
}