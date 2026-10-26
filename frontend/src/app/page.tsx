import { getProducts } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function CatalogPage() {
  const products = await getProducts().catch((error: unknown) => {
    console.error("Failed to load products", error);
    return null;
  });

  return (
    <main>
      <h1>Каталог</h1>
      {products === null ? (
        <p>Не удалось загрузить товары.</p>
      ) : products.length === 0 ? (
        <p>Товаров пока нет.</p>
      ) : (
        <ul>
          {products.map((product) => (
            <li key={product.id}>
              <h2>{product.name}</h2>
              <img src={product.image_url} alt={product.name} width={320} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
