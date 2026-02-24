// Common types shared across the application

export interface User {
  id: string;
  email: string;
  name: string;
  role: "NUT" | "KIT" | "QLT" | "OPS" | "ADM";
  site_ids: string[];
  is_active: boolean;
}

export interface Site {
  id: string;
  name: string;
  type: string;
  capacity: number;
  address?: string;
  operating_hours?: Record<string, { start: string; end: string }>;
  rules?: Record<string, unknown>;
  is_active: boolean;
}

export interface Item {
  id: string;
  name: string;
  category: string;
  sub_category?: string;
  spec?: string;
  unit: string;
  allergens: string[];
  storage_condition?: string;
  substitute_group?: string;
  nutrition_per_100g?: NutritionInfo;
  is_active: boolean;
}

export interface NutritionInfo {
  kcal: number;
  protein: number;
  fat?: number;
  carbs?: number;
  sodium: number;
  [key: string]: number | undefined;
}

export interface MenuPlan {
  id: string;
  site_id: string;
  title?: string;
  period_start: string;
  period_end: string;
  status: "draft" | "review" | "confirmed" | "archived";
  version: number;
  budget_per_meal?: number;
  target_headcount?: number;
  items: MenuPlanItem[];
}

export interface MenuPlanItem {
  id: string;
  date: string;
  meal_type: "breakfast" | "lunch" | "dinner" | "snack";
  course: string;
  item_name: string;
  recipe_id?: string;
  nutrition?: NutritionInfo;
  allergens: string[];
  sort_order: number;
}

export interface Recipe {
  id: string;
  name: string;
  version: number;
  category?: string;
  sub_category?: string;
  servings_base: number;
  prep_time_min?: number;
  cook_time_min?: number;
  difficulty?: "easy" | "medium" | "hard";
  ingredients: RecipeIngredient[];
  steps: RecipeStep[];
  nutrition_per_serving?: NutritionInfo;
  allergens: string[];
  tags: string[];
}

export interface RecipeIngredient {
  item_id?: string;
  name: string;
  amount: number;
  unit: string;
}

export interface RecipeStep {
  order: number;
  description: string;
  duration_min?: number;
  ccp?: { type: string; target: string; critical: boolean } | null;
}

export interface WorkOrder {
  id: string;
  menu_plan_id: string;
  site_id: string;
  date: string;
  meal_type: string;
  recipe_id: string;
  recipe_name: string;
  scaled_servings: number;
  scaled_ingredients: RecipeIngredient[];
  steps: RecipeStep[];
  seasoning_notes?: string;
  status: "pending" | "in_progress" | "completed";
}

export interface HaccpChecklist {
  id: string;
  site_id: string;
  date: string;
  checklist_type: "daily" | "weekly";
  meal_type?: string;
  template: unknown;
  status: "pending" | "in_progress" | "completed" | "overdue";
}

export interface HaccpRecord {
  id: string;
  checklist_id: string;
  ccp_point: string;
  category?: string;
  target_value?: string;
  actual_value?: string;
  is_compliant?: boolean;
  corrective_action?: string;
}

export interface HaccpIncident {
  id: string;
  site_id: string;
  incident_type: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
  status: "open" | "in_progress" | "resolved" | "closed";
}

// ─── MVP 2: Purchase & Inventory Types ──────────────────────────────────────

export type POStatus = "draft" | "submitted" | "approved" | "received" | "cancelled";
export type BomStatus = "draft" | "ready" | "ordered" | "partial" | "complete";
export type LotStatus = "active" | "partially_used" | "fully_used" | "expired" | "rejected";

export interface Vendor {
  id: string;
  name: string;
  business_no?: string;
  contact: Record<string, string>;
  categories: string[];
  lead_days: number;
  rating: number;
  is_active: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface VendorPrice {
  id: string;
  vendor_id: string;
  item_id: string;
  site_id?: string;
  unit_price: number;
  unit: string;
  currency: string;
  effective_from: string;
  effective_to?: string;
  is_current: boolean;
  source: string;
  created_at: string;
}

export interface BomItem {
  id: string;
  bom_id: string;
  item_id: string;
  item_name: string;
  quantity: number;
  unit: string;
  unit_price?: number;
  subtotal?: number;
  inventory_available: number;
  order_quantity: number;
  preferred_vendor_id?: string;
  source_recipes: Array<{
    recipe_id: string;
    recipe_name: string;
    amount: number;
    unit: string;
  }>;
  notes?: string;
}

export interface Bom {
  id: string;
  menu_plan_id: string;
  site_id: string;
  period_start: string;
  period_end: string;
  headcount: number;
  status: BomStatus;
  total_cost: number;
  cost_per_meal?: number;
  ai_summary?: string;
  generated_by: string;
  created_at: string;
  updated_at: string;
  items?: BomItem[];
}

export interface PurchaseOrderItem {
  id: string;
  po_id: string;
  bom_item_id?: string;
  item_id: string;
  item_name: string;
  spec?: string;
  quantity: number;
  unit: string;
  unit_price: number;
  subtotal: number;
  received_qty: number;
  received_at?: string;
  reject_reason?: string;
}

export interface PurchaseOrder {
  id: string;
  bom_id?: string;
  site_id: string;
  vendor_id: string;
  po_number?: string;
  status: POStatus;
  order_date: string;
  delivery_date: string;
  total_amount: number;
  tax_amount: number;
  note?: string;
  submitted_by?: string;
  submitted_at?: string;
  approved_by?: string;
  approved_at?: string;
  received_at?: string;
  cancelled_at?: string;
  cancel_reason?: string;
  created_at: string;
  updated_at: string;
  items?: PurchaseOrderItem[];
}

export interface Inventory {
  id: string;
  site_id: string;
  item_id: string;
  item_name?: string;
  item_category?: string;
  quantity: number;
  unit: string;
  location?: string;
  min_qty?: number;
  is_low_stock?: boolean;
  last_updated: string;
}

export interface InventoryLot {
  id: string;
  site_id: string;
  item_id: string;
  item_name?: string;
  vendor_id?: string;
  po_id?: string;
  lot_number?: string;
  quantity: number;
  unit: string;
  unit_cost?: number;
  received_at: string;
  expiry_date?: string;
  days_until_expiry?: number;
  storage_temp?: number;
  status: LotStatus;
  inspect_result: Record<string, unknown>;
  used_in_menus: Array<{
    menu_plan_id: string;
    date: string;
    used_qty: number;
  }>;
  created_at: string;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  meta: {
    page: number;
    per_page: number;
    total: number;
  };
}

// Chat types
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tool_calls?: { name: string; input: unknown }[];
  citations?: { title: string; type: string; source?: string }[];
  timestamp: string;
}

export interface SSEEvent {
  type: "text_delta" | "tool_call" | "tool_result" | "citations" | "done";
  content?: string;
  name?: string;
  status?: string;
  data?: unknown;
  sources?: { title: string; type: string }[];
}
