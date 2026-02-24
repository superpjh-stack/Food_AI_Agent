/** Legal allergens (22 types) with Korean number mapping */
export const LEGAL_ALLERGENS: Record<string, number> = {
  "난류": 1, "우유": 2, "메밀": 3, "땅콩": 4, "대두": 5,
  "밀": 6, "고등어": 7, "게": 8, "새우": 9, "돼지고기": 10,
  "복숭아": 11, "토마토": 12, "아황산류": 13, "호두": 14,
  "닭고기": 15, "쇠고기": 16, "오징어": 17, "조개류": 18,
  "잣": 19, "쑥": 20, "홍합": 21, "전복": 22,
};

export const ALLERGEN_NAMES: Record<number, string> = Object.fromEntries(
  Object.entries(LEGAL_ALLERGENS).map(([name, num]) => [num, name])
);

export function getAllergenNumber(name: string): number | null {
  return LEGAL_ALLERGENS[name] ?? null;
}

export function getAllergenName(num: number): string {
  return ALLERGEN_NAMES[num] ?? `알레르겐${num}`;
}

export function formatAllergenDisplay(allergens: string[], format: "number" | "text" | "both" = "both"): string {
  if (!allergens.length) return "";
  const mapped = allergens
    .map((a) => ({ name: a, num: LEGAL_ALLERGENS[a] }))
    .filter((a) => a.num !== undefined)
    .sort((a, b) => (a.num ?? 0) - (b.num ?? 0));

  if (format === "number") return mapped.map((a) => a.num).join(".");
  if (format === "text") return mapped.map((a) => a.name).join(", ");
  return mapped.map((a) => `${a.name}(${a.num})`).join(", ");
}
