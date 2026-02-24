"use client";

import { useState } from "react";
import { useCreateClaim } from "@/lib/hooks/use-claims";
import { useSiteStore } from "@/lib/stores/site-store";

const CATEGORIES = ["맛/품질", "이물", "양/분량", "온도", "알레르겐", "위생/HACCP", "서비스", "기타"];
const SEVERITIES = [
  { value: "low", label: "낮음" },
  { value: "medium", label: "보통" },
  { value: "high", label: "높음" },
  { value: "critical", label: "긴급" },
];

interface ClaimRegisterFormProps {
  onSuccess?: (claimId: string) => void;
}

export function ClaimRegisterForm({ onSuccess }: ClaimRegisterFormProps) {
  const siteId = useSiteStore((s) => s.currentSite?.id);
  const { mutate: createClaim, isPending } = useCreateClaim();

  const [form, setForm] = useState({
    incident_date: new Date().toISOString().slice(0, 16),
    category: "맛/품질",
    severity: "medium",
    title: "",
    description: "",
    reporter_name: "",
    reporter_role: "",
    lot_number: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!siteId) return;
    createClaim(
      {
        site_id: siteId,
        incident_date: new Date(form.incident_date).toISOString(),
        category: form.category,
        severity: form.severity,
        title: form.title,
        description: form.description,
        reporter_name: form.reporter_name || undefined,
        reporter_role: form.reporter_role || undefined,
        lot_number: form.lot_number || undefined,
      },
      {
        onSuccess: (data) => {
          onSuccess?.(data.claim_id);
          setForm({
            incident_date: new Date().toISOString().slice(0, 16),
            category: "맛/품질",
            severity: "medium",
            title: "",
            description: "",
            reporter_name: "",
            reporter_role: "",
            lot_number: "",
          });
        },
      }
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-muted-foreground">발생 일시</label>
          <input
            type="datetime-local"
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.incident_date}
            onChange={(e) => setForm({ ...form, incident_date: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">카테고리</label>
          <select
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground">심각도</label>
          <select
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.severity}
            onChange={(e) => setForm({ ...form, severity: e.target.value })}
          >
            {SEVERITIES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-muted-foreground">로트 번호 (선택)</label>
          <input
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.lot_number}
            onChange={(e) => setForm({ ...form, lot_number: e.target.value })}
            placeholder="LOT-2026-001"
          />
        </div>
      </div>
      <div>
        <label className="text-xs text-muted-foreground">제목</label>
        <input
          className="w-full rounded border px-2 py-1 text-sm"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
          placeholder="클레임 요약"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground">상세 내용</label>
        <textarea
          className="w-full rounded border px-2 py-1 text-sm"
          rows={3}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          required
          placeholder="발생 상황을 상세히 기술해주세요"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-muted-foreground">접수자명</label>
          <input
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.reporter_name}
            onChange={(e) => setForm({ ...form, reporter_name: e.target.value })}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">접수자 역할</label>
          <select
            className="w-full rounded border px-2 py-1 text-sm"
            value={form.reporter_role}
            onChange={(e) => setForm({ ...form, reporter_role: e.target.value })}
          >
            <option value="">선택</option>
            {["CS", "OPS", "KIT", "NUT", "QLT"].map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
      </div>
      <button
        type="submit"
        disabled={isPending}
        className="w-full rounded bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
      >
        {isPending ? "접수 중..." : "클레임 접수"}
      </button>
    </form>
  );
}
