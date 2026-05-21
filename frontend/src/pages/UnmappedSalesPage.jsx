import React, { useState, useEffect } from 'react';
import { onboardingService, inventoryService } from '../services/apiServices';
import Button from '../components/ui/Button';

export default function UnmappedSalesPage() {
  const [unmatched, setUnmatched] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [mappings, setMappings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [unmatchedRes, invRes] = await Promise.all([
        onboardingService.getUnmatched(),
        inventoryService.getAll()
      ]);
      setUnmatched(unmatchedRes.data.data || []);
      setInventory(invRes.data.data || []);
    } catch (err) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (uploadedName, inventoryId) => {
    setMappings(prev => ({ ...prev, [uploadedName]: inventoryId }));
  };

  const handleSave = async () => {
    const payload = [];
    for (const [uploaded_name, inventory_id] of Object.entries(mappings)) {
      if (inventory_id) {
        payload.push({ uploaded_name, inventory_id });
      }
    }
    
    if (payload.length === 0) {
      setError('No mappings selected.');
      return;
    }

    setSaving(true);
    setError('');
    setSuccessMsg('');
    try {
      const res = await onboardingService.mapSales({ mappings: payload });
      setSuccessMsg(res.data.message || 'Mappings saved successfully!');
      setMappings({});
      fetchData(); // reload
    } catch (err) {
      setError('Failed to save mappings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading unmapped sales...</div>;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Unmapped Sales Records</h1>
        <p className="text-gray-500 mt-1">
          These product names were found in your CSV or POS uploads but did not automatically match any inventory item. 
          Map them here so the ML can use their sales history.
        </p>
      </div>

      {error && <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-100">{error}</div>}
      {successMsg && <div className="p-4 bg-green-50 text-green-700 rounded-lg border border-green-100">{successMsg}</div>}

      {unmatched.length === 0 ? (
        <div className="bg-white rounded-xl p-12 text-center shadow-sm border border-gray-100">
          <div className="text-4xl mb-3">🎉</div>
          <h3 className="text-lg font-bold text-gray-900">All caught up!</h3>
          <p className="text-gray-500">No unmatched sales records found.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Uploaded Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sales Records</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Qty</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Map To Inventory</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {unmatched.map((item, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{item.uploaded_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.rows}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.total_qty}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    <select
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 text-sm"
                      value={mappings[item.uploaded_name] || ''}
                      onChange={(e) => handleSelect(item.uploaded_name, e.target.value)}
                    >
                      <option value="">-- Select Product --</option>
                      {inventory.map(inv => (
                        <option key={inv._id} value={inv._id}>
                          {inv.product_name}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="p-4 border-t border-gray-100 flex justify-end">
            <Button onClick={handleSave} loading={saving} disabled={Object.keys(mappings).length === 0}>
              Save Selected Mappings
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
