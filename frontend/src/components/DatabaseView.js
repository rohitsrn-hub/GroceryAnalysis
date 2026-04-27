import { apiFetch } from '../utils/api';
import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Badge } from "./ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Download, RefreshCw, Search, Database, Filter, Calendar, Package } from "lucide-react";
import { toast } from "sonner";
import { formatIndianNumber } from "../utils/numberUtils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DatabaseView = () => {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [totalRecords, setTotalRecords] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(50);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [groupFilter, setGroupFilter] = useState("all");
  const [periodFilter, setPeriodFilter] = useState("");
  const [gpIndexNoFilter, setGpIndexNoFilter] = useState("");
  const [aggregated, setAggregated] = useState(false);

  useEffect(() => {
    fetchRecords();
  }, [page, groupFilter, periodFilter, gpIndexNoFilter, aggregated]);

  // Reset page when filters change
  useEffect(() => {
    if (page !== 0) {
      setPage(0);
    }
  }, [groupFilter, periodFilter, searchTerm, gpIndexNoFilter, aggregated]);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        skip: (page * limit).toString()
      });

      if (searchTerm) params.append("search", searchTerm);
      if (groupFilter !== "all") params.append("group_filter", groupFilter);
      if (periodFilter && periodFilter !== "all-periods") params.append("period_filter", periodFilter);
      if (gpIndexNoFilter) params.append("gp_index_no", gpIndexNoFilter);
      if (aggregated) params.append("aggregated", "true");

      const response = await apiFetch(`${API}/database-view?${params}`);
      if (!response.ok) throw new Error("Failed to fetch records");

      const data = await response.json();
      setRecords(data.records || []);
      setTotalRecords(data.total || 0);
      setSummary(data.summary || null);
    } catch (error) {
      console.error("Error fetching database records:", error);
      toast.error("Failed to load database records");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(0);
    fetchRecords();
  };

  const exportToCSV = async () => {
    if (totalRecords === 0) {
      toast.error("No records to export");
      return;
    }

    const toastId = toast.loading(`Fetching ${totalRecords} records for export...`);

    try {
      // Fetch records in chunks (backend limit is 500)
      const chunkSize = 500;
      let allRecords = [];
      let fetchedCount = 0;

      // Fetch in batches
      for (let skip = 0; skip < totalRecords; skip += chunkSize) {
        const params = new URLSearchParams({
          limit: Math.min(chunkSize, totalRecords - skip).toString(),
          skip: skip.toString()
        });

        if (searchTerm) params.append("search", searchTerm);
        if (groupFilter !== "all") params.append("group_filter", groupFilter);
        if (periodFilter && periodFilter !== "all-periods") params.append("period_filter", periodFilter);
        if (gpIndexNoFilter) params.append("gp_index_no", gpIndexNoFilter);
        if (aggregated) params.append("aggregated", "true");

        const response = await apiFetch(`${API}/database-view?${params}`);
        if (!response.ok) throw new Error("Failed to fetch records");

        const data = await response.json();
        const records = data.records || [];
        allRecords = allRecords.concat(records);
        
        fetchedCount += records.length;
        toast.loading(`Fetching records... ${fetchedCount}/${totalRecords}`, { id: toastId });
      }

      if (allRecords.length === 0) {
        toast.error("No records to export", { id: toastId });
        return;
      }

      const headers = [
        "Item Code",
        "Item Name",
        "Product Group",
        "Quantity Sold",
        "Net Quantity",
        "Wholesale Rate",
        "Retail Rate",
        "Wholesale Amount",
        "Retail Amount",
        "Profit",
        "Closing Stock",
        "Opening Balance",
        "Net Tax",
        "Data Period",
        "Upload Date"
      ];

      const csvRows = [headers.join(",")];

      allRecords.forEach(record => {
        // Handle both aggregated and non-aggregated records
        const qty = record.qty || record.total_qty || 0;
        const wAmt = record.w_amt || record.total_w_amt || 0;
        const rAmt = record.r_amt || record.total_r_amt || 0;
        
        // Use latest rates for aggregated view, actual rates for non-aggregated
        const wRate = record.w_rate || record.latest_w_rate || 0;
        const rRate = record.r_rate || record.latest_r_rate || 0;
        
        const row = [
          `"${record.pluno || record.gp_index_no || ''}"`,
          `"${record.item_name || ''}"`,
          `"${record.product_group || ''}"`,
          qty,
          record.net_qty || record.total_net_qty || 0,
          wRate.toFixed(2),
          rRate.toFixed(2),
          wAmt.toFixed(2),
          rAmt.toFixed(2),
          (record.profit || record.total_profit || 0).toFixed(2),
          record.closing_stock || record.avg_closing_stock || 0,
          record.o_b || 0,
          (record.net_tax || 0).toFixed(2),
          `"${record.data_period || (record.periods ? record.periods.join(', ') : '') || ''}"`,
          `"${record.upload_date ? new Date(record.upload_date).toLocaleString() : 'N/A'}"`
        ];
        csvRows.push(row.join(","));
      });

      const csvContent = csvRows.join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);

      link.setAttribute("href", url);
      link.setAttribute("download", `database-export-${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast.success(`Exported ${allRecords.length} records successfully`, { id: toastId });
    } catch (error) {
      console.error("Export error:", error);
      toast.error("Failed to export records", { id: toastId });
    }
  };

  const totalPages = Math.ceil(totalRecords / limit);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center">
            <Database className="h-6 w-6 mr-2 text-cyan-600" />
            Database View
          </CardTitle>
          <CardDescription>
            Browse and analyze all sales records in the database
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Summary Stats */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="p-4 bg-cyan-50 rounded-lg border border-cyan-200">
                <div className="text-sm text-cyan-600 font-medium">Total Records</div>
                <div className="text-2xl font-bold text-cyan-900">
                  {summary.total_records.toLocaleString()}
                </div>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-sm text-blue-600 font-medium">Available Periods</div>
                <div className="text-2xl font-bold text-blue-900">
                  {summary.available_periods?.length || 0}
                </div>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div className="text-sm text-purple-600 font-medium">Product Groups</div>
                <div className="text-2xl font-bold text-purple-900">
                  {summary.available_groups?.length || 0}
                </div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="text-sm text-green-600 font-medium">Date Range</div>
                <div className="text-sm font-medium text-green-900">
                  {summary.date_range?.earliest && summary.date_range?.latest ? (
                    <>
                      {new Date(summary.date_range.earliest).toLocaleDateString()} - {new Date(summary.date_range.latest).toLocaleDateString()}
                    </>
                  ) : "N/A"}
                </div>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-wrap gap-4 mb-6">
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block flex items-center">
                <Search className="h-4 w-4 mr-1" />
                Search Item Name
              </label>
              <div className="flex gap-2">
                <Input
                  placeholder="Search by item name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                />
                <Button onClick={handleSearch} size="icon">
                  <Search className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="w-48">
              <label className="text-sm font-medium mb-2 block flex items-center">
                <Package className="h-4 w-4 mr-1" />
                Product Group
              </label>
              <Select value={groupFilter} onValueChange={setGroupFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Groups</SelectItem>
                  {summary?.available_groups?.filter(group => group && group.trim() !== '').map(group => (
                    <SelectItem key={group} value={group}>{group}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="w-48">
              <label className="text-sm font-medium mb-2 block flex items-center">
                <Calendar className="h-4 w-4 mr-1" />
                Period Filter
              </label>
              <Select value={periodFilter} onValueChange={setPeriodFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Periods" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all-periods">All Periods</SelectItem>
                  {summary?.periods_detailed?.map(period => (
                    <SelectItem key={period.value} value={period.value}>
                      {period.label}
                    </SelectItem>
                  )) || summary?.available_periods?.filter(period => period && period.trim() !== '').map(period => (
                    <SelectItem key={period} value={period}>{period}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block flex items-center">
                <Filter className="h-4 w-4 mr-1" />
                Item Code (Gp_Index_No)
              </label>
              <Input
                placeholder="e.g., 1/001009S"
                value={gpIndexNoFilter}
                onChange={(e) => setGpIndexNoFilter(e.target.value)}
              />
            </div>

            <div className="flex gap-2 items-end">
              <div className="flex items-center space-x-2 px-4 py-2 border rounded-md">
                <input
                  type="checkbox"
                  id="aggregated"
                  checked={aggregated}
                  onChange={(e) => setAggregated(e.target.checked)}
                  className="w-4 h-4 text-cyan-600 rounded focus:ring-cyan-500"
                />
                <label htmlFor="aggregated" className="text-sm font-medium cursor-pointer">
                  Aggregated View
                </label>
              </div>
              <Button onClick={fetchRecords} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button onClick={exportToCSV} variant="outline" disabled={records.length === 0}>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="text-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-cyan-600" />
              <p className="text-gray-600">Loading database records...</p>
            </div>
          ) : records.length === 0 ? (
            <div className="text-center py-12">
              <Database className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600">No records found</p>
              <p className="text-sm text-gray-500 mt-2">Try adjusting your filters or upload some data</p>
            </div>
          ) : (
            <>
              <div className="border rounded-lg overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Item Code</TableHead>
                      <TableHead>Item Name</TableHead>
                      <TableHead>Group</TableHead>
                      <TableHead className="text-right">{aggregated ? "Total Qty" : "Qty"}</TableHead>
                      {!aggregated && <TableHead className="text-right">W. Rate</TableHead>}
                      {!aggregated && <TableHead className="text-right">R. Rate</TableHead>}
                      <TableHead className="text-right">{aggregated ? "Total W. Amt" : "W. Amt"}</TableHead>
                      <TableHead className="text-right">{aggregated ? "Total R. Amt" : "R. Amt"}</TableHead>
                      <TableHead className="text-right">{aggregated ? "Total Profit" : "Profit"}</TableHead>
                      {!aggregated && <TableHead className="text-right">Stock</TableHead>}
                      <TableHead>{aggregated ? "Periods" : "Period"}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {records.map((record, index) => (
                      <TableRow key={record.id || record._id || index}>
                        <TableCell className="font-mono text-xs">
                          {aggregated ? record._id : (record.pluno || record.gp_index_no || "N/A")}
                        </TableCell>
                        <TableCell className="max-w-xs">
                          <div className="truncate" title={record.item_name}>
                            {record.item_name?.substring(0, 40)}
                            {record.item_name?.length > 40 ? "..." : ""}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {record.product_group || "Unknown"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {aggregated ? (record.total_qty || 0) : (record.net_qty || 0)}
                        </TableCell>
                        {!aggregated && (
                          <TableCell className="text-right font-mono text-sm">
                            ₹{(record.w_rate || 0).toFixed(2)}
                          </TableCell>
                        )}
                        {!aggregated && (
                          <TableCell className="text-right font-mono text-sm">
                            ₹{(record.r_rate || 0).toFixed(2)}
                          </TableCell>
                        )}
                        <TableCell className="text-right font-mono text-sm">
                          ₹{aggregated ? (record.total_w_amt || 0).toFixed(2) : (record.w_amt || 0).toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          ₹{aggregated ? (record.total_r_amt || 0).toFixed(2) : (record.r_amt || 0).toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          <span className={(aggregated ? record.total_profit : record.profit) > 0 ? "text-green-600" : "text-red-600"}>
                            ₹{aggregated ? (record.total_profit || 0).toFixed(2) : (record.profit || 0).toFixed(2)}
                          </span>
                        </TableCell>
                        {!aggregated && (
                          <TableCell className="text-right font-mono text-sm">
                            {record.closing_stock || 0}
                          </TableCell>
                        )}
                        <TableCell>
                          {aggregated ? (
                            <div className="text-xs text-gray-600">
                              {record.periods?.length || 0} periods
                            </div>
                          ) : (
                            <Badge className="text-xs">{record.data_period || "N/A"}</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-6">
                <div className="text-sm text-gray-600">
                  Showing {page * limit + 1} to {Math.min((page + 1) * limit, totalRecords)} of {totalRecords.toLocaleString()} records
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                  >
                    Previous
                  </Button>
                  <div className="flex items-center px-4 py-2 bg-gray-100 rounded">
                    Page {page + 1} of {totalPages}
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                    disabled={page >= totalPages - 1}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DatabaseView;
