import React, { useMemo, useState, useEffect } from 'react';
import {
  BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
  LineChart, Line,
  AreaChart, Area,
  ScatterChart, Scatter, ZAxis,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ComposedChart,
  Legend,
} from 'recharts';
import { QueryResult } from '../types';

type ChartType =
  | 'bar'
  | 'stacked-bar'
  | 'line'
  | 'area'
  | 'pie'
  | 'donut'
  | 'scatter'
  | 'radar'
  | 'composed';

interface DataChartProps {
  data: QueryResult;
}

const COLORS = [
  '#fa6400', '#ff8c42', '#ffc107', '#10b981',
  '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4',
];

interface ChartTypeOption {
  type: ChartType;
  label: string;
}

const ALL_CHART_OPTIONS: ChartTypeOption[] = [
  { type: 'bar',         label: 'Bar'         },
  { type: 'stacked-bar', label: 'Stacked Bar'  },
  { type: 'line',        label: 'Line'         },
  { type: 'area',        label: 'Area'         },
  { type: 'pie',         label: 'Pie'          },
  { type: 'donut',       label: 'Donut'        },
  { type: 'scatter',     label: 'Scatter'      },
  { type: 'radar',       label: 'Radar'        },
  { type: 'composed',    label: 'Composed'     },
];

