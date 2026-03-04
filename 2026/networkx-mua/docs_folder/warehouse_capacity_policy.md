# Warehouse Capacity Policy

## Stock Level Thresholds
Each warehouse has defined stock thresholds. Minimum stock level: 200 units. Reorder trigger: 250 units. Maximum capacity: Delhi Hub (warehouse_1) holds 800 units, Bangalore Hub (warehouse_2) holds 600 units. When stock drops below minimum, emergency replenishment is triggered.

## Reorder Process
When stock at any warehouse hits the reorder trigger (250 units), an automatic purchase order is generated to the primary vendor. Delhi Hub currently holds 450 units (above threshold). Bangalore Hub currently holds 280 units (near reorder trigger). Reorder quantity is calculated as maximum capacity minus current stock.

## Critical Product Priority
Products marked as "critical" priority (Steel Coil, Steel Sheets) receive preferential warehouse allocation. During capacity constraints, standard priority products (Petrochemical Products) are deprioritized. Critical products must maintain a minimum 30-day supply buffer.

## Warehouse Disruption Handling
If a warehouse status changes to "flooded" or "under_maintenance," all inbound shipments are redirected to the nearest operational warehouse. Cross-warehouse transfers are authorized for critical products without additional approval. Insurance claims for damaged inventory must be filed within 48 hours.

## Inventory Reconciliation
Monthly physical inventory counts are mandatory. Variance above 3% triggers an audit. All product movements between warehouses must be logged with timestamps and authorization codes.