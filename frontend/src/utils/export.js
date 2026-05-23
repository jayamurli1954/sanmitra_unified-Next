/**
 * Export utility functions
 */
import { buildReportHeaderHtml, reportBaseStyles, formatReportPeriod } from './reportBranding';

/**
 * Export data to CSV
 */
export const exportToCSV = (data, filename = 'export.csv', headers = null) => {
  if (!data || data.length === 0) {
    console.error('No data to export');
    return;
  }

  // Get headers from first object if not provided
  const csvHeaders = headers || Object.keys(data[0]);
  
  // Create CSV content
  const csvContent = [
    csvHeaders.join(','), // Header row
    ...data.map(row => 
      csvHeaders.map(header => {
        const value = row[header];
        // Handle values with commas or quotes
        if (value === null || value === undefined) return '';
        const stringValue = String(value);
        if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }
        return stringValue;
      }).join(',')
    )
  ].join('\n');

  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

/**
 * Export data to Excel (using CSV format, can be opened in Excel)
 */
export const exportToExcel = (data, filename = 'export.xlsx', headers = null) => {
  // For now, export as CSV which Excel can open
  // In future, can use a library like xlsx for proper Excel format
  exportToCSV(data, filename.replace('.xlsx', '.csv'), headers);
};

/**
 * Export table to CSV
 */
export const exportTableToCSV = (tableId, filename = 'table-export.csv') => {
  const table = document.getElementById(tableId);
  if (!table) {
    console.error(`Table with id "${tableId}" not found`);
    return;
  }

  const rows = Array.from(table.querySelectorAll('tr'));
  const csvData = rows.map(row => {
    const cols = Array.from(row.querySelectorAll('th, td'));
    return cols.map(col => {
      const text = col.textContent.trim();
      if (text.includes(',') || text.includes('"') || text.includes('\n')) {
        return `"${text.replace(/"/g, '""')}"`;
      }
      return text;
    }).join(',');
  });

  const csvContent = csvData.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

/**
 * Export JSON data
 */
export const exportToJSON = (data, filename = 'export.json') => {
  const jsonContent = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonContent], { type: 'application/json' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

/**
 * Export data to PDF via print dialog (browser Save as PDF).
 */
export const exportToPDF = (data, title = 'Report', options = {}) => {
  if (!Array.isArray(data) || data.length === 0) {
    return;
  }
  const headers = Object.keys(data[0]);
  const safeTitle = String(title || 'Report').replace(/[<>]/g, '').trim();
  const period = formatReportPeriod(options.period);
  const pageSize = Number(options.pageSize) > 0 ? Number(options.pageSize) : 28;
  const numericHeaders = headers.filter((header) => data.some((row) => {
    const value = row?.[header];
    if (value === null || value === undefined || value === '') return false;
    const num = Number(String(value).replace(/,/g, ''));
    return Number.isFinite(num);
  }));
  const parseNumeric = (value) => {
    const num = Number(String(value ?? '').replace(/,/g, ''));
    return Number.isFinite(num) ? num : 0;
  };
  const escapeHtml = (value = '') =>
    String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  const formatNumber = (num) => {
    try {
      return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(num || 0);
    } catch (err) {
      return String(num || 0);
    }
  };

  const pageChunks = [];
  for (let index = 0; index < data.length; index += pageSize) {
    pageChunks.push(data.slice(index, index + pageSize));
  }

  const runningTotals = Object.fromEntries(numericHeaders.map((header) => [header, 0]));
  const pageTablesHtml = pageChunks
    .map((chunk, pageIndex) => {
      const headerHtml = headers
        .map((header) => {
          const className = numericHeaders.includes(header) ? 'num' : '';
          return `<th class="${className}">${escapeHtml(header)}</th>`;
        })
        .join('');

      const bfFromRow = pageIndex > 0
        ? `<tr>${headers.map((header, idx) => {
          if (idx === 0) return `<td><strong>B/F from Previous Page</strong></td>`;
          if (numericHeaders.includes(header)) return `<td class="num"><strong>${formatNumber(runningTotals[header])}</strong></td>`;
          return '<td></td>';
        }).join('')}</tr>`
        : '';

      const rowHtml = chunk
        .map((row) => {
          numericHeaders.forEach((header) => {
            runningTotals[header] += parseNumeric(row?.[header]);
          });
          const cells = headers
            .map((header) => {
              const value = row?.[header] ?? '';
              const className = numericHeaders.includes(header) ? 'num' : '';
              return `<td class="${className}">${escapeHtml(value)}</td>`;
            })
            .join('');
          return `<tr>${cells}</tr>`;
        })
        .join('');

      const bfToRow = pageIndex < pageChunks.length - 1
        ? `<tr>${headers.map((header, idx) => {
          if (idx === 0) return `<td><strong>B/F to Next Page</strong></td>`;
          if (numericHeaders.includes(header)) return `<td class="num"><strong>${formatNumber(runningTotals[header])}</strong></td>`;
          return '<td></td>';
        }).join('')}</tr>`
        : '';

      const totalRow = pageIndex === pageChunks.length - 1 && numericHeaders.length > 0
        ? `<tr>${headers.map((header, idx) => {
          if (idx === 0) return `<td><strong>Grand Total</strong></td>`;
          if (numericHeaders.includes(header)) return `<td class="num"><strong>${formatNumber(runningTotals[header])}</strong></td>`;
          return '<td></td>';
        }).join('')}</tr>`
        : '';

      return `
        <div class="${pageIndex < pageChunks.length - 1 ? 'page-break' : ''}">
          ${buildReportHeaderHtml({ title: safeTitle, period })}
          <table>
            <thead><tr>${headerHtml}</tr></thead>
            <tbody>
              ${bfFromRow}
              ${rowHtml}
              ${bfToRow}
              ${totalRow}
            </tbody>
          </table>
          <div class="page-footer">Page ${pageIndex + 1} of ${pageChunks.length}</div>
        </div>
      `;
    })
    .join('');

  const printWindow = window.open('', '_blank');
  if (!printWindow) return;
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>${safeTitle}</title>
        <style>
          ${reportBaseStyles}
        </style>
      </head>
      <body>
        ${pageTablesHtml}
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




