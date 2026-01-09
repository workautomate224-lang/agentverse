/**
 * Export Service
 * Handles exporting data and charts to various formats
 */

// CSV Export
export function exportToCSV(data: Record<string, unknown>[], filename: string): void {
  if (data.length === 0) {
    return;
  }

  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row =>
      headers.map(header => {
        const value = row[header];
        // Handle values that might contain commas or quotes
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value ?? '';
      }).join(',')
    )
  ].join('\n');

  downloadFile(csvContent, `${filename}.csv`, 'text/csv');
}

// JSON Export
export function exportToJSON(data: unknown, filename: string): void {
  const jsonContent = JSON.stringify(data, null, 2);
  downloadFile(jsonContent, `${filename}.json`, 'application/json');
}

// Helper function to trigger download
function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// PNG Export using html2canvas
export async function exportToPNG(
  element: HTMLElement,
  filename: string
): Promise<void> {
  try {
    // Dynamic import of html2canvas
    const html2canvas = (await import('html2canvas')).default;

    const canvas = await html2canvas(element, {
      backgroundColor: '#000000',
      scale: 2, // Higher resolution
      logging: false,
      useCORS: true,
    });

    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  } catch (error) {
    throw error;
  }
}

// PDF Export - simplified HTML-based approach
export async function exportToPDF(
  title: string,
  sections: {
    heading: string;
    content: string | Record<string, unknown>[];
    type: 'text' | 'table' | 'chart';
  }[],
  filename: string
): Promise<void> {
  // Create HTML content
  const htmlContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>${title}</title>
      <style>
        body {
          font-family: 'Courier New', monospace;
          margin: 40px;
          color: #333;
          background: #fff;
        }
        h1 {
          font-size: 24px;
          margin-bottom: 20px;
          border-bottom: 2px solid #000;
          padding-bottom: 10px;
        }
        h2 {
          font-size: 16px;
          margin-top: 30px;
          margin-bottom: 15px;
          color: #555;
        }
        p {
          font-size: 12px;
          line-height: 1.6;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin: 15px 0;
          font-size: 11px;
        }
        th, td {
          border: 1px solid #ddd;
          padding: 8px;
          text-align: left;
        }
        th {
          background: #f5f5f5;
          font-weight: bold;
        }
        tr:nth-child(even) {
          background: #fafafa;
        }
        .metadata {
          font-size: 10px;
          color: #888;
          margin-top: 40px;
          border-top: 1px solid #ddd;
          padding-top: 10px;
        }
      </style>
    </head>
    <body>
      <h1>${title}</h1>
      ${sections.map(section => {
        if (section.type === 'text') {
          return `
            <h2>${section.heading}</h2>
            <p>${section.content}</p>
          `;
        }
        if (section.type === 'table' && Array.isArray(section.content)) {
          const data = section.content as Record<string, unknown>[];
          if (data.length === 0) return '';
          const headers = Object.keys(data[0]);
          return `
            <h2>${section.heading}</h2>
            <table>
              <thead>
                <tr>
                  ${headers.map(h => `<th>${h}</th>`).join('')}
                </tr>
              </thead>
              <tbody>
                ${data.map(row => `
                  <tr>
                    ${headers.map(h => `<td>${row[h] ?? ''}</td>`).join('')}
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `;
        }
        return '';
      }).join('')}
      <div class="metadata">
        Generated on ${new Date().toLocaleString()} | AgentVerse Analytics
      </div>
    </body>
    </html>
  `;

  // Open in new window for printing
  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(htmlContent);
    printWindow.document.close();
    printWindow.onload = () => {
      printWindow.print();
    };
  }
}

// Results data transformer for export
export interface ExportableResult {
  category: string;
  value: number;
  percentage: number;
  count: number;
}

export function transformResultsForExport(
  results: Record<string, unknown>
): ExportableResult[] {
  const exportData: ExportableResult[] = [];

  // Handle sentiment distribution
  if (results.sentiment_distribution) {
    const dist = results.sentiment_distribution as Record<string, number>;
    const total = Object.values(dist).reduce((a, b) => a + b, 0);
    Object.entries(dist).forEach(([category, count]) => {
      exportData.push({
        category: `Sentiment: ${category}`,
        value: count,
        percentage: total > 0 ? (count / total) * 100 : 0,
        count,
      });
    });
  }

  // Handle purchase likelihood
  if (results.purchase_likelihood) {
    const dist = results.purchase_likelihood as Record<string, number>;
    const total = Object.values(dist).reduce((a, b) => a + b, 0);
    Object.entries(dist).forEach(([category, count]) => {
      exportData.push({
        category: `Purchase: ${category}`,
        value: count,
        percentage: total > 0 ? (count / total) * 100 : 0,
        count,
      });
    });
  }

  // Handle demographics
  if (results.demographics) {
    const demos = results.demographics as Record<string, Record<string, number>>;
    Object.entries(demos).forEach(([demoType, distribution]) => {
      const total = Object.values(distribution).reduce((a, b) => a + b, 0);
      Object.entries(distribution).forEach(([category, count]) => {
        exportData.push({
          category: `${demoType}: ${category}`,
          value: count,
          percentage: total > 0 ? (count / total) * 100 : 0,
          count,
        });
      });
    });
  }

  return exportData;
}

// Comparison data transformer
export function transformComparisonForExport(
  results: { id: string; name: string; data: Record<string, unknown> }[]
): Record<string, unknown>[] {
  if (results.length === 0) return [];

  // Get all unique categories across all results
  const allCategories = new Set<string>();
  results.forEach(result => {
    if (result.data.sentiment_distribution) {
      Object.keys(result.data.sentiment_distribution as Record<string, number>).forEach(k =>
        allCategories.add(`Sentiment: ${k}`)
      );
    }
    if (result.data.purchase_likelihood) {
      Object.keys(result.data.purchase_likelihood as Record<string, number>).forEach(k =>
        allCategories.add(`Purchase: ${k}`)
      );
    }
  });

  // Create comparison rows
  return Array.from(allCategories).map(category => {
    const row: Record<string, unknown> = { category };

    results.forEach(result => {
      let value = 0;
      const [type, key] = category.split(': ');

      if (type === 'Sentiment' && result.data.sentiment_distribution) {
        value = (result.data.sentiment_distribution as Record<string, number>)[key] || 0;
      } else if (type === 'Purchase' && result.data.purchase_likelihood) {
        value = (result.data.purchase_likelihood as Record<string, number>)[key] || 0;
      }

      row[result.name] = value;
    });

    return row;
  });
}
