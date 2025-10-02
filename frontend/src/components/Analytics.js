import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Badge } from "./ui/badge";
import { Skeleton } from "./ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, ScatterChart, Scatter, PieChart, Pie, Cell } from "recharts";
import { TrendingUp, TrendingDown, Package, AlertTriangle, Filter, RefreshCw, Calendar, BarChart3, Download } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'];

const Analytics = () => {
  const [fastestItems, setFastestItems] = useState([]);
  const [groupAnalysis, setGroupAnalysis] = useState([]);
  const [inventoryAnalysis, setInventoryAnalysis] = useState(null);
  const [abcAnalysis, setAbcAnalysis] = useState(null);
  const [capitalAnalysis, setCapitalAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState('all');
  const [selectedPeriod, setSelectedPeriod] = useState('all');
  const [activeTab, setActiveTab] = useState('performance');

  const exportToExcel = async (analysisType) => {
    try {
      const groupParam = selectedGroup !== 'all' ? `?group=${selectedGroup}` : '';
      const response = await fetch(`${API}/export-data/${analysisType}${groupParam}`);
      
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${analysisType}-analysis-${selectedGroup || 'all'}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success(`${analysisType} analysis exported successfully`);
    } catch (error) {
      console.error('Export error:', error);
      toast.error('Failed to export data');
    }
  };

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      
      const [fastestResponse, groupResponse, inventoryResponse, abcResponse, capitalResponse] = await Promise.all([
        fetch(`${API}/fastest-selling-items?limit=20`),
        fetch(`${API}/group-analysis`),
        fetch(`${API}/inventory-analysis`),
        fetch(`${API}/abc-analysis${selectedGroup !== 'all' ? `?group=${selectedGroup}` : ''}`),
        fetch(`${API}/capital-blocking-analysis${selectedGroup !== 'all' ? `?group=${selectedGroup}` : ''}`)
      ]);

      if (!fastestResponse.ok || !groupResponse.ok || !inventoryResponse.ok) {
        throw new Error('Failed to fetch analytics data');
      }

      const fastest = await fastestResponse.json();
      const groups = await groupResponse.json();
      const inventory = await inventoryResponse.json();
      const abc = await abcResponse.json();
      const capital = await capitalResponse.json();

      setFastestItems(fastest);
      setGroupAnalysis(groups);
      setInventoryAnalysis(inventory);
      setAbcAnalysis(abc);
      setCapitalAnalysis(capital);
    } catch (error) {
      console.error("Error fetching analytics data:", error);
      toast.error("Failed to load analytics data");
    } finally {
      setLoading(false);
    }
  };

  const filteredFastestItems = fastestItems.filter(item => 
    selectedGroup === 'all' || item.group === selectedGroup
  );

  const filteredGroupAnalysis = groupAnalysis.filter(group =>
    selectedGroup === 'all' || group.group === selectedGroup
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  const performanceChartData = filteredFastestItems.slice(0, 15).map(item => ({
    name: `${item.item_code || 'N/A'} - ${item.item_name.substring(0, 20)}${item.item_name.length > 20 ? '...' : ''}`,
    shortName: item.item_code || 'N/A',
    fullName: item.item_name,
    itemCode: item.item_code,
    sold: item.total_sold,
    avgSales: item.avg_monthly_sales,
    revenue: item.total_revenue || 0,
    group: item.group
  }));

  const seasonalData = filteredFastestItems.slice(0, 5).map(item => {
    const patterns = Object.entries(item.seasonal_pattern || {}).map(([period, value]) => ({
      period,
      value,
      itemName: item.item_name.substring(0, 20)
    }));
    return patterns;
  }).flat();

  const profitabilityData = filteredGroupAnalysis.map(group => ({
    group: group.group.replace('Group ', ''),
    revenue: group.total_revenue || 0,
    profit: group.total_profit || 0,
    margin: group.profit_margin || 0,
    items: group.item_count || 0
  }));

  const inventoryIssues = [
    ...(inventoryAnalysis?.dead_inventory || []).map(item => ({
      ...item,
      type: 'Dead Inventory',
      severity: 'high',
      color: 'red'
    })),
    ...(inventoryAnalysis?.slow_moving || []).slice(0, 10).map(item => ({
      ...item,
      type: 'Slow Moving',
      severity: 'medium',
      color: 'orange'
    })),
    ...(inventoryAnalysis?.high_cost_poor_performance || []).slice(0, 10).map(item => ({
      ...item,
      type: 'High Cost/Poor Performance',
      severity: 'medium',
      color: 'yellow'
    }))
  ];

  return (
    <div className="space-y-6">
      {/* Analytics Header with Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center space-x-2">
              <TrendingUp className="h-6 w-6" />
              <span>Advanced Analytics</span>
            </span>
            <Button variant="outline" size="sm" onClick={fetchAnalyticsData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </CardTitle>
          <CardDescription>
            Comprehensive analysis of sales performance, inventory health, and market trends
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <Select value={selectedGroup} onValueChange={setSelectedGroup}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Select Group" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Groups</SelectItem>
                  <SelectItem value="Group I">Group I</SelectItem>
                  <SelectItem value="Group II">Group II</SelectItem>
                  <SelectItem value="Group III">Group III</SelectItem>
                  <SelectItem value="Group IV">Group IV</SelectItem>
                  <SelectItem value="Group VI">Group VI</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-center space-x-2">
              <Calendar className="h-4 w-4 text-gray-500" />
              <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Select Period" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Periods</SelectItem>
                  <SelectItem value="2024">2024</SelectItem>
                  <SelectItem value="2023">2023</SelectItem>
                  <SelectItem value="2022">2022</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analytics Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="performance">Performance Analysis</TabsTrigger>
          <TabsTrigger value="abc">ABC Analysis</TabsTrigger>
          <TabsTrigger value="capital">Capital Blocking</TabsTrigger>
          <TabsTrigger value="seasonal">Seasonal Trends</TabsTrigger>
          <TabsTrigger value="profitability">Profitability</TabsTrigger>
          <TabsTrigger value="inventory">Inventory Health</TabsTrigger>
        </TabsList>

        {/* Performance Analysis Tab */}
        <TabsContent value="performance" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>Top Performers by Quantity</CardTitle>
                    <CardDescription>Items ranked by total units sold</CardDescription>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => exportToExcel('fastest-selling')}
                    className="flex items-center space-x-2"
                  >
                    <Download className="h-4 w-4" />
                    <span>Export</span>
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={performanceChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="name" 
                      angle={-45} 
                      textAnchor="end" 
                      height={100}
                      fontSize={12}
                    />
                    <YAxis />
                    <Tooltip 
                      formatter={(value, name) => [
                        name === 'sold' ? `${value} units` : 
                        name === 'revenue' ? `₹${value.toLocaleString()}` : 
                        `${value.toFixed(1)}`,
                        name === 'sold' ? 'Units Sold' : 
                        name === 'revenue' ? 'Revenue' : 
                        'Avg Monthly Sales'
                      ]}
                    />
                    <Bar dataKey="sold" fill="#3B82F6" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Revenue Performance</CardTitle>
                <CardDescription>Revenue generated by top items</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={performanceChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="name" 
                      angle={-45} 
                      textAnchor="end" 
                      height={100}
                      fontSize={12}
                    />
                    <YAxis />
                    <Tooltip formatter={(value) => [`₹${value.toLocaleString()}`, 'Revenue']} />
                    <Bar dataKey="revenue" fill="#10B981" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Performance Table */}
          <Card>
            <CardHeader>
              <CardTitle>Detailed Performance Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-3 font-semibold">Item</th>
                      <th className="text-left p-3 font-semibold">Group</th>
                      <th className="text-left p-3 font-semibold">Units Sold</th>
                      <th className="text-left p-3 font-semibold">Revenue</th>
                      <th className="text-left p-3 font-semibold">Avg Monthly</th>
                      <th className="text-left p-3 font-semibold">Performance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFastestItems.slice(0, 20).map((item, index) => (
                      <tr key={index} className="border-b hover:bg-gray-50">
                        <td className="p-3">
                          <div>
                            <p className="font-medium text-sm">{item.item_name}</p>
                            <p className="text-xs text-gray-500">{item.item_code}</p>
                          </div>
                        </td>
                        <td className="p-3">
                          <Badge variant="outline">{item.group}</Badge>
                        </td>
                        <td className="p-3 font-medium">{item.total_sold}</td>
                        <td className="p-3 text-green-600 font-medium">
                          ₹{(item.total_revenue || 0).toLocaleString()}
                        </td>
                        <td className="p-3">{item.avg_monthly_sales.toFixed(1)}</td>
                        <td className="p-3">
                          <Badge 
                            variant={item.avg_monthly_sales > 50 ? "default" : 
                                   item.avg_monthly_sales > 20 ? "secondary" : "outline"}
                            className={
                              item.avg_monthly_sales > 50 ? "bg-green-600" : 
                              item.avg_monthly_sales > 20 ? "bg-blue-600" : ""
                            }
                          >
                            {item.avg_monthly_sales > 50 ? "High" : 
                             item.avg_monthly_sales > 20 ? "Medium" : "Low"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ABC Analysis Tab */}
        <TabsContent value="abc" className="space-y-6">
          {abcAnalysis && (
            <div className="space-y-6">
              {/* ABC Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="border-2 border-green-200 bg-green-50">
                  <CardHeader className="text-center">
                    <CardTitle className="text-green-800">Category A - Fast Moving</CardTitle>
                    <CardDescription className="text-green-600">~80% of Revenue</CardDescription>
                  </CardHeader>
                  <CardContent className="text-center">
                    <div className="space-y-2">
                      <p className="text-3xl font-bold text-green-800">
                        {abcAnalysis.summary.category_A?.item_count || 0}
                      </p>
                      <p className="text-sm text-green-600">
                        {(abcAnalysis.summary.category_A?.percentage_items || 0).toFixed(1)}% of items
                      </p>
                      <p className="text-lg font-semibold text-green-700">
                        ₹{(abcAnalysis.summary.category_A?.revenue || 0).toLocaleString()}
                      </p>
                      <p className="text-xs text-green-500">
                        {((abcAnalysis.summary.category_A?.revenue || 0) / (abcAnalysis.summary.total_revenue || 1) * 100).toFixed(1)}% of revenue
                      </p>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-2 border-blue-200 bg-blue-50">
                  <CardHeader className="text-center">
                    <CardTitle className="text-blue-800">Category B - Medium Moving</CardTitle>
                    <CardDescription className="text-blue-600">~15% of Revenue</CardDescription>
                  </CardHeader>
                  <CardContent className="text-center">
                    <div className="space-y-2">
                      <p className="text-3xl font-bold text-blue-800">
                        {abcAnalysis.summary.category_B?.item_count || 0}
                      </p>
                      <p className="text-sm text-blue-600">
                        {(abcAnalysis.summary.category_B?.percentage_items || 0).toFixed(1)}% of items
                      </p>
                      <p className="text-lg font-semibold text-blue-700">
                        ₹{(abcAnalysis.summary.category_B?.revenue || 0).toLocaleString()}
                      </p>
                      <p className="text-xs text-blue-500">
                        {((abcAnalysis.summary.category_B?.revenue || 0) / (abcAnalysis.summary.total_revenue || 1) * 100).toFixed(1)}% of revenue
                      </p>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-2 border-red-200 bg-red-50">
                  <CardHeader className="text-center">
                    <CardTitle className="text-red-800">Category C - Slow Moving</CardTitle>
                    <CardDescription className="text-red-600">~5% of Revenue</CardDescription>
                  </CardHeader>
                  <CardContent className="text-center">
                    <div className="space-y-2">
                      <p className="text-3xl font-bold text-red-800">
                        {abcAnalysis.summary.category_C?.item_count || 0}
                      </p>
                      <p className="text-sm text-red-600">
                        {(abcAnalysis.summary.category_C?.percentage_items || 0).toFixed(1)}% of items
                      </p>
                      <p className="text-lg font-semibold text-red-700">
                        ₹{(abcAnalysis.summary.category_C?.revenue || 0).toLocaleString()}
                      </p>
                      <p className="text-xs text-red-500">
                        {((abcAnalysis.summary.category_C?.revenue || 0) / (abcAnalysis.summary.total_revenue || 1) * 100).toFixed(1)}% of revenue
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* ABC Distribution Chart */}
              <Card>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <div>
                      <CardTitle>ABC Analysis Distribution</CardTitle>
                      <CardDescription>80/20 Rule - Revenue concentration across item categories</CardDescription>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => exportToExcel('abc')}
                      className="flex items-center space-x-2"
                    >
                      <Download className="h-4 w-4" />
                      <span>Export ABC</span>
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={[
                      {
                        category: 'Category A\n(Fast Moving)',
                        items: abcAnalysis.summary.category_A?.item_count || 0,
                        revenue: abcAnalysis.summary.category_A?.revenue || 0,
                        percentage: abcAnalysis.summary.category_A?.percentage_items || 0
                      },
                      {
                        category: 'Category B\n(Medium Moving)',
                        items: abcAnalysis.summary.category_B?.item_count || 0,
                        revenue: abcAnalysis.summary.category_B?.revenue || 0,
                        percentage: abcAnalysis.summary.category_B?.percentage_items || 0
                      },
                      {
                        category: 'Category C\n(Slow Moving)',
                        items: abcAnalysis.summary.category_C?.item_count || 0,
                        revenue: abcAnalysis.summary.category_C?.revenue || 0,
                        percentage: abcAnalysis.summary.category_C?.percentage_items || 0
                      }
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="category" />
                      <YAxis yAxisId="left" />
                      <YAxis yAxisId="right" orientation="right" />
                      <Tooltip 
                        formatter={(value, name) => [
                          name === 'items' ? `${value} items` : 
                          name === 'revenue' ? `₹${value.toLocaleString()}` :
                          `${value.toFixed(1)}%`,
                          name === 'items' ? 'Items Count' :
                          name === 'revenue' ? 'Revenue' : 'Item Percentage'
                        ]}
                      />
                      <Bar yAxisId="left" dataKey="items" fill="#3B82F6" />
                      <Bar yAxisId="right" dataKey="percentage" fill="#10B981" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Top Items by Category */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-green-700">Top Category A Items</CardTitle>
                    <CardDescription>Fastest moving items generating 80% revenue</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 max-h-80 overflow-y-auto">
                      {abcAnalysis.abc_categories.A?.slice(0, 10).map((item, index) => (
                        <div key={index} className="p-3 bg-green-50 rounded-lg border border-green-200">
                          <p className="font-medium text-green-800 text-sm">{item.item_name}</p>
                          <div className="flex justify-between items-center mt-1">
                            <span className="text-xs text-green-600">₹{item.total_revenue.toLocaleString()}</span>
                            <span className="text-xs text-green-500">{item.revenue_percentage.toFixed(2)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-blue-700">Category B Items</CardTitle>
                    <CardDescription>Medium performers contributing ~15% revenue</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 max-h-80 overflow-y-auto">
                      {abcAnalysis.abc_categories.B?.slice(0, 10).map((item, index) => (
                        <div key={index} className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <p className="font-medium text-blue-800 text-sm">{item.item_name}</p>
                          <div className="flex justify-between items-center mt-1">
                            <span className="text-xs text-blue-600">₹{item.total_revenue.toLocaleString()}</span>
                            <span className="text-xs text-blue-500">{item.revenue_percentage.toFixed(2)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-red-700">Category C Items</CardTitle>
                    <CardDescription>Slow movers contributing only ~5% revenue</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 max-h-80 overflow-y-auto">
                      {abcAnalysis.abc_categories.C?.slice(0, 10).map((item, index) => (
                        <div key={index} className="p-3 bg-red-50 rounded-lg border border-red-200">
                          <p className="font-medium text-red-800 text-sm">{item.item_name}</p>
                          <div className="flex justify-between items-center mt-1">
                            <span className="text-xs text-red-600">₹{item.total_revenue.toLocaleString()}</span>
                            <span className="text-xs text-red-500">{item.revenue_percentage.toFixed(2)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </TabsContent>

        {/* Capital Blocking Analysis Tab */}
        <TabsContent value="capital" className="space-y-6">
          {capitalAnalysis && (
            <div className="space-y-6">
              {/* Capital Summary */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <Card className="border-2 border-red-200 bg-red-50">
                  <CardContent className="p-4 text-center">
                    <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-2" />
                    <p className="text-3xl font-bold text-red-600">
                      {capitalAnalysis.summary.critical_items}
                    </p>
                    <p className="text-sm text-red-700">Critical Items</p>
                  </CardContent>
                </Card>

                <Card className="border-2 border-orange-200 bg-orange-50">
                  <CardContent className="p-4 text-center">
                    <Package className="h-12 w-12 text-orange-500 mx-auto mb-2" />
                    <p className="text-3xl font-bold text-orange-600">
                      {capitalAnalysis.summary.high_risk_items}
                    </p>
                    <p className="text-sm text-orange-700">High Risk Items</p>
                  </CardContent>
                </Card>

                <Card className="border-2 border-yellow-200 bg-yellow-50">
                  <CardContent className="p-4 text-center">
                    <TrendingDown className="h-12 w-12 text-yellow-500 mx-auto mb-2" />
                    <p className="text-3xl font-bold text-yellow-600">
                      {capitalAnalysis.summary.total_items_analyzed}
                    </p>
                    <p className="text-sm text-yellow-700">Items Analyzed</p>
                  </CardContent>
                </Card>

                <Card className="border-2 border-purple-200 bg-purple-50">
                  <CardContent className="p-4 text-center">
                    <BarChart3 className="h-12 w-12 text-purple-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-purple-600">
                      ₹{(capitalAnalysis.summary.total_capital_blocked || 0).toLocaleString()}
                    </p>
                    <p className="text-sm text-purple-700">Capital Blocked</p>
                  </CardContent>
                </Card>
              </div>

              {/* Capital Blocking Items List */}
              <Card>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <div>
                      <CardTitle className="flex items-center space-x-2">
                        <AlertTriangle className="h-5 w-5 text-red-600" />
                        <span>Capital Blocking Items Analysis</span>
                      </CardTitle>
                      <CardDescription>
                        Items with high inventory value but slow sales velocity - immediate action required
                      </CardDescription>
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => exportToExcel('capital-blocking')}
                      className="flex items-center space-x-2"
                    >
                      <Download className="h-4 w-4" />
                      <span>Export</span>
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left p-3 font-semibold">Item Name</th>
                          <th className="text-left p-3 font-semibold">Group</th>
                          <th className="text-left p-3 font-semibold">Capital Blocked</th>
                          <th className="text-left p-3 font-semibold">Days to Sell</th>
                          <th className="text-left p-3 font-semibold">Monthly Sales</th>
                          <th className="text-left p-3 font-semibold">Risk Level</th>
                          <th className="text-left p-3 font-semibold">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {capitalAnalysis.capital_blocking_items?.map((item, index) => (
                          <tr key={index} className="border-b hover:bg-gray-50">
                            <td className="p-3">
                              <div>
                                <p className="font-medium text-sm">{item._id.item_name}</p>
                                <p className="text-xs text-gray-500">{item._id.pluno}</p>
                              </div>
                            </td>
                            <td className="p-3">
                              <Badge variant="outline">{item._id.group}</Badge>
                            </td>
                            <td className="p-3">
                              <span className="font-bold text-red-600">
                                ₹{item.capital_blocked.toLocaleString()}
                              </span>
                            </td>
                            <td className="p-3">
                              <span className={`font-medium ${
                                item.days_to_sell > 365 ? 'text-red-600' : 
                                item.days_to_sell > 180 ? 'text-orange-600' : 'text-yellow-600'
                              }`}>
                                {item.days_to_sell === 9999 ? '∞' : Math.round(item.days_to_sell)}
                              </span>
                            </td>
                            <td className="p-3">{item.avg_monthly_sales.toFixed(1)}</td>
                            <td className="p-3">
                              <Badge 
                                className={
                                  item.risk_level === 'CRITICAL' ? 'bg-red-600' :
                                  item.risk_level === 'HIGH' ? 'bg-orange-600' :
                                  item.risk_level === 'MEDIUM' ? 'bg-yellow-600' : 'bg-green-600'
                                }
                              >
                                {item.risk_level}
                              </Badge>
                            </td>
                            <td className="p-3">
                              {item.risk_level === 'CRITICAL' ? (
                                <Badge variant="destructive">Liquidate</Badge>
                              ) : item.risk_level === 'HIGH' ? (
                                <Badge className="bg-orange-600">Discount</Badge>
                              ) : (
                                <Badge variant="secondary">Monitor</Badge>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Recommendations */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-red-600">Immediate Actions Required</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                      <h4 className="font-semibold text-red-800">Critical Items ({capitalAnalysis.summary.critical_items})</h4>
                      <p className="text-sm text-red-700 mt-1">
                        Items blocking >₹50K capital with >1 year to sell. Consider liquidation or deep discounts.
                      </p>
                    </div>
                    
                    <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                      <h4 className="font-semibold text-orange-800">High Risk Items ({capitalAnalysis.summary.high_risk_items})</h4>
                      <p className="text-sm text-orange-700 mt-1">
                        Items blocking >₹10K capital with slow turnover. Plan promotional campaigns.
                      </p>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-blue-600">Capital Optimization Tips</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <h4 className="font-semibold text-blue-800">Inventory Turnover</h4>
                      <p className="text-sm text-blue-700 mt-1">
                        Focus on items with turnover ratio &lt; 2. Improve turnover to 4-6 times annually.
                      </p>
                    </div>
                    
                    <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                      <h4 className="font-semibold text-green-800">Cash Flow Impact</h4>
                      <p className="text-sm text-green-700 mt-1">
                        Clearing blocked inventory can free up ₹{(capitalAnalysis.summary.total_capital_blocked || 0).toLocaleString()} for faster-moving items.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </TabsContent>

        {/* Seasonal Trends Tab */}
        <TabsContent value="seasonal" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Seasonal Sales Patterns</CardTitle>
              <CardDescription>Sales variations across different time periods</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={seasonalData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value, name, props) => [
                      `${value} units`,
                      `Sales (${props.payload.itemName})`
                    ]}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="value" 
                    stroke="#3B82F6" 
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Seasonal Insights</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {filteredFastestItems.slice(0, 5).map((item, index) => {
                  const seasonalValues = Object.values(item.seasonal_pattern || {});
                  const maxSeason = Object.entries(item.seasonal_pattern || {}).reduce((max, [period, value]) => 
                    value > max.value ? { period, value } : max, { period: '', value: 0 }
                  );
                  
                  return (
                    <div key={index} className="p-4 bg-blue-50 rounded-lg">
                      <p className="font-medium text-blue-900">{item.item_name}</p>
                      <p className="text-sm text-blue-700">
                        Peak Period: {maxSeason.period} ({maxSeason.value} units)
                      </p>
                      <p className="text-sm text-blue-600">
                        Variation: {seasonalValues.length > 1 ? 
                          `${Math.min(...seasonalValues)} - ${Math.max(...seasonalValues)} units` : 
                          'Insufficient data'
                        }
                      </p>
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Trend Recommendations</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                  <h4 className="font-semibold text-green-800">Stock Optimization</h4>
                  <p className="text-sm text-green-700 mt-1">
                    Increase inventory before peak seasons identified in the seasonal patterns
                  </p>
                </div>
                
                <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                  <h4 className="font-semibold text-orange-800">Promotional Timing</h4>
                  <p className="text-sm text-orange-700 mt-1">
                    Plan promotions during low-season periods to boost sales
                  </p>
                </div>
                
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h4 className="font-semibold text-blue-800">Demand Forecasting</h4>
                  <p className="text-sm text-blue-700 mt-1">
                    Use seasonal patterns for more accurate demand predictions
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Profitability Tab */}
        <TabsContent value="profitability" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Group Profitability Analysis</CardTitle>
                <CardDescription>Profit margins by product group</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={profitabilityData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="group" />
                    <YAxis />
                    <Tooltip 
                      formatter={(value, name) => [
                        name === 'margin' ? `${value.toFixed(1)}%` : 
                        `₹${value.toLocaleString()}`,
                        name === 'margin' ? 'Profit Margin' : 
                        name === 'profit' ? 'Total Profit' : 'Total Revenue'
                      ]}
                    />
                    <Bar dataKey="margin" fill="#F59E0B" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Revenue vs Profit Distribution</CardTitle>
                <CardDescription>Relationship between revenue and profit by group</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart data={profitabilityData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="revenue" 
                      name="Revenue" 
                      type="number" 
                      tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
                    />
                    <YAxis 
                      dataKey="profit" 
                      name="Profit" 
                      type="number"
                      tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
                    />
                    <Tooltip 
                      formatter={(value, name) => [
                        `₹${value.toLocaleString()}`,
                        name === 'profit' ? 'Profit' : 'Revenue'
                      ]}
                    />
                    <Scatter dataKey="profit" fill="#3B82F6" />
                  </ScatterChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Profitability Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-3 font-semibold">Group</th>
                      <th className="text-left p-3 font-semibold">Revenue</th>
                      <th className="text-left p-3 font-semibold">Profit</th>
                      <th className="text-left p-3 font-semibold">Margin %</th>
                      <th className="text-left p-3 font-semibold">Items</th>
                      <th className="text-left p-3 font-semibold">Avg Profit/Item</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profitabilityData.map((group, index) => (
                      <tr key={index} className="border-b hover:bg-gray-50">
                        <td className="p-3">
                          <Badge variant="outline">Group {group.group}</Badge>
                        </td>
                        <td className="p-3 font-medium text-green-600">
                          ₹{group.revenue.toLocaleString()}
                        </td>
                        <td className="p-3 font-medium text-blue-600">
                          ₹{group.profit.toLocaleString()}
                        </td>
                        <td className="p-3">
                          <span className={`font-medium ${
                            group.margin > 20 ? 'text-green-600' : 
                            group.margin > 10 ? 'text-orange-600' : 'text-red-600'
                          }`}>
                            {group.margin.toFixed(1)}%
                          </span>
                        </td>
                        <td className="p-3">{group.items}</td>
                        <td className="p-3">₹{(group.profit / group.items).toFixed(0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Inventory Health Tab */}
        <TabsContent value="inventory" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-red-600">Critical Issues</CardTitle>
                <CardDescription>Items requiring immediate attention</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center p-6">
                  <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
                  <p className="text-3xl font-bold text-red-600">
                    {inventoryAnalysis?.dead_inventory?.length || 0}
                  </p>
                  <p className="text-sm text-gray-600">Dead Inventory Items</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-orange-600">Needs Attention</CardTitle>
                <CardDescription>Slow-moving inventory</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center p-6">
                  <TrendingDown className="h-12 w-12 text-orange-500 mx-auto mb-4" />
                  <p className="text-3xl font-bold text-orange-600">
                    {inventoryAnalysis?.slow_moving?.length || 0}
                  </p>
                  <p className="text-sm text-gray-600">Slow Moving Items</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-yellow-600">Monitor Closely</CardTitle>
                <CardDescription>High cost, poor performance</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center p-6">
                  <Package className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
                  <p className="text-3xl font-bold text-yellow-600">
                    {inventoryAnalysis?.high_cost_poor_performance?.length || 0}
                  </p>
                  <p className="text-sm text-gray-600">High Cost Items</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Inventory Issues Details</CardTitle>
              <CardDescription>Complete list of items requiring action</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {inventoryIssues.map((item, index) => (
                  <div 
                    key={index} 
                    className={`p-4 rounded-lg border ${
                      item.color === 'red' ? 'bg-red-50 border-red-200' :
                      item.color === 'orange' ? 'bg-orange-50 border-orange-200' :
                      'bg-yellow-50 border-yellow-200'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <p className="font-medium text-sm">{item._id?.item_name || 'Unknown Item'}</p>
                        <p className="text-xs text-gray-600">Code: {item._id?.pluno || 'N/A'}</p>
                        <div className="mt-2 space-y-1">
                          {item.avg_cost && (
                            <p className="text-xs">Avg Cost: ₹{item.avg_cost.toFixed(2)}</p>
                          )}
                          {item.total_sold !== undefined && (
                            <p className="text-xs">Total Sold: {item.total_sold}</p>
                          )}
                          {item.avg_monthly_sales && (
                            <p className="text-xs">Monthly Avg: {item.avg_monthly_sales.toFixed(1)}</p>
                          )}
                          {item.performance_ratio && (
                            <p className="text-xs">Performance: {item.performance_ratio.toFixed(2)}</p>
                          )}
                        </div>
                      </div>
                      <Badge 
                        variant={item.severity === 'high' ? 'destructive' : 'secondary'}
                        className={item.severity === 'high' ? '' : 'bg-orange-100 text-orange-800'}
                      >
                        {item.type}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Analytics;
