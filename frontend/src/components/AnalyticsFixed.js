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
import { formatIndianNumber, formatTableNumber, formatPercentage } from "../utils/numberUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'];

const AnalyticsFixed = () => {
  const [fastestItems, setFastestItems] = useState([]);
  const [groupAnalysis, setGroupAnalysis] = useState([]);
  const [inventoryAnalysis, setInventoryAnalysis] = useState(null);
  const [abcAnalysis, setAbcAnalysis] = useState(null);
  const [capitalAnalysis, setCapitalAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState('all');
  const [selectedPeriod, setSelectedPeriod] = useState('all');
  const [activeTab, setActiveTab] = useState('performance');

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      console.log('Fetching analytics data...');
      
      const [fastestResponse, groupResponse, inventoryResponse, abcResponse, capitalResponse] = await Promise.all([
        fetch(`${API}/fastest-selling-items?limit=20`),
        fetch(`${API}/group-analysis`),
        fetch(`${API}/inventory-analysis`),
        fetch(`${API}/abc-analysis${selectedGroup !== 'all' ? `?group=${selectedGroup}` : ''}`),
        fetch(`${API}/capital-blocking-analysis${selectedGroup !== 'all' ? `?group=${selectedGroup}` : ''}`)
      ]);

      console.log('API responses received:', {
        fastest: fastestResponse.ok,
        groups: groupResponse.ok,
        inventory: inventoryResponse.ok,
        abc: abcResponse.ok,
        capital: capitalResponse.ok
      });

      if (!fastestResponse.ok || !groupResponse.ok || !inventoryResponse.ok) {
        throw new Error(`API Error: Fastest:${fastestResponse.status}, Groups:${groupResponse.status}, Inventory:${inventoryResponse.status}`);
      }

      const fastest = await fastestResponse.json();
      const groups = await groupResponse.json();
      const inventory = await inventoryResponse.json();
      const abc = await abcResponse.json();
      const capital = await capitalResponse.json();
      
      console.log('Data parsed successfully:', {
        fastest: fastest.length,
        groups: groups.length,
        abc: abc.summary?.total_items,
        capital: capital.summary?.total_items_analyzed
      });

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

  const profitabilityData = filteredGroupAnalysis.map(group => ({
    group: group.group.replace('Group ', ''),
    revenue: group.total_revenue || 0,
    profit: group.total_profit || 0,
    margin: group.profit_margin || 0,
    items: group.item_count || 0
  }));

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
        <TabsList className="grid w-full grid-cols-4 bg-white shadow-md rounded-lg p-1 border border-gray-200">
          <TabsTrigger 
            value="performance"
            className="px-4 py-3 rounded-md font-medium transition-all duration-200 hover:bg-blue-50 data-[state=active]:bg-blue-600 data-[state=active]:text-white data-[state=active]:shadow-md"
          >
            Performance Analysis
          </TabsTrigger>
          <TabsTrigger 
            value="abc"
            className="px-4 py-3 rounded-md font-medium transition-all duration-200 hover:bg-green-50 data-[state=active]:bg-green-600 data-[state=active]:text-white data-[state=active]:shadow-md"
          >
            ABC Analysis
          </TabsTrigger>
          <TabsTrigger 
            value="capital"
            className="px-4 py-3 rounded-md font-medium transition-all duration-200 hover:bg-red-50 data-[state=active]:bg-red-600 data-[state=active]:text-white data-[state=active]:shadow-md"
          >
            Capital Blocking
          </TabsTrigger>
          <TabsTrigger 
            value="inventory"
            className="px-4 py-3 rounded-md font-medium transition-all duration-200 hover:bg-orange-50 data-[state=active]:bg-orange-600 data-[state=active]:text-white data-[state=active]:shadow-md"
          >
            Inventory Health
          </TabsTrigger>
        </TabsList>

        {/* Performance Analysis Tab */}
        <TabsContent value="performance" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>Top Performers by Quantity</CardTitle>
                    <CardDescription>Items ranked by total units sold with item codes for identification</CardDescription>
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
                      dataKey="shortName" 
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
                      labelFormatter={(label, payload) => {
                        if (payload && payload[0]) {
                          return `${payload[0].payload.fullName} (${payload[0].payload.itemCode})`;
                        }
                        return '';
                      }}
                    />
                    <Bar dataKey="sold" fill="#3B82F6" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Revenue Performance</CardTitle>
                <CardDescription>Revenue generated by top items showing business impact</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={performanceChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="shortName" 
                      angle={-45} 
                      textAnchor="end" 
                      height={100}
                      fontSize={12}
                    />
                    <YAxis />
                    <Tooltip 
                      formatter={(value) => [`₹${value.toLocaleString()}`, 'Revenue']}
                      labelFormatter={(label, payload) => {
                        if (payload && payload[0]) {
                          return `${payload[0].payload.fullName} (${payload[0].payload.itemCode})`;
                        }
                        return '';
                      }}
                    />
                    <Bar dataKey="revenue" fill="#10B981" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ABC Analysis Tab */}
        <TabsContent value="abc" className="space-y-6">
          {abcAnalysis && (
            <div className="space-y-6">
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
                    </div>
                  </CardContent>
                </Card>
              </div>

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
            </div>
          )}
        </TabsContent>

        {/* Capital Blocking Tab */}
        <TabsContent value="capital" className="space-y-6">
          {capitalAnalysis && (
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle className="flex items-center space-x-2">
                      <AlertTriangle className="h-5 w-5 text-red-600" />
                      <span>Capital Blocking Items Analysis</span>
                    </CardTitle>
                    <CardDescription>
                      Items with high inventory value but slow sales velocity requiring immediate attention
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
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                  <div className="p-4 bg-red-50 rounded-lg text-center">
                    <AlertTriangle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-red-600">
                      {capitalAnalysis.summary.critical_items}
                    </p>
                    <p className="text-sm text-red-700">Critical Items</p>
                  </div>
                  
                  <div className="p-4 bg-orange-50 rounded-lg text-center">
                    <Package className="h-8 w-8 text-orange-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-orange-600">
                      {capitalAnalysis.summary.high_risk_items}
                    </p>
                    <p className="text-sm text-orange-700">High Risk Items</p>
                  </div>
                  
                  <div className="p-4 bg-yellow-50 rounded-lg text-center">
                    <TrendingDown className="h-8 w-8 text-yellow-500 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-yellow-600">
                      {capitalAnalysis.summary.total_items_analyzed}
                    </p>
                    <p className="text-sm text-yellow-700">Items Analyzed</p>
                  </div>
                  
                  <div className="p-4 bg-purple-50 rounded-lg text-center">
                    <BarChart3 className="h-8 w-8 text-purple-500 mx-auto mb-2" />
                    <p className="text-xl font-bold text-purple-600">
                      ₹{(capitalAnalysis.summary.total_capital_blocked || 0).toLocaleString()}
                    </p>
                    <p className="text-sm text-purple-700">Capital Blocked</p>
                  </div>
                </div>

                <div className="space-y-3">
                  {capitalAnalysis.capital_blocking_items?.slice(0, 10).map((item, index) => (
                    <div key={index} className="p-4 bg-gray-50 rounded-lg border">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <span className="text-xs bg-gray-600 text-white px-2 py-1 rounded font-bold">#{index + 1}</span>
                            <Badge 
                              className={
                                item.risk_level === 'CRITICAL' ? 'bg-red-600' :
                                item.risk_level === 'HIGH' ? 'bg-orange-600' :
                                'bg-yellow-600'
                              }
                            >
                              {item.risk_level}
                            </Badge>
                          </div>
                          <p className="font-medium text-sm">
                            {item._id.pluno} - {item._id.item_name}
                          </p>
                          <div className="flex space-x-4 mt-2 text-xs text-gray-600">
                            <span>Capital: ₹{item.capital_blocked.toLocaleString()}</span>
                            <span>Days to Sell: {item.days_to_sell === 9999 ? '∞' : Math.round(item.days_to_sell)}</span>
                            <span>Monthly Sales: {item.avg_monthly_sales.toFixed(1)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Inventory Health Tab */}
        <TabsContent value="inventory" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle className="flex items-center space-x-2">
                    <Package className="h-5 w-5 text-orange-600" />
                    <span>Inventory Health Analysis</span>
                  </CardTitle>
                  <CardDescription>
                    Comprehensive analysis of inventory performance identifying dead stock, slow-moving items
                  </CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => exportToExcel('inventory-health')}
                  className="flex items-center space-x-2"
                >
                  <Download className="h-4 w-4" />
                  <span>Export Inventory</span>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {inventoryAnalysis && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-red-600">Dead Inventory</CardTitle>
                      <CardDescription>Items with no sales but holding stock</CardDescription>
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
                              Capital Blocked: ₹{(item.capital_blocked || 0).toFixed(2)}
                            </p>
                          </div>
                        )) || <p className="text-gray-500 text-sm">No dead inventory found</p>}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-orange-600">Slow Moving</CardTitle>
                      <CardDescription>Items with low sales velocity</CardDescription>
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
                          </div>
                        )) || <p className="text-gray-500 text-sm">No slow moving items found</p>}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-yellow-600">High Cost, Poor Performance</CardTitle>
                      <CardDescription>Expensive items with low sales</CardDescription>
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
                              Performance: {(item.performance_ratio || 0).toFixed(2)}
                            </p>
                          </div>
                        )) || <p className="text-gray-500 text-sm">No items found</p>}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AnalyticsFixed;