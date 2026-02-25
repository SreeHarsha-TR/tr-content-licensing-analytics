import React from 'react';
import { QueryResult } from '../types';

interface DataTableProps {
  data: QueryResult;
  maxRows?: number;
}

const DataTable: React.FC<DataTableProps> = ({ data, maxRows = 100 }) => {
  const { columns, rows, rowCount } = data;
  const displayRows = rows.slice(0, maxRows);

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
      // Format currency
      if (value > 1000) {
        return new Intl.NumberFormat('en-US', {
          style: 'decimal',
          minimumFractionDigits: 0,
          maximumFractionDigits: 2,
        }).format(value);
      }
      return value.toString();
    }
    if (value instanceof Date) {
      return value.toLocaleDateString();
    }
    return String(value);
  };

  const formatColumnName = (column: string): string => {
    return column
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ')
      .trim();
  };

  return (
    <div className="data-table-container">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th key={index}>{formatColumnName(column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayRows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column, colIndex) => (
                <td key={colIndex}>{formatValue(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="row-count">
        Showing {displayRows.length} of {rowCount} rows
        {rowCount > maxRows && ` (limited to ${maxRows})`}
      </div>
    </div>
  );
};

export default DataTable;
