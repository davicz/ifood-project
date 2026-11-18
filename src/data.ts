export type Ingredient = { id: string; name: string; unit: string; pack: number; price: number };
export type Recipe = { id: string; name: string; description: string; category: string; minutes: number; tag: string; image: string; needs: Record<string, number>; estimate_per_person: number };
export type Need = Ingredient & { quantity: number; packs: number };
export type MarketOption = { id: string; name: string; initials: string; color: string; subtotal: number; freight: number; total: number; minutes: number; missing: string[]; valid: boolean; minimum: number; allocation: string };
export type Plan = { needs: Need[]; shopping: Need[]; estimate: number; options: MarketOption[] };
export type Catalog = { simulated: true; ingredients: Ingredient[]; recipes: Recipe[] };
export const money = (n: number) => n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
export const photo = (id: string, width = 720) => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=${width}&q=80`;
