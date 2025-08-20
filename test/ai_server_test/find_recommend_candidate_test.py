from src.shared.db.product.productRepository import ProductRepository
from src.shared.db.util.MysqlUtil import MysqlUtil

if __name__ == "__main__":
    ####
    util = MysqlUtil()
    connection = util.get_connection()
    repository = ProductRepository()
    payload = repository.build_ai_payload(connection=connection)
    ####
    print(f"tax_rate: {payload.tax_rate}\n")

    for idx, p in enumerate(payload.products, 1):
        print(f"[{idx}] product")
        pd = p.model_dump() if hasattr(p, "model_dump") else p.dict()
        periods = (pd.pop("product_period", []) or [])
        for k, v in pd.items():
            print(f"  {k}: {v}")

        if periods:
            print("  product_period:")
            for j, pp in enumerate(periods, 1):
                ppd = pp.model_dump() if hasattr(pp, "model_dump") else (pp.dict() if hasattr(pp, "dict") else pp)
                items = ", ".join(f"{kk}={vv}" for kk, vv in ppd.items())
                print(f"    - #{j} {items}")

        print()
