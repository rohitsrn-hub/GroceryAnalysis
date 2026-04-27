import { apiFetch } from '../utils/api';
import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { X, Upload, Calendar, FileText, Image as ImageIcon, Zap, FileDown } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DailyUploadModal = ({ isOpen, onClose, onSuccess }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [uploading, setUploading] = useState(false);
  const [stepLabel, setStepLabel] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [autoGenerate, setAutoGenerate] = useState(true);

  // Previous-day financial baseline (auto-fetched; editable if missing)
  const [previousBankAmount, setPreviousBankAmount] = useState('');
  const [previousStockValue, setPreviousStockValue] = useState('');
  const [previousFound, setPreviousFound] = useState(false);
  const [previousDate, setPreviousDate] = useState(null);
  const [fetchingPrevious, setFetchingPrevious] = useState(false);

  // Fetch previous financial data whenever the modal opens or date changes
  useEffect(() => {
    if (!isOpen) return;
    const fetchPrevious = async () => {
      try {
        setFetchingPrevious(true);
        const resp = await apiFetch(`${API}/previous-financial-data?date=${selectedDate}`);
        if (resp.ok) {
          const data = await resp.json();
          if (data.found) {
            setPreviousFound(true);
            setPreviousDate(data.previous_date);
            setPreviousBankAmount(
              data.bank_amount !== null && data.bank_amount !== undefined ? String(data.bank_amount) : ''
            );
            setPreviousStockValue(
              data.stock_value !== null && data.stock_value !== undefined ? String(data.stock_value) : ''
            );
          } else {
            setPreviousFound(false);
            setPreviousDate(null);
          }
        }
      } catch (err) {
        console.error('Error fetching previous financial data:', err);
      } finally {
        setFetchingPrevious(false);
      }
    };
    fetchPrevious();
  }, [isOpen, selectedDate]);

  const resetState = () => {
    setSelectedFile(null);
    setSelectedImage(null);
    setImagePreview(null);
    setSelectedDate(new Date().toISOString().split('T')[0]);
    setPreviousBankAmount('');
    setPreviousStockValue('');
    setPreviousFound(false);
    setPreviousDate(null);
    setStepLabel('');
    setAutoGenerate(true);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
        setSelectedFile(file);
      } else {
        toast.error('Please upload an Excel file (.xlsx or .xls)');
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Please select a valid image file');
      return;
    }
    setSelectedImage(file);
    const reader = new FileReader();
    reader.onloadend = () => setImagePreview(reader.result);
    reader.readAsDataURL(file);
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
  };

  const autoGenerateReport = async ({ grocerySales, liquorSales }) => {
    // Backend auto-falls-back to last generated report if previous_bank_amount
    // is omitted — so this value is now optional. Only a hard fail if there is
    // truly no prior record anywhere, which the backend returns as 400.
    const params = new URLSearchParams({ date: selectedDate });
    if (liquorSales !== undefined && liquorSales !== null) {
      params.append('liquor_sales', String(liquorSales));
    }
    if (previousBankAmount !== '' && previousBankAmount !== null && previousBankAmount !== undefined) {
      params.append('previous_bank_amount', String(previousBankAmount));
    }
    if (grocerySales !== undefined && grocerySales !== null) {
      params.append('grocery_sales', String(grocerySales));
    }
    if (previousStockValue !== '' && previousStockValue !== null) {
      params.append('previous_stock_value', String(previousStockValue));
    }

    const resp = await apiFetch(`${API}/generate-daily-report?${params.toString()}`, {
      method: 'POST',
    });
    if (!resp.ok) {
      let detail = 'Failed to generate daily sales report';
      try {
        const errJson = await resp.json();
        detail = errJson.detail || detail;
      } catch {
        detail = (await resp.text()) || detail;
      }
      throw new Error(detail);
    }
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `daily_sales_report_${selectedDate}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    return true;
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error('Please select an Excel file first');
      return;
    }
    if (!selectedDate) {
      toast.error('Please select a date');
      return;
    }

    const willAutoGenerate = Boolean(selectedImage) && autoGenerate;
    setUploading(true);

    try {
      // STEP 1: Upload Excel daily sales data
      setStepLabel('Uploading daily sales data…');
      const excelForm = new FormData();
      excelForm.append('file', selectedFile);
      excelForm.append('upload_type', 'daily');
      excelForm.append('data_date', selectedDate);

      const uploadResp = await apiFetch(`${API}/upload-sales-data`, {
        method: 'POST',
        body: excelForm,
      });
      if (!uploadResp.ok) {
        let errorDetail;
        try {
          const err = await uploadResp.json();
          errorDetail = err.detail;
        } catch {
          errorDetail = await uploadResp.text();
        }
        throw new Error(errorDetail || 'Upload failed');
      }
      const uploadResult = await uploadResp.json();
      toast.success(
        `Uploaded ${uploadResult.records_count} records for ${new Date(selectedDate).toLocaleDateString()}`
      );

      // STEP 2: (optional) extract data from CSD image + auto-generate report
      if (willAutoGenerate) {
        setStepLabel('Extracting data from CSD summary image…');
        const imgForm = new FormData();
        imgForm.append('file', selectedImage);
        const extractResp = await apiFetch(`${API}/extract-canteen-summary`, {
          method: 'POST',
          body: imgForm,
        });
        if (!extractResp.ok) {
          const errText = await extractResp.text();
          throw new Error(errText || 'Failed to extract data from image');
        }
        const extractJson = await extractResp.json();
        const extracted = extractJson.data || {};
        const grocerySales = extracted.grocery_sales;
        const liquorSales = extracted.liquor_sales;
        toast.success(
          `Extracted: Grocery ₹${Number(grocerySales || 0).toLocaleString('en-IN')} • Liquor ₹${Number(liquorSales || 0).toLocaleString('en-IN')}`
        );
        if (liquorSales === undefined || liquorSales === null) {
          toast.warning('Liquor sales not found in image — defaulting to ₹0. Edit the report if needed.');
        }

        setStepLabel('Generating daily sales report…');
        const ok = await autoGenerateReport({ grocerySales, liquorSales });
        if (ok) {
          toast.success(`Daily sales report generated & downloaded for ${new Date(selectedDate).toLocaleDateString()}`);
        }
      }

      // Done – reset and close
      resetState();
      if (onSuccess) onSuccess();
      onClose();
    } catch (error) {
      console.error('Upload error:', error);
      toast.error(error.message || 'Failed to complete upload');
    } finally {
      setUploading(false);
      setStepLabel('');
    }
  };

  if (!isOpen) return null;

  const prettyPrevDate = previousDate
    ? new Date(previousDate).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" data-testid="daily-upload-modal">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <div className="bg-blue-100 p-2 rounded-lg">
              <Upload className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Upload Today's Sales Data</h2>
              <p className="text-sm text-gray-600">Upload daily sales Excel & CSD image — report auto-generated</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={uploading}
            data-testid="daily-upload-close-btn"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Calendar className="w-4 h-4 inline mr-2" />
              Select Date
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={uploading}
              data-testid="daily-upload-date-input"
            />
          </div>

          {/* Excel file upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <FileText className="w-4 h-4 inline mr-2" />
              Daily Sales Excel File <span className="text-red-500">*</span>
            </label>
            <div
              className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                id="file-upload"
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                className="hidden"
                disabled={uploading}
                data-testid="daily-upload-excel-input"
              />
              {selectedFile ? (
                <div className="space-y-2">
                  <div className="w-14 h-14 mx-auto bg-green-100 rounded-full flex items-center justify-center">
                    <FileText className="w-7 h-7 text-green-600" />
                  </div>
                  <p className="text-base font-medium text-gray-900">{selectedFile.name}</p>
                  <p className="text-xs text-gray-600">{(selectedFile.size / 1024).toFixed(2)} KB</p>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="text-sm text-red-600 hover:text-red-700 font-medium"
                    disabled={uploading}
                    data-testid="daily-upload-remove-excel-btn"
                  >
                    Remove file
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="w-14 h-14 mx-auto bg-gray-100 rounded-full flex items-center justify-center">
                    <Upload className="w-7 h-7 text-gray-400" />
                  </div>
                  <p className="text-base font-medium text-gray-900">Drop your Excel file here</p>
                  <p className="text-sm text-gray-600">
                    or{' '}
                    <label htmlFor="file-upload" className="text-blue-600 hover:text-blue-700 font-medium cursor-pointer">
                      browse
                    </label>
                  </p>
                  <p className="text-xs text-gray-500">Supports .xlsx and .xls files</p>
                </div>
              )}
            </div>
          </div>

          {/* CSD image (optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <ImageIcon className="w-4 h-4 inline mr-2" />
              CSD Sales Summary Image <span className="text-gray-400 text-xs">(optional — enables auto-report)</span>
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 hover:border-emerald-400 transition-colors">
              <input
                id="image-upload"
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="hidden"
                disabled={uploading}
                data-testid="daily-upload-image-input"
              />
              {selectedImage ? (
                <div className="flex items-center gap-4">
                  {imagePreview && (
                    <img
                      src={imagePreview}
                      alt="CSD preview"
                      className="w-24 h-24 object-contain bg-gray-50 border rounded"
                    />
                  )}
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{selectedImage.name}</p>
                    <p className="text-xs text-gray-600">{(selectedImage.size / 1024).toFixed(1)} KB</p>
                    <button
                      onClick={clearImage}
                      className="text-xs text-red-600 hover:text-red-700 font-medium mt-1"
                      disabled={uploading}
                      data-testid="daily-upload-remove-image-btn"
                    >
                      Remove image
                    </button>
                  </div>
                </div>
              ) : (
                <label htmlFor="image-upload" className="flex items-center gap-3 cursor-pointer">
                  <div className="w-12 h-12 bg-emerald-50 rounded-full flex items-center justify-center flex-shrink-0">
                    <ImageIcon className="w-6 h-6 text-emerald-500" />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium text-gray-900">Click to attach CSD summary image</p>
                    <p className="text-xs text-gray-500">
                      PNG, JPG up to 10MB. When attached, the daily sales report will be generated automatically.
                    </p>
                  </div>
                </label>
              )}
            </div>
          </div>

          {/* Auto-generate controls — appear only when image is present */}
          {selectedImage && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 space-y-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoGenerate}
                  onChange={(e) => setAutoGenerate(e.target.checked)}
                  className="w-4 h-4 accent-emerald-600"
                  disabled={uploading}
                  data-testid="daily-upload-autogen-checkbox"
                />
                <span className="text-sm font-medium text-emerald-900 flex items-center gap-1">
                  <Zap className="w-4 h-4" /> Auto-generate daily sales report (PDF)
                </span>
              </label>

              {autoGenerate && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Previous Bank Amount (₹){' '}
                      {previousFound ? (
                        <span className="text-green-600">(auto from {prettyPrevDate})</span>
                      ) : (
                        <span className="text-gray-400">(optional – server will auto-use last report)</span>
                      )}
                    </label>
                    <input
                      type="number"
                      value={previousBankAmount}
                      onChange={(e) => setPreviousBankAmount(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-emerald-500"
                      placeholder={fetchingPrevious ? 'Loading…' : '0.00'}
                      disabled={uploading}
                      data-testid="daily-upload-prev-bank-input"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Previous Stock Value (₹){' '}
                      {previousFound ? (
                        <span className="text-green-600">(auto)</span>
                      ) : (
                        <span className="text-gray-400">(optional)</span>
                      )}
                    </label>
                    <input
                      type="number"
                      value={previousStockValue}
                      onChange={(e) => setPreviousStockValue(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-emerald-500"
                      placeholder={fetchingPrevious ? 'Loading…' : '0.00'}
                      disabled={uploading}
                      data-testid="daily-upload-prev-stock-input"
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Info box */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">How this works</h4>
            <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
              <li>Excel sales data is uploaded for the selected date.</li>
              <li>If a CSD image is attached, grocery & liquor sales are extracted automatically.</li>
              <li>The system pulls the last available bank & stock values and generates the PDF report instantly.</li>
              <li>Only one upload per day is allowed.</li>
            </ul>
          </div>

          {/* Step indicator */}
          {uploading && stepLabel && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex items-center gap-3" data-testid="daily-upload-step-indicator">
              <svg className="animate-spin h-5 w-5 text-blue-600" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-sm text-gray-700">{stepLabel}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-4 p-6 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors font-medium"
            disabled={uploading}
            data-testid="daily-upload-cancel-btn"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || !selectedDate || uploading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center space-x-2"
            data-testid="daily-upload-submit-btn"
          >
            {uploading ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Processing…</span>
              </>
            ) : selectedImage && autoGenerate ? (
              <>
                <FileDown className="w-5 h-5" />
                <span>Upload & Auto-Generate Report</span>
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                <span>Upload Data</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DailyUploadModal;
