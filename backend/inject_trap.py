import pandas as pd

def apply_heuristic_trap():
    df = pd.read_csv("data_advantage/routes.csv")
    
    # We want the classical heuristic to pick W1 -> C1 -> C2 -> C3 -> C4 -> W1
    # Cost = 10 + 10 + 10 + 10 + 1000 = 1040
    # True Optimal: W1 -> C1 -> C4 -> C2 -> C3 -> W1
    # Cost = 10 + 5 + 10 + 10 + 10 = 45
    
    # We need to set specific distances in both directions
    def set_dist(f, t, d):
        df.loc[(df['from_node'] == f) & (df['to_node'] == t), 'distance_km'] = d
        
    nodes = ["W1", "C1", "C2", "C3", "C4"]
    for f in nodes:
        for t in nodes:
            if f != t:
                set_dist(f, t, 500.0) # default high
                
    set_dist("W1", "C1", 10.0)
    set_dist("C1", "C4", 5.0)
    set_dist("C4", "C2", 10.0)
    set_dist("C2", "C3", 10.0)
    set_dist("C3", "W1", 10.0)
    
    # Trap path
    set_dist("C1", "C2", 10.0)
    set_dist("C3", "C4", 10.0)
    set_dist("C4", "W1", 1000.0) 
    
    df.to_csv("data_advantage/routes.csv", index=False)
    print("Injected trap!")

if __name__ == "__main__":
    apply_heuristic_trap()
