import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Calendar, DollarSign, FileText, TrendingUp, Download, AlertCircle, Edit2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { formatIndianNumber } from '../utils/numberUtils';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const FinancialHealth = ({ onReportGenerated }) => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [showReportModal, setShowReportModal] = useState(false);
  const [showImageDialog, setShowImageDialog] = useState(false);
  const [financialRecords, setFinancialRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingRecord, setEditingRecord] = useState(null);
  const [extractedData, setExtractedData] = useState(null);

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

  const handleEditRecord = (record) => {
    setEditingRecord(record);
    setShowReportModal(true);
  };

  const handleDeleteRecord = async (record) => {
    if (!window.confirm(`Are you sure you want to delete the financial report for ${new Date(record.date).toLocaleDateString('en-IN')}?`)) {
      return;
    }

    try {
      const response = await fetch(`${API}/financial-data/${record.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete financial record');
      }

      toast.success('Financial report deleted successfully!');
      fetchFinancialRecords();
      
      // Refresh dashboard if available
      if (onReportGenerated) {
        onReportGenerated();
      }
    } catch (error) {
      console.error('Error deleting financial record:', error);
      toast.error('Failed to delete financial report');
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
              onClick={() => setShowImageDialog(true)}
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
                    <th className="text-center p-3 font-semibold">Actions</th>
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
                      <td className="p-3 text-center">
                        <div className="flex items-center justify-center space-x-2">
                          <button
                            onClick={() => handleEditRecord(record)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteRecord(record)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Image Upload Dialog */}
      {showImageDialog && (
        <ImageUploadDialog
          isOpen={showImageDialog}
          onClose={() => setShowImageDialog(false)}
          onProceedWithImage={(data) => {
            setExtractedData(data);
            setShowImageDialog(false);
            setShowReportModal(true);
          }}
          onProceedWithoutImage={() => {
            setExtractedData(null);
            setShowImageDialog(false);
            setShowReportModal(true);
          }}
        />
      )}

      {/* Generate Report Modal */}
      {showReportModal && (
        <ReportGenerationModal
          isOpen={showReportModal}
          onClose={() => {
            setShowReportModal(false);
            setEditingRecord(null);
            setExtractedData(null);
          }}
          onSuccess={() => {
            fetchFinancialRecords();
            setEditingRecord(null);
            setExtractedData(null);
          }}
          onReportGenerated={onReportGenerated}
          editingRecord={editingRecord}
          extractedData={extractedData}
        />
      )}
    </div>
  );
};

// Image Upload Dialog Component
const ImageUploadDialog = ({ isOpen, onClose, onProceedWithImage, onProceedWithoutImage }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUploadAndExtract = async () => {
    if (!selectedFile) {
      toast.error('Please select an image first');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch(`${API}/extract-canteen-summary`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to extract data from image');
      }

      const result = await response.json();
      toast.success('Data extracted successfully from image!');
      onProceedWithImage(result.data);
    } catch (error) {
      console.error('Error extracting data:', error);
      toast.error('Failed to extract data from image. Please try manual entry.');
      onProceedWithoutImage();
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
        <div className="p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            CSD Sales Summary Image
          </h2>
          <p className="text-sm text-gray-600 mb-6">
            Do you have an image of the daily sales summary from your CSD software?
          </p>

          {!selectedFile ? (
            <div className="space-y-4">
              <label className="block">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-green-500 transition-colors">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <div className="text-gray-600">
                    <svg className="w-12 h-12 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <p className="font-medium">Click to upload image</p>
                    <p className="text-xs text-gray-500 mt-1">PNG, JPG, JPEG up to 10MB</p>
                  </div>
                </div>
              </label>

              <button
                onClick={onProceedWithoutImage}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors font-medium"
              >
                No, Proceed with Manual Entry
              </button>

              <button
                onClick={onClose}
                className="w-full px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {previewUrl && (
                <div className="border rounded-lg overflow-hidden">
                  <img src={previewUrl} alt="Preview" className="w-full h-48 object-contain bg-gray-50" />
                </div>
              )}
              
              <p className="text-sm text-gray-600">
                <strong>{selectedFile.name}</strong> ({(selectedFile.size / 1024).toFixed(1)} KB)
              </p>

              <div className="flex space-x-3">
                <button
                  onClick={handleUploadAndExtract}
                  disabled={uploading}
                  className="flex-1 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {uploading ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Extracting...
                    </span>
                  ) : (
                    'Extract & Continue'
                  )}
                </button>
                <button
                  onClick={() => {
                    setSelectedFile(null);
                    setPreviewUrl(null);
                  }}
                  disabled={uploading}
                  className="px-4 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors font-medium"
                >
                  Change
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Report Generation Modal Component
const ReportGenerationModal = ({ isOpen, onClose, onSuccess, onReportGenerated, editingRecord, extractedData }) => {
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    grocerySales: '',
    liquorSales: '',
    previousBankAmount: '',
    previousStockValue: '',
    currentStockValue: '',
    notes: ''
  });
  const [loading, setLoading] = useState(false);
  const [loadingPreviousData, setLoadingPreviousData] = useState(false);
  const [todaysWAmt, setTodaysWAmt] = useState(null);
  const [calculatingStock, setCalculatingStock] = useState(false);

  // Load editing record data when in edit mode
  useEffect(() => {
    if (editingRecord) {
      setFormData({
        date: new Date(editingRecord.date).toISOString().split('T')[0],
        grocerySales: editingRecord.grocery_sales?.toString() || '',
        liquorSales: editingRecord.liquor_sales?.toString() || '',
        previousBankAmount: editingRecord.previous_bank_amount?.toString() || '',
        previousStockValue: editingRecord.previous_stock_value?.toString() || '',
        currentStockValue: editingRecord.current_stock_value?.toString() || '',
        notes: editingRecord.notes || ''
      });
    }
  }, [editingRecord]);

  // Load extracted data from image when available
  useEffect(() => {
    if (extractedData && !editingRecord) {
      // Only update grocery and liquor sales, preserve other fields like previousBankAmount
      setFormData(prev => ({
        ...prev,
        grocerySales: extractedData.grocery_sales?.toString() || '',
        liquorSales: extractedData.liquor_sales?.toString() || ''
        // previousBankAmount and previousStockValue are preserved from fetchPreviousBankAmount
      }));
      toast.success('Sales data populated from image! Previous day data loaded automatically.');
    }
  }, [extractedData, editingRecord]);

  useEffect(() => {
    if (isOpen && !editingRecord) {
      fetchPreviousBankAmount();
    }
  }, [isOpen, formData.date, editingRecord]);

  // Fetch today's upload data (grocery sales + W_Amt for stock calculation)
  // This runs AFTER previousStockValue is loaded
  useEffect(() => {
    console.log('useEffect for upload data - isOpen:', isOpen, 'editingRecord:', editingRecord, 'extractedData:', extractedData);
    console.log('formData.grocerySales:', formData.grocerySales, 'formData.previousStockValue:', formData.previousStockValue);
    
    if (isOpen && !editingRecord && !loadingPreviousData) {
      // Only fetch if we don't already have the data
      const needsGrocery = !extractedData && !formData.grocerySales;
      const needsStock = formData.previousStockValue && !formData.currentStockValue;
      
      console.log('needsGrocery:', needsGrocery, 'needsStock:', needsStock);
      
      if (needsGrocery || needsStock) {
        console.log('Calling fetchTodaysUploadData...');
        // Small delay to ensure previousStockValue is set
        setTimeout(() => {
          fetchTodaysUploadData();
        }, 100);
      }
    }
  }, [isOpen, formData.previousStockValue, formData.date, editingRecord, extractedData, loadingPreviousData]);

  const fetchPreviousBankAmount = async () => {
    try {
      setLoadingPreviousData(true);
      const response = await fetch(`${API}/previous-financial-data?date=${formData.date}`);
      if (response.ok) {
        const data = await response.json();
        if (data.found) {
          const updates = {};
          if (data.bank_amount !== null) {
            updates.previousBankAmount = data.bank_amount.toString();
          }
          if (data.stock_value !== null) {
            updates.previousStockValue = data.stock_value.toString();
          }
          if (Object.keys(updates).length > 0) {
            setFormData(prev => ({
              ...prev,
              ...updates
            }));
          }
        }
      }
    } catch (error) {
      console.error('Error fetching previous financial data:', error);
    } finally {
      setLoadingPreviousData(false);
    }
  };

  const fetchTodaysUploadData = async () => {
    try {
      setCalculatingStock(true);
      console.log('Fetching upload data for date:', formData.date);
      const response = await fetch(`${API}/upload-history?data_date=${formData.date}`);
      if (response.ok) {
        const data = await response.json();
        console.log('Upload history response:', data);
        
        // Find today's daily upload - use string comparison to avoid timezone issues
        const todayUpload = data.uploads?.find(u => {
          if (u.upload_type !== 'daily' || u.status !== 'success') {
            return false;
          }
          
          // Extract just the date part from the data_date string (handles timezone properly)
          const uploadDate = u.data_date.split('T')[0];
          const matches = uploadDate === formData.date;
          
          console.log('Checking upload:', {
            upload_type: u.upload_type,
            status: u.status,
            data_date: u.data_date,
            uploadDate: uploadDate,
            formData_date: formData.date,
            matches: matches
          });
          
          return matches;
        });
        console.log('Found today upload:', todayUpload);
        
        if (todayUpload) {
          console.log('Processing today upload:', todayUpload);
          const updates = {};
          
          // Auto-fill grocery sales from Net Amt if not from image
          if (!extractedData && todayUpload.net_amt) {
            const netAmt = parseFloat(todayUpload.net_amt);
            console.log('Setting grocery sales to:', netAmt);
            updates.grocerySales = netAmt.toFixed(2);
            toast.success(`✓ Grocery sales auto-filled from today's upload: ₹${netAmt.toFixed(2)}`);
          } else {
            console.log('Skipping grocery sales - extractedData:', extractedData, 'net_amt:', todayUpload.net_amt);
          }
          
          // Calculate stock value if W_Amt is available
          if (todayUpload.w_amt) {
            const wAmt = parseFloat(todayUpload.w_amt);
            setTodaysWAmt(wAmt);
            console.log('W_Amt found:', wAmt);
            console.log('Current formData.previousStockValue:', formData.previousStockValue);
            
            // Calculate current stock value if we have previous stock
            // Use the callback form to get the latest state
            setFormData(prev => {
              console.log('Inside setFormData - prev.previousStockValue:', prev.previousStockValue);
              
              if (prev.previousStockValue && prev.previousStockValue !== '') {
                const prevStock = parseFloat(prev.previousStockValue);
                const currentStock = prevStock - wAmt;
                console.log(`✓ Stock calculation: ${prevStock} - ${wAmt} = ${currentStock}`);
                toast.success(`✓ Stock calculated: ₹${prevStock.toFixed(2)} - ₹${wAmt.toFixed(2)} = ₹${currentStock.toFixed(2)}`);
                
                return {
                  ...prev,
                  ...updates,
                  currentStockValue: currentStock.toFixed(2)
                };
              } else {
                console.log('No previous stock value available for calculation');
                return {
                  ...prev,
                  ...updates
                };
              }
            });
            
            return; // Exit early since we're using setFormData callback
          } else {
            setTodaysWAmt(null);
          }
          
          // Apply all updates at once (only if no w_amt, otherwise already applied above)
          console.log('Applying remaining updates:', updates);
          if (!todayUpload.w_amt && Object.keys(updates).length > 0) {
            setFormData(prev => ({
              ...prev,
              ...updates
            }));
          }
        } else {
          console.log('No matching upload found for today');
        }
      }
    } catch (error) {
      console.error('Error fetching today\'s upload data:', error);
    } finally {
      setCalculatingStock(false);
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
      if (editingRecord) {
        // Update existing record
        const params = new URLSearchParams({
          liquor_sales: formData.liquorSales,
          previous_bank_amount: formData.previousBankAmount,
        });

        if (formData.grocerySales) {
          params.append('grocery_sales', formData.grocerySales);
        }
        if (formData.previousStockValue) {
          params.append('previous_stock_value', formData.previousStockValue);
        }
        if (formData.currentStockValue) {
          params.append('current_stock_value', formData.currentStockValue);
        }
        if (formData.notes) {
          params.append('notes', formData.notes);
        }

        const response = await fetch(`${API}/financial-data/${editingRecord.id}?${params}`, {
          method: 'PUT',
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to update report');
        }

        const reportDate = new Date(formData.date).toLocaleDateString('en-IN', {
          day: '2-digit',
          month: 'short',
          year: 'numeric'
        });
        toast.success(`Financial Report for ${reportDate} updated successfully! Dashboard will refresh...`);
        
        if (onSuccess) {
          onSuccess();
        }
        
        // Refresh dashboard data
        if (onReportGenerated) {
          setTimeout(() => {
            onReportGenerated();
            toast.success('Dashboard updated!');
          }, 500);
        }
        
        onClose();
      } else {
        // Generate new report
        const params = new URLSearchParams({
          date: formData.date,
          liquor_sales: formData.liquorSales,
          previous_bank_amount: formData.previousBankAmount,
        });

        if (formData.grocerySales) {
          params.append('grocery_sales', formData.grocerySales);
        }
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

        const reportDate = new Date(formData.date).toLocaleDateString('en-IN', {
          day: '2-digit',
          month: 'short',
          year: 'numeric'
        });
        toast.success(`Financial Report for ${reportDate} generated successfully! Dashboard will refresh...`);
        
        if (onSuccess) {
          onSuccess();
        }
        
        // Refresh dashboard data after report generation
        if (onReportGenerated) {
          setTimeout(() => {
            onReportGenerated();
            toast.success('Dashboard updated with new stock value!');
          }, 500);
        }
        
        onClose();
      }
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
            <h2 className="text-2xl font-bold text-gray-900">
              {editingRecord ? 'Edit Financial Report' : 'Generate Daily Sales Report'}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {editingRecord ? 'Update the financial details for this report' : 'Fill in the financial details for the selected date'}
            </p>
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
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              disabled={loading || editingRecord}
            />
            {editingRecord && (
              <p className="text-xs text-gray-500 mt-1">Date cannot be changed when editing</p>
            )}
          </div>

          {/* Sales Input Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Grocery Sales */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Grocery Sales for the Day (₹) 
                {extractedData ? (
                  <span className="text-green-600 text-xs ml-1">(From Image)</span>
                ) : formData.grocerySales ? (
                  <span className="text-blue-600 text-xs ml-1">(From Upload)</span>
                ) : (
                  <span className="text-gray-400 text-xs ml-1">(Optional)</span>
                )}
                {calculatingStock && !formData.grocerySales && (
                  <span className="text-xs text-blue-600 ml-2">(Loading...)</span>
                )}
              </label>
              <input
                type="number"
                name="grocerySales"
                value={formData.grocerySales}
                onChange={handleInputChange}
                placeholder="Auto-filled from upload or image"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading || calculatingStock}
              />
              {formData.grocerySales && !extractedData && (
                <p className="text-xs text-blue-600 mt-1">
                  ✓ Auto-filled from today's uploaded Excel data
                </p>
              )}
              {!formData.grocerySales && !extractedData && !calculatingStock && (
                <p className="text-xs text-gray-500 mt-1">
                  Will be auto-filled from today's uploaded data if available
                </p>
              )}
            </div>

            {/* Liquor Sales */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Liquor Sales for the Day (₹) {extractedData ? <span className="text-green-600 text-xs">(From Image)</span> : <span className="text-red-500">*</span>}
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
                {calculatingStock && <span className="text-xs text-blue-600 ml-2">(Calculating...)</span>}
                {todaysWAmt && <span className="text-xs text-green-600 ml-2">(Auto-calculated)</span>}
              </label>
              <input
                type="number"
                name="currentStockValue"
                value={formData.currentStockValue}
                onChange={handleInputChange}
                placeholder="Will be auto-calculated if W_Amt data available"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={loading || calculatingStock}
              />
              {todaysWAmt && (
                <p className="text-xs text-green-600 mt-1">
                  ✓ Calculated from today's W_Amt: ₹{todaysWAmt.toFixed(2)}
                </p>
              )}
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
          <div className={`border rounded-lg p-4 ${extractedData ? 'bg-green-50 border-green-200' : formData.grocerySales ? 'bg-blue-50 border-blue-200' : 'bg-yellow-50 border-yellow-200'}`}>
            <p className={`text-sm ${extractedData ? 'text-green-800' : formData.grocerySales ? 'text-blue-800' : 'text-yellow-800'}`}>
              {extractedData ? (
                <>
                  <strong>✓ Data from Image:</strong> Grocery and Liquor sales extracted automatically from your uploaded image. 
                  Previous day's data and stock value also auto-populated. Review and edit if needed.
                </>
              ) : formData.grocerySales ? (
                <>
                  <strong>✓ Data from Daily Upload:</strong> Grocery sales auto-filled from today's uploaded Excel data. 
                  Previous day's bank amount and stock calculations are also populated automatically.
                </>
              ) : (
                <>
                  <strong>ℹ️ Auto-Fill Available:</strong> If you uploaded today's Excel data, grocery sales and stock value will be auto-calculated. 
                  Previous day's data is also fetched automatically. Just enter liquor sales!
                </>
              )}
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
                <span>{editingRecord ? 'Updating...' : 'Generating...'}</span>
              </>
            ) : (
              <>
                {editingRecord ? (
                  <>
                    <Edit2 className="w-5 h-5" />
                    <span>Update Report</span>
                  </>
                ) : (
                  <>
                    <Download className="w-5 h-5" />
                    <span>Generate & Download PDF</span>
                  </>
                )}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FinancialHealth;
