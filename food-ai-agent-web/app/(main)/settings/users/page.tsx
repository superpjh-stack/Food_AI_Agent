"use client";

import { useEffect, useState } from "react";
import { http } from "@/lib/http";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  site_ids: string[];
  is_active: boolean;
  last_login_at: string | null;
}

const ROLES = ["NUT", "KIT", "QLT", "OPS", "ADM"];

const ROLE_LABELS: Record<string, string> = {
  NUT: "Nutritionist",
  KIT: "Kitchen",
  QLT: "Quality",
  OPS: "Operations",
  ADM: "Admin",
};

const ROLE_COLORS: Record<string, string> = {
  NUT: "bg-blue-100 text-blue-700",
  KIT: "bg-orange-100 text-orange-700",
  QLT: "bg-purple-100 text-purple-700",
  OPS: "bg-teal-100 text-teal-700",
  ADM: "bg-red-100 text-red-700",
};

export default function UsersSettingsPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [roleFilter, setRoleFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ per_page: "100" });
      if (roleFilter) params.set("role", roleFilter);

      const res = await http<{ data: User[] }>(`/users?${params}`);
      const list: User[] = Array.isArray(res) ? res : (res as { data: User[] }).data ?? [];
      setUsers(list);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load users. ADM role required.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleFilter]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">User Management</h1>
        <p className="text-sm text-muted-foreground">
          Manage system users and roles. ADM access required.
        </p>
      </div>

      {/* Role filter tabs */}
      <div className="flex gap-1">
        <button
          onClick={() => setRoleFilter("")}
          className={`rounded-full px-3 py-1 text-sm transition-colors ${
            !roleFilter ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"
          }`}
        >
          All
        </button>
        {ROLES.map((r) => (
          <button
            key={r}
            onClick={() => setRoleFilter(r)}
            className={`rounded-full px-3 py-1 text-sm transition-colors ${
              roleFilter === r ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"
            }`}
          >
            {r}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex h-40 items-center justify-center text-muted-foreground">
          Loading users...
        </div>
      ) : (
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Name</th>
                <th className="px-4 py-3 text-left font-medium">Email</th>
                <th className="px-4 py-3 text-left font-medium">Role</th>
                <th className="px-4 py-3 text-right font-medium">Sites</th>
                <th className="px-4 py-3 text-left font-medium">Last Login</th>
                <th className="px-4 py-3 text-center font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                    No users found
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-muted/20">
                    <td className="px-4 py-3 font-medium">{user.name}</td>
                    <td className="px-4 py-3 text-muted-foreground">{user.email}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          ROLE_COLORS[user.role] ?? "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {ROLE_LABELS[user.role] ?? user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-muted-foreground">
                      {user.site_ids.length}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {user.last_login_at
                        ? new Date(user.last_login_at).toLocaleDateString()
                        : "Never"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          user.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
