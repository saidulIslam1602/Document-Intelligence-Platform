interface ChartProps {
  data: { label: string; value: number }[];
  type?: 'bar' | 'line';
}

export default function Chart({ data }: ChartProps) {
  const maxValue = Math.max(...data.map(d => d.value));

  return (
    <div className="space-y-4">
      {data.map((item, idx) => (
        <div key={idx} className="space-y-1">
          <div className="flex justify-between text-sm">
            <span>{item.label}</span>
            <span className="font-semibold">{item.value}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${(item.value / maxValue) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

