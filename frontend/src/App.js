import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import "./App.css";
import Dashboard from "./components/Dashboard";
import DataUpload from "./components/DataUpload";
import DataSummaries from "./components/DataSummaries";
import AnalyticsFixed from "./components/AnalyticsFixed";
import Forecasting from "./components/Forecasting";
import UploadHistory from "./components/UploadHistory";
import DatabaseView from "./components/DatabaseView";
import FinancialHealth from "./components/FinancialHealth";
import ChatBot from "./components/ChatBot";
import CustomerBot from "./components/CustomerBot";
import DemandAnalytics from "./components/DemandAnalytics";
import { Toaster, toast } from "./components/ui/sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { BarChart3, Upload, TrendingUp, FileSpreadsheet, Building2, Download, Clock, Database, DollarSign, RefreshCw, Layers, ShoppingCart } from "lucide-react";
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
  const [selectedPeriods, setSelectedPeriods] = useState([]);
  const [availablePeriods, setAvailablePeriods] = useState([]);

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
      
      // Extract and set available periods
      if (data.available_periods && data.available_periods.length > 0) {
        setAvailablePeriods(data.available_periods);
      }
      
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
      // Validate that at least one period is selected
      if (selectedPeriods.length === 0) {
        toast.error('Please select at least one period for the report');
        return;
      }
      
      let url = `${API}/comprehensive-report?format=${reportFormat}`;
      
      // Add selected periods as comma-separated list
      if (selectedPeriods.length > 0) {
        url += `&periods=${selectedPeriods.join(',')}`;
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
      
      // Create download filename based on selected periods
      let filename = 'URC101-Report';
      if (selectedPeriods.length === availablePeriods.length) {
        filename += '-AllPeriods';
      } else if (selectedPeriods.length === 1) {
        filename += `-${selectedPeriods[0]}`;
      } else {
        filename += `-${selectedPeriods.length}Periods`;
      }
      filename += `.${reportFormat === 'excel' ? 'xlsx' : 'pdf'}`;
      
      // Create download link
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
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
                  onClick={async () => {
                    setReportFormat('excel');
                    // Fetch available periods
                    try {
                      const response = await fetch(`${API}/available-periods`);
                      const data = await response.json();
                      if (data.periods_detailed && data.periods_detailed.length > 0) {
                        setAvailablePeriods(data.periods_detailed);
                        // Select all periods by default (store values for API call)
                        setSelectedPeriods(data.periods_detailed.map(p => p.value));
                      }
                    } catch (error) {
                      console.error('Error fetching available periods:', error);
                    }
                    setShowReportDialog(true);
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors shadow-md"
                >
                  <Download className="h-4 w-4" />
                  <span>Excel Report</span>
                </button>
                
                <button
                  onClick={async () => {
                    setReportFormat('pdf');
                    // Fetch available periods
                    try {
                      const response = await fetch(`${API}/available-periods`);
                      const data = await response.json();
                      if (data.periods_detailed && data.periods_detailed.length > 0) {
                        setAvailablePeriods(data.periods_detailed);
                        // Select all periods by default (store values for API call)
                        setSelectedPeriods(data.periods_detailed.map(p => p.value));
                      }
                    } catch (error) {
                      console.error('Error fetching available periods:', error);
                    }
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
          <TabsList className="grid w-full grid-cols-8 mb-6 bg-gradient-to-r from-gray-100 to-gray-200 shadow-xl rounded-2xl p-2 border border-gray-300">
            <TabsTrigger 
              value="dashboard" 
              className="flex items-start px-2 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg hover:shadow-xl hover:from-blue-600 hover:to-blue-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <BarChart3 className="h-4 w-4 mt-0.5 mr-1.5 flex-shrink-0" />
              <span className="text-left leading-tight whitespace-normal">Daily Upload Dashboard</span>
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
              className="flex items-start px-2 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-lg hover:shadow-xl hover:from-purple-600 hover:to-purple-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <TrendingUp className="h-4 w-4 mt-0.5 mr-1.5 flex-shrink-0" />
              <span className="text-left leading-tight whitespace-normal">Detailed Analytics</span>
            </TabsTrigger>
            <TabsTrigger 
              value="demand" 
              className="flex items-start px-2 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-pink-500 to-pink-600 text-white shadow-lg hover:shadow-xl hover:from-pink-600 hover:to-pink-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <ShoppingCart className="h-4 w-4 mt-0.5 mr-1.5 flex-shrink-0" />
              <span className="text-left leading-tight whitespace-normal">Demand Analytics</span>
            </TabsTrigger>
            <TabsTrigger 
              value="forecasting" 
              className="flex items-start px-2 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg hover:shadow-xl hover:from-orange-600 hover:to-orange-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <FileSpreadsheet className="h-4 w-4 mt-0.5 mr-1.5 flex-shrink-0" />
              <span className="text-left leading-tight whitespace-normal">Forecast</span>
            </TabsTrigger>
            <TabsTrigger 
              value="upload" 
              className="flex items-start px-2 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-green-500 to-green-600 text-white shadow-lg hover:shadow-xl hover:from-green-600 hover:to-green-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <Upload className="h-4 w-4 mt-0.5 mr-1.5 flex-shrink-0" />
              <span className="text-left leading-tight whitespace-normal">Bulk Data Upload</span>
            </TabsTrigger>
            <TabsTrigger 
              value="history" 
              className="flex items-start px-2 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-lg hover:shadow-xl hover:from-indigo-600 hover:to-indigo-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <Clock className="h-4 w-4 mt-0.5 mr-1.5 flex-shrink-0" />
              <span className="text-left leading-tight whitespace-normal">Upload History</span>
            </TabsTrigger>
            <TabsTrigger 
              value="database" 
              className="flex items-start px-2 py-2 rounded-xl font-semibold text-xs transition-all duration-300 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white shadow-lg hover:shadow-xl hover:from-cyan-600 hover:to-cyan-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100 min-h-[60px]"
            >
              <Database className="h-4 w-4 mt-0.5 mr-1.5 flex-shrink-0" />
              <span className="text-left leading-tight whitespace-normal">Database View</span>
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
            {/* Sub-tabs for Bulk Upload section */}
            <Tabs defaultValue="upload-data" className="w-full">
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl shadow-sm border border-blue-100 p-3 mb-6">
                <TabsList className="grid w-full max-w-lg grid-cols-2 bg-white/80 p-1.5 rounded-lg shadow-inner">
                  <TabsTrigger 
                    value="upload-data" 
                    className="flex items-center justify-center space-x-2 py-3 px-4 text-gray-600 data-[state=active]:bg-blue-600 data-[state=active]:text-white data-[state=active]:shadow-md rounded-md transition-all duration-200 font-medium"
                  >
                    <Upload className="h-4 w-4" />
                    <span>Upload Data</span>
                  </TabsTrigger>
                  <TabsTrigger 
                    value="data-summaries" 
                    className="flex items-center justify-center space-x-2 py-3 px-4 text-gray-600 data-[state=active]:bg-blue-600 data-[state=active]:text-white data-[state=active]:shadow-md rounded-md transition-all duration-200 font-medium"
                  >
                    <Layers className="h-4 w-4" />
                    <span>Data Summaries</span>
                  </TabsTrigger>
                </TabsList>
              </div>
              
              <TabsContent value="upload-data">
                <DataUpload onUploadSuccess={handleDataUpload} />
              </TabsContent>
              
              <TabsContent value="data-summaries">
                <DataSummaries onSummaryChange={handleDataUpload} />
              </TabsContent>
            </Tabs>
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

          <TabsContent value="demand" className="space-y-6">
            <DemandAnalytics />
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
                  <div className="flex items-center justify-between mb-3">
                    <label className="block text-sm font-medium text-gray-700">
                      Select Periods for Report:
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        if (selectedPeriods.length === availablePeriods.length) {
                          setSelectedPeriods([]);
                        } else {
                          setSelectedPeriods(availablePeriods.map(p => p.value));
                        }
                      }}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {selectedPeriods.length === availablePeriods.length ? 'Deselect All' : 'Select All'}
                    </button>
                  </div>
                  
                  <div className="space-y-2 max-h-60 overflow-y-auto border border-gray-200 rounded-lg p-3">
                    {availablePeriods.length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-4">No data available. Please upload data first.</p>
                    ) : (
                      availablePeriods.map((period) => (
                        <label key={period.value} className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded">
                          <input
                            type="checkbox"
                            checked={selectedPeriods.includes(period.value)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedPeriods([...selectedPeriods, period.value]);
                              } else {
                                setSelectedPeriods(selectedPeriods.filter(p => p !== period.value));
                              }
                            }}
                            className="form-checkbox h-4 w-4 text-blue-600 rounded"
                          />
                          <span className="text-sm">{period.label}</span>
                        </label>
                      ))
                    )}
                  </div>
                  
                  {selectedPeriods.length > 0 && (
                    <p className="text-xs text-gray-600 mt-2">
                      {selectedPeriods.length} period{selectedPeriods.length !== 1 ? 's' : ''} selected
                    </p>
                  )}
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
      
      {/* AI Chatbot */}
      <ChatBot />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainApp />} />
        <Route path="/sandy" element={<CustomerBot />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
