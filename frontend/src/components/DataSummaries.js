import { apiFetch } from '../utils/api';
import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { 
  Database, 
  Trash2, 
  RefreshCw, 
  Upload, 
  Eye, 
  Calendar, 
  FileSpreadsheet,
  CheckCircle,
  AlertCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Loader2,
  X
} from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DataSummaries = ({ onSummaryChange }) => {
  const [summaries, setSummaries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedSummary, setExpandedSummary] = useState(null);
  const [summaryDetails, setSummaryDetails] = useState({});
  const [loadingDetails, setLoadingDetails] = useState({});
  
  // Delete dialog state
  const [deleteDialog, setDeleteDialog] = useState({ open: false, summary: null });
  const [deleting, setDeleting] = useState(false);
  
  // Generate summary state
  const [generateYear, setGenerateYear] = useState(new Date().getFullYear().toString());
  const [generateMonth, setGenerateMonth] = useState("");
  const [generating, setGenerating] = useState(false);
  
  // Upload override state
  const [uploadDialog, setUploadDialog] = useState({ open: false });
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadPeriod, setUploadPeriod] = useState("");
  const [uploadYear, setUploadYear] = useState(new Date().getFullYear().toString());
  const [uploadMonth, setUploadMonth] = useState("");
  const [uploadType, setUploadType] = useState("monthly");
  const [overrideExisting, setOverrideExisting] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Fetch summaries on component mount
  useEffect(() => {
    fetchSummaries();
  }, []);

  const fetchSummaries = async () => {
    setLoading(true);
    try {
      const response = await apiFetch(`${API}/monthly-summaries`);
      if (response.ok) {
        const data = await response.json();
        setSummaries(data.summaries || []);
      } else {
        throw new Error("Failed to fetch summaries");
      }
    } catch (error) {
      console.error("Error fetching summaries:", error);
      toast.error("Failed to load data summaries");
    } finally {
      setLoading(false);
    }
  };

  const fetchSummaryDetails = async (period) => {
    if (summaryDetails[period]) {
      // Already loaded
      return;
    }
    
    setLoadingDetails(prev => ({ ...prev, [period]: true }));
    try {
      const response = await apiFetch(`${API}/monthly-summary-details/${period}`);
      if (response.ok) {
        const data = await response.json();
        setSummaryDetails(prev => ({ ...prev, [period]: data }));
      } else {
        throw new Error("Failed to fetch summary details");
      }
    } catch (error) {
      console.error("Error fetching summary details:", error);
      toast.error("Failed to load summary details");
    } finally {
      setLoadingDetails(prev => ({ ...prev, [period]: false }));
    }
  };

  const toggleExpand = (period) => {
    if (expandedSummary === period) {
      setExpandedSummary(null);
    } else {
      setExpandedSummary(period);
      fetchSummaryDetails(period);
    }
  };

  const handleDelete = async () => {
    if (!deleteDialog.summary) return;
    
    setDeleting(true);
    try {
      const response = await apiFetch(`${API}/monthly-summaries/${deleteDialog.summary.period}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        toast.success(`Deleted summary for ${deleteDialog.summary.display_name}`);
        setDeleteDialog({ open: false, summary: null });
        fetchSummaries();
        if (onSummaryChange) onSummaryChange();
      } else {
        const error = await response.json();
        throw new Error(error.detail || "Failed to delete summary");
      }
    } catch (error) {
      console.error("Error deleting summary:", error);
      toast.error(error.message);
    } finally {
      setDeleting(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!generateYear) {
      toast.error("Please select a year");
      return;
    }
    
    setGenerating(true);
    try {
      const period = generateMonth 
        ? `${generateYear}-${generateMonth.padStart(2, '0')}`
        : generateYear;
      
      const response = await apiFetch(`${API}/trigger-summary-generation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period })
      });
      
      const result = await response.json();
      
      if (response.ok) {
        toast.success(result.message || `Summary generated for ${period}`);
        fetchSummaries();
        if (onSummaryChange) onSummaryChange();
      } else {
        throw new Error(result.detail || "Failed to generate summary");
      }
    } catch (error) {
      console.error("Error generating summary:", error);
      toast.error(error.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleUploadOverride = async () => {
    if (!uploadFile) {
      toast.error("Please select a file");
      return;
    }
    
    const period = uploadType === "monthly" 
      ? `${uploadYear}-${uploadMonth.padStart(2, '0')}`
      : uploadYear;
    
    if (uploadType === "monthly" && !uploadMonth) {
      toast.error("Please select a month");
      return;
    }
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('period', period);
      formData.append('override_existing', overrideExisting.toString());
      
      const response = await apiFetch(`${API}/upload-forecast-history`, {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (response.ok) {
        toast.success(result.message || `Successfully uploaded data for ${period}`);
        setUploadDialog({ open: false });
        setUploadFile(null);
        setUploadMonth("");
        setOverrideExisting(false);
        fetchSummaries();
        if (onSummaryChange) onSummaryChange();
      } else {
        throw new Error(result.detail || "Failed to upload data");
      }
    } catch (error) {
      console.error("Error uploading override data:", error);
      toast.error(error.message);
    } finally {
      setUploading(false);
    }
  };

  const formatCurrency = (amount) => {
    if (!amount) return "₹0";
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  };

  const months = [
    { value: "01", label: "January" },
    { value: "02", label: "February" },
    { value: "03", label: "March" },
    { value: "04", label: "April" },
    { value: "05", label: "May" },
    { value: "06", label: "June" },
    { value: "07", label: "July" },
    { value: "08", label: "August" },
    { value: "09", label: "September" },
    { value: "10", label: "October" },
    { value: "11", label: "November" },
    { value: "12", label: "December" }
  ];

  const years = Array.from({ length: 10 }, (_, i) => {
    const year = new Date().getFullYear() - i;
    return { value: year.toString(), label: year.toString() };
  });

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Database className="h-5 w-5" />
            <span>Data Summaries Management</span>
          </CardTitle>
          <CardDescription>
            View, manage, and create monthly/yearly data summaries used for forecasting. 
            These summaries are automatically generated when you upload daily data, or you can create them manually.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Actions Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Generate Summary Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center space-x-2">
              <RefreshCw className="h-4 w-4" />
              <span>Generate Summary from Existing Data</span>
            </CardTitle>
            <CardDescription className="text-sm">
              Create a summary from daily data already in the system
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3 items-end">
              <div className="space-y-1">
                <Label className="text-xs">Year</Label>
                <Select value={generateYear} onValueChange={setGenerateYear}>
                  <SelectTrigger className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {years.map(y => (
                      <SelectItem key={y.value} value={y.value}>{y.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Month (optional)</Label>
                <Select value={generateMonth || "yearly"} onValueChange={(val) => setGenerateMonth(val === "yearly" ? "" : val)}>
                  <SelectTrigger className="w-32">
                    <SelectValue placeholder="All year" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="yearly">Yearly Summary</SelectItem>
                    {months.map(m => (
                      <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button 
                onClick={handleGenerateSummary} 
                disabled={generating}
                size="sm"
              >
                {generating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Generate
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Upload Override Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center space-x-2">
              <Upload className="h-4 w-4" />
              <span>Upload Custom Summary Data</span>
            </CardTitle>
            <CardDescription className="text-sm">
              Upload your own Excel file to override or add summary data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              onClick={() => setUploadDialog({ open: true })}
              variant="outline"
              className="w-full"
            >
              <Upload className="h-4 w-4 mr-2" />
              Upload Override Data (Excel)
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Summaries List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Available Summaries</CardTitle>
            <Button variant="ghost" size="sm" onClick={fetchSummaries} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : summaries.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Database className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p className="font-medium">No summaries found</p>
              <p className="text-sm">Upload daily data or generate summaries manually</p>
            </div>
          ) : (
            <div className="space-y-3">
              {summaries.map((summary) => (
                <div 
                  key={summary.period}
                  className="border rounded-lg overflow-hidden"
                >
                  {/* Summary Header */}
                  <div 
                    className={`p-4 bg-gray-50 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors ${
                      expandedSummary === summary.period ? 'border-b' : ''
                    }`}
                    onClick={() => toggleExpand(summary.period)}
                  >
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-2">
                        {summary.summary_type === 'yearly' ? (
                          <Calendar className="h-5 w-5 text-purple-600" />
                        ) : (
                          <FileSpreadsheet className="h-5 w-5 text-blue-600" />
                        )}
                        <div>
                          <p className="font-medium">{summary.display_name}</p>
                          <p className="text-xs text-gray-500">
                            {summary.summary_type === 'yearly' ? 'Yearly' : 'Monthly'} Summary
                          </p>
                        </div>
                      </div>
                      
                      <Badge 
                        variant={summary.source === 'user_uploaded' ? 'default' : 'secondary'}
                        className="text-xs"
                      >
                        {summary.source === 'user_uploaded' ? 'User Uploaded' : 'Auto Generated'}
                      </Badge>
                    </div>

                    <div className="flex items-center space-x-4">
                      <div className="text-right text-sm hidden md:block">
                        <p className="text-gray-600">{summary.item_count?.toLocaleString()} items</p>
                        <p className="font-medium text-green-700">{formatCurrency(summary.total_revenue)}</p>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteDialog({ open: true, summary });
                          }}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                        
                        {expandedSummary === summary.period ? (
                          <ChevronUp className="h-5 w-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-gray-400" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedSummary === summary.period && (
                    <div className="p-4 bg-white">
                      {loadingDetails[summary.period] ? (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                        </div>
                      ) : summaryDetails[summary.period] ? (
                        <div className="space-y-4">
                          {/* Summary Stats */}
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-blue-50 p-3 rounded-lg">
                              <p className="text-xs text-blue-600">Total Items</p>
                              <p className="text-lg font-bold text-blue-900">
                                {summaryDetails[summary.period].item_count?.toLocaleString()}
                              </p>
                            </div>
                            <div className="bg-green-50 p-3 rounded-lg">
                              <p className="text-xs text-green-600">Total Revenue</p>
                              <p className="text-lg font-bold text-green-900">
                                {formatCurrency(summaryDetails[summary.period].total_revenue)}
                              </p>
                            </div>
                            <div className="bg-purple-50 p-3 rounded-lg">
                              <p className="text-xs text-purple-600">Total Profit</p>
                              <p className="text-lg font-bold text-purple-900">
                                {formatCurrency(summaryDetails[summary.period].total_profit)}
                              </p>
                            </div>
                            <div className="bg-orange-50 p-3 rounded-lg">
                              <p className="text-xs text-orange-600">Total Qty Sold</p>
                              <p className="text-lg font-bold text-orange-900">
                                {summaryDetails[summary.period].total_qty_sold?.toLocaleString()}
                              </p>
                            </div>
                          </div>

                          {/* Items Table */}
                          <div className="border rounded-lg overflow-hidden">
                            <div className="bg-gray-100 px-4 py-2 border-b">
                              <p className="text-sm font-medium">Top Items (First 20)</p>
                            </div>
                            <div className="max-h-64 overflow-y-auto">
                              <table className="w-full text-sm">
                                <thead className="bg-gray-50 sticky top-0">
                                  <tr>
                                    <th className="text-left px-4 py-2 font-medium">Item Name</th>
                                    <th className="text-right px-4 py-2 font-medium">Qty</th>
                                    <th className="text-right px-4 py-2 font-medium">Revenue</th>
                                    <th className="text-right px-4 py-2 font-medium">Profit</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {summaryDetails[summary.period].items?.slice(0, 20).map((item, idx) => (
                                    <tr key={idx} className="border-t hover:bg-gray-50">
                                      <td className="px-4 py-2 truncate max-w-48" title={item.item_name}>
                                        {item.item_name}
                                      </td>
                                      <td className="text-right px-4 py-2">
                                        {item.net_qty?.toLocaleString()}
                                      </td>
                                      <td className="text-right px-4 py-2 text-green-700">
                                        {formatCurrency(item.r_amt)}
                                      </td>
                                      <td className="text-right px-4 py-2 text-purple-700">
                                        {formatCurrency(item.profit)}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>

                          {/* Metadata */}
                          <div className="text-xs text-gray-500 flex items-center space-x-4">
                            <span>Created: {new Date(summaryDetails[summary.period].created_at).toLocaleString()}</span>
                            {summaryDetails[summary.period].original_filename && (
                              <span>Source file: {summaryDetails[summary.period].original_filename}</span>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-4 text-gray-500">
                          <p>Unable to load details</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="p-4">
          <div className="flex items-start space-x-3">
            <Info className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">How Data Summaries Work</p>
              <ul className="list-disc list-inside space-y-1 text-blue-700">
                <li><strong>Auto-generation:</strong> When you upload daily data for a new month, the system automatically creates a summary for the previous month.</li>
                <li><strong>Forecasting:</strong> The forecasting system uses these summaries for accurate predictions instead of raw daily data.</li>
                <li><strong>Override:</strong> You can upload your own summary data to replace or supplement auto-generated summaries.</li>
                <li><strong>Manual generation:</strong> Use "Generate Summary" to create summaries from existing daily data in the system.</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialog.open} onOpenChange={(open) => setDeleteDialog({ ...deleteDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-red-900">Delete Summary?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-700">
              {deleteDialog.summary && (
                <>
                  <p className="mb-3">
                    This will permanently delete the summary for:
                  </p>
                  <div className="p-3 bg-gray-50 rounded border mb-3">
                    <strong>{deleteDialog.summary.display_name}</strong>
                    <p className="text-sm text-gray-500">
                      {deleteDialog.summary.item_count?.toLocaleString()} items | {formatCurrency(deleteDialog.summary.total_revenue)} revenue
                    </p>
                  </div>
                  <p className="text-orange-700 font-medium">
                    This may affect forecasting results. You can regenerate this summary later if needed.
                  </p>
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleting ? "Deleting..." : "Delete Summary"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Upload Override Dialog */}
      <Dialog open={uploadDialog.open} onOpenChange={(open) => setUploadDialog({ open })}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <Upload className="h-5 w-5" />
              <span>Upload Custom Summary Data</span>
            </DialogTitle>
            <DialogDescription>
              Upload an Excel file with item-wise summary data for a specific period.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {/* Summary Type */}
            <div className="space-y-2">
              <Label>Summary Type</Label>
              <Select value={uploadType} onValueChange={setUploadType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">Monthly Summary</SelectItem>
                  <SelectItem value="yearly">Yearly Summary</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Year Selection */}
            <div className="space-y-2">
              <Label>Year</Label>
              <Select value={uploadYear} onValueChange={setUploadYear}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {years.map(y => (
                    <SelectItem key={y.value} value={y.value}>{y.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Month Selection (only for monthly) */}
            {uploadType === "monthly" && (
              <div className="space-y-2">
                <Label>Month</Label>
                <Select value={uploadMonth} onValueChange={setUploadMonth}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select month" />
                  </SelectTrigger>
                  <SelectContent>
                    {months.map(m => (
                      <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* File Upload */}
            <div className="space-y-2">
              <Label>Excel File</Label>
              <div className="flex items-center space-x-2">
                <Input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  className="flex-1"
                />
                {uploadFile && (
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setUploadFile(null)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
              {uploadFile && (
                <p className="text-xs text-gray-500">
                  Selected: {uploadFile.name} ({(uploadFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>

            {/* Override Checkbox */}
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="override"
                checked={overrideExisting}
                onChange={(e) => setOverrideExisting(e.target.checked)}
                className="rounded border-gray-300"
              />
              <Label htmlFor="override" className="text-sm font-normal cursor-pointer">
                Override existing summary if present
              </Label>
            </div>

            {/* Format Info */}
            <div className="bg-gray-50 p-3 rounded-lg text-xs text-gray-600">
              <p className="font-medium mb-1">Expected Excel Format:</p>
              <p>Same as regular sales data with columns: Item_Name, pluno, R_Amt, W_Amt, Net_Qty, Profit, etc.</p>
            </div>
          </div>

          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={() => setUploadDialog({ open: false })}>
              Cancel
            </Button>
            <Button 
              onClick={handleUploadOverride}
              disabled={uploading || !uploadFile || (uploadType === "monthly" && !uploadMonth)}
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DataSummaries;
