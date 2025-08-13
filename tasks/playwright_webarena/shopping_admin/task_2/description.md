Perform a comprehensive products and sales analysis in the Magento Admin panel to identify inventory status and sales performance metrics.

**Task Requirements:**

1. Navigate to http://34.143.185.85:7780/admin/. if need to login, login with username 'admin' and password 'admin1234'

2. Go to Catalog > Products and perform the following:
   - Search for all products containing 'Yoga' in their name - count the exact number of results
   - Clear the search and find the product with SKU 'WH11' - record its exact price
   - Apply a filter to show only products with Quantity = 0.0000 - count how many products match

3. Navigate to the Dashboard and from the Bestsellers table:
   - Identify the product at position #3 (third row) - record the product name and quantity sold
   - Find 'Quest Lumaflex™ Band' in the table - record its exact quantity sold
   - Note the total Revenue amount displayed in the dashboard

4. Go to Customers > All Customers:
   - Find customer 'Sarah Miller' - record her exact email address
   - Count the total number of customers shown in the grid

5. Navigate to Sales > Orders:
   - Count the total number of orders with 'Pending' status
   - Find the order ID of Grace Nguyen's order with the completed status and the most expensive price (starting with "000")

6. Compile all your findings and output them in the following exact format:

```
<answer>
YogaProducts|count
WH11Price|price
ZeroQuantityProducts|count
Position3Product|name:quantity
QuestLumaflexQuantity|quantity
DashboardRevenue|amount
SarahMillerEmail|email
TotalCustomers|count
PendingOrders|count
GraceNguyenOrderID|orderid
</answer>
```

**Example Output:**
```
<answer>
YogaProducts|XX
WH11Price|$XX.XX
ZeroQuantityProducts|XX
Position3Product|Product Name Here:XX
QuestLumaflexQuantity|XX
DashboardRevenue|$XX.XX
SarahMillerEmail|email@example.com
TotalCustomers|XX
PendingOrders|X
GraceNguyenOrderID|00000XXXX
</answer>
```

**Success Criteria:**
- Successfully logged into Magento Admin with admin/admin123
- Searched for 'Yoga' products and counted results accurately
- Found product with SKU 'WH11' and extracted correct price
- Filtered products by zero quantity and counted results
- Identified product at position #3 in Bestsellers with quantity
- Found Quest Lumaflex™ Band quantity in Bestsellers
- Extracted Dashboard revenue amount
- Located Sarah Miller and extracted email address
- Counted total customers in grid
- Counted orders with Pending status
- Found Grace Nguyen's order ID
- Output answer in exact format with 11 data lines
- Answer wrapped in <answer> tags