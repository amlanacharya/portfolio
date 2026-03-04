# Shipping Policy: Route Selection and Disruption Protocols

## Route Selection Rules
Routes are selected based on transit time, cost, and reliability. For urgent shipments (under 5 days lead time), prioritize speed over cost. For standard shipments, use the lowest-cost active route. No single route should exceed 70% utilization.

## Weather Disruption Protocol
When a cyclone or severe weather is detected, any route in the affected zone is marked "disrupted." Cargo in transit is held at the nearest port. New shipments are rerouted to the next available active route. If Vizag Port (port_1) is congested, divert to Chennai Port (port_2) at a 12% cost increase.

## Alternative Routing
If route_1 (sea) is disrupted, use route_3 (rail) as backup. If route_2 (land) is disrupted, use route_3 (rail) at an 8% cost premium. All rerouting decisions above 25% cost increase require Supply Chain Director approval.

## Port Congestion Response
When a port status is "congested," notify all shippers within 24 hours. If congestion exceeds 3 days, activate modal shift from sea to rail. If congestion exceeds 7 days, escalate to Supply Chain Director and consider emergency procurement from alternative suppliers.