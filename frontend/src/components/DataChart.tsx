import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import { QueryResult } from '../types';

interface DataChartProps {
  data: QueryResult;
}

const COLORS = [
  '#fa6400', '#ff8c42', '#ffc107', '#10b981',
  '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4'
];

const DataChart: React.FC<DataChartProps> = ({ data }) => {
  const { columns, rows } = data;

  // Determine chart type and prepare data
  const chartConfig = useMemo(() => {
    if (rows.length === 0) return null;

    // Find numeric and categorical columns
    const numericColumns: string[] = [];
    const categoricalColumns: string[] = [];
    const dateColumns: string[] = [];

    columns.forEach(col => {
      const sampleValue = rows[0][col];
      const colLower = col.toLowerCase();

      if (colLower.includes('date') || colLower.includes('quarter') ||
          colLower.includes('month') || colLower.includes('year')) {
        dateColumns.push(col);
      } else if (typeof sampleValue === 'number') {
        numericColumns.push(col);
      } else {
        categoricalColumns.push(col);
      }
    });

    // Determine best chart type
    let chartType: 'bar' | 'pie' | 'line' = 'bar';
    let labelColumn = categoricalColumns[0] || dateColumns[0] || columns[0];
    let valueColumns = numericColumns.length > 0 ? numericColumns : [columns[1]];

    // Use pie chart for small categorical datasets
    if (rows.length <= 6 && numericColumns.length === 1 && categoricalColumns.length === 1) {
      chartType = 'pie';
    }

    // Use line chart for time series
    if (dateColumns.length > 0 && numericColumns.length > 0) {
      chartType = 'line';
      labelColumn = dateColumns[0];
    }

    // Prepare chart data
    const chartData = rows.slice(0, 20).map(row => {
      const item: Record<string, any> = {
        name: String(row[labelColumn] || 'Unknown'),
      };
      valueColumns.forEach(col => {
        item[col] = Number(row[col]) || 0;
      });
      return item;
    });

    return { chartType, chartData, valueColumns, labelColumn };
  }, [columns, rows]);

  if (!chartConfig || rows.length === 0) {
    return (
      <div className="chart-container">
        <p style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>
          No data available for visualization
        </p>
      </div>
    );
  }

  const { chartType, chartData, valueColumns } = chartConfig;

  const formatYAxis = (value: number) => {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return value.toString();
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'var(--surface-color)',
          border: '1px solid var(--border-color)',
          borderRadius: '0.5rem',
          padding: '0.75rem',
        }}>
          <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }}>
              {entry.name}: {new Intl.NumberFormat('en-US').format(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={300}>
        {chartType === 'pie' ? (
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
              outerRadius={100}
              fill="#8884d8"
              dataKey={valueColumns[0]}
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        ) : chartType === 'line' ? (
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
            <XAxis
              dataKey="name"
              stroke="var(--text-secondary)"
              tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            />
            <YAxis
              stroke="var(--text-secondary)"
              tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
              tickFormatter={formatYAxis}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            {valueColumns.map((col, index) => (
              <Line
                key={col}
                type="monotone"
                dataKey={col}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={{ fill: COLORS[index % COLORS.length] }}
              />
            ))}
          </LineChart>
        ) : (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
            <XAxis
              dataKey="name"
              stroke="var(--text-secondary)"
              tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={80}
            />
            <YAxis
              stroke="var(--text-secondary)"
              tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
              tickFormatter={formatYAxis}
            />
            <Tooltip content={<CustomTooltip />} />
            {valueColumns.length > 1 && <Legend />}
            {valueColumns.map((col, index) => (
              <Bar
                key={col}
                dataKey={col}
                fill={COLORS[index % COLORS.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
};

export default DataChart;
