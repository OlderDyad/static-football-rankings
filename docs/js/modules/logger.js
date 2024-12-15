// logger.js
export const DEBUG_LEVELS = {
    ERROR: 0,
    WARN: 1,
    INFO: 2,
    DEBUG: 3
};

const CURRENT_LEVEL = DEBUG_LEVELS.INFO; // Set default level

export function log(level, ...args) {
    if (level <= CURRENT_LEVEL) {
        const timestamp = new Date().toISOString();
        const levelName = Object.keys(DEBUG_LEVELS).find(key => DEBUG_LEVELS[key] === level);
        
        switch (level) {
            case DEBUG_LEVELS.ERROR:
                console.error(`[${timestamp}] [${levelName}]`, ...args);
                break;
            case DEBUG_LEVELS.WARN:
                console.warn(`[${timestamp}] [${levelName}]`, ...args);
                break;
            case DEBUG_LEVELS.INFO:
                console.info(`[${timestamp}] [${levelName}]`, ...args);
                break;
            case DEBUG_LEVELS.DEBUG:
                console.debug(`[${timestamp}] [${levelName}]`, ...args);
                break;
        }
    }
}