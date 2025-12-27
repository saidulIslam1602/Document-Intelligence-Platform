interface DocumentStatsProps {
  total: number;
  completed: number;
  processing: number;
  failed: number;
}

export default function DocumentStats({ total, completed, processing, failed }: DocumentStatsProps) {
  const stats = [
    { label: 'Total', value: total, color: 'text-gray-700', bgColor: 'bg-gray-100' },
    { label: 'Completed', value: completed, color: 'text-green-700', bgColor: 'bg-green-100' },
    { label: 'Processing', value: processing, color: 'text-yellow-700', bgColor: 'bg-yellow-100' },
    { label: 'Failed', value: failed, color: 'text-red-700', bgColor: 'bg-red-100' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map(stat => (
        <div key={stat.label} className={`${stat.bgColor} rounded-lg p-4`}>
          <p className={`text-sm font-medium ${stat.color}`}>{stat.label}</p>
          <p className={`text-2xl font-bold ${stat.color} mt-1`}>{stat.value}</p>
        </div>
      ))}
    </div>
  );
}

