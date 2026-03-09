from neo4j  import GraphDatabase
from typing import List,Dict,Any,Optional
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager

class NodeType(Enum): #Labels for Supplychaingraph(SCG)
    VENDOR = "Vendor"
    FACTORY = "Factory"
    PRODUCT = "Product"
    ROUTE = "Route"
    PORT = "Port"
    WAREHOUSE = "Warehouse"
    EVENT = "Event"

class RelationshipType(Enum): #Relationshipes in SCG
    SUPPLIES_TO = "SUPPLIES_TO"
    PRODUCES = "PRODUCES"
    SHIPS_VIA = "SHIPS_VIA"
    CONNECTS_TO = "CONNECTS_TO"
    STORES = "STORES"
    AFFECTS = "AFFECTS"

@dataclass
class NodeData:
    id:str
    label:NodeType
    name:str
    attributes:Dict[str,Any]

@dataclass
class QueryResult:
    success:bool
    data:List[Dict[str,Any]]
    message:str =""

class SupplyChainGraph:
    """
    1.complete graph build and traverse
    2.RCA/Upstream
    3.Downstream
    4.Bottleneck
    5.Path Finding
    """

    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", 
                 password: str = "password123"):
        
        self.uri=uri
        self.user=user
        self.password=password
        self.driver=None

    def connect(self)->bool:
        try:
            self.driver=GraphDatabase.driver(self.uri,auth=(self.user,self.password))
            with self.driver.session()  as session:
                session.run("RETURN 1")
            print("Connection Success")
            return True
        except Exception as e:
            print("!!!Connection Failed!!!")
            return False
        
    
    def close(self):
        if self.driver:
            self.driver.close()
            print("Connection Closed :)")
    
    @contextmanager
    def session(self):
        if not self.driver:
            raise RuntimeError("NotConnected")
        session=self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def clear_graph(self)->QueryResult:
        query="MATCH (n) DETACH DELETE n"
        try:
            with self.session() as session:
                session.run(query)
            return QueryResult(success=True, data=[], message="Graph cleared successfully")
        except Exception as e:
            return QueryResult(success=False, data=[], message=str(e))
        
    def create_node(self,node:NodeData)->QueryResult:
        props={"id":node.id,"name":node.name,**node.attributes}
        query=f"""
        CREATE(n:{node.label.value} $props)
        return n
        """
        try:
            with self.session() as session:
                result=session.run(query,props=props)
                return QueryResult(success=True,data=[dict(record["n"]) for record in result])
        except Exception as e:
            return QueryResult(success=False,,data=[],message=str(e))
        
    def create_relationship(self,source_id:str,target_id:str,
                            rel_type=RelationshipType)->QueryResult:
        query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        CREATE (source)-[:{rel_type.value}]->(target)
        RETURN source, target
        """
        try:
            with self.session() as session:
                session.run(query, source_id=source_id, target_id=target_id)
            return QueryResult(success=True, data=[], 
                             message=f"Created {rel_type.value} relationship")
        except Exception as e:
            return QueryResult(success=False, data=[], message=str(e))
    
    def build_full_graph(self)->QueryResult:
        print("\n Building Supply Chain Knowledge Graph...")
        self.clear_graph()
        nodes = [
            NodeData("vendor_1", NodeType.VENDOR, "Tata Steel", 
                    {"material": "steel_coil", "sla_adherence": 92, "reliability": 0.88}),
            NodeData("vendor_2", NodeType.VENDOR, "Reliance Industries",
                    {"material": "petrochemicals", "sla_adherence": 88, "reliability": 0.91}),
            NodeData("vendor_3", NodeType.VENDOR, "JSW Steel",
                    {"material": "steel_sheet", "sla_adherence": 95, "reliability": 0.93}),
            
            NodeData("factory_1", NodeType.FACTORY, "Mumbai Plant",
                    {"location": "Mumbai", "status": "operational", "capacity_pct": 85}),
            NodeData("factory_2", NodeType.FACTORY, "Chennai Plant",
                    {"location": "Chennai", "status": "operational", "capacity_pct": 90}),
            NodeData("factory_3", NodeType.FACTORY, "Kolkata Plant",
                    {"location": "Kolkata", "status": "maintenance", "capacity_pct": 40}),
            
            NodeData("product_1", NodeType.PRODUCT, "Steel Coil",
                    {"demand_level": "high", "priority": "critical"}),
            NodeData("product_2", NodeType.PRODUCT, "Petrochemical Products",
                    {"demand_level": "medium", "priority": "standard"}),
            NodeData("product_3", NodeType.PRODUCT, "Steel Sheets",
                    {"demand_level": "high", "priority": "critical"}),
            
            NodeData("route_1", NodeType.ROUTE, "Mumbai-Vizag Sea Route",
                    {"mode": "sea", "status": "active", "transit_time_days": 5}),
            NodeData("route_2", NodeType.ROUTE, "Chennai-Delhi Land Route",
                    {"mode": "land", "status": "disrupted", "transit_time_days": 3}),
            NodeData("route_3", NodeType.ROUTE, "Kolkata-Delhi Rail Route",
                    {"mode": "rail", "status": "active", "transit_time_days": 2}),
            
            NodeData("port_1", NodeType.PORT, "Vizag Port",
                    {"location": "Visakhapatnam", "status": "congested", "throughput": 1200}),
            NodeData("port_2", NodeType.PORT, "Chennai Port",
                    {"location": "Chennai", "status": "operational", "throughput": 800}),
            
            NodeData("warehouse_1", NodeType.WAREHOUSE, "Delhi Hub",
                    {"location": "Delhi", "stock_level": 450, "status": "operational"}),
            NodeData("warehouse_2", NodeType.WAREHOUSE, "Bangalore Hub",
                    {"location": "Bangalore", "stock_level": 280, "status": "operational"}),
            
            NodeData("event_1", NodeType.EVENT, "Cyclone Dana",
                    {"event_type": "weather", "severity": "high", "status": "active"}),
            NodeData("event_2", NodeType.EVENT, "Labor Strike",
                    {"event_type": "industrial", "severity": "medium", "status": "active"}),
        ]
        
        relationships = [
            ("vendor_1", "factory_1", RelationshipType.SUPPLIES_TO),
            ("vendor_2", "factory_2", RelationshipType.SUPPLIES_TO),
            ("vendor_3", "factory_3", RelationshipType.SUPPLIES_TO),
            
            ("factory_1", "product_1", RelationshipType.PRODUCES),
            ("factory_2", "product_2", RelationshipType.PRODUCES),
            ("factory_3", "product_3", RelationshipType.PRODUCES),
            
            ("factory_1", "route_1", RelationshipType.SHIPS_VIA),
            ("factory_2", "route_2", RelationshipType.SHIPS_VIA),
            ("factory_3", "route_3", RelationshipType.SHIPS_VIA),
            
            ("route_1", "port_1", RelationshipType.CONNECTS_TO),
            ("route_2", "port_1", RelationshipType.CONNECTS_TO),  
            ("route_3", "port_2", RelationshipType.CONNECTS_TO),
            
            ("port_1", "warehouse_1", RelationshipType.CONNECTS_TO),
            ("port_2", "warehouse_2", RelationshipType.CONNECTS_TO),
            
            ("warehouse_1", "product_1", RelationshipType.STORES),
            ("warehouse_1", "product_2", RelationshipType.STORES),
            ("warehouse_2", "product_2", RelationshipType.STORES),
            ("warehouse_2", "product_3", RelationshipType.STORES),
            
            ("event_1", "port_1", RelationshipType.AFFECTS),
            ("event_1", "route_2", RelationshipType.AFFECTS),
            ("event_2", "factory_3", RelationshipType.AFFECTS),
        ]

        for node in nodes:
            result=self.create_node(node)
            if not result.success:
                return QueryResult(success=False,data=[],
                                   message=f"Failed to create node {result.message} ")
            
        for source,target,rel_type in relationships:
            result=self.create_relationship(source,target,rel_type)
            if not result.success:
                return QueryResult(success=False,data=[],
                                   message=f"Failed to create reln {result.message} ")
            
        stats=self.get_graph_statistics()
        return QueryResult(
            success=True, 
            data=stats.data,
            message=f"Graph built successfully: {stats.data.get('nodes', 0)} nodes, {stats.data.get('relationships', 0)} relationships"
        )
    

    def get_graph_statistics(self)->QueryResult:
        query = """
        MATCH (n)
        WITH count(n) AS nodeCount
        MATCH ()-[r]->()
        RETURN nodeCount, count(r) AS relationshipCount
        """
        try:
            with self.session() as session:
                result = session.run(query)
                record = result.single()
                return QueryResult(success=True, data={
                    "nodes": record["nodeCount"],
                    "relationships": record["relationshipCount"]
                })
        except Exception as e:
            return QueryResult(success=False, data={}, message=str(e))
        
    