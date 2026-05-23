/**
 * Tests for the axios API service (src/services/api.js)
 * Covers: auth token injection, 401 redirect, error message extraction
 *
 * Strategy: We capture the interceptor functions registered by the api module
 * and test them in isolation using a module-level mock of axios.
 */

// Capture interceptor functions when they are registered
let requestInterceptor = null;
let responseSuccessInterceptor = null;
let responseErrorInterceptor = null;

jest.mock('axios', () => {
    const mockInstance = {
        interceptors: {
            request: {
                use: jest.fn((fn) => { requestInterceptor = fn; }),
            },
            response: {
                use: jest.fn((success, error) => {
                    responseSuccessInterceptor = success;
                    responseErrorInterceptor = error;
                }),
            },
        },
        defaults: { headers: { common: {} } },
    };

    return {
        __esModule: true,
        default: {
            create: jest.fn(() => mockInstance),
        },
        create: jest.fn(() => mockInstance),
    };
});

// Import AFTER mock is set up so interceptors register on our mocked axios
require('../services/api');

beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    delete window.location;
    window.location = { href: '' };
});

describe('API Service - Request Interceptor', () => {
    it('registers a request interceptor', () => {
        expect(requestInterceptor).toBeInstanceOf(Function);
    });

    it('adds Authorization header when token exists in sessionStorage', () => {
        sessionStorage.setItem('mm_access_token_v1', 'my-jwt-token');
        const config = { headers: {} };
        const result = requestInterceptor(config);
        expect(result.headers.Authorization).toBe('Bearer my-jwt-token');
    });

    it('does not add Authorization header when no token in sessionStorage', () => {
        const config = { headers: {} };
        const result = requestInterceptor(config);
        expect(result.headers['Authorization']).toBeUndefined();
    });
});

describe('API Service - Response Interceptor', () => {
    it('registers success and error handlers', () => {
        expect(responseSuccessInterceptor).toBeInstanceOf(Function);
        expect(responseErrorInterceptor).toBeInstanceOf(Function);
    });

    it('success handler returns the response unchanged', () => {
        const fakeResponse = { data: [{ id: 1 }], status: 200 };
        expect(responseSuccessInterceptor(fakeResponse)).toBe(fakeResponse);
    });

    it('error handler clears auth session and redirects to /login on 401', async () => {
        sessionStorage.setItem('mm_access_token_v1', 'expired');
        sessionStorage.setItem('mm_current_user_v1', '{"email":"a@b.com"}');

        const error = { response: { status: 401, data: {} }, message: 'Unauthorized' };
        try { await responseErrorInterceptor(error); } catch (e) { }

        expect(sessionStorage.getItem('mm_access_token_v1')).toBeNull();
        expect(sessionStorage.getItem('mm_current_user_v1')).toBeNull();
        expect(window.location.href).toBe('/login');
    });

    it('error handler attaches userMessage from response.data.detail', async () => {
        const error = { response: { status: 400, data: { detail: 'Invalid phone' } }, message: '' };
        let caught;
        try { await responseErrorInterceptor(error); } catch (e) { caught = e; }
        expect(caught.userMessage).toBe('Invalid phone');
    });

    it('error handler attaches userMessage from response.data.message', async () => {
        const error = { response: { status: 422, data: { message: 'Validation error' } }, message: '' };
        let caught;
        try { await responseErrorInterceptor(error); } catch (e) { caught = e; }
        expect(caught.userMessage).toBe('Validation error');
    });

    it('error handler attaches userMessage from error.message when no response data', async () => {
        const error = { response: { status: 500, data: {} }, message: 'Internal error' };
        let caught;
        try { await responseErrorInterceptor(error); } catch (e) { caught = e; }
        expect(caught.userMessage).toBeDefined();
    });

    it('error handler attaches fallback message when no response', async () => {
        const error = { response: null, message: 'Network Error' };
        let caught;
        try { await responseErrorInterceptor(error); } catch (e) { caught = e; }
        expect(caught.userMessage).toBe('Network Error');
    });
});
