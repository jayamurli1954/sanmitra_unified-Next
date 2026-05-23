// jest-dom adds custom jest matchers for asserting on DOM nodes.
import '@testing-library/jest-dom';

// Mock window.matchMedia (not available in jsdom)
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
    })),
});

// Mock IntersectionObserver (not available in jsdom)
global.IntersectionObserver = class IntersectionObserver {
    constructor() { }
    observe() { return null; }
    unobserve() { return null; }
    disconnect() { return null; }
};

// Suppress noisy warnings/errors that clutter test output
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
    console.error = (...args) => {
        const msg = typeof args[0] === 'string' ? args[0] : '';
        if (
            msg.includes('Warning: An update to') ||
            msg.includes('Warning: validateDOMNesting') ||
            msg.includes('Not implemented: navigation') ||
            msg.includes('React Router') ||
            msg.includes('MemoryRouter')
        ) {
            return;
        }
        originalError.call(console, ...args);
    };

    console.warn = (...args) => {
        const msg = typeof args[0] === 'string' ? args[0] : '';
        if (
            msg.includes('React Router') ||
            msg.includes('No routes matched') ||
            msg.includes('basename')
        ) {
            return;
        }
        originalWarn.call(console, ...args);
    };
});

afterAll(() => {
    console.error = originalError;
    console.warn = originalWarn;
});
