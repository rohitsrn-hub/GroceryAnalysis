import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Calendar, DollarSign, FileText, TrendingUp, Download, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { formatIndianNumber } from '../utils/numberUtils';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FinancialHealth = () => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [showReportModal, setShowReportModal] = useState(false);
  const [financialRecords, setFinancialRecords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFinancialRecords();
  }, []);

  const fetchFinancialRecords = async () => {
    try {
      setLoading(true);
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const response = await fetch(`${API}/financial-data-range?start_date=${startDate}&end_date=${endDate}`);
      if (!response.ok) throw new Error('Failed to fetch financial records');
      
      const data = await response.json();
      setFinancialRecords(data.records || []);
    } catch (error) {
      console.error('Error fetching financial records:', error);
      toast.error('Failed to load financial records');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card className="bg-gradient-to-r from-green-500 to-emerald-600 text-white border-none">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex-1">
              <h2 className="text-2xl font-bold mb-2">Financial Health Tracking</h2>
              <p className="text-green-50 text-sm">
                Track daily sales, bank balances, and generate financial reports
              </p>
            </div>
            <button
              onClick={() => setShowReportModal(true)}
              className="bg-white text-green-600 px-6 py-3 rounded-lg font-bold text-lg hover:bg-green-50 transition-colors shadow-lg flex items-center space-x-2"
              data-testid="generate-report-button"
            >
              <FileText className="w-5 h-5" />
              <span>Generate Daily Report</span>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Instructions Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-blue-600" />
            <span>How to Generate Daily Sales Report</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
            <li>First, upload today's sales data using the "Upload Today's Data" button on the dashboard</li>
            <li>Click "Generate Daily Report" button above</li>
            <li>Enter the required financial information (Liquor sales, Bank amount)</li>
            <li>Download the PDF report for your records</li>
          </ol>
        </CardContent>
      </Card>

      {/* Recent Financial Records */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Calendar className="w-5 h-5" />
            <span>Recent Financial Records</span>
          </CardTitle>
          <CardDescription>Last 30 days of financial tracking</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading records...</div>
          ) : financialRecords.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
              <p>No financial records yet</p>
              <p className="text-sm">Generate your first daily report to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 font-semibold">Date</th>
                    <th className="text-right p-3 font-semibold">Grocery Sales</th>
                    <th className="text-right p-3 font-semibold">Liquor Sales</th>
                    <th className="text-right p-3 font-semibold">Total Sales</th>
                    <th className="text-right p-3 font-semibold">Bank Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {financialRecords.map((record) => (
                    <tr key={record.id} className="border-b hover:bg-gray-50">
                      <td className="p-3">
                        {new Date(record.date).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric'
                        })}
                      </td>
                      <td className="p-3 text-right">₹{formatIndianNumber(record.grocery_sales)}</td>
                      <td className="p-3 text-right">₹{formatIndianNumber(record.liquor_sales)}</td>
                      <td className="p-3 text-right font-semibold">₹{formatIndianNumber(record.total_sales)}</td>
                      <td className="p-3 text-right text-green-600 font-semibold">
                        ₹{formatIndianNumber(record.current_bank_amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Generate Report Modal */}
      {showReportModal && (
        <ReportGenerationModal
          isOpen={showReportModal}
          onClose={() => setShowReportModal(false)}
          onSuccess={fetchFinancialRecords}
        />
      )}
    </div>
  );
};

// Report Generation Modal Component
const ReportGenerationModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    liquorSales: '',
    previousBankAmount: '',
    previousStockValue: '',
    currentStockValue: '',
    notes: ''
  });
  const [loading, setLoading] = useState(false);
  const [loadingPreviousData, setLoadingPreviousData] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchPreviousBankAmount();
    }
  }, [isOpen, formData.date]);

  const fetchPreviousBankAmount = async () => {
    try {
      setLoadingPreviousData(true);
      const response = await fetch(`${API}/previous-bank-amount?date=${formData.date}`);
      if (response.ok) {
        const data = await response.json();
        if (data.found && data.bank_amount !== null) {
          setFormData(prev => ({
            ...prev,
            previousBankAmount: data.bank_amount.toString()
          }));
        }
      }
    } catch (error) {
      console.error('Error fetching previous bank amount:', error);
    } finally {
      setLoadingPreviousData(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleGenerateReport = async () => {
    // Validation
    if (!formData.liquorSales || parseFloat(formData.liquorSales) < 0) {
      toast.error('Please enter a valid liquor sales amount');
      return;
    }

    if (!formData.previousBankAmount || parseFloat(formData.previousBankAmount) < 0) {
      toast.error('Please enter a valid previous bank amount');
      return;
    }

    setLoading(true);

    try {
      const params = new URLSearchParams({
        date: formData.date,
        liquor_sales: formData.liquorSales,
        previous_bank_amount: formData.previousBankAmount,
      });

      if (formData.previousStockValue) {
        params.append('previous_stock_value', formData.previousStockValue);
      }
      if (formData.currentStockValue) {
        params.append('current_stock_value', formData.currentStockValue);
      }
      if (formData.notes) {
        params.append('notes', formData.notes);
      }

      const response = await fetch(`${API}/generate-daily-report?${params}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate report');
      }

      // Download PDF
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `daily_sales_report_${formData.date}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success('Daily sales report generated successfully!');
      
      if (onSuccess) {
        onSuccess();
      }
      
      onClose();
    } catch (error) {
      console.error('Error generating report:', error);
      toast.error(error.message || 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Generate Daily Sales Report</h2>
            <p className="text-sm text-gray-600 mt-1">Fill in the financial details for the selected date</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={loading}
          >
            <span className="text-2xl">&times;</span>
          </button>
        </div>

        {/* Form Content */}
        <div className="p-6 space-y-4">
          {/* Date Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Report Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              name="date"
              value={formData.date}
              onChange={handleInputChange}
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
          </div>

          {/* Liquor Sales */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Liquor Sales for the Day (₹) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              name="liquorSales"
              value={formData.liquorSales}
              onChange={handleInputChange}
              placeholder="Enter liquor sales amount"
              step="0.01"
              min="0"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
          </div>

          {/* Previous Bank Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Bank Amount as on Previous Day (₹) <span className="text-red-500">*</span>
              {loadingPreviousData && <span className="text-xs text-blue-600 ml-2">(Loading...)</span>}
            </label>
            <input
              type="number"
              name="previousBankAmount"
              value={formData.previousBankAmount}
              onChange={handleInputChange}
              placeholder="Enter previous day's bank balance"
              step="0.01"
              min="0"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading || loadingPreviousData}
            />
            <p className="text-xs text-gray-500 mt-1">
              This will be auto-filled if data from previous day exists
            </p>
          </div>

          {/* Stock Values (Optional) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Previous Day Stock Value (₹) <span className="text-gray-400 text-xs">(Optional)</span>
              </label>
              <input
                type="number"
                name="previousStockValue"
                value={formData.previousStockValue}
                onChange={handleInputChange}
                placeholder="Previous stock value"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Current Day Stock Value (₹) <span className="text-gray-400 text-xs">(Optional)</span>
              </label>
              <input
                type="number"
                name="currentStockValue"
                value={formData.currentStockValue}
                onChange={handleInputChange}
                placeholder="Current stock value"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading}
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes <span className="text-gray-400 text-xs">(Optional)</span>
            </label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleInputChange}
              placeholder="Any additional notes or observations"
              rows="3"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              disabled={loading}
            />
          </div>

          {/* Info Box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> Grocery sales will be automatically calculated from today's uploaded data. 
              The report will show breakdown of grocery sales, liquor sales, bank balances, and stock values.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-4 p-6 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors font-medium"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleGenerateReport}
            disabled={loading || !formData.liquorSales || !formData.previousBankAmount}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Generating...</span>
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                <span>Generate & Download PDF</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FinancialHealth;
