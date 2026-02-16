/**
 * 简单柱状图组件
 */

"use client";

interface SimpleBarChartProps {
  data: { label: string; value: number }[];
  height?: number;
  showLabels?: boolean;
  color?: string;
}

export function SimpleBarChart({
  data,
  height = 200,
  showLabels = true,
  color = "bg-primary-500",
}: SimpleBarChartProps) {
  const maxValue = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="w-full" style={{ height }}>
      <div className="flex items-end justify-between h-full gap-1">
        {data.map((item, index) => (
          <div
            key={index}
            className="flex-1 flex flex-col items-center justify-end h-full"
          >
            <div
              className={`w-full ${color} rounded-t transition-all duration-300 hover:opacity-80`}
              style={{
                height: `${(item.value / maxValue) * 100}%`,
                minHeight: item.value > 0 ? "4px" : "0",
              }}
              title={`${item.label}: ${item.value}`}
            />
            {showLabels && (
              <span className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate w-full text-center">
                {item.label}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

interface SimpleLineChartProps {
  data: { label: string; value: number }[];
  height?: number;
  color?: string;
}

export function SimpleLineChart({
  data,
  height = 200,
  color = "#3b82f6",
}: SimpleLineChartProps) {
  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const minValue = Math.min(...data.map((d) => d.value));
  const range = maxValue - minValue || 1;

  const points = data
    .map((item, index) => {
      const x = (index / (data.length - 1 || 1)) * 100;
      const y = 100 - ((item.value - minValue) / range) * 100;
      return `${x},${y}`;
    })
    .join(" ");

  const areaPoints = `0,100 ${points} 100,100`;

  return (
    <div className="w-full" style={{ height }}>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="w-full h-full"
      >
        <defs>
          <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon
          points={areaPoints}
          fill="url(#gradient)"
          className="transition-all duration-300"
        />
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="transition-all duration-300"
        />
        {data.map((item, index) => {
          const x = (index / (data.length - 1 || 1)) * 100;
          const y = 100 - ((item.value - minValue) / range) * 100;
          return (
            <circle
              key={index}
              cx={x}
              cy={y}
              r="3"
              fill={color}
              className="transition-all duration-300"
            >
              <title>
                {item.label}: {item.value}
              </title>
            </circle>
          );
        })}
      </svg>
    </div>
  );
}
