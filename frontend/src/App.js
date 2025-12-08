import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import "./App.css";
import Dashboard from "./components/Dashboard";
import DataUpload from "./components/DataUpload";
import AnalyticsFixed from "./components/AnalyticsFixed";
import Forecasting from "./components/Forecasting";
import UploadHistory from "./components/UploadHistory";
import DatabaseView from "./components/DatabaseView";
import FinancialHealth from "./components/FinancialHealth";
import { Toaster, toast } from "./components/ui/sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { BarChart3, Upload, TrendingUp, FileSpreadsheet, Building2, Download, Clock, Database, DollarSign, RefreshCw } from "lucide-react";
import { formatIndianNumber, formatPercentage } from "./utils/numberUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function MainApp() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshingStock, setRefreshingStock] = useState(false);
  const [dashboardPeriod, setDashboardPeriod] = useState(`${new Date().getFullYear()} - Current Year`);
  const [showReportDialog, setShowReportDialog] = useState(false);
  const [reportFormat, setReportFormat] = useState('excel');
  const [reportPeriodType, setReportPeriodType] = useState('all');
  const [reportCustomFrom, setReportCustomFrom] = useState('');
  const [reportCustomTo, setReportCustomTo] = useState('');

  const fetchDashboardData = async (period = `${new Date().getFullYear()} - Current Year`) => {
    try {
      setLoading(true);
      // Add period parameter to the API call
      const periodParam = period && period !== 'all' ? `&period=${period}` : '';
      // Add timestamp and cache control to prevent caching
      const response = await fetch(`${API}/dashboard-summary?t=${Date.now()}${periodParam}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        }
      });
      const data = await response.json();
      setDashboardData(data);
      console.log('Dashboard data fetched:', data.total_records, 'records');
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshStock = async () => {
    setRefreshingStock(true);
    try {
      const cacheBuster = new Date().getTime();
      const periodParam = dashboardPeriod && dashboardPeriod !== 'all' ? `&period=${dashboardPeriod}` : '';
      const response = await fetch(`${API}/dashboard-summary?t=${cacheBuster}${periodParam}`);
      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error("Error refreshing stock data:", error);
    } finally {
      setTimeout(() => setRefreshingStock(false), 500);
    }
  };

  const handlePeriodChange = (period) => {
    setDashboardPeriod(period);
    fetchDashboardData(period);
  };

  useEffect(() => {
    // Fetch with current year on initial load
    fetchDashboardData(`${new Date().getFullYear()} - Current Year`);
  }, []);

  const handleDataUpload = async () => {
    // Refresh dashboard data after upload
    console.log('Refreshing dashboard data...');
    await fetchDashboardData();
    console.log('Dashboard data refreshed');
  };

  const handleGenerateReport = async () => {
    let loadingToast;
    try {
      let url = `${API}/comprehensive-report?format=${reportFormat}`;
      
      if (reportPeriodType === 'all') {
        // No period filter - all data
      } else if (reportPeriodType === 'current') {
        url += `&period=${dashboardPeriod}`;
      } else if (reportPeriodType === 'custom') {
        if (!reportCustomFrom || !reportCustomTo) {
          alert('Please select both From and To dates');
          return;
        }
        url += `&from_date=${reportCustomFrom}&to_date=${reportCustomTo}`;
      } else {
        // Specific period selected
        url += `&period=${reportPeriodType}`;
      }
      
      // Show loading toast
      loadingToast = toast.loading('Generating report...');
      
      // Fetch the report as a blob
      const response = await fetch(url);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Report generation failed: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      
      // Create download link
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `URC101-Report-${reportPeriodType}.${reportFormat === 'excel' ? 'xlsx' : 'pdf'}`;
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(link);
      
      toast.success('Report downloaded successfully', { id: loadingToast });
      setShowReportDialog(false);
    } catch (error) {
      console.error('Report generation error:', error);
      toast.error(error.message || 'Failed to generate report', { id: loadingToast });
    } finally {
      // Ensure toast is always dismissed
      if (loadingToast) {
        toast.dismiss(loadingToast);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <Building2 className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">URC 101 Area</h1>
                <p className="text-gray-600">Sales Analytics Dashboard - Updated {new Date().toLocaleString()}</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    setReportFormat('excel');
                    setShowReportDialog(true);
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors shadow-md"
                >
                  <Download className="h-4 w-4" />
                  <span>Excel Report</span>
                </button>
                
                <button
                  onClick={() => {
                    setReportFormat('pdf');
                    setShowReportDialog(true);
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md"
                >
                  <FileSpreadsheet className="h-4 w-4" />
                  <span>PDF Report</span>
                </button>
                
                <div className="text-xs text-gray-500 mt-1">
                  v2.1 - Analytics Fixed
                </div>
              </div>
            </div>
          </div>
          
          {/* Quick Stats */}
          {dashboardData && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-gray-600 font-medium">
                        Total Revenue {dashboardData.data_from && <span className="text-xs">(from {dashboardData.data_from})</span>}
                      </p>
                      <p className="text-3xl font-bold text-green-600">
                        {formatIndianNumber(dashboardData.total_revenue || 0, true)}
                      </p>
                      <p className="text-base font-semibold text-green-500 mt-1">
                        Avg: {formatIndianNumber(dashboardData.avg_yearly_revenue || 0, true)}
                      </p>
                    </div>
                    <BarChart3 className="h-10 w-10 text-green-600" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-gray-600 font-medium">
                        Total Profit {dashboardData.data_from && <span className="text-xs">(from {dashboardData.data_from})</span>}
                      </p>
                      <p className="text-3xl font-bold text-blue-600">
                        {formatIndianNumber(dashboardData.total_profit || 0, true)}
                      </p>
                      <div className="flex items-center space-x-2 mt-1">
                        <p className="text-base font-semibold text-blue-500">
                          Avg: {formatIndianNumber(dashboardData.avg_yearly_profit || 0, true)}
                        </p>
                        <span className="text-sm text-blue-700 font-bold bg-blue-100 px-2 py-0.5 rounded">
                          {formatPercentage(dashboardData.profit_percentage || 0)}
                        </span>
                      </div>
                    </div>
                    <TrendingUp className="h-10 w-10 text-blue-600" />
                  </div>
                </CardContent>
              </Card>
              
              <Card className="relative">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-gray-600 font-medium">
                        Current Stock Value
                      </p>
                      <p className="text-3xl font-bold text-purple-600">
                        {formatIndianNumber(dashboardData.current_stock_value || 0, true)}
                      </p>
                      <p className="text-base font-semibold text-purple-500 mt-1">
                        Avg: {formatIndianNumber(dashboardData.avg_yearly_stock_value || 0, true)}
                      </p>
                    </div>
                    <FileSpreadsheet className="h-10 w-10 text-purple-600" />
                  </div>
                  <button
                    onClick={handleRefreshStock}
                    disabled={refreshingStock}
                    className="absolute bottom-2 right-2 p-1.5 rounded-full hover:bg-purple-50 transition-colors disabled:opacity-50"
                    title="Refresh stock value"
                  >
                    <RefreshCw className={`h-4 w-4 text-purple-600 ${refreshingStock ? 'animate-spin' : ''}`} />
                  </button>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-gray-600 font-medium">
                        C Category Stock
                      </p>
                      <p className="text-3xl font-bold text-orange-600">
                        {formatIndianNumber(dashboardData.c_category_stock_value || 0, true)}
                      </p>
                      <p className="text-base font-semibold text-orange-500 mt-1">
                        Avg: {formatIndianNumber(dashboardData.avg_yearly_c_stock_value || 0, true)}
                      </p>
                    </div>
                    <BarChart3 className="h-10 w-10 text-orange-600" />
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-7 mb-6 bg-gradient-to-r from-gray-100 to-gray-200 shadow-xl rounded-2xl p-2 border border-gray-300">
            <TabsTrigger 
              value="dashboard" 
              className="flex items-start px-2 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg hover:shadow-xl hover:from-blue-600 hover:to-blue-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <BarChart3 className="h-4 w-4 mt-0.5 mr-1.5 flex-shrink-0" />
              <span className="text-left leading-tight whitespace-normal">Daily Dashboard</span>
            </TabsTrigger>
            <TabsTrigger 
              value="financial" 
              className="flex items-start px-2 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-lg hover:shadow-xl hover:from-emerald-600 hover:to-emerald-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <DollarSign className="h-4 w-4 mt-0.5 mr-1.5 flex-shrink-0" />
              <span className="text-left leading-tight whitespace-normal">Daily Sales Report</span>
            </TabsTrigger>
            <TabsTrigger 
              value="analytics" 
              className="flex flex-col items-center justify-center px-1 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-lg hover:shadow-xl hover:from-purple-600 hover:to-purple-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <TrendingUp className="h-4 w-4 mb-1 flex-shrink-0" />
              <span className="text-center leading-tight break-words w-full px-1">Analytics</span>
            </TabsTrigger>
            <TabsTrigger 
              value="forecasting" 
              className="flex flex-col items-center justify-center px-1 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg hover:shadow-xl hover:from-orange-600 hover:to-orange-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <FileSpreadsheet className="h-4 w-4 mb-1 flex-shrink-0" />
              <span className="text-center leading-tight break-words w-full px-1">Forecast</span>
            </TabsTrigger>
            <TabsTrigger 
              value="upload" 
              className="flex flex-col items-center justify-center px-1 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-green-500 to-green-600 text-white shadow-lg hover:shadow-xl hover:from-green-600 hover:to-green-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <Upload className="h-4 w-4 mb-1 flex-shrink-0" />
              <span className="text-center leading-tight break-words w-full px-1">Bulk Upload</span>
            </TabsTrigger>
            <TabsTrigger 
              value="history" 
              className="flex flex-col items-center justify-center px-1 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-lg hover:shadow-xl hover:from-indigo-600 hover:to-indigo-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <Clock className="h-4 w-4 mb-1 flex-shrink-0" />
              <span className="text-center leading-tight break-words w-full px-1">History</span>
            </TabsTrigger>
            <TabsTrigger 
              value="database" 
              className="flex flex-col items-center justify-center px-1 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white shadow-lg hover:shadow-xl hover:from-cyan-600 hover:to-cyan-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <Database className="h-4 w-4 mb-1 flex-shrink-0" />
              <span className="text-center leading-tight break-words w-full px-1">Database</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <Dashboard 
              dashboardData={dashboardData} 
              loading={loading} 
              dashboardPeriod={dashboardPeriod}
              onPeriodChange={handlePeriodChange}
              onDataUpload={() => fetchDashboardData(dashboardPeriod)}
            />
          </TabsContent>

          <TabsContent value="upload" className="space-y-6">
            <DataUpload onUploadSuccess={handleDataUpload} />
          </TabsContent>

          <TabsContent value="history" className="space-y-6">
            <UploadHistory onDataChange={handleDataUpload} />
          </TabsContent>

          <TabsContent value="database" className="space-y-6">
            <DatabaseView />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <AnalyticsFixed />
          </TabsContent>

          <TabsContent value="forecasting" className="space-y-6">
            <Forecasting />
          </TabsContent>


          <TabsContent value="financial" className="space-y-6">
            <FinancialHealth onReportGenerated={fetchDashboardData} />
          </TabsContent>

        </Tabs>
      </div>

      {/* Report Generation Dialog */}
      {showReportDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Generate {reportFormat === 'excel' ? 'Excel' : 'PDF'} Report
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Period for Report:
                  </label>
                  
                  <div className="space-y-2">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        value="all"
                        checked={reportPeriodType === 'all'}
                        onChange={(e) => setReportPeriodType(e.target.value)}
                        className="form-radio h-4 w-4 text-blue-600"
                      />
                      <span>All Data (All periods till date)</span>
                    </label>
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        value="current"
                        checked={reportPeriodType === 'current'}
                        onChange={(e) => setReportPeriodType(e.target.value)}
                        className="form-radio h-4 w-4 text-blue-600"
                      />
                      <span>Current Period ({dashboardPeriod})</span>
                    </label>
                    
                    {dashboardData?.available_periods && dashboardData.available_periods.map((period) => (
                      <label key={period} className="flex items-center space-x-2 cursor-pointer">
                        <input
                          type="radio"
                          value={period}
                          checked={reportPeriodType === period}
                          onChange={(e) => setReportPeriodType(e.target.value)}
                          className="form-radio h-4 w-4 text-blue-600"
                        />
                        <span>{period}</span>
                      </label>
                    ))}
                    
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        value="custom"
                        checked={reportPeriodType === 'custom'}
                        onChange={(e) => setReportPeriodType(e.target.value)}
                        className="form-radio h-4 w-4 text-blue-600"
                      />
                      <span>Custom Date Range</span>
                    </label>
                    
                    {reportPeriodType === 'custom' && (
                      <div className="ml-6 mt-2 space-y-2">
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">From Date:</label>
                          <input
                            type="date"
                            value={reportCustomFrom}
                            onChange={(e) => setReportCustomFrom(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">To Date:</label>
                          <input
                            type="date"
                            value={reportCustomTo}
                            onChange={(e) => setReportCustomTo(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="flex space-x-3 mt-6">
                <button
                  onClick={handleGenerateReport}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  Generate Report
                </button>
                <button
                  onClick={() => setShowReportDialog(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      <Toaster />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainApp />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