const DataChart: React.FC<DataChartProps> = ({ data }) => {
  const { columns, rows } = data;
  const [selectedType, setSelectedType] = useState<ChartType | null>(null);

  // Reset manual selection whenever data changes
  useEffect(() => {
    setSelectedType(null);
  }, [data]);

  const chartConfig = useMemo(() => {
    if (rows.length === 0) return null;

    const numericColumns: string[] = [];
    const categoricalColumns: string[] = [];
    const dateColumns: string[] = [];

    // Patterns that signal an identifier/code column – never a plottable metric
    const ID_PATTERNS = /(_id|_code|_key|_no|_num|_ref|_seq|code$|_pk$|id$)$/i;

    columns.forEach(col => {
      const sampleValue = rows[0][col];
      const colLower = col.toLowerCase();
      if (
        colLower.includes('date') || colLower.includes('quarter') ||
        colLower.includes('month') || colLower.includes('year')
      ) {
        dateColumns.push(col);
      } else if (typeof sampleValue === 'number' && !ID_PATTERNS.test(col)) {
        // Only treat truly numeric columns as metrics; skip ID/code columns
        numericColumns.push(col);
      } else {
        categoricalColumns.push(col);
      }
    });

    // If there are no real numeric metrics, a chart adds no value – bail out
    if (numericColumns.length === 0) return null;

    // Auto-detect best chart type
    let autoType: ChartType = 'bar';
    let labelColumn = categoricalColumns[0] || dateColumns[0] || columns[0];
    let valueColumns = numericColumns.slice();

    if (rows.length <= 6 && numericColumns.length === 1 && categoricalColumns.length === 1) {
      autoType = 'pie';
    }
    if (dateColumns.length > 0 && numericColumns.length > 0) {
      autoType = numericColumns.length > 1 ? 'area' : 'line';
      labelColumn = dateColumns[0];
    }
    if (numericColumns.length >= 2 && categoricalColumns.length === 0 && dateColumns.length === 0) {
      autoType = 'scatter';
    }

    const chartData = rows.slice(0, 20).map(row => {
      const item: Record<string, any> = {
        name: String(row[labelColumn] ?? 'Unknown'),
      };
      valueColumns.forEach(col => {
        item[col] = Number(row[col]) || 0;
      });
      return item;
    });

    // Build list of chart types that make sense for this data shape
    const available: ChartType[] = ['bar', 'line', 'area'];
    if (numericColumns.length === 1) available.push('pie', 'donut');
    if (numericColumns.length > 1)  available.push('stacked-bar', 'composed');
    if (numericColumns.length >= 2 && categoricalColumns.length === 0 && dateColumns.length === 0) {
      available.push('scatter');
    }
    if (numericColumns.length >= 3) available.push('radar');

    return { autoType, chartData, valueColumns, labelColumn, available };
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

  const { autoType, chartData, valueColumns, available } = chartConfig;
  const chartType: ChartType = selectedType ?? autoType;
  const availableOptions = ALL_CHART_OPTIONS.filter(o => available.includes(o.type));

  // ── Formatters & shared helpers ──────────────────────────────────────────────

  const formatYAxis = (value: number) => {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000)     return `${(value / 1_000).toFixed(1)}K`;
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
          {payload.map((entry: any, i: number) => (
            <p key={i} style={{ color: entry.color }}>
              {entry.name}: {new Intl.NumberFormat('en-US').format(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const commonAxes = (multiSeries = false) => (
    <>
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
      {multiSeries && <Legend />}
    </>
  );

  // ── Chart renderer ───────────────────────────────────────────────────────────

  const renderChart = (): React.ReactElement => {
    const multi = valueColumns.length > 1;

    switch (chartType) {
      /* ── Bar ───────────────────────────────────────────────── */
      case 'bar':
        return (
          <BarChart data={chartData}>
            {commonAxes(multi)}
            {valueColumns.map((col, i) => (
              <Bar key={col} dataKey={col} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        );

      /* ── Stacked Bar ───────────────────────────────────────── */
      case 'stacked-bar':
        return (
          <BarChart data={chartData}>
            {commonAxes(true)}
            {valueColumns.map((col, i) => (
              <Bar
                key={col}
                dataKey={col}
                stackId="stack"
                fill={COLORS[i % COLORS.length]}
                radius={i === valueColumns.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
              />
            ))}
          </BarChart>
        );

      /* ── Line ──────────────────────────────────────────────── */
      case 'line':
        return (
          <LineChart data={chartData}>
            {commonAxes(multi)}
            {valueColumns.map((col, i) => (
              <Line
                key={col}
                type="monotone"
                dataKey={col}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={{ fill: COLORS[i % COLORS.length] }}
              />
            ))}
          </LineChart>
        );

      /* ── Area ──────────────────────────────────────────────── */
      case 'area':
        return (
          <AreaChart data={chartData}>
            {commonAxes(multi)}
            {valueColumns.map((col, i) => (
              <Area
                key={col}
                type="monotone"
                dataKey={col}
                stroke={COLORS[i % COLORS.length]}
                fill={COLORS[i % COLORS.length]}
                fillOpacity={0.15}
                strokeWidth={2}
              />
            ))}
          </AreaChart>
        );

      /* ── Pie ───────────────────────────────────────────────── */
      case 'pie':
        return (
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              outerRadius={100}
              labelLine={false}
              label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
              dataKey={valueColumns[0]}
            >
              {chartData.map((_, i) => (
                <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend />
          </PieChart>
        );

      /* ── Donut ─────────────────────────────────────────────── */
      case 'donut':
        return (
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={100}
              labelLine={false}
              label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
              dataKey={valueColumns[0]}
            >
              {chartData.map((_, i) => (
                <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend />
          </PieChart>
        );

      /* ── Scatter ───────────────────────────────────────────── */
      case 'scatter': {
        const scatterData = chartData.map(d => ({
          x: d[valueColumns[0]],
          y: d[valueColumns[1]] ?? 0,
          name: d.name,
        }));
        return (
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
            <XAxis
              dataKey="x"
              name={valueColumns[0]}
              type="number"
              stroke="var(--text-secondary)"
              tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
              tickFormatter={formatYAxis}
              label={{ value: valueColumns[0], position: 'insideBottom', offset: -5, fill: 'var(--text-secondary)', fontSize: 11 }}
            />
            <YAxis
              dataKey="y"
              name={valueColumns[1]}
              type="number"
              stroke="var(--text-secondary)"
              tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
              tickFormatter={formatYAxis}
              label={{ value: valueColumns[1], angle: -90, position: 'insideLeft', fill: 'var(--text-secondary)', fontSize: 11 }}
            />
            <ZAxis range={[50, 50]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ active, payload }: any) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div style={{
                      background: 'var(--surface-color)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '0.5rem',
                      padding: '0.75rem',
                    }}>
                      {d.name && <p style={{ fontWeight: 600 }}>{d.name}</p>}
                      <p style={{ color: COLORS[0] }}>{valueColumns[0]}: {new Intl.NumberFormat('en-US').format(d.x)}</p>
                      <p style={{ color: COLORS[1] }}>{valueColumns[1]}: {new Intl.NumberFormat('en-US').format(d.y)}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Scatter name="Data Points" data={scatterData} fill={COLORS[0]} />
          </ScatterChart>
        );
      }

      /* ── Radar ─────────────────────────────────────────────── */
      case 'radar':
        return (
          <RadarChart cx="50%" cy="50%" outerRadius={95} data={chartData}>
            <PolarGrid stroke="var(--border-color)" />
            <PolarAngleAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
            <PolarRadiusAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} tickFormatter={formatYAxis} />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            {valueColumns.map((col, i) => (
              <Radar
                key={col}
                name={col}
                dataKey={col}
                stroke={COLORS[i % COLORS.length]}
                fill={COLORS[i % COLORS.length]}
                fillOpacity={0.2}
              />
            ))}
          </RadarChart>
        );

      /* ── Composed (Bar + Line) ─────────────────────────────── */
      case 'composed': {
        const barCols  = valueColumns.slice(0, -1);
        const lineCols = valueColumns.slice(-1);
        return (
          <ComposedChart data={chartData}>
            {commonAxes(true)}
            {barCols.map((col, i) => (
              <Bar key={col} dataKey={col} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />
            ))}
            {lineCols.map((col, i) => (
              <Line
                key={col}
                type="monotone"
                dataKey={col}
                stroke={COLORS[(i + barCols.length) % COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </ComposedChart>
        );
      }

      default:
        return <BarChart data={chartData}>{commonAxes()}</BarChart>;
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="chart-container">
      {/* Chart type selector toolbar */}
      {availableOptions.length > 1 && (
        <div style={{
          display: 'flex',
          gap: '0.35rem',
          marginBottom: '0.75rem',
          flexWrap: 'wrap',
          alignItems: 'center',
        }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginRight: '0.25rem' }}>
            Chart:
          </span>
          {availableOptions.map(opt => {
            const active = chartType === opt.type;
            return (
              <button
                key={opt.type}
                onClick={() => setSelectedType(opt.type)}
                title={opt.label}
                style={{
                  padding: '0.2rem 0.55rem',
                  fontSize: '0.7rem',
                  fontWeight: active ? 700 : 500,
                  borderRadius: '0.375rem',
                  border: `1px solid ${active ? 'var(--primary-color)' : 'var(--border-color)'}`,
                  background: active ? 'var(--primary-color)' : 'transparent',
                  color: active ? '#fff' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  lineHeight: 1.5,
                }}
              >
                {opt.label}
              </button>
            );
          })}
          {selectedType && (
            <button
              onClick={() => setSelectedType(null)}
              title="Reset to auto-detected chart"
              style={{
                padding: '0.2rem 0.5rem',
                fontSize: '0.65rem',
                borderRadius: '0.375rem',
                border: '1px dashed var(--border-color)',
                background: 'transparent',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                marginLeft: '0.25rem',
              }}
            >
              Auto
            </button>
          )}
        </div>
      )}

      <ResponsiveContainer width="100%" height={450}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
};

export default DataChart;
