import type { Catalog, Plan } from './data';
async function request<T>(path: string, signal: AbortSignal, body?: unknown): Promise<T> {
  const response = await fetch(path, { signal, method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json' } : undefined, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) throw new Error('Não foi possível consultar os dados da compra.');
  return response.json() as Promise<T>;
}
export const getCatalog = (signal: AbortSignal) => request<Catalog>('/api/catalog', signal);
export const getPlan = (signal: AbortSignal, body: { recipe_ids: string[]; servings: number; pantry_ids: string[]; split: boolean; sort: string }) => request<Plan>('/api/plan', signal, body);
