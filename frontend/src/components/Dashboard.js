import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";
import { Skeleton } from "./ui/skeleton";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from "recharts";
import { TrendingUp, TrendingDown, Package, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'];

const Dashboard = ({ dashboardData, loading }) => {
  const [fastestItems, setFastestItems] = useState([]);
  const [groupAnalysis, setGroupAnalysis] = useState([]);
  const [inventoryAnalysis, setInventoryAnalysis] = useState(null);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      setLoadingData(true);
      
      const [fastestResponse, groupResponse, inventoryResponse] = await Promise.all([
        fetch(`${API}/fastest-selling-items?limit=10`),
        fetch(`${API}/group-analysis`),
        fetch(`${API}/inventory-analysis`)
      ]);

      const fastest = await fastestResponse.json();
      const groups = await groupResponse.json();
      const inventory = await inventoryResponse.json();

      setFastestItems(fastest);
      setGroupAnalysis(groups);
      setInventoryAnalysis(inventory);
    } catch (error) {
      console.error("Error fetching analytics data:", error);
      toast.error("Failed to load analytics data");
    } finally {
      setLoadingData(false);
    }
  };

  if (loading || loadingData) {
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

  const groupChartData = groupAnalysis.map(group => ({
    name: group.group.replace('Group ', ''),
    revenue: group.total_revenue || 0,
    profit: group.total_profit || 0,
    items: group.item_count || 0
  }));

  const topItemsData = fastestItems.slice(0, 8).map(item => ({
    name: item.item_name.substring(0, 20) + (item.item_name.length > 20 ? '...' : ''),
    sold: item.total_sold,
    revenue: item.total_revenue || 0
  }));

  return (
    <div className="space-y-6">
      {/* Group Performance Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>Group-wise Revenue & Profit</span>
            </CardTitle>
            <CardDescription>
              This chart compares revenue (blue bars) and profit (green bars) across all product groups. 
              It helps identify which groups contribute most to business growth and profitability.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={groupChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(value, name) => [
                  `₹${value.toLocaleString()}`,
                  name === 'revenue' ? 'Revenue' : 'Profit'
                ]} />
                <Bar dataKey="revenue" fill="#3B82F6" name="revenue" />
                <Bar dataKey="profit" fill="#10B981" name="profit" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Package className="h-5 w-5" />
              <span>Group Distribution</span>
            </CardTitle>
            <CardDescription>Revenue distribution by product groups</CardDescription>
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
                <Tooltip formatter={(value) => [`₹${value.toLocaleString()}`, 'Revenue']} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Top Selling Items */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5" />
            <span>Top Selling Items</span>
          </CardTitle>
          <CardDescription>Best performing items by quantity sold</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={topItemsData} layout="horizontal">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" width={120} />
              <Tooltip formatter={(value, name) => [
                name === 'sold' ? `${value} units` : `₹${value.toLocaleString()}`,
                name === 'sold' ? 'Units Sold' : 'Revenue'
              ]} />
              <Bar dataKey="sold" fill="#3B82F6" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Inventory Alerts */}
      {inventoryAnalysis && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-red-600">
                <AlertTriangle className="h-5 w-5" />
                <span>Dead Inventory</span>
              </CardTitle>
              <CardDescription>Items with no sales</CardDescription>
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
              <CardTitle className="flex items-center space-x-2 text-orange-600">
                <TrendingDown className="h-5 w-5" />
                <span>Slow Moving</span>
              </CardTitle>
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
              <CardTitle className="flex items-center space-x-2 text-yellow-600">
                <Package className="h-5 w-5" />
                <span>High Cost, Poor Performance</span>
              </CardTitle>
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
                      ₹{(group.total_revenue || 0).toLocaleString()}
                    </td>
                    <td className="p-3 font-medium text-blue-600">
                      ₹{(group.total_profit || 0).toLocaleString()}
                    </td>
                    <td className="p-3">
                      <span className={`font-medium ${
                        (group.profit_margin || 0) > 20 ? 'text-green-600' : 
                        (group.profit_margin || 0) > 10 ? 'text-orange-600' : 'text-red-600'
                      }`}>
                        {(group.profit_margin || 0).toFixed(1)}%
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
    </div>
  );
};

export default Dashboard;
