"use client";

import { useState, useEffect, useCallback } from "react";
import TestHistoryList from "@/components/dashboard/TestHistoryList";
import { executionsApi } from "@/lib/api";
import type { TestExecution } from "@/lib/types";
import { useToast } from "@/hooks/use-toast";

export default function DashboardActivityPage() {
  const [executions, setExecutions] = useState<TestExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchHistory = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      // Hits GET /api/tests (list_tests view in Django)
      const data = await executionsApi.list();
      // data.results matches your backend Response({"results": data})
      setExecutions(data.results ?? []);
    } catch (err) {
      console.error("Failed to fetch activity:", err);
      setExecutions([]);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  async function handleDeleteExecution(id: string) {
    if (!confirm("Delete this execution record?")) return;
    try {
      await executionsApi.delete(id);
      setExecutions(prev => prev.filter(e => e.id !== id));
      toast({ title: "Record deleted" });
    } catch (err) {
      toast({ title: "Delete failed", variant: "destructive" });
    }
  }

  return (
    <div className="max-w-6xl p-6">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Activity Log</h1>
        <p className="mt-2 text-gray-600">Review recent test runs and their results.</p>
      </header>

      {/* This component handles the actual table rendering */}
      <TestHistoryList 
        executions={executions} 
        loading={loading} 
        onDelete={handleDeleteExecution}
      />
    </div>
  );
}