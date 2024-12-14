// docs/js/modules/logger.js
export const DEBUG_LEVELS = {
    ERROR: 'ERROR',
    WARN: 'WARN',
    INFO: 'INFO',
    DEBUG: 'DEBUG'
};

export function log(level, ...args) {
    console.log([], ...args);
}
