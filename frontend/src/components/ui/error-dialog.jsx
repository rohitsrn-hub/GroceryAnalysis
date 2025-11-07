import * as React from "react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./alert-dialog"
import { AlertTriangle, X, Info } from "lucide-react"

export function ErrorDialog({ open, onOpenChange, title, message, details }) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <AlertDialogHeader>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-red-100 rounded-full">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <AlertDialogTitle className="text-xl font-semibold text-red-900">
              {title || "Upload Error"}
            </AlertDialogTitle>
          </div>
          <AlertDialogDescription className="text-base text-gray-700 mt-4">
            {message}
          </AlertDialogDescription>
        </AlertDialogHeader>
        
        {details && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center space-x-2 mb-2">
              <Info className="h-4 w-4 text-blue-600" />
              <h4 className="font-semibold text-sm text-gray-900">Error Details:</h4>
            </div>
            <div className="text-sm text-gray-600 space-y-2">
              {typeof details === 'string' ? (
                <p className="whitespace-pre-wrap font-mono text-xs bg-white p-3 rounded border border-gray-200">
                  {details}
                </p>
              ) : (
                <ul className="list-disc list-inside space-y-1">
                  {Array.isArray(details) ? details.map((detail, index) => (
                    <li key={index}>{detail}</li>
                  )) : Object.entries(details).map(([key, value]) => (
                    <li key={key}><strong>{key}:</strong> {value}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
        
        <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h4 className="font-semibold text-sm text-blue-900 mb-2">Required Excel Format:</h4>
          <ul className="text-xs text-blue-800 space-y-1">
            <li>• <strong>Columns:</strong> S.No, GP_Index, pluno, Item_Name, W_Rate, R_Rate, Qty, Refund_Qty, Net_Qty, R_Amt, W_Amt, Profit, O_B, Closing_Stock, Net_Tax</li>
            <li>• <strong>File Types:</strong> .xlsx or .xls files only</li>
            <li>• <strong>Data Period:</strong> Include year/month in filename (e.g., "YR 2024 C.xlsx")</li>
            <li>• <strong>Product Groups:</strong> Items should have group codes (I/, II/, III/, IV/, VI/)</li>
          </ul>
        </div>
        
        <AlertDialogFooter>
          <AlertDialogAction className="bg-red-600 hover:bg-red-700">
            Close
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
