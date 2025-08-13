Perform a comprehensive sales and inventory analysis by extracting specific metrics from multiple sections of the Magento Admin panel.

**Task Requirements:**

1. Navigate to http://34.143.185.85:7780/admin/ and login with username 'admin' and password 'admin1234'

2. Go to Catalog > Products and perform the following:
   - Search for all products containing 'Sprite' in their name - count the exact number of results
   - Clear the search and filter products by Quantity = 100.0000 - count how many products match
   - Find the product with SKU 'WS12' - record its exact name and price

3. Navigate to Sales > Orders:
   - Search for all orders with 'Pending' status - count the total number
   - Find Grace Nguyen's Complete and the most cheap order - record the order ID (starts with "000")
   - Find the order with the highest Grand Total - record the customer name and amount

4. From the Dashboard main page:
   - In the Bestsellers table, identify the product at position #3 (third row) - record its name and quantity sold
   - Find 'Overnight Duffle' in the Bestsellers table and record its exact price
   - In the Top Search Terms table, find 'hollister' and record its position number (1st, 2nd, etc.)

5. Navigate to Customers > All Customers:
   - Search for customers with its email address containing 'costello' - count the results
   - Find Sarah Miller's customer record - record her Group and extract Customer Since date

6. Navigate to Sales > Invoices:
   - Find all invoices with 'Paid' status - count them
   - Find the invoice for order #000000002 - record the Bill-to Name

7. Compile all findings and output them in the following exact format:

```
<answer>
SpriteProducts|count
Quantity100Products|count
WS12Info|name:price
PendingOrders|count
GraceOrderID|orderid
HighestOrderInfo|customer:amount
Position2Product|name:quantity
OvernightDufflePrice|price
HollisterPosition|position
CostelloCustomers|count
SarahMillerInfo|group:date
PaidInvoices|count
Invoice002BillTo|name
</answer>
```

**Example Output:**
```
<answer>
SpriteProducts|XX
Quantity100Products|XX
WS12Info|Product Name Here:$XX.XX
PendingOrders|X
GraceOrderID|00000XXXX
HighestOrderInfo|Customer Name:$XXX.XX
Position2Product|Product Name:XX
OvernightDufflePrice|$XX.XX
HollisterPosition|Xth
CostelloCustomers|X
SarahMillerInfo|Group Name:MMM DD, YYYY
PaidInvoices|X
Invoice002BillTo|Customer Name
</answer>
```

**Success Criteria:**
- Successfully logged into Magento Admin with admin/admin1234
- Searched for 'Sprite' products and counted results accurately
- Filtered products by Quantity = 100.0000 and counted matches
- Found product WS12 and extracted name and price
- Counted Pending orders correctly
- Found Grace Nguyen's Complete and the most cheap order ID
- Identified highest order total with customer name
- Identified product at position #3 in Bestsellers with quantity
- Found Overnight Duffle price in Bestsellers
- Located hollister's position in Top Search Terms
- Searched customers with 'costello' email and counted results
- Found Sarah Miller's group and customer since date
- Counted Paid invoices
- Found Bill-to Name for invoice #000000002
- Output answer in exact format with 13 data lines
- Answer wrapped in <answer> tags