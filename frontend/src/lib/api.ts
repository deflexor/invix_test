/**
 * Product as returned by GET /api/products (snake_case mirrors the FastAPI contract).
 */
export interface Product {
  id: number;
  name: string;
  image_url: string;
  created_at: string;
}

function getApiUrl(): string {
  const apiUrl = process.env.API_URL;
  if (apiUrl === undefined || apiUrl.length === 0) {
    throw new Error("Environment variable API_URL is not set");
  }
  return apiUrl;
}

export async function getProducts(): Promise<Product[]> {
  const response = await fetch(new URL("/api/products", getApiUrl()), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`GET /api/products failed with status ${response.status}`);
  }
  return (await response.json()) as Product[];
}
