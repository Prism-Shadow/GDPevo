# task_group_007 Environment

This directory contains the shared Northwind Components ERP environment for task_group_007. It uses Python standard library only.

## Generate Data

```bash
python generate_data.py
```

The generator uses fixed seed `7007` and writes JSON fixtures plus `data/manifest.json`.

## Start API

```bash
python server.py --host 127.0.0.1 --port ${PORT:-8007}
```

Or use:

```bash
bash setup.sh start
```

## Domain Endpoints

- `GET /health`
- `GET /products`
- `GET /products/<sku>`
- `GET /customers`
- `GET /customers/<customer_id>`
- `GET /warehouses`
- `GET /inventory?warehouse_id=&sku=`
- `GET /purchase_orders?supplier_id=&sku=&status=`
- `GET /orders?wave=&required_date=&customer_id=`
- `GET /orders/<order_id>`
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
- `GET /suppliers`
- `GET /boms`
- `GET /boms/<bom_id>`
