import React, { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";
import { Skeleton } from "./ui/skeleton";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from "recharts";
import { TrendingUp, TrendingDown, Package, AlertTriangle, Monitor, Smartphone, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { formatIndianNumber, formatTableNumber, formatPercentage } from "../utils/numberUtils";
import DailyUploadModal from "./DailyUploadModal";
import SalesTrendsChart from "./SalesTrendsChart";
import useDeviceDetect from '../hooks/useDeviceDetect';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'];

const Dashboard = ({ dashboardData, loading, dashboardPeriod, onPeriodChange, onDataUpload }) => {
  const [fastestItems, setFastestItems] = useState([]);
  const [groupAnalysis, setGroupAnalysis] = useState([]);
  const [inventoryAnalysis, setInventoryAnalysis] = useState(null);
  const [loadingData, setLoadingData] = useState(true);
  const [showDailyUploadModal, setShowDailyUploadModal] = useState(false);
  const [topSellersMetric, setTopSellersMetric] = useState('quantity'); // 'quantity', 'revenue', or 'profit'
  const [dailySalesTrend, setDailySalesTrend] = useState(null);
  const [availablePeriods, setAvailablePeriods] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const { isMobile, isTablet, isDesktop, screenWidth } = useDeviceDetect();
  const isMounted = useRef(false);

  useEffect(() => {
    fetchAvailablePeriods();
  }, []);

  useEffect(() => {
    if (!isMounted.current) {
      isMounted.current = true;
    }
    fetchAnalyticsData();
  }, [dashboardPeriod]);

  const fetchAvailablePeriods = async () => {
    try {
      const response = await fetch(`${API}/available-periods`);
      if (response.ok) {
        const data = await response.json();
        // Route returns {available_periods: [...], periods_detailed: [...], count: N}
        const periods = Array.isArray(data) ? data : (data.available_periods || []);
        setAvailablePeriods(periods);
      }
    } catch (error) {
      console.error("Error fetching available periods:", error);
    }
  };

  const fetchAnalyticsData = async () => {
    try {
      setLoadingData(true);
      
      // Build query parameter for period using prop from parent
      const periodParam = dashboardPeriod && dashboardPeriod !== 'all' ? `&period=${dashboardPeriod}` : '';
      
      const [fastestResponse, groupResponse, inventoryResponse, trendResponse] = await Promise.all([
        fetch(`${API}/fastest-selling-items?limit=10${periodParam}`),
        fetch(`${API}/group-analysis?period=${dashboardPeriod || 'all'}`),
        fetch(`${API}/inventory-analysis?period=${dashboardPeriod || 'all'}`),
        fetch(`${API}/daily-sales-trend?period=${dashboardPeriod || 'all'}`)
      ]);

      if (!fastestResponse.ok || !groupResponse.ok || !inventoryResponse.ok || !trendResponse.ok) {
        throw new Error('Failed to fetch analytics data');
      }

      const fastest = await fastestResponse.json();
      const groups = await groupResponse.json();
      const inventory = await inventoryResponse.json();
      const trend = await trendResponse.json();

      setFastestItems(fastest);
      setGroupAnalysis(groups);
      setInventoryAnalysis(inventory);
      setDailySalesTrend(trend);
    } catch (error) {
      console.error("Error fetching analytics data:", error);
      toast.error("Failed to load analytics data");
    } finally {
      setLoadingData(false);
    }
  };

  const handleManualRefresh = async () => {
    setRefreshing(true);
    toast.info("Refreshing dashboard data...");
    try {
      await fetchAnalyticsData();
      toast.success("Dashboard refreshed successfully!");
    } catch (error) {
      toast.error("Failed to refresh dashboard");
    } finally {
      setTimeout(() => setRefreshing(false), 500);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-48" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-64 w-full" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-48" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-64 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (loadingData) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Loading analytics data...</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  const groupChartData = groupAnalysis.map(group => ({
    name: group.group.replace('Group ', ''),
    revenue: group.total_revenue || 0,
    profit: group.total_profit || 0,
    items: group.item_count || 0
  }));

  // Filter items based on selected metric to exclude zero/negative values
  const filteredItems = fastestItems.filter(item => {
    if (topSellersMetric === 'quantity') {
      return (item.total_sold || 0) > 0;
    } else if (topSellersMetric === 'revenue') {
      return (item.total_revenue || 0) > 0;
    } else {
      return (item.total_profit || 0) > 0;
    }
  });

  // Sort items based on selected metric
  const sortedItems = [...filteredItems].sort((a, b) => {
    if (topSellersMetric === 'quantity') {
      return (b.total_sold || 0) - (a.total_sold || 0);
    } else if (topSellersMetric === 'revenue') {
      return (b.total_revenue || 0) - (a.total_revenue || 0);
    } else {
      return (b.total_profit || 0) - (a.total_profit || 0);
    }
  });

  const topItemsData = sortedItems.slice(0, 8).map(item => ({
    name: item.item_name.substring(0, 20) + (item.item_name.length > 20 ? '...' : ''),
    sold: item.total_sold || 0,
    revenue: item.total_revenue || 0,
    profit: item.total_profit || 0
  }));

  // Debug log
  console.log('Top Sellers Metric:', topSellersMetric);
  console.log('Filtered Items Count:', filteredItems.length);
  console.log('Top Items Data:', topItemsData);
  console.log('Sample top item:', topItemsData[0]);

  return (
    <div className="space-y-6">
      {/* Device Indicator - Only visible in dev mode, can be removed */}
      {process.env.NODE_ENV === 'development' && (
        <div className={`fixed top-20 right-4 z-50 px-3 py-2 rounded-lg shadow-lg text-xs font-semibold ${
          isMobile ? 'bg-green-500 text-white' : 
          isTablet ? 'bg-yellow-500 text-white' : 
          'bg-blue-500 text-white'
        }`}>
          {isMobile && <Smartphone className="inline w-3 h-3 mr-1" />}
          {isDesktop && <Monitor className="inline w-3 h-3 mr-1" />}
          {isMobile ? 'Mobile' : isTablet ? 'Tablet' : 'Desktop'} ({screenWidth}px)
        </div>
      )}

      {/* Upload Today's Data Button - Responsive */}
      <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white border-none">
        <CardContent className={isMobile ? "p-4" : "p-6"}>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex-1">
              <h2 className={`font-bold mb-2 ${isMobile ? 'text-lg' : 'text-2xl'}`}>
                Upload Today's Sales Data
              </h2>
              {!isMobile && (
                <p className="text-blue-50 text-sm">
                  Upload your daily sales report for {new Date().toLocaleDateString('en-IN', { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  })}
                </p>
              )}
            </div>
            <button
              onClick={() => setShowDailyUploadModal(true)}
              className={`bg-white text-blue-600 rounded-lg font-bold hover:bg-blue-50 transition-colors shadow-lg flex items-center ${
                isMobile ? 'w-full justify-center px-4 py-3 text-base space-x-2' : 'px-8 py-4 text-lg space-x-2'
              }`}
              data-testid="upload-today-button"
            >
              <svg className={isMobile ? "w-5 h-5" : "w-6 h-6"} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span>{isMobile ? 'Upload Data' : 'Upload Today\'s Data'}</span>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Period Filter Dropdown */}
      {availablePeriods.length > 0 && (
        <Card className="bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200">
          <CardContent className={isMobile ? "p-4" : "p-6"}>
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex-1">
                <h3 className={`font-bold text-gray-800 ${isMobile ? 'text-base' : 'text-lg'}`}>
                  Filter by Period
                </h3>
                {!isMobile && (
                  <p className="text-gray-600 text-sm mt-1">
                    View dashboard data for a specific time period
                  </p>
                )}
              </div>
              <div className={`flex items-center gap-3 ${isMobile ? 'w-full' : ''}`}>
                <label className="text-sm font-medium text-gray-700">Period:</label>
                <select
                  value={dashboardPeriod}
                  onChange={(e) => onPeriodChange(e.target.value)}
                  className={`border border-gray-300 rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white ${
                    isMobile ? 'flex-1 px-4 py-3 text-base' : 'px-4 py-2 text-sm min-w-[200px]'
                  }`}
                  data-testid="dashboard-period-filter"
                >
                  <option value="all">All Periods</option>
                  {availablePeriods.map((period) => (
                    <option key={period} value={period}>
                      {period}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleManualRefresh}
                  disabled={refreshing}
                  className={`flex items-center space-x-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed ${
                    isMobile ? 'px-4 py-3 text-sm' : 'px-4 py-2 text-sm'
                  }`}
                  title="Refresh dashboard data"
                >
                  <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                  {!isMobile && <span>Refresh</span>}
                </button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Enhanced Daily Sales Trends Chart */}
      <SalesTrendsChart />

      {/* Group Performance Charts */}
      <div className={`grid gap-6 ${isMobile ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
        <Card>
          <CardHeader>
            <CardTitle className={`flex items-center space-x-2 ${isMobile ? 'text-base' : ''}`}>
              <TrendingUp className={isMobile ? "h-4 w-4" : "h-5 w-5"} />
              <span>Group-wise Revenue & Profit</span>
            </CardTitle>
            {!isMobile && (
              <CardDescription>
                This chart compares revenue (blue bars) and profit (green bars) across all product groups. 
                It helps identify which groups contribute most to business growth and profitability.
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={isMobile ? 250 : 300}>
              <BarChart data={groupChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: isMobile ? 10 : 12 }} />
                <YAxis tick={{ fontSize: isMobile ? 10 : 12 }} />
                <Tooltip formatter={(value, name) => [
                  `₹${formatTableNumber(value)}`,
                  name === 'revenue' ? 'Revenue' : 'Profit'
                ]} />
                {!isMobile && <Legend />}
                <Bar dataKey="revenue" fill="#3B82F6" name="revenue" />
                <Bar dataKey="profit" fill="#10B981" name="profit" />
              </BarChart>
            </ResponsiveContainer>
            {isMobile && (
              <div className="flex justify-center gap-4 mt-2 text-xs">
                <span className="flex items-center"><span className="w-3 h-3 bg-blue-500 rounded mr-1"></span>Revenue</span>
                <span className="flex items-center"><span className="w-3 h-3 bg-green-500 rounded mr-1"></span>Profit</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Package className="h-5 w-5" />
              <span>Group Distribution</span>
            </CardTitle>
            <CardDescription>
              This pie chart shows the revenue contribution of each product group as a percentage of total sales. 
              Larger slices indicate groups that generate more revenue for the business.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={groupChartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="revenue"
                >
                  {groupChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [`₹${formatTableNumber(value)}`, 'Revenue']} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Top Selling Items */}
      <Card>
        <CardHeader>
          <div className={`flex ${isMobile ? 'flex-col space-y-3' : 'items-center justify-between'}`}>
            <div>
              <CardTitle className={`flex items-center space-x-2 ${isMobile ? 'text-base' : ''}`}>
                <TrendingUp className={isMobile ? "h-4 w-4" : "h-5 w-5"} />
                <span>Top Selling Items</span>
              </CardTitle>
              {!isMobile && (
                <CardDescription>Best performing items by selected metric</CardDescription>
              )}
            </div>
            <div className={`flex items-center ${isMobile ? 'w-full' : 'space-x-2'}`}>
              {!isMobile && <span className="text-sm text-gray-600">View by:</span>}
              <select
                value={topSellersMetric}
                onChange={(e) => setTopSellersMetric(e.target.value)}
                className={`border border-gray-300 rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isMobile ? 'w-full px-4 py-3 text-base' : 'px-3 py-2 text-sm'
                }`}
                data-testid="top-sellers-metric-selector"
              >
                <option value="quantity">Quantity Sold</option>
                <option value="revenue">Revenue</option>
                <option value="profit">Profit</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {topItemsData && topItemsData.length > 0 ? (
            <div className={isMobile ? "space-y-2" : "space-y-3"}>
              {topItemsData.map((item, index) => {
                const displayValue = topSellersMetric === 'quantity' 
                  ? item.sold 
                  : topSellersMetric === 'revenue' 
                  ? item.revenue 
                  : item.profit;
                
                const formattedValue = topSellersMetric === 'quantity'
                  ? `${formatTableNumber(displayValue)} units`
                  : formatIndianNumber(displayValue, true);

                return (
                  <div 
                    key={index}
                    className={`flex items-center justify-between rounded-lg border-2 ${
                      isMobile ? 'p-3' : 'p-4'
                    } ${
                      topSellersMetric === 'quantity' ? 'bg-blue-50 border-blue-200' :
                      topSellersMetric === 'revenue' ? 'bg-green-50 border-green-200' :
                      'bg-orange-50 border-orange-200'
                    }`}
                  >
                    <div className={`flex items-center flex-1 ${isMobile ? 'space-x-2' : 'space-x-4'}`}>
                      <span className={`font-bold rounded ${
                        isMobile ? 'text-sm px-2 py-1' : 'text-lg px-3 py-1'
                      } ${
                        topSellersMetric === 'quantity' ? 'bg-blue-600 text-white' :
                        topSellersMetric === 'revenue' ? 'bg-green-600 text-white' :
                        'bg-orange-600 text-white'
                      }`}>
                        #{index + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className={`font-semibold text-gray-900 ${isMobile ? 'text-sm truncate' : ''}`}>
                          {item.name}
                        </p>
                        {!isMobile && (
                          <p className="text-sm text-gray-600">
                            {topSellersMetric === 'quantity' && `Revenue: ${formatIndianNumber(item.revenue, true)} | Profit: ${formatIndianNumber(item.profit, true)}`}
                            {topSellersMetric === 'revenue' && `Quantity: ${formatTableNumber(item.sold)} units | Profit: ${formatIndianNumber(item.profit, true)}`}
                            {topSellersMetric === 'profit' && `Quantity: ${formatTableNumber(item.sold)} units | Revenue: ${formatIndianNumber(item.revenue, true)}`}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="text-right ml-2">
                      <p className={`font-bold ${
                        isMobile ? 'text-base' : 'text-2xl'
                      } ${
                        topSellersMetric === 'quantity' ? 'text-blue-700' :
                        topSellersMetric === 'revenue' ? 'text-green-700' :
                        'text-orange-700'
                      }`}>
                        {isMobile ? (
                          topSellersMetric === 'quantity' ? formatTableNumber(displayValue) : 
                          `₹${(displayValue/1000).toFixed(0)}k`
                        ) : formattedValue}
                      </p>
                      {!isMobile && (
                        <p className="text-xs text-gray-500">
                          {topSellersMetric === 'quantity' ? 'Units Sold' :
                           topSellersMetric === 'revenue' ? 'Revenue' : 'Profit'}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className={`flex items-center justify-center text-gray-500 ${isMobile ? 'h-32 text-sm' : 'h-64'}`}>
              <p>No data available for {topSellersMetric}. Try selecting a different metric.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Inventory Alerts */}
      {inventoryAnalysis && (
        <div className={`grid gap-6 ${isMobile ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-3'}`}>
          <Card>
            <CardHeader>
              <CardTitle className={`flex items-center space-x-2 text-red-600 ${isMobile ? 'text-base' : ''}`}>
                <AlertTriangle className={isMobile ? "h-4 w-4" : "h-5 w-5"} />
                <span>Dead Inventory</span>
              </CardTitle>
              {!isMobile && <CardDescription>Items with no sales</CardDescription>}
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {inventoryAnalysis.dead_inventory?.slice(0, 5).map((item, index) => (
                  <div key={index} className="p-3 bg-red-50 rounded-lg border border-red-200">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-xs bg-red-600 text-white px-2 py-1 rounded font-bold">#{index + 1}</span>
                    </div>
                    <p className="font-medium text-red-800 text-sm">
                      {item._id?.pluno || 'N/A'} - {item._id?.item_name || 'Unknown Item'}
                    </p>
                    <p className="text-red-600 text-xs">
                      Avg Cost: ₹{(item.avg_cost || 0).toFixed(2)}
                    </p>
                  </div>
                )) || <p className="text-gray-500 text-sm">No dead inventory found</p>}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className={`flex items-center space-x-2 text-orange-600 ${isMobile ? 'text-base' : ''}`}>
                <TrendingDown className={isMobile ? "h-4 w-4" : "h-5 w-5"} />
                <span>Slow Moving</span>
              </CardTitle>
              {!isMobile && <CardDescription>Items with low sales velocity</CardDescription>}
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {inventoryAnalysis.slow_moving?.slice(0, 5).map((item, index) => (
                  <div key={index} className="p-3 bg-orange-50 rounded-lg border border-orange-200">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-xs bg-orange-600 text-white px-2 py-1 rounded font-bold">#{index + 1}</span>
                    </div>
                    <p className="font-medium text-orange-800 text-sm">
                      {item._id?.pluno || 'N/A'} - {item._id?.item_name || 'Unknown Item'}
                    </p>
                    <p className="text-orange-600 text-xs">
                      Monthly Avg: {(item.avg_monthly_sales || 0).toFixed(1)} units
                    </p>
                    <p className="text-orange-600 text-xs">
                      Total Sold: {item.total_sold || 0}
                    </p>
                  </div>
                )) || <p className="text-gray-500 text-sm">No slow moving items found</p>}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className={`flex items-center space-x-2 text-yellow-600 ${isMobile ? 'text-base' : ''}`}>
                <Package className={isMobile ? "h-4 w-4" : "h-5 w-5"} />
                <span>{isMobile ? 'High Cost Items' : 'High Cost, Poor Performance'}</span>
              </CardTitle>
              {!isMobile && <CardDescription>Expensive items with low sales</CardDescription>}
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {inventoryAnalysis.high_cost_poor_performance?.slice(0, 5).map((item, index) => (
                  <div key={index} className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-xs bg-yellow-600 text-white px-2 py-1 rounded font-bold">#{index + 1}</span>
                    </div>
                    <p className="font-medium text-yellow-800 text-sm">
                      {item._id?.pluno || 'N/A'} - {item._id?.item_name || 'Unknown Item'}
                    </p>
                    <p className="text-yellow-600 text-xs">
                      Avg Cost: ₹{(item.avg_cost || 0).toFixed(2)}
                    </p>
                    <p className="text-yellow-600 text-xs">
                      Performance: {(item.performance_ratio || 0).toFixed(2)}
                    </p>
                  </div>
                )) || <p className="text-gray-500 text-sm">No items found</p>}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Group Performance Table */}
      <Card>
        <CardHeader>
          <CardTitle>Group Performance Summary</CardTitle>
          <CardDescription>Detailed performance metrics by product group</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-3 font-semibold">#</th>
                  <th className="text-left p-3 font-semibold">Group</th>
                  <th className="text-left p-3 font-semibold">Items</th>
                  <th className="text-left p-3 font-semibold">Revenue</th>
                  <th className="text-left p-3 font-semibold">Profit</th>
                  <th className="text-left p-3 font-semibold">Margin</th>
                  <th className="text-left p-3 font-semibold">Top Performer</th>
                </tr>
              </thead>
              <tbody>
                {groupAnalysis.map((group, index) => (
                  <tr key={index} className="border-b hover:bg-gray-50">
                    <td className="p-3">
                      <span className="text-sm bg-blue-600 text-white px-2 py-1 rounded font-bold">#{index + 1}</span>
                    </td>
                    <td className="p-3">
                      <Badge variant="outline">{group.group}</Badge>
                    </td>
                    <td className="p-3">{group.item_count}</td>
                    <td className="p-3 font-medium text-green-600">
                      ₹{formatTableNumber(group.total_revenue || 0)}
                    </td>
                    <td className="p-3 font-medium text-blue-600">
                      ₹{formatTableNumber(group.total_profit || 0)}
                    </td>
                    <td className="p-3">
                      <span className={`font-medium ${
                        (group.profit_margin || 0) > 20 ? 'text-green-600' : 
                        (group.profit_margin || 0) > 10 ? 'text-orange-600' : 'text-red-600'
                      }`}>
                        {formatPercentage(group.profit_margin || 0)}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className="text-sm text-gray-600">
                        {group.top_performers?.[0]?.item_name?.substring(0, 30) || 'N/A'}
                        {group.top_performers?.[0]?.item_name?.length > 30 ? '...' : ''}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Daily Upload Modal */}
      <DailyUploadModal
        isOpen={showDailyUploadModal}
        onClose={() => setShowDailyUploadModal(false)}
        onSuccess={() => {
          // Refresh dashboard analytics data
          fetchAnalyticsData();
          // Refresh parent summary cards
          if (onDataUpload) {
            onDataUpload();
          }
          toast.success("Dashboard data refreshed!");
        }}
      />
    </div>
  );
};

export default Dashboard;
