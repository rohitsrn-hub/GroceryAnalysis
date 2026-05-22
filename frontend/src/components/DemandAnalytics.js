import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import { Skeleton } from "./ui/skeleton";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { TrendingUp, Search, AlertTriangle, CheckCircle, Package, Clock, Filter, Eye, ArrowUpDown, RefreshCw, ShoppingCart, HelpCircle } from "lucide-react";
import { toast } from "sonner";
import { formatIndianNumber, formatPercentage } from "../utils/numberUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
const API = `${BACKEND_URL}/api/customer`;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4'];

export default function DemandAnalytics() {
  const [days, setDays] = useState(30);
  const [searchType, setSearchType] = useState(""); // "" (All), "chat", "list_parse"
  const [popularSearches, setPopularSearches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchFilter, setSearchFilter] = useState("");
  const [sortField, setSortField] = useState("search_count");
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    fetchPopularSearches();
  }, [days, searchType]);

  const fetchPopularSearches = async () => {
    try {
      setLoading(true);
      let url = `${API}/popular-searches?days=${days}&limit=100`;
      if (searchType) {
        url += `&search_type=${searchType}`;
      }
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setPopularSearches(data.popular_searches || []);
      } else {
        throw new Error("Failed to fetch popular searches");
      }
    } catch (error) {
      console.error("Error fetching popular searches:", error);
      toast.error("Failed to load customer demand data");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetchPopularSearches();
      toast.success("Demand data updated");
    } catch (e) {
      // Error handled in fetch
    } finally {
      setRefreshing(false);
    }
  };

  // KPI Calculations
  const totalSearchVolume = popularSearches.reduce((acc, curr) => acc + (curr.search_count || 0), 0);
  
  const weightedAvailabilityRate = totalSearchVolume > 0
    ? (popularSearches.reduce((acc, curr) => acc + (curr.availability_rate * curr.search_count), 0) / totalSearchVolume)
    : 0;

  const totalUniqueQueries = popularSearches.length;

  // High demand but unavailable (stock gap) items
  // Query with at least 2 searches and < 50% availability rate
  const stockGaps = popularSearches.filter(
    (item) => item.availability_rate < 50
  );

  // Sorting & Filtering
  const filteredSearches = popularSearches
    .filter((item) => 
      item.query.toLowerCase().includes(searchFilter.toLowerCase())
    )
    .sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      // Handle strings vs numbers
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }

      if (aVal < bVal) return sortAsc ? -1 : 1;
      if (aVal > bVal) return sortAsc ? 1 : -1;
      return 0;
    });

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  // Chart Data Preparation
  // Top 10 searches
  const topTenData = [...popularSearches]
    .sort((a, b) => b.search_count - a.search_count)
    .slice(0, 10)
    .map((item) => ({
      name: item.query.length > 15 ? item.query.substring(0, 12) + "..." : item.query,
      fullName: item.query,
      "Search Count": item.search_count,
      "Availability %": Math.round(item.availability_rate),
    }));

  // Availability Pie Chart Data
  const availableSearchesCount = popularSearches.reduce(
    (acc, curr) => acc + Math.round((curr.availability_rate / 100) * curr.search_count),
    0
  );
  const unavailableSearchesCount = totalSearchVolume - availableSearchesCount;

  const pieData = [
    { name: "In Stock (Available)", value: availableSearchesCount },
    { name: "Out of Stock / Not Found", value: unavailableSearchesCount }
  ];

  if (loading && popularSearches.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <Skeleton className="h-8 w-64 mb-1" />
            <Skeleton className="h-4 w-96" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-4 w-24 mb-3" />
                <Skeleton className="h-8 w-16 mb-2" />
                <Skeleton className="h-3 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader><Skeleton className="h-6 w-48" /></CardHeader>
            <CardContent><Skeleton className="h-64 w-full" /></CardContent>
          </Card>
          <Card>
            <CardHeader><Skeleton className="h-6 w-48" /></CardHeader>
            <CardContent><Skeleton className="h-64 w-full" /></CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <ShoppingCart className="h-6 w-6 text-[#712ae2]" />
            Customer Demand Analytics
          </h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Monitor popular search queries, shopping lists, and detect stock gaps directly from Sandy interactions.
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Time range select */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-medium text-slate-700">
            <Clock className="h-3.5 w-3.5 text-slate-400" />
            <select 
              value={days} 
              onChange={(e) => setDays(Number(e.target.value))}
              className="bg-transparent border-0 p-0 focus:ring-0 text-xs font-medium cursor-pointer"
            >
              <option value={7}>Last 7 Days</option>
              <option value={15}>Last 15 Days</option>
              <option value={30}>Last 30 Days</option>
              <option value={90}>Last 90 Days</option>
              <option value={365}>Last 1 Year</option>
            </select>
          </div>

          {/* Search type select */}
          <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-medium text-slate-700">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <select 
              value={searchType} 
              onChange={(e) => setSearchType(e.target.value)}
              className="bg-transparent border-0 p-0 focus:ring-0 text-xs font-medium cursor-pointer"
            >
              <option value="">All Interactions</option>
              <option value="chat">Conversational Chat</option>
              <option value="list_parse">Shopping List Checker</option>
            </select>
          </div>

          {/* Refresh button */}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center justify-center p-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-600 transition-colors disabled:opacity-50"
            title="Refresh demand data"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="relative overflow-hidden border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-semibold text-slate-500 tracking-wider uppercase">Total Customer Queries</p>
                <h3 className="text-3xl font-bold text-slate-900 mt-2">
                  {formatIndianNumber(totalSearchVolume)}
                </h3>
              </div>
              <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
                <Search className="h-5 w-5" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-3 font-medium flex items-center gap-1">
              <span>Across all user-submitted keywords & lists</span>
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-semibold text-slate-500 tracking-wider uppercase">Avg. Availability Rate</p>
                <h3 className="text-3xl font-bold text-emerald-600 mt-2">
                  {formatPercentage(weightedAvailabilityRate / 100)}
                </h3>
              </div>
              <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
                <CheckCircle className="h-5 w-5" />
              </div>
            </div>
            <div className="mt-3">
              <Progress value={weightedAvailabilityRate} className="h-1.5 bg-emerald-100" indicatorColor="bg-emerald-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-semibold text-slate-500 tracking-wider uppercase">Unique Product Terms</p>
                <h3 className="text-3xl font-bold text-purple-600 mt-2">
                  {formatIndianNumber(totalUniqueQueries)}
                </h3>
              </div>
              <div className="p-3 bg-purple-50 text-purple-600 rounded-xl">
                <Package className="h-5 w-5" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-3 font-medium">
              Distinct items customers searched for
            </p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-semibold text-slate-500 tracking-wider uppercase">Stock Gap Alerts</p>
                <h3 className="text-3xl font-bold text-red-600 mt-2">
                  {formatIndianNumber(stockGaps.length)}
                </h3>
              </div>
              <div className="p-3 bg-red-50 text-red-600 rounded-xl">
                <AlertTriangle className="h-5 w-5" />
              </div>
            </div>
            <p className="text-xs text-slate-400 mt-3 font-medium">
              Popular searches with low availability (&lt;50%)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Visual Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bar Chart - Top Searched Items */}
        <Card className="lg:col-span-2 border border-slate-100 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Top 10 Popular Search Queries
            </CardTitle>
            <CardDescription>Most frequently queried items and their store availability</CardDescription>
          </CardHeader>
          <CardContent>
            {topTenData.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-[300px] text-slate-400">
                <ShoppingCart className="h-12 w-12 opacity-30 mb-2" />
                <p className="text-sm font-medium">No search query data in this period</p>
              </div>
            ) : (
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topTenData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <YAxis yAxisId="left" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="right" orientation="right" stroke="#10b981" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ background: '#fff', border: '1px solid #f1f5f9', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }} 
                      formatter={(value, name) => [value, name]}
                    />
                    <Legend iconSize={10} iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                    <Bar yAxisId="left" dataKey="Search Count" fill="#712ae2" radius={[4, 4, 0, 0]} barSize={25} />
                    <Bar yAxisId="right" dataKey="Availability %" fill="#10b981" radius={[4, 4, 0, 0]} barSize={25} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pie Chart - Availability Ratio */}
        <Card className="border border-slate-100 shadow-sm">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Overall Availability Rate
            </CardTitle>
            <CardDescription>Percentage of searches matching in-stock items</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center justify-center">
            {totalSearchVolume === 0 ? (
              <div className="flex flex-col items-center justify-center h-[230px] text-slate-400">
                <HelpCircle className="h-12 w-12 opacity-30 mb-2" />
                <p className="text-sm font-medium">No search data</p>
              </div>
            ) : (
              <>
                <div className="h-[230px] w-full flex items-center justify-center relative">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={65}
                        outerRadius={85}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        <Cell fill="#10b981" />
                        <Cell fill="#ef4444" />
                      </Pie>
                      <Tooltip formatter={(value) => [formatIndianNumber(value) + " searches", "Volume"]} />
                    </PieChart>
                  </ResponsiveContainer>
                  
                  {/* Central Text overlay */}
                  <div className="absolute flex flex-col items-center justify-center">
                    <span className="text-2xl font-bold text-slate-800">
                      {Math.round(weightedAvailabilityRate)}%
                    </span>
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                      Available
                    </span>
                  </div>
                </div>

                {/* Pie Chart Legend details */}
                <div className="w-full space-y-2 mt-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="flex items-center gap-1.5 font-medium text-slate-600">
                      <span className="w-2.5 h-2.5 bg-[#10b981] rounded-full"></span>
                      In Stock & Available
                    </span>
                    <span className="font-bold text-slate-800">
                      {formatIndianNumber(availableSearchesCount)} ({Math.round((availableSearchesCount/totalSearchVolume)*100)}%)
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="flex items-center gap-1.5 font-medium text-slate-600">
                      <span className="w-2.5 h-2.5 bg-[#ef4444] rounded-full"></span>
                      Out of Stock / Not Found
                    </span>
                    <span className="font-bold text-slate-800">
                      {formatIndianNumber(unavailableSearchesCount)} ({Math.round((unavailableSearchesCount/totalSearchVolume)*100)}%)
                    </span>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Stock Gaps / Low Availability Priority Panel */}
      <Card className="border border-slate-100 shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base font-bold text-red-700 flex items-center gap-1.5" style={{ fontFamily: 'Outfit, sans-serif' }}>
                <AlertTriangle className="h-4.5 w-4.5 text-red-600" />
                Inventory Stock Gaps & Demand Alerts
              </CardTitle>
              <CardDescription>
                High customer search demand but currently low or zero availability in our records. Prioritize replenishing these!
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {stockGaps.length === 0 ? (
            <div className="text-center py-6 text-slate-500 text-sm font-medium">
              ✓ Good news! No high-demand items are currently experiencing critical stock gaps.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-[220px] overflow-y-auto pr-1">
              {stockGaps.slice(0, 9).map((gap, idx) => (
                <div key={idx} className="p-3 bg-red-50/50 border border-red-100 rounded-xl flex items-center justify-between">
                  <div className="overflow-hidden mr-2">
                    <span className="font-bold text-sm text-slate-800 block truncate">{gap.query}</span>
                    <span className="text-[10px] text-slate-500">
                      Searched <strong className="text-slate-800">{gap.search_count}</strong> times • Category: {gap.categories.filter(Boolean)[0] || 'General'}
                    </span>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <Badge variant="destructive" className="text-[10px] font-bold py-0.5 px-2 bg-red-100 text-red-800 border-red-200">
                      {Math.round(gap.availability_rate)}% Avail.
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Interactive Queries Data Table */}
      <Card className="border border-slate-100 shadow-sm">
        <CardHeader className="pb-3 border-b border-slate-100">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
            <div>
              <CardTitle className="text-base font-bold text-slate-900" style={{ fontFamily: 'Outfit, sans-serif' }}>
                All Customer Search Queries Log
              </CardTitle>
              <CardDescription>Complete record of terms queried by shoppers using the Sandy client.</CardDescription>
            </div>
            
            {/* Search Filter Input */}
            <div className="relative w-full md:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Filter search terms..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-xs focus:ring-1 focus:ring-[#712ae2] focus:border-[#712ae2]"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filteredSearches.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Search className="h-8 w-8 mx-auto opacity-30 mb-2" />
              <p className="text-sm font-medium">No matching search logs found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/75 hover:bg-slate-50/75">
                    <TableHead className="font-semibold text-slate-700 cursor-pointer select-none" onClick={() => handleSort("query")}>
                      <div className="flex items-center gap-1">
                        Search Query <ArrowUpDown className="h-3 w-3" />
                      </div>
                    </TableHead>
                    <TableHead className="font-semibold text-slate-700 cursor-pointer select-none text-center" onClick={() => handleSort("search_count")}>
                      <div className="flex items-center justify-center gap-1">
                        Query Count <ArrowUpDown className="h-3 w-3" />
                      </div>
                    </TableHead>
                    <TableHead className="font-semibold text-slate-700 cursor-pointer select-none text-center" onClick={() => handleSort("availability_rate")}>
                      <div className="flex items-center justify-center gap-1">
                        Availability Rate <ArrowUpDown className="h-3 w-3" />
                      </div>
                    </TableHead>
                    <TableHead className="font-semibold text-slate-700">Filter Department</TableHead>
                    <TableHead className="font-semibold text-slate-700">Database Matches</TableHead>
                    <TableHead className="font-semibold text-slate-700 cursor-pointer select-none text-right" onClick={() => handleSort("last_searched")}>
                      <div className="flex items-center justify-end gap-1">
                        Last Queried <ArrowUpDown className="h-3 w-3" />
                      </div>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredSearches.map((item, idx) => {
                    const isAvailable = item.availability_rate >= 80;
                    const isLowAvailability = item.availability_rate < 50;
                    
                    return (
                      <TableRow key={idx} className="hover:bg-slate-50/50">
                        <TableCell className="font-bold text-slate-800">{item.query}</TableCell>
                        <TableCell className="text-center font-semibold text-slate-900">
                          {formatIndianNumber(item.search_count)}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge 
                            variant="outline" 
                            className={`font-bold ${
                              isAvailable 
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                                : isLowAvailability 
                                  ? 'bg-red-50 text-red-700 border-red-200' 
                                  : 'bg-amber-50 text-amber-700 border-amber-200'
                            }`}
                          >
                            {Math.round(item.availability_rate)}%
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {item.categories.filter(Boolean).length === 0 ? (
                              <span className="text-xs text-slate-400 italic">None</span>
                            ) : (
                              item.categories.filter(Boolean).map((cat, i) => (
                                <Badge key={i} variant="secondary" className="text-[10px] px-2 py-0.5">
                                  {cat}
                                </Badge>
                              ))
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="max-w-xs">
                          {item.matched_items.length === 0 ? (
                            <span className="text-xs text-red-500 font-medium">No Match (Not Found)</span>
                          ) : (
                            <div className="flex flex-wrap gap-1 max-h-12 overflow-y-auto">
                              {item.matched_items.map((dbItem, i) => (
                                <span key={i} className="text-[10px] bg-slate-100 text-slate-700 border border-slate-200 rounded px-1.5 py-0.5 truncate max-w-[120px]" title={dbItem}>
                                  {dbItem}
                                </span>
                              ))}
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="text-right text-xs text-slate-500 font-medium">
                          {new Date(item.last_searched).toLocaleDateString()} {new Date(item.last_searched).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
