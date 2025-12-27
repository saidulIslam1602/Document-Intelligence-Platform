interface DocumentFiltersProps {
  filters: {
    status: string;
    fileType: string;
    dateFrom: string;
    dateTo: string;
  };
  onChange: (filters: any) => void;
  onReset: () => void;
}

export default function DocumentFilters({ filters, onChange, onReset }: DocumentFiltersProps) {
  const updateFilter = (key: string, value: string) => {
    onChange({ ...filters, [key]: value });
  };

  return (
    <div className="bg-gray-50 p-4 rounded-lg space-y-3">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold">Filters</h3>
        <button onClick={onReset} className="text-sm text-blue-600 hover:underline">
          Reset
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div>
          <label className="block text-sm font-medium mb-1">Status</label>
          <select
            value={filters.status}
            onChange={(e) => updateFilter('status', e.target.value)}
            className="w-full px-3 py-2 border rounded-lg"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">File Type</label>
          <select
            value={filters.fileType}
            onChange={(e) => updateFilter('fileType', e.target.value)}
            className="w-full px-3 py-2 border rounded-lg"
          >
            <option value="all">All Types</option>
            <option value="pdf">PDF</option>
            <option value="doc">Word</option>
            <option value="txt">Text</option>
            <option value="image">Image</option>
            <option value="xls">Excel</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Date From</label>
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(e) => updateFilter('dateFrom', e.target.value)}
            className="w-full px-3 py-2 border rounded-lg"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Date To</label>
          <input
            type="date"
            value={filters.dateTo}
            onChange={(e) => updateFilter('dateTo', e.target.value)}
            className="w-full px-3 py-2 border rounded-lg"
          />
        </div>
      </div>
    </div>
  );
}

