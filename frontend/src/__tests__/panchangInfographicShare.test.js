import {
  WHATSAPP_WEB_URL,
  sharePanchangInfographicToWhatsApp,
} from '../utils/panchangInfographic';

describe('sharePanchangInfographicToWhatsApp', () => {
  const file = new File(['png'], 'panchang-2026-11-10.png', { type: 'image/png' });
  const original = {
    canShare: navigator.canShare,
    share: navigator.share,
    clipboard: navigator.clipboard,
    open: window.open,
    ClipboardItem: window.ClipboardItem,
    createObjectURL: URL.createObjectURL,
    revokeObjectURL: URL.revokeObjectURL,
  };

  const setNavigator = (key, value) => {
    Object.defineProperty(navigator, key, { value, configurable: true, writable: true });
  };

  beforeEach(() => {
    window.open = jest.fn();
    window.ClipboardItem = function ClipboardItem(items) {
      this.items = items;
    };
    URL.createObjectURL = jest.fn(() => 'blob:card');
    URL.revokeObjectURL = jest.fn();
  });

  afterEach(() => {
    setNavigator('canShare', original.canShare);
    setNavigator('share', original.share);
    setNavigator('clipboard', original.clipboard);
    window.open = original.open;
    window.ClipboardItem = original.ClipboardItem;
    URL.createObjectURL = original.createObjectURL;
    URL.revokeObjectURL = original.revokeObjectURL;
  });

  it('hands the image to the share sheet when the browser can share files', async () => {
    setNavigator('canShare', jest.fn(() => true));
    setNavigator('share', jest.fn(() => Promise.resolve()));

    await expect(sharePanchangInfographicToWhatsApp(file)).resolves.toBe('shared');
    expect(navigator.share).toHaveBeenCalledWith({ files: [file], title: 'Panchang' });
    expect(window.open).not.toHaveBeenCalled();
  });

  it('does nothing more when the user closes the share sheet', async () => {
    setNavigator('canShare', jest.fn(() => true));
    setNavigator('share', jest.fn(() => Promise.reject(Object.assign(new Error('x'), { name: 'AbortError' }))));

    await expect(sharePanchangInfographicToWhatsApp(file)).resolves.toBe('cancelled');
    expect(window.open).not.toHaveBeenCalled();
  });

  it('copies the image and opens WhatsApp Web when files cannot be shared', async () => {
    setNavigator('canShare', undefined);
    const write = jest.fn(() => Promise.resolve());
    setNavigator('clipboard', { write });

    await expect(sharePanchangInfographicToWhatsApp(file)).resolves.toBe('copied');
    expect(write).toHaveBeenCalledTimes(1);
    expect(window.open).toHaveBeenCalledWith(WHATSAPP_WEB_URL, '_blank', 'noopener,noreferrer');
  });

  it('downloads the image and opens WhatsApp Web when the clipboard is blocked', async () => {
    setNavigator('canShare', undefined);
    setNavigator('clipboard', { write: jest.fn(() => Promise.reject(new Error('denied'))) });

    await expect(sharePanchangInfographicToWhatsApp(file)).resolves.toBe('downloaded');
    expect(URL.createObjectURL).toHaveBeenCalledWith(file);
    expect(window.open).toHaveBeenCalledWith(WHATSAPP_WEB_URL, '_blank', 'noopener,noreferrer');
  });

  it('reports when the image is not ready', async () => {
    await expect(sharePanchangInfographicToWhatsApp(null)).resolves.toBe('unavailable');
  });
});
