import { useState } from 'react';
import api from '../services/api';
import Card from '../components/common/Card';
import SearchBar from '../components/common/SearchBar';
import DocumentCard from '../components/documents/DocumentCard';
import Button from '../components/common/Button';

export default function Search() {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({
    fileType: 'all',
    dateFrom: '',
    dateTo: '',
    status: 'all',
  });
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        q: query,
        ...filters
      });
      const res = await api.get(`/search?${params}`);
      setResults(res.data.results || []);
    } catch (error) {
      console.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Advanced Search</h1>

      <Card>
        <div className="space-y-4">
          <SearchBar 
            value={query}
            onChange={setQuery}
            placeholder="Search documents, entities, or content..."
          />

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">File Type</label>
              <select
                value={filters.fileType}
                onChange={(e) => setFilters({...filters, fileType: e.target.value})}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="all">All Types</option>
                <option value="pdf">PDF</option>
                <option value="doc">Word</option>
                <option value="txt">Text</option>
                <option value="image">Image</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Date From</label>
              <input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => setFilters({...filters, dateFrom: e.target.value})}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Date To</label>
              <input
                type="date"
                value={filters.dateTo}
                onChange={(e) => setFilters({...filters, dateTo: e.target.value})}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({...filters, status: e.target.value})}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>

          <Button onClick={handleSearch} disabled={!query || loading}>
            {loading ? 'Searching...' : 'Search'}
          </Button>
        </div>
      </Card>

      {results.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">
            Found {results.length} results
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {results.map((doc) => (
              <DocumentCard key={doc.id} document={doc} />
            ))}
          </div>
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <Card>
          <p className="text-center text-gray-500 py-8">
            No results found for "{query}"
          </p>
        </Card>
      )}
    </div>
  );
}

