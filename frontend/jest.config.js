const { createDefaultPreset } = require("ts-jest");

const tsJestTransformCfg = createDefaultPreset().transform;

/** @type {import("jest").Config} **/
module.exports = {
    testEnvironment: "jsdom",
    transform: {
        "^.+\\.(ts|tsx)$": ["ts-jest", { tsconfig: "<rootDir>/tsconfig.test.json" }],
    },
    setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
    moduleFileExtensions: ["ts", "tsx", "js", "jsx", "json", "node"],
    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/$1',
        '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
        '^.*\\.css$': 'identity-obj-proxy',
    },
    testPathIgnorePatterns: [
        '/node_modules/',
        '/.next/',
        '/dist/',
    ],
    transformIgnorePatterns: [
        '/node_modules/(?!(.*\\.css$))',
    ],
    // Configure Jest for React 18
    testEnvironmentOptions: {
        customExportConditions: [''],
    },
    // Increase timeout for async operations
    testTimeout: 10000,
};