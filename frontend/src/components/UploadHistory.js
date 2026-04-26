import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Badge } from "./ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Download, RefreshCw, Search, AlertCircle, CheckCircle2, XCircle, Clock, Undo2 } from "lucide-react";
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

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const UploadHistory = ({ onDataChange }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalRecords, setTotalRecords] = useState(0);
  const [statusCounts, setStatusCounts] = useState({ success: 0, failed: 0, partial: 0 });
  const [page, setPage] = useState(0);
  const [limit] = useState(20);
  const [statusFilter, setStatusFilter] = useState("all");
  const [periodSearch, setPeriodSearch] = useState("");
  const [undoDialog, setUndoDialog] = useState({ open: false, record: null });
  const [undoing, setUndoing] = useState(false);

  useEffect(() => {
    fetchStatusCounts();
    fetchHistory();
  }, [page, statusFilter]);

  const fetchStatusCounts = async () => {
    try {
      const [s, f, p] = await Promise.all([
        fetch(`${API}/upload-history?limit=1&skip=0&status_filter=success`).then(r => r.json()),
        fetch(`${API}/upload-history?limit=1&skip=0&status_filter=failed`).then(r => r.json()),
        fetch(`${API}/upload-history?limit=1&skip=0&status_filter=partial`).then(r => r.json()),
      ]);
      setStatusCounts({
        success: s.total || 0,
        failed: f.total || 0,
        partial: p.total || 0,
      });
    } catch (e) {
      // non-critical: counts remain at 0
    }
  };

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        skip: (page * limit).toString()
      });

      if (statusFilter !== "all") {
        params.append("status_filter", statusFilter);
      }
      if (periodSearch) {
        params.append("period_filter", periodSearch);
      }

      const response = await fetch(`${API}/upload-history?${params}`);
      if (!response.ok) throw new Error("Failed to fetch history");

      const data = await response.json();
      setHistory(data.results || []);
      setTotalRecords(data.total || 0);
    } catch (error) {
      console.error("Error fetching upload history:", error);
      toast.error("Failed to load upload history");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(0);
    fetchHistory();
  };

  const handleUndo = async () => {
    if (!undoDialog.record) return;
    
    setUndoing(true);
    try {
      const response = await fetch(`${API}/undo-upload/${undoDialog.record.id}`, {
        method: 'DELETE',
      });

      const result = await response.json();

      if (response.ok) {
        toast.success(`Successfully undone upload: ${undoDialog.record.filename}. Deleted ${result.deleted_count} records.`);
        setUndoDialog({ open: false, record: null });
        fetchStatusCounts();
        fetchHistory();
        if (onDataChange) {
          onDataChange(); // Refresh dashboard
        }
      } else {
        throw new Error(result.detail || 'Undo failed');
      }
    } catch (error) {
      console.error("Error undoing upload:", error);
      toast.error(`Failed to undo upload: ${error.message}`);
    } finally {
      setUndoing(false);
    }
  };

  const formatTimestamp = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
  };

  const exportHistory = () => {
    // Create CSV content
    const headers = [
      "Filename",
      "Upload Date",
      "Period",
      "Data Type",
      "Records",
      "Status",
      "File Size (KB)",
      "Processing Time (s)",
      "Error Message"
    ];

    const csvRows = [headers.join(",")];

    history.forEach(record => {
      const row = [
        `"${record.filename || ''}"`,
        `"${new Date(record.upload_date).toLocaleString()}"`,
        `"${record.period_covered || 'N/A'}"`,
        `"${record.data_type || 'N/A'}"`,
        record.records_count || 0,
        `"${record.status}"`,
        (record.file_size_kb || 0).toFixed(2),
        (record.processing_time_seconds || 0).toFixed(2),
        `"${record.error_message || ''}"`
      ];
      csvRows.push(row.join(","));
    });

    const csvContent = csvRows.join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);

    link.setAttribute("href", url);
    link.setAttribute("download", `upload-history-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast.success("Upload history exported successfully");
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-600" />;
      case "partial":
        return <AlertCircle className="h-4 w-4 text-yellow-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      success: "bg-green-100 text-green-800",
      failed: "bg-red-100 text-red-800",
      partial: "bg-yellow-100 text-yellow-800"
    };

    return (
      <Badge className={variants[status] || "bg-gray-100 text-gray-800"}>
        {status}
      </Badge>
    );
  };

  const totalPages = Math.ceil(totalRecords / limit);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center">
            <Clock className="h-6 w-6 mr-2 text-blue-600" />
            Upload History
          </CardTitle>
          <CardDescription>
            View all data uploads, track status, and monitor for errors
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex flex-wrap gap-4 mb-6">
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block">Filter by Status</label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="partial">Partial</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block">Search by Period</label>
              <div className="flex gap-2">
                <Input
                  placeholder="e.g., 2024-08, 2024"
                  value={periodSearch}
                  onChange={(e) => setPeriodSearch(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                />
                <Button onClick={handleSearch} size="icon">
                  <Search className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="flex gap-2 items-end">
              <Button onClick={fetchHistory} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button onClick={exportHistory} variant="outline" disabled={history.length === 0}>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-sm text-blue-600 font-medium">Total Uploads</div>
              <div className="text-2xl font-bold text-blue-900">{totalRecords}</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="text-sm text-green-600 font-medium">Successful</div>
              <div className="text-2xl font-bold text-green-900">
                {statusCounts.success}
              </div>
            </div>
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <div className="text-sm text-red-600 font-medium">Failed</div>
              <div className="text-2xl font-bold text-red-900">
                {statusCounts.failed}
              </div>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="text-sm text-gray-600 font-medium">Current Page</div>
              <div className="text-2xl font-bold text-gray-900">{page + 1} / {totalPages || 1}</div>
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="text-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
              <p className="text-gray-600">Loading upload history...</p>
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600">No upload history found</p>
              <p className="text-sm text-gray-500 mt-2">Upload some data to see history here</p>
            </div>
          ) : (
            <>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Status</TableHead>
                      <TableHead>Filename</TableHead>
                      <TableHead>Period</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Records</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead>Upload Date</TableHead>
                      <TableHead>Error</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((record, index) => (
                      <TableRow key={record.id || index}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getStatusIcon(record.status)}
                            {getStatusBadge(record.status)}
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">
                          {record.filename?.substring(0, 30)}
                          {record.filename?.length > 30 ? "..." : ""}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{record.period_covered || "N/A"}</Badge>
                        </TableCell>
                        <TableCell>
                          <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                            {record.data_type || "unknown"}
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {(record.records_count || 0).toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-mono text-sm">
                          {(record.file_size_kb || 0).toFixed(1)} KB
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatTimestamp(record.upload_date)}
                        </TableCell>
                        <TableCell>
                          {record.error_message ? (
                            <div className="max-w-xs">
                              <p className="text-xs text-red-600 truncate" title={record.error_message}>
                                {record.error_message}
                              </p>
                            </div>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {record.status === 'success' && record.records_count > 0 && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setUndoDialog({ open: true, record })}
                              className="text-orange-600 hover:text-orange-700 hover:bg-orange-50"
                            >
                              <Undo2 className="h-3 w-3 mr-1" />
                              Undo
                            </Button>
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
                  Showing {page * limit + 1} to {Math.min((page + 1) * limit, totalRecords)} of {totalRecords} records
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                  >
                    Previous
                  </Button>
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
      
      {/* Undo Confirmation Dialog */}
      <AlertDialog open={undoDialog.open} onOpenChange={(open) => setUndoDialog({ ...undoDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-orange-900">Undo Upload?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-700">
              {undoDialog.record && (
                <>
                  <p className="mb-3">
                    This will delete all <strong>{undoDialog.record.records_count} records</strong> uploaded from:
                  </p>
                  <div className="p-3 bg-gray-50 rounded border space-y-2 text-sm">
                    <div><strong>File:</strong> {undoDialog.record.filename}</div>
                    <div><strong>Period:</strong> {undoDialog.record.period_covered || 'N/A'}</div>
                    <div><strong>Uploaded:</strong> {formatTimestamp(undoDialog.record.upload_date)}</div>
                  </div>
                  <p className="mt-3 font-semibold text-orange-700">
                    This action cannot be undone. You will need to re-upload the file if needed.
                  </p>
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleUndo}
              disabled={undoing}
              className="bg-orange-600 hover:bg-orange-700"
            >
              {undoing ? "Undoing..." : "Yes, Undo Upload"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default UploadHistory;
