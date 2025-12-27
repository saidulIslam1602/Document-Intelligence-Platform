import { useState, useEffect } from 'react';
import api from '../services/api';
import Card from '../components/common/Card';
import SearchBar from '../components/common/SearchBar';
import Badge from '../components/common/Badge';

interface Entity {
  id: string;
  type: string;
  value: string;
  confidence: number;
  documentId: string;
  documentName: string;
}

export default function Entities() {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [filteredEntities, setFilteredEntities] = useState<Entity[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEntities();
  }, []);

  useEffect(() => {
    let filtered = entities;
    
    if (filterType !== 'all') {
      filtered = filtered.filter(e => e.type === filterType);
    }
    
    if (searchQuery) {
      filtered = filtered.filter(e => 
        e.value.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    
    setFilteredEntities(filtered);
  }, [searchQuery, filterType, entities]);

  const loadEntities = async () => {
    try {
      await api.get('/entities');
      // Using mock data for now
      const mockEntities: Entity[] = [
        { id: '1', type: 'PERSON', value: 'John Smith', confidence: 0.98, documentId: '1', documentName: 'contract.pdf' },
        { id: '2', type: 'ORGANIZATION', value: 'Acme Corp', confidence: 0.95, documentId: '1', documentName: 'contract.pdf' },
        { id: '3', type: 'DATE', value: '2024-01-15', confidence: 0.99, documentId: '2', documentName: 'invoice.pdf' },
        { id: '4', type: 'MONEY', value: '$1,500.00', confidence: 0.97, documentId: '2', documentName: 'invoice.pdf' },
        { id: '5', type: 'LOCATION', value: 'New York', confidence: 0.92, documentId: '3', documentName: 'report.docx' },
      ];
      setEntities(mockEntities);
    } catch (error) {
      console.error('Failed to load entities');
    } finally {
      setLoading(false);
    }
  };

  const entityTypes = ['all', ...Array.from(new Set(entities.map(e => e.type)))];
  
  const entityStats = entityTypes.slice(1).map(type => ({
    type,
    count: entities.filter(e => e.type === type).length
  }));

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Extracted Entities</h1>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {entityStats.map(stat => (
          <Card key={stat.type}>
            <p className="text-sm text-gray-500">{stat.type}</p>
            <p className="text-2xl font-bold">{stat.count}</p>
          </Card>
        ))}
      </div>

      <div className="flex gap-4">
        <div className="flex-1">
          <SearchBar 
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search entities..."
          />
        </div>
        
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-4 py-2 border rounded-lg"
        >
          {entityTypes.map(type => (
            <option key={type} value={type}>
              {type === 'all' ? 'All Types' : type}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">Loading...</div>
      ) : (
        <Card>
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3">Type</th>
                <th className="text-left py-3">Value</th>
                <th className="text-left py-3">Confidence</th>
                <th className="text-left py-3">Document</th>
              </tr>
            </thead>
            <tbody>
              {filteredEntities.map(entity => (
                <tr key={entity.id} className="border-b hover:bg-gray-50">
                  <td className="py-3">
                    <Badge variant="info">{entity.type}</Badge>
                  </td>
                  <td className="py-3 font-medium">{entity.value}</td>
                  <td className="py-3">
                    <span className={`${entity.confidence >= 0.95 ? 'text-green-600' : 'text-yellow-600'}`}>
                      {(entity.confidence * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="py-3 text-sm text-gray-600">{entity.documentName}</td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {filteredEntities.length === 0 && (
            <p className="text-center py-8 text-gray-500">No entities found</p>
          )}
        </Card>
      )}
    </div>
  );
}

