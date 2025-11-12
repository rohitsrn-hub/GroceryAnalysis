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
import { Toaster } from "./components/ui/sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { BarChart3, Upload, TrendingUp, FileSpreadsheet, Building2, Download, Clock, Database, DollarSign } from "lucide-react";
import { formatIndianNumber, formatPercentage } from "./utils/numberUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function MainApp() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      // Add timestamp and cache control to prevent caching
      const response = await fetch(`${API}/dashboard-summary?t=${Date.now()}`, {
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

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleDataUpload = async () => {
    // Refresh dashboard data after upload
    console.log('Refreshing dashboard data...');
    await fetchDashboardData();
    console.log('Dashboard data refreshed');
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
                    const link = document.createElement('a');
                    link.href = `${API}/comprehensive-report?format=excel`;
                    link.download = 'URC101-Comprehensive-Analysis-Report.xlsx';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors shadow-md"
                >
                  <Download className="h-4 w-4" />
                  <span>Excel Report</span>
                </button>
                
                <button
                  onClick={() => {
                    const link = document.createElement('a');
                    link.href = `${API}/comprehensive-report?format=pdf`;
                    link.download = 'URC101-Comprehensive-Analysis-Report.html';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
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
                    <div>
                      <p className="text-sm text-gray-600 font-medium">Total Revenue</p>
                      <p className="text-4xl font-bold text-green-600">
                        {formatIndianNumber(dashboardData.total_revenue || 0, true)}
                      </p>
                    </div>
                    <BarChart3 className="h-10 w-10 text-green-600" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600 font-medium">Total Profit</p>
                      <p className="text-4xl font-bold text-blue-600">
                        {formatIndianNumber(dashboardData.total_profit || 0, true)}
                      </p>
                    </div>
                    <TrendingUp className="h-10 w-10 text-blue-600" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600 font-medium">Items Sold</p>
                      <p className="text-4xl font-bold text-purple-600">
                        {formatIndianNumber(dashboardData.total_items_sold || 0)}
                      </p>
                    </div>
                    <FileSpreadsheet className="h-10 w-10 text-purple-600" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600 font-medium">Profit Margin</p>
                      <p className="text-4xl font-bold text-orange-600">
                        {formatPercentage(dashboardData.profit_margin || 0)}
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
          <TabsList className="grid w-full grid-cols-7 mb-6 bg-gradient-to-r from-gray-100 to-gray-200 shadow-xl rounded-2xl p-3 border border-gray-300">
            <TabsTrigger 
              value="dashboard" 
              className="flex items-center space-x-2 px-4 py-4 rounded-xl font-bold transition-all duration-300 bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg hover:shadow-xl hover:from-blue-600 hover:to-blue-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100"
            >
              <BarChart3 className="h-5 w-5" />
              <span>Dashboard</span>
            </TabsTrigger>
            <TabsTrigger 
              value="upload" 
              className="flex items-center space-x-2 px-4 py-4 rounded-xl font-bold transition-all duration-300 bg-gradient-to-r from-green-500 to-green-600 text-white shadow-lg hover:shadow-xl hover:from-green-600 hover:to-green-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100"
            >
              <Upload className="h-5 w-5" />
              <span>Historical Data</span>
            </TabsTrigger>
            <TabsTrigger 
              value="history" 
              className="flex items-center space-x-2 px-4 py-4 rounded-xl font-bold transition-all duration-300 bg-gradient-to-r from-indigo-500 to-indigo-600 text-white shadow-lg hover:shadow-xl hover:from-indigo-600 hover:to-indigo-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100"
            >
              <Clock className="h-5 w-5" />
              <span>Upload History</span>
            </TabsTrigger>
            <TabsTrigger 
              value="database" 
              className="flex items-center space-x-2 px-4 py-4 rounded-xl font-bold transition-all duration-300 bg-gradient-to-r from-cyan-500 to-cyan-600 text-white shadow-lg hover:shadow-xl hover:from-cyan-600 hover:to-cyan-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100"
            >
              <Database className="h-5 w-5" />
              <span>Database View</span>
            </TabsTrigger>
            <TabsTrigger 
              value="analytics" 
              className="flex items-center space-x-2 px-4 py-4 rounded-xl font-bold transition-all duration-300 bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-lg hover:shadow-xl hover:from-purple-600 hover:to-purple-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100"
            >
              <TrendingUp className="h-5 w-5" />
              <span>Analytics</span>
            </TabsTrigger>
            <TabsTrigger 
              value="forecasting" 
              className="flex items-center space-x-2 px-4 py-4 rounded-xl font-bold transition-all duration-300 bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg hover:shadow-xl hover:from-orange-600 hover:to-orange-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100"
            >
              <FileSpreadsheet className="h-5 w-5" />
              <span>Forecasting</span>
            </TabsTrigger>
            <TabsTrigger 
              value="financial" 
              className="flex items-center space-x-2 px-4 py-4 rounded-xl font-bold transition-all duration-300 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-lg hover:shadow-xl hover:from-emerald-600 hover:to-emerald-700 transform hover:scale-105 data-[state=active]:from-gray-300 data-[state=active]:to-gray-400 data-[state=active]:text-gray-700 data-[state=active]:shadow-inner data-[state=active]:scale-100"
            >
              <DollarSign className="h-5 w-5" />
              <span>Financial Health</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <Dashboard dashboardData={dashboardData} loading={loading} />
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
            <FinancialHealth />
          </TabsContent>

        </Tabs>
      </div>
      
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
