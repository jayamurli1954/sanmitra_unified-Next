/**
 * Print utility functions
 */
import { buildReportHeaderHtml, reportBaseStyles, formatReportPeriod, tryExtractPeriodFromText } from './reportBranding';

const removeActionColumns = (root) => {
  root.querySelectorAll('table').forEach((table) => {
    const headerCells = Array.from(table.querySelectorAll('thead tr:first-child th, thead tr:first-child td'));
    const actionIndexes = headerCells
      .map((cell, index) => ({ index, text: (cell.textContent || '').trim().toLowerCase() }))
      .filter(({ text }) => ['action', 'actions', 'quick actions'].includes(text))
      .map(({ index }) => index);

    if (!actionIndexes.length) return;

    Array.from(table.rows).forEach((row) => {
      actionIndexes
        .slice()
        .sort((a, b) => b - a)
        .forEach((index) => {
          if (row.cells[index]) row.deleteCell(index);
        });
    });
  });
};

const sanitizePrintContent = (element) => {
  const clone = element.cloneNode(true);

  clone.querySelectorAll([
    '.no-print',
    'button',
    'input',
    'select',
    'textarea',
    'label',
    'svg',
    '[role="button"]',
    '[aria-label*="print" i]',
    '[aria-label*="export" i]',
  ].join(',')).forEach((node) => node.remove());

  removeActionColumns(clone);
  return clone.innerHTML;
};

/**
 * Print a specific element by ID
 */
export const printElement = (elementId, title = 'Print', options = {}) => {
  const element = document.getElementById(elementId);
  if (!element) {
    console.error(`Element with id "${elementId}" not found`);
    return;
  }

  const printWindow = window.open('', '_blank');
  if (!printWindow) return;
  const printContent = sanitizePrintContent(element);
  const derivedPeriod = options.period || tryExtractPeriodFromText(element.innerText || '');
  const headerHtml = buildReportHeaderHtml({ title, period: formatReportPeriod(derivedPeriod) });
  
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>${title}</title>
        <style>
          ${reportBaseStyles}
          @media print {
            @page {
              margin: 1cm;
            }
            body {
              font-family: Arial, sans-serif;
              font-size: 12px;
            }
            table {
              width: 100%;
              border-collapse: collapse;
            }
            th, td {
              border: 1px solid #ddd;
              padding: 8px;
              text-align: left;
            }
            th {
              background-color: #f2f2f2;
              font-weight: bold;
            }
            .no-print {
              display: none;
            }
          }
        </style>
      </head>
      <body>
        ${headerHtml}
        ${printContent}
      </body>
    </html>
  `);
  
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
    printWindow.close();
  }, 250);
};

/**
 * Print current page
 */
export const printPage = () => {
  window.print();
};

/**
 * Print table data
 */
export const printTable = (data, columns, title = 'Report', options = {}) => {
  const printWindow = window.open('', '_blank');
  if (!printWindow) return;
  const headerHtml = buildReportHeaderHtml({ title, period: formatReportPeriod(options.period) });
  
  let tableHTML = `
    <table>
      <thead>
        <tr>
          ${columns.map(col => `<th>${col.label || col.field}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${data.map(row => `
          <tr>
            ${columns.map(col => `<td>${row[col.field] || ''}</td>`).join('')}
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
  
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>${title}</title>
        <style>
          ${reportBaseStyles}
          @media print {
            @page { margin: 1cm; }
            body { font-family: Arial, sans-serif; font-size: 12px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; font-weight: bold; }
          }
        </style>
      </head>
      <body>
        ${headerHtml}
        ${tableHTML}
      </body>
    </html>
  `);
  
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
    printWindow.close();
  }, 250);
};




